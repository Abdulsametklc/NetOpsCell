import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_publisher import publish_event
from app.models import (
    Badge,
    FaultTypeResolutionCount,
    PersonnelName,
    PointLedger,
    StationResolutionLog,
    UserBadge,
    UserStats,
)
from app.schemas.contracts import BadgeEarned, FaultType, GamePointsAwarded, Level, Priority

# ARCHITECTURE.md SS4.4 SLA sureleri - burada sadece puan hesabi icin (hizli mudahale /
# KRITIK-SLA-icinde bonuslari), Incident Service'in kendi SLA scheduler'indan (CP5) BAGIMSIZ
# statik bir sabit olarak kullanilir; ikisi de ayni case tablosuna dayanir.
SLA_DURATIONS: dict[Priority, timedelta] = {
    Priority.KRITIK: timedelta(hours=1),
    Priority.YUKSEK: timedelta(hours=4),
    Priority.ORTA: timedelta(hours=12),
    Priority.DUSUK: timedelta(hours=48),
}

RESOLVED_BASE_POINTS = 10
FAST_RESOLUTION_BONUS = 5
CRITICAL_WITHIN_SLA_BONUS = 10
PERMANENT_SOLUTION_BONUS = 15
TEMPORARY_SOLUTION_PENALTY = -3
SLA_BREACH_PENALTY = -5
REPEAT_FAULT_PENALTY = -3
REPEAT_FAULT_WINDOW = timedelta(hours=24)

# Case Bolum 6.2 - rozet adi <-> kazanma kosulu eslesmesi ARCHITECTURE.md SS9'da
# gerekcelendirilmis (orijinal PDF tablosu OCR kaymasiyla bozuk geldigi icin isim/kosul
# eslesmesi anlamsal olarak yeniden kuruldu).
FIRST_RESOLUTION_BADGE = ("ilk_mudahale", "Ilk Mudahale", "Ilk arizayi cozme")
SPEED_MASTER_BADGE = ("hiz_ustasi", "Hiz Ustasi", "SLA'nin yarisinda 10 mudahale")
CRISIS_MANAGER_BADGE = ("kriz_yoneticisi", "Kriz Yoneticisi", "10 KRITIK arizayi SLA icinde cozme")
MARATHONER_BADGE = ("maratoncu", "Maratoncu", "Bir gunde 15 ariza cozumu")
EXPERT_BADGE = ("uzman", "Uzman", "Tek turde 50 ariza cozumu")
PERMANENT_FIX_BADGE = ("kalici_cozum", "Kalici Cozum", "20 arizada tekrar olmadan")

SPEED_MASTER_THRESHOLD = 10
CRISIS_MANAGER_THRESHOLD = 10
MARATHONER_DAILY_THRESHOLD = 15
EXPERT_THRESHOLD = 50
PERMANENT_FIX_STREAK_THRESHOLD = 20


def _compute_level(total_points: int) -> Level:
    if total_points >= 3000:
        return Level.PLATIN
    if total_points >= 1500:
        return Level.ALTIN
    if total_points >= 500:
        return Level.GUMUS
    return Level.BRONZ


async def _get_or_create_stats(db: AsyncSession, user_id: uuid.UUID) -> UserStats:
    stats = await db.get(UserStats, user_id)
    if stats is None:
        stats = UserStats(user_id=user_id, total_points=0, resolved_count=0, avg_points=0.0)
        db.add(stats)
        await db.flush()
    return stats


async def _add_points(
    db: AsyncSession, user_id: uuid.UUID, incident_id: uuid.UUID, event_type: str, points: int, reason: str
) -> UserStats:
    db.add(
        PointLedger(user_id=user_id, incident_id=incident_id, event_type=event_type, points=points, reason=reason)
    )
    stats = await _get_or_create_stats(db, user_id)
    stats.total_points += points
    stats.level = _compute_level(stats.total_points)
    await publish_event(
        "game.points_awarded",
        GamePointsAwarded(
            user_id=str(user_id),
            incident_id=str(incident_id),
            points=points,
            reason=reason,
            new_total=stats.total_points,
        ),
    )
    return stats


