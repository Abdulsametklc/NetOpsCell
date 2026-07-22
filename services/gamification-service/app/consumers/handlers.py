import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Badge, PointLedger, UserBadge, UserStats
from app.schemas.contracts import Level, Priority

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

FIRST_RESOLUTION_BADGE = ("ilk_mudahale", "Ilk Mudahale", "Ilk arizayi cozme")


def _compute_level(total_points: int) -> Level:
    if total_points >= 3000:
        return Level.PLATIN
    if total_points >= 1500:
        return Level.ALTIN
    if total_points >= 500:
        return Level.GUMUS
    return Level.BRONZ


async def _get_or_create_badge(db: AsyncSession, code: str, name: str, description: str) -> Badge:
    badge = (await db.execute(select(Badge).where(Badge.code == code))).scalar_one_or_none()
    if badge is None:
        badge = Badge(code=code, name=name, description=description)
        db.add(badge)
        await db.flush()
    return badge


async def _award_badge_if_missing(db: AsyncSession, user_id: uuid.UUID, badge: Badge) -> bool:
    existing = (
        await db.execute(select(UserBadge).where(UserBadge.user_id == user_id, UserBadge.badge_id == badge.id))
    ).scalar_one_or_none()
    if existing is not None:
        return False
    db.add(UserBadge(user_id=user_id, badge_id=badge.id))
    return True


async def _check_first_resolution_badge(db: AsyncSession, user_id: uuid.UUID, stats: UserStats) -> None:
    if stats.resolved_count != 1:
        return
    code, name, description = FIRST_RESOLUTION_BADGE
    badge = await _get_or_create_badge(db, code, name, description)
    awarded = await _award_badge_if_missing(db, user_id, badge)
    if awarded:
        # TODO (CP5+/Notification Hub): badge.earned event yayinla (bkz. docs/CONTRACTS.md).
        pass


async def handle_incident_resolved(db: AsyncSession, event: dict) -> None:
    user_id = uuid.UUID(event["team_id"])
    incident_id = uuid.UUID(event["incident_id"])
    priority = Priority(event["priority"])
    created_at = datetime.fromisoformat(event["created_at"])
    resolved_at = datetime.fromisoformat(event["resolved_at"])

    resolution_time = resolved_at - created_at
    sla_duration = SLA_DURATIONS[priority]

    points = RESOLVED_BASE_POINTS
    reasons = ["Ariza cozuldu"]

    if resolution_time < sla_duration / 2:
        points += FAST_RESOLUTION_BONUS
        reasons.append("Hizli mudahale bonusu")

    if priority == Priority.KRITIK and resolution_time <= sla_duration:
        points += CRITICAL_WITHIN_SLA_BONUS
        reasons.append("KRITIK ariza SLA icinde cozuldu")

    db.add(
        PointLedger(
            user_id=user_id,
            incident_id=incident_id,
            event_type="incident.resolved",
            points=points,
            reason="; ".join(reasons),
        )
    )

    stats = await db.get(UserStats, user_id)
    if stats is None:
        stats = UserStats(user_id=user_id, total_points=0, resolved_count=0, avg_points=0.0)
        db.add(stats)
        await db.flush()

    stats.total_points += points
    stats.resolved_count += 1
    stats.avg_points = stats.total_points / stats.resolved_count
    stats.level = _compute_level(stats.total_points)

    await _check_first_resolution_badge(db, user_id, stats)
    await db.commit()