async def _get_or_create_badge(db: AsyncSession, code: str, name: str, description: str) -> Badge:
    badge = (await db.execute(select(Badge).where(Badge.code == code))).scalar_one_or_none()
    if badge is None:
        badge = Badge(code=code, name=name, description=description)
        db.add(badge)
        await db.flush()
    return badge


async def _award_badge_if_missing(db: AsyncSession, user_id: uuid.UUID, code: str, name: str, description: str) -> None:
    badge = await _get_or_create_badge(db, code, name, description)
    existing = (
        await db.execute(select(UserBadge).where(UserBadge.user_id == user_id, UserBadge.badge_id == badge.id))
    ).scalar_one_or_none()
    if existing is not None:
        return
    earned_at = datetime.now(timezone.utc)
    db.add(UserBadge(user_id=user_id, badge_id=badge.id, earned_at=earned_at))
    await publish_event(
        "badge.earned",
        BadgeEarned(user_id=str(user_id), badge_code=code, earned_at=earned_at),
    )


async def _check_daily_marathoner_badge(db: AsyncSession, user_id: uuid.UUID, now: datetime) -> None:
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    count = (
        await db.execute(
            select(func.count())
            .select_from(PointLedger)
            .where(
                PointLedger.user_id == user_id,
                PointLedger.event_type == "incident.resolved",
                PointLedger.created_at >= day_start,
                PointLedger.created_at < day_end,
            )
        )
    ).scalar_one()
    if count >= MARATHONER_DAILY_THRESHOLD:
        await _award_badge_if_missing(db, user_id, *MARATHONER_BADGE)


async def _increment_fault_type_count(db: AsyncSession, user_id: uuid.UUID, fault_type: FaultType) -> int:
    row = await db.get(FaultTypeResolutionCount, (user_id, fault_type))
    if row is None:
        row = FaultTypeResolutionCount(user_id=user_id, fault_type=fault_type, count=1)
        db.add(row)
        await db.flush()
        return 1
    row.count += 1
    return row.count


async def handle_incident_resolved(db: AsyncSession, event: dict) -> None:
    user_id = uuid.UUID(event["team_id"])
    incident_id = uuid.UUID(event["incident_id"])
    station_code = event["station_code"]
    fault_type = FaultType(event["fault_type"])
    priority = Priority(event["priority"])
    created_at = datetime.fromisoformat(event["created_at"])
    resolved_at = datetime.fromisoformat(event["resolved_at"])

    resolution_time = resolved_at - created_at
    sla_duration = SLA_DURATIONS[priority]

    points = RESOLVED_BASE_POINTS
    reasons = ["Ariza cozuldu"]
    is_fast = resolution_time < sla_duration / 2
    is_critical_within_sla = priority == Priority.KRITIK and resolution_time <= sla_duration

    if is_fast:
        points += FAST_RESOLUTION_BONUS
        reasons.append("Hizli mudahale bonusu")
    if is_critical_within_sla:
        points += CRITICAL_WITHIN_SLA_BONUS
        reasons.append("KRITIK ariza SLA icinde cozuldu")

    stats = await _add_points(db, user_id, incident_id, "incident.resolved", points, "; ".join(reasons))
    stats.resolved_count += 1
    stats.avg_points = stats.total_points / stats.resolved_count
    stats.clean_resolution_streak += 1
    if is_fast:
        stats.fast_resolution_count += 1
    if is_critical_within_sla:
        stats.critical_within_sla_count += 1

    # "Bu istasyonun en son cozumu bu kullanicidir" kaydini guncelle - tekrar ariza tespiti
    # (handle_incident_created) bunu okuyacak.
    log = await db.get(StationResolutionLog, station_code)
    if log is None:
        db.add(StationResolutionLog(station_code=station_code, user_id=user_id, resolved_at=resolved_at))
    else:
        log.user_id = user_id
        log.resolved_at = resolved_at

    fault_type_count = await _increment_fault_type_count(db, user_id, fault_type)

    if stats.resolved_count == 1:
        await _award_badge_if_missing(db, user_id, *FIRST_RESOLUTION_BADGE)
    if stats.fast_resolution_count >= SPEED_MASTER_THRESHOLD:
        await _award_badge_if_missing(db, user_id, *SPEED_MASTER_BADGE)
    if stats.critical_within_sla_count >= CRISIS_MANAGER_THRESHOLD:
        await _award_badge_if_missing(db, user_id, *CRISIS_MANAGER_BADGE)
    if fault_type_count >= EXPERT_THRESHOLD:
        await _award_badge_if_missing(db, user_id, *EXPERT_BADGE)
    if stats.clean_resolution_streak >= PERMANENT_FIX_STREAK_THRESHOLD:
        await _award_badge_if_missing(db, user_id, *PERMANENT_FIX_BADGE)
    await _check_daily_marathoner_badge(db, user_id, resolved_at)

    await db.commit()


async def handle_incident_created(db: AsyncSession, event: dict) -> None:
    """Tekrar eden ariza tespiti (case Bolum 6.1): ayni istasyonda 24 saat icinde ikinci
    arizanin acilmasi, onceki cozumu yapan teknisyene -3 ceza olarak yansir ve o kisinin
    "Kalici Cozum" rozeti icin biriktirdigi temiz-cozum serisini sifirlar."""
    station_code = event["station_code"]
    created_at = datetime.fromisoformat(event["created_at"])

    log = await db.get(StationResolutionLog, station_code)
    if log is None:
        return
    if created_at - log.resolved_at > REPEAT_FAULT_WINDOW:
        return

    incident_id = uuid.UUID(event["incident_id"])
    stats = await _add_points(
        db,
        log.user_id,
        incident_id,
        "incident.created",
        REPEAT_FAULT_PENALTY,
        "Tekrar eden ariza (24 saat icinde ayni istasyon)",
    )
    stats.clean_resolution_streak = 0
    await db.commit()


async def handle_incident_evaluated(db: AsyncSession, event: dict) -> None:
    """incident.evaluated event'i cozumu yapan kisinin kimligini tasimiyor (bkz.
    docs/CONTRACTS.md) - bu yuzden ilgili incident_id'nin "incident.resolved" point_ledger
    kaydindan cozumu yapan kullaniciyi buluyoruz."""
    incident_id = uuid.UUID(event["incident_id"])
    is_permanent = bool(event["is_permanent"])

    entry = (
        await db.execute(
            select(PointLedger).where(
                PointLedger.incident_id == incident_id, PointLedger.event_type == "incident.resolved"
            )
        )
    ).scalar_one_or_none()
    if entry is None:
        return

    points = PERMANENT_SOLUTION_BONUS if is_permanent else TEMPORARY_SOLUTION_PENALTY
    reason = "Kalici cozum (5 yildiz)" if is_permanent else "Gecici cozum"
    await _add_points(db, entry.user_id, incident_id, "incident.evaluated", points, reason)
    await db.commit()


async def handle_sla_breached(db: AsyncSession, event: dict) -> None:
    team_id = event.get("team_id")
    if not team_id:
        return  # atanmamis vaka - cezalandirilacak kimse yok
    user_id = uuid.UUID(team_id)
    incident_id = uuid.UUID(event["incident_id"])
    await _add_points(db, user_id, incident_id, "incident.sla_breached", SLA_BREACH_PENALTY, "SLA asimi")
    await db.commit()


async def handle_personnel_upserted(db: AsyncSession, event: dict) -> None:
    """identity.personnel.upserted -> personnel_name read-model cache'ini gunceller
    (ai-service'in team_profile'i ile ayni desen). Bu event su an sadece
    SAHA_TEKNISYENI icin yayinlaniyor (identity-service), ki zaten liderlik
    tablosunda gorunecek tek rol de bu (puanlar sadece cozen teknisyene yazilir)."""
    user_id = uuid.UUID(event["user_id"])
    name = event["name"]

    cache = await db.get(PersonnelName, user_id)
    if cache is None:
        db.add(PersonnelName(user_id=user_id, name=name))
    else:
        cache.name = name
    await db.commit()
