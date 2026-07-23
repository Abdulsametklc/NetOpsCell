import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_client import AIServiceUnavailable, assign, predict
from app.core.auth import CurrentUser, get_current_user, require_roles
from app.core.database import get_db
from app.core.event_publisher import publish_event
from app.core.sequence import generate_incident_number
from app.core.sla import SLA_DURATIONS
from app.core.state_machine import (
    SYSTEM_ACTOR_ID,
    InvalidTransition,
    UnauthorizedTransition,
    validate_transition,
)
from app.models.incident import (
    Incident,
    IncidentEvaluation,
    IncidentMessage,
    IncidentResolutionNote,
    IncidentStatusHistory,
    TelemetryReading,
)
from app.schemas.contracts import (
    AssignRequest,
    FaultType,
    IncidentAssigned,
    IncidentCreated,
    IncidentEvaluated,
    IncidentResolved,
    IncidentStatus,
    IncidentTypeChanged,
    Priority,
    Suggestion,
    TelemetryInput,
)
from app.schemas.incident import (
    CustomerReportCreate,
    EvaluationCreate,
    FaultTypeChangeRequest,
    ManualAssignRequest,
    MessageCreate,
    ResolutionNoteCreate,
    StatusChangeRequest,
)

router = APIRouter(prefix="/api/v1", tags=["incidents"])

MESSAGING_ROLES = {"SAHA_TEKNISYENI", "NOC_OPERATORU"}
MANUAL_ASSIGN_ROLES = {"SUPERVIZOR", "ADMIN"}
FAULT_TYPE_OVERRIDE_ROLES = {"NOC_OPERATORU", "SUPERVIZOR"}
DASHBOARD_ROLES = ["SUPERVIZOR", "ADMIN"]
STAFF_ROLES = ["SAHA_TEKNISYENI", "NOC_OPERATORU", "SUPERVIZOR", "ADMIN"]
TERMINAL_STATUSES = (IncidentStatus.COZULDU, IncidentStatus.KAPANDI)
TR_WEEKDAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]


def _incident_summary(incident: Incident) -> dict:
    return {
        "id": str(incident.id),
        "incident_number": incident.incident_number,
        "station_code": incident.station_code,
        "current_status": incident.current_status,
        "fault_type": incident.fault_type,
        "priority": incident.priority,
        "probability": incident.probability,
        "ai_suggestion": incident.ai_suggestion,
        "assigned_team_id": str(incident.assigned_team_id) if incident.assigned_team_id else None,
        "assigned_team_name": incident.assigned_team_name,
        "sla_due_at": incident.sla_due_at.isoformat() if incident.sla_due_at else None,
        "sla_status": incident.sla_status,
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
        "customer_description": incident.customer_description,
    }


async def _create_incident(
    db: AsyncSession,
    reading: TelemetryReading,
    *,
    fault_type: FaultType,
    priority: Priority,
    probability: float | None,
    ai_suggestion: Suggestion | None,
) -> Incident:
    incident_number = await generate_incident_number(db)
    now = datetime.now(timezone.utc)
    incident = Incident(
        incident_number=incident_number,
        station_code=reading.station_code,
        lat=reading.lat,
        lng=reading.lng,
        current_status=IncidentStatus.YENI,
        fault_type=fault_type,
        priority=priority,
        probability=probability,
        ai_suggestion=ai_suggestion,
        sla_due_at=now + SLA_DURATIONS[priority],
    )
    db.add(incident)
    await db.flush()
    reading.incident_id = incident.id

    await publish_event(
        "incident.created",
        IncidentCreated(
            incident_id=str(incident.id),
            incident_number=incident.incident_number,
            station_code=incident.station_code,
            fault_type=fault_type,
            priority=priority,
            probability=probability or 0.0,
            created_at=now,
        ),
    )
    return incident


async def _attempt_auto_assign(db: AsyncSession, incident: Incident) -> None:
    """AI Service'in /assign'ini cagirir, uygun ekip bulunursa YENI->ATANDI'ya gecirir ve
    incident.assigned event'i yayinlar. AI Service'e ulasilamazsa ya da kapasite yoksa vaka
    YENI/atanmamis kalir - manuel atama kuyruguna duser (bkz. ARCHITECTURE.md SS7)."""
    try:
        response = await assign(
            AssignRequest(
                incident_id=str(incident.id),
                incident_number=incident.incident_number,
                fault_type=incident.fault_type,
                priority=incident.priority,
                lat=incident.lat,
                lng=incident.lng,
            )
        )
    except AIServiceUnavailable:
        return

    if response.queued or response.team_id is None:
        return

    validate_transition(
        from_status=incident.current_status,
        to_status=IncidentStatus.ATANDI,
        actor_role="SYSTEM",
        actor_user_id=SYSTEM_ACTOR_ID,
        assigned_team_id=incident.assigned_team_id,
    )

    score = response.score or 0.0
    history = IncidentStatusHistory(
        incident_id=incident.id,
        from_status=incident.current_status,
        to_status=IncidentStatus.ATANDI,
        changed_by=SYSTEM_ACTOR_ID,
        note=f"AI otomatik atama (skor: {score:.2f})",
    )
    db.add(history)

    incident.assigned_team_id = uuid.UUID(response.team_id)
    incident.assigned_team_name = response.team_name
    incident.current_status = IncidentStatus.ATANDI
    await db.flush()

    await publish_event(
        "incident.assigned",
        IncidentAssigned(
            incident_id=str(incident.id),
            team_id=response.team_id,
            team_name=response.team_name or "",
            score=score,
            assigned_by="SYSTEM",
            assigned_at=datetime.now(timezone.utc),
        ),
    )


@router.post("/telemetry", status_code=status.HTTP_201_CREATED)
async def submit_telemetry(payload: TelemetryInput, db: AsyncSession = Depends(get_db)):
    reading = TelemetryReading(
        station_code=payload.station_code,
        lat=payload.lat,
        lng=payload.lng,
        signal_strength=payload.signal_strength,
        packet_loss=payload.packet_loss,
        temperature=payload.temperature,
        power_status=payload.power_status,
        raw_payload=payload.model_dump(mode="json"),
    )
    db.add(reading)
    await db.flush()

    try:
        prediction = await predict(payload)
    except AIServiceUnavailable:
        # Case kurali: AI Service'e ulasilamiyorsa vaka yine de acilir (BELIRSIZ/ORTA) ve
        # manuel atama kuyruguna duser (atama denemesi bile yapilmaz - tur bilinmiyor).
        incident = await _create_incident(
            db,
            reading,
            fault_type=FaultType.BELIRSIZ,
            priority=Priority.ORTA,
            probability=None,
            ai_suggestion=None,
        )
        await db.commit()
        await db.refresh(incident)
        return {
            "success": True,
            "data": {
                "telemetry_id": str(reading.id),
                "ai_available": False,
                "incident": _incident_summary(incident),
            },
            "error": None,
        }

    if prediction.suggestion == Suggestion.IZLE:
        # Olasilik dusuk: sadece izleniyor, vaka acilmiyor.
        await db.commit()
        return {
            "success": True,
            "data": {
                "telemetry_id": str(reading.id),
                "ai_available": True,
                "incident": None,
                "prediction": prediction.model_dump(),
            },
            "error": None,
        }

    incident = await _create_incident(
        db,
        reading,
        fault_type=prediction.fault_type,
        priority=prediction.priority,
        probability=prediction.probability,
        ai_suggestion=prediction.suggestion,
    )
    await _attempt_auto_assign(db, incident)
    await db.commit()
    await db.refresh(incident)
    return {
        "success": True,
        "data": {
            "telemetry_id": str(reading.id),
            "ai_available": True,
            "incident": _incident_summary(incident),
        },
        "error": None,
    }


@router.get("/incidents")
async def list_incidents(
    current_user: CurrentUser = Depends(require_roles(STAFF_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """CP6: rol bazli scope (case SS3.3 - Saha Teknisyeni sadece kendine atanan
    vakalari gorur, NOC/Supervizor/Admin tumunu gorur). Musteri rolunun bu
    endpoint'te hicbir yetkisi yok (yetki matrisinde sadece "arıza oluşturma" var)."""
    query = select(Incident)
    if current_user.role == "SAHA_TEKNISYENI":
        query = query.where(Incident.assigned_team_id == current_user.user_id)
    result = await db.execute(query.order_by(Incident.created_at.desc()))
    incidents = result.scalars().all()
    return {"success": True, "data": [_incident_summary(i) for i in incidents], "error": None}


@router.post("/incidents/report", status_code=status.HTTP_201_CREATED)
async def report_incident(
    payload: CustomerReportCreate,
    current_user: CurrentUser = Depends(require_roles(["MUSTERI"])),
    db: AsyncSession = Depends(get_db),
):
    """Case SS3.3 yetki matrisi: 'Arıza oluşturma' sadece Müşteri'nin hakkı. Telemetri/AI
    boru hattından tamamen bağımsız - müşteri kendi yaşadığı sorunu bildirir, konum/teknik
    veri bilmedigi icin lat/lng yok, fault_type BELIRSIZ ve öncelik ORTA ile manuel atama
    kuyruğuna düşer (NOC/Süpervizör triaj eder, mevcut fault-type-override ve manuel atama
    akışlarıyla devam eder)."""
    incident_number = await generate_incident_number(db)
    now = datetime.now(timezone.utc)
    incident = Incident(
        incident_number=incident_number,
        station_code="MUSTERI-BILDIRIMI",
        current_status=IncidentStatus.YENI,
        fault_type=FaultType.BELIRSIZ,
        priority=Priority.ORTA,
        sla_due_at=now + SLA_DURATIONS[Priority.ORTA],
        created_by=current_user.user_id,
        customer_description=payload.description,
    )
    db.add(incident)
    await db.flush()
    await db.commit()
    await db.refresh(incident)

    await publish_event(
        "incident.created",
        IncidentCreated(
            incident_id=str(incident.id),
            incident_number=incident.incident_number,
            station_code=incident.station_code,
            fault_type=FaultType.BELIRSIZ,
            priority=Priority.ORTA,
            probability=0.0,
            created_at=now,
        ),
    )

    return {"success": True, "data": _incident_summary(incident), "error": None}


@router.get("/incidents/mine")
async def list_my_incidents(
    current_user: CurrentUser = Depends(require_roles(["MUSTERI"])),
    db: AsyncSession = Depends(get_db),
):
    """Case SS3.3: 'Kendi kayıtlarını görme' - Müşteri sadece kendi bildirdiği arızaları görür."""
    result = await db.execute(
        select(Incident).where(Incident.created_by == current_user.user_id).order_by(Incident.created_at.desc())
    )
    incidents = result.scalars().all()
    return {"success": True, "data": [_incident_summary(i) for i in incidents], "error": None}


@router.get("/incidents/queue/unassigned")
async def unassigned_queue(
    current_user: CurrentUser = Depends(require_roles(DASHBOARD_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Case Bolum 5.3: kapasite/tur eslesmesi bulunamadigi ya da AI erisilemedigi icin
    otomatik atanamamis vakalar - Supervizor burada manuel atama yapar. Dashboard
    goruntuleme yetki matrisinde sadece Supervizor/Admin var (case SS3.3)."""
    result = await db.execute(
        select(Incident)
        .where(Incident.assigned_team_id.is_(None), Incident.current_status.notin_(TERMINAL_STATUSES))
        .order_by(Incident.created_at)
    )
    incidents = result.scalars().all()
    return {"success": True, "data": [_incident_summary(i) for i in incidents], "error": None}


@router.get("/incidents/stats/summary")
async def stats_summary(
    current_user: CurrentUser = Depends(require_roles(DASHBOARD_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Supervizor Dashboard icin agregasyonlar (bkz. ARCHITECTURE.md SS10). Yetki matrisinde
    'Dashboard goruntuleme' sadece Supervizor/Admin (case SS3.3)."""
    fault_type_rows = await db.execute(select(Incident.fault_type, func.count()).group_by(Incident.fault_type))
    priority_rows = await db.execute(select(Incident.priority, func.count()).group_by(Incident.priority))

    sla_outcome_rows = await db.execute(
        select(Incident.sla_status, func.count()).where(Incident.sla_status != "ACTIVE").group_by(Incident.sla_status)
    )
    sla_outcomes = {row[0]: row[1] for row in sla_outcome_rows.all()}
    met = sla_outcomes.get("MET", 0)
    breached = sla_outcomes.get("BREACHED", 0)
    sla_compliance_rate = round(met / (met + breached) * 100, 1) if (met + breached) > 0 else None

    sla_breached_active_count = (
        await db.execute(
            select(func.count()).where(
                Incident.sla_status == "BREACHED", Incident.current_status.notin_(TERMINAL_STATUSES)
            )
        )
    ).scalar_one()

    resolved_count = (await db.execute(select(func.count()).where(Incident.resolved_at.is_not(None)))).scalar_one()

    avg_resolution_seconds = (
        await db.execute(
            select(func.avg(func.extract("epoch", Incident.resolved_at - Incident.created_at))).where(
                Incident.resolved_at.is_not(None)
            )
        )
    ).scalar_one()
    avg_resolution_minutes = round(avg_resolution_seconds / 60, 1) if avg_resolution_seconds is not None else None

    unassigned_queue_count = (
        await db.execute(
            select(func.count()).where(
                Incident.assigned_team_id.is_(None), Incident.current_status.notin_(TERMINAL_STATUSES)
            )
        )
    ).scalar_one()

    # Son 7 gun (bugun dahil), gunluk oncelik kirilimi - Supervizor Dashboard cizgi grafigi.
    now = datetime.now(timezone.utc)
    trend_start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    day_expr = func.date_trunc("day", Incident.created_at)
    trend_rows = await db.execute(
        select(day_expr.label("day"), Incident.priority, func.count())
        .where(Incident.created_at >= trend_start, Incident.priority.is_not(None))
        .group_by(day_expr, Incident.priority)
    )
    trend_map: dict[str, dict[str, int]] = {}
    for day_val, priority_val, count_val in trend_rows.all():
        key = day_val.date().isoformat()
        trend_map.setdefault(key, {})[priority_val] = count_val

    priority_trend = []
    for offset in range(7):
        day_date = (trend_start + timedelta(days=offset)).date()
        counts = trend_map.get(day_date.isoformat(), {})
        priority_trend.append(
            {
                "day": TR_WEEKDAYS[day_date.weekday()],
                "DUSUK": counts.get("DUSUK", 0),
                "ORTA": counts.get("ORTA", 0),
                "YUKSEK": counts.get("YUKSEK", 0),
                "KRITIK": counts.get("KRITIK", 0),
            }
        )

    # Ekip bazli performans - assigned_team_name incident-service kendi tablosunda
    # denormalize tutuluyor (database-per-service, identity/ai-service'e sorgu atmadan
    # gosterilebiliyor). Reopen orani: cozulen vakanin degerlendirmesi is_permanent=False ise.
    team_rows = await db.execute(
        select(
            Incident.assigned_team_id,
            Incident.assigned_team_name,
            func.count().filter(Incident.resolved_at.is_not(None)).label("resolved"),
            func.avg(func.extract("epoch", Incident.resolved_at - Incident.created_at))
            .filter(Incident.resolved_at.is_not(None))
            .label("avg_seconds"),
        )
        .where(Incident.assigned_team_id.is_not(None))
        .group_by(Incident.assigned_team_id, Incident.assigned_team_name)
    )
    reopen_rows = await db.execute(
        select(
            Incident.assigned_team_id,
            func.count().filter(IncidentEvaluation.is_permanent.is_(False)).label("reopened"),
            func.count(IncidentEvaluation.id).label("total_eval"),
        )
        .join(IncidentEvaluation, IncidentEvaluation.incident_id == Incident.id)
        .where(Incident.assigned_team_id.is_not(None))
        .group_by(Incident.assigned_team_id)
    )
    reopen_map = {row[0]: (row[1], row[2]) for row in reopen_rows.all()}

    team_performance = []
    for team_id, team_name, resolved, avg_seconds in team_rows.all():
        if resolved == 0:
            continue
        reopened, total_eval = reopen_map.get(team_id, (0, 0))
        team_performance.append(
            {
                "team_id": str(team_id),
                "team_name": team_name or "Bilinmeyen ekip",
                "resolved": resolved,
                "avg_minutes": round(avg_seconds / 60, 1) if avg_seconds else 0.0,
                "reopen_rate": round(reopened / total_eval, 2) if total_eval else 0.0,
            }
        )

    return {
        "success": True,
        "data": {
            "fault_type_distribution": {row[0]: row[1] for row in fault_type_rows.all()},
            "priority_distribution": {row[0]: row[1] for row in priority_rows.all()},
            "sla_compliance_rate": sla_compliance_rate,
            "sla_breached_active_count": sla_breached_active_count,
            "resolved_count": resolved_count,
            "avg_resolution_minutes": avg_resolution_minutes,
            "unassigned_queue_count": unassigned_queue_count,
            "priority_trend": priority_trend,
            "team_performance": team_performance,
        },
        "error": None,
    }


@router.get("/incidents/{incident_id}")
async def get_incident(
    incident_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_roles(STAFF_ROLES + ["MUSTERI"])),
    db: AsyncSession = Depends(get_db),
):
    incident = await db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Vaka bulunamadi"},
        )
    if current_user.role == "SAHA_TEKNISYENI" and current_user.user_id != incident.assigned_team_id:
        # IDOR korumasi (case SS10 - jüri "kayit ID degistirerek baskasinin verisini
        # gorme" senaryosunu dener): kaynagin var oldugunu sizdirmamak icin 404.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Vaka bulunamadi"},
        )
    if current_user.role == "MUSTERI" and current_user.user_id != incident.created_by:
        # Musteri sadece kendi bildirdigi arizayi gorebilir - ayni IDOR korumasi.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Vaka bulunamadi"},
        )
    return {"success": True, "data": _incident_summary(incident), "error": None}


@router.patch("/incidents/{incident_id}/status")
async def change_status(
    incident_id: uuid.UUID,
    payload: StatusChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    incident = await db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Vaka bulunamadi"},
        )

    try:
        validate_transition(
            from_status=incident.current_status,
            to_status=payload.to_status,
            actor_role=current_user.role,
            actor_user_id=current_user.user_id,
            assigned_team_id=incident.assigned_team_id,
        )
    except InvalidTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_TRANSITION", "message": str(exc)},
        ) from exc
    except UnauthorizedTransition as exc:
        # NOT (CP3, Kisi 1): Identity Service ayaga kalkinca burada POST /internal/audit
        # cagrisi eklenip 403'ler audit log'a yazilacak (bkz. ARCHITECTURE.md SS3.4).
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "UNAUTHORIZED_TRANSITION", "message": str(exc)},
        ) from exc

    if payload.to_status == IncidentStatus.COZULDU and not (payload.note and payload.note.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "RESOLUTION_NOTE_REQUIRED", "message": "COZULDU icin cozum notu zorunludur"},
        )

    history = IncidentStatusHistory(
        incident_id=incident.id,
        from_status=incident.current_status,
        to_status=payload.to_status,
        changed_by=current_user.user_id,
        note=payload.note,
    )
    db.add(history)

    incident.current_status = payload.to_status

    if payload.to_status == IncidentStatus.COZULDU:
        incident.resolved_at = datetime.now(timezone.utc)
        if incident.sla_status == "ACTIVE":
            incident.sla_status = "MET"
        db.add(
            IncidentResolutionNote(
                incident_id=incident.id,
                technician_id=current_user.user_id,
                note=payload.note,
            )
        )

    await db.flush()
    await db.commit()
    await db.refresh(incident)

    if payload.to_status == IncidentStatus.COZULDU:
        await publish_event(
            "incident.resolved",
            IncidentResolved(
                incident_id=str(incident.id),
                team_id=str(incident.assigned_team_id),
                station_code=incident.station_code,
                fault_type=incident.fault_type,
                priority=incident.priority,
                created_at=incident.created_at,
                resolved_at=incident.resolved_at,
            ),
        )

    return {"success": True, "data": _incident_summary(incident), "error": None}


@router.post("/incidents/{incident_id}/messages", status_code=status.HTTP_201_CREATED)
async def create_message(
    incident_id: uuid.UUID,
    payload: MessageCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Case Bolum 4.5: saha teknisyeni ve NOC operatoru vaka uzerinden mesajlasabilir (thread)."""
    incident = await db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Vaka bulunamadi"},
        )
    if current_user.role not in MESSAGING_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "UNAUTHORIZED_TRANSITION", "message": "Bu role mesaj yazma yetkisi yok"},
        )
    if current_user.role == "SAHA_TEKNISYENI" and current_user.user_id != incident.assigned_team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "UNAUTHORIZED_TRANSITION", "message": "Bu vakaya atanan teknisyen siz degilsiniz"},
        )

    message = IncidentMessage(
        incident_id=incident.id,
        sender_id=current_user.user_id,
        sender_role=current_user.role,
        content=payload.content,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    return {
        "success": True,
        "data": {
            "id": str(message.id),
            "sender_id": str(message.sender_id),
            "sender_role": message.sender_role,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        },
        "error": None,
    }


@router.get("/incidents/{incident_id}/messages")
async def list_messages(
    incident_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_roles(["SAHA_TEKNISYENI", "NOC_OPERATORU", "SUPERVIZOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Vaka mesaj thread'i sadece atanan teknisyen, NOC ve yonetim rolleri icin gorunur
    (case SS4.5) - musteri veya baska teknisyenin ozel yazismasi sizmasin diye."""
    incident = await db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Vaka bulunamadi"},
        )
    if current_user.role == "SAHA_TEKNISYENI" and current_user.user_id != incident.assigned_team_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Vaka bulunamadi"},
        )
    result = await db.execute(
        select(IncidentMessage).where(IncidentMessage.incident_id == incident_id).order_by(IncidentMessage.created_at)
    )
    messages = result.scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": str(m.id),
                "sender_id": str(m.sender_id),
                "sender_role": m.sender_role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
        "error": None,
    }


@router.post("/incidents/{incident_id}/resolution-note", status_code=status.HTTP_201_CREATED)
async def add_resolution_note(
    incident_id: uuid.UUID,
    payload: ResolutionNoteCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Atanan teknisyenin, COZULDU gecisinden bagimsiz olarak vakaya ek cozum notu eklemesi
    icin (durum degisikligi gerektirmeyen ara notlar)."""
    incident = await db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Vaka bulunamadi"},
        )
    if current_user.role != "SAHA_TEKNISYENI" or current_user.user_id != incident.assigned_team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "UNAUTHORIZED_TRANSITION", "message": "Bu vakaya atanan teknisyen siz degilsiniz"},
        )

    note = IncidentResolutionNote(incident_id=incident.id, technician_id=current_user.user_id, note=payload.note)
    db.add(note)
    await db.commit()
    await db.refresh(note)

    return {
        "success": True,
        "data": {"id": str(note.id), "note": note.note, "created_at": note.created_at.isoformat()},
        "error": None,
    }


@router.post("/incidents/{incident_id}/evaluation", status_code=status.HTTP_201_CREATED)
async def create_evaluation(
    incident_id: uuid.UUID,
    payload: EvaluationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Case Bolum 4.6: vaka KAPANDI durumuna gectikten sonra NOC operatoru cozumu 1-5 yildiz
    degerlendirir. Tek seferliktir."""
    incident = await db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Vaka bulunamadi"},
        )
    if current_user.role != "NOC_OPERATORU":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "UNAUTHORIZED_TRANSITION", "message": "Sadece NOC operatoru degerlendirme yapabilir"},
        )
    if incident.current_status != IncidentStatus.KAPANDI:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INCIDENT_NOT_CLOSED", "message": "Vaka henuz KAPANDI durumunda degil"},
        )

    existing = await db.execute(select(IncidentEvaluation).where(IncidentEvaluation.incident_id == incident.id))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ALREADY_EVALUATED", "message": "Bu vaka zaten degerlendirildi"},
        )

    evaluation = IncidentEvaluation(
        incident_id=incident.id,
        noc_operator_id=current_user.user_id,
        stars=payload.stars,
        is_permanent=payload.is_permanent,
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)

    await publish_event(
        "incident.evaluated",
        IncidentEvaluated(
            incident_id=str(incident.id),
            stars=payload.stars,
            is_permanent=payload.is_permanent,
            evaluated_by=str(current_user.user_id),
        ),
    )

    return {
        "success": True,
        "data": {
            "id": str(evaluation.id),
            "stars": evaluation.stars,
            "is_permanent": evaluation.is_permanent,
            "created_at": evaluation.created_at.isoformat(),
        },
        "error": None,
    }


@router.patch("/incidents/{incident_id}/fault-type")
async def change_fault_type(
    incident_id: uuid.UUID,
    payload: FaultTypeChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Case Bolum 4.3: NOC operatoru veya Supervizor AI'nin atadigi turu degistirebilir.
    Bu degisiklik incident.type_changed olarak AI Service'e bildirilir (dogruluk metrigi
    icin, bkz. ARCHITECTURE.md SS8.8)."""
    incident = await db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Vaka bulunamadi"},
        )
    if current_user.role not in FAULT_TYPE_OVERRIDE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "UNAUTHORIZED_TRANSITION", "message": "Bu role tur degistirme yetkisi yok"},
        )

    original_fault_type = incident.fault_type
    if original_fault_type == payload.fault_type:
        return {"success": True, "data": _incident_summary(incident), "error": None}

    incident.fault_type = payload.fault_type
    incident.is_manual_override = True
    await db.commit()
    await db.refresh(incident)

    await publish_event(
        "incident.type_changed",
        IncidentTypeChanged(
            incident_id=str(incident.id),
            original_fault_type=original_fault_type,
            new_fault_type=payload.fault_type,
            changed_by=str(current_user.user_id),
            changed_at=datetime.now(timezone.utc),
        ),
    )

    return {"success": True, "data": _incident_summary(incident), "error": None}


@router.patch("/incidents/{incident_id}/assign")
async def manual_assign(
    incident_id: uuid.UUID,
    payload: ManualAssignRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Case Bolum 5.3: Supervizor (veya Admin) her zaman manuel atama yapabilir. CP6 kapsaminda
    sadece henuz atanmamis (YENI) vakalar icin - atanmis bir vakayi yeniden atamak (reassign)
    kapsam disi birakildi."""
    incident = await db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Vaka bulunamadi"},
        )
    if current_user.role not in MANUAL_ASSIGN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "UNAUTHORIZED_TRANSITION", "message": "Bu role manuel atama yetkisi yok"},
        )

    try:
        validate_transition(
            from_status=incident.current_status,
            to_status=IncidentStatus.ATANDI,
            actor_role=current_user.role,
            actor_user_id=current_user.user_id,
            assigned_team_id=incident.assigned_team_id,
        )
    except InvalidTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_TRANSITION", "message": str(exc)},
        ) from exc
    except UnauthorizedTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "UNAUTHORIZED_TRANSITION", "message": str(exc)},
        ) from exc

    history = IncidentStatusHistory(
        incident_id=incident.id,
        from_status=incident.current_status,
        to_status=IncidentStatus.ATANDI,
        changed_by=current_user.user_id,
        note=f"Manuel atama: {payload.team_name}",
    )
    db.add(history)

    incident.assigned_team_id = payload.team_id
    incident.assigned_team_name = payload.team_name
    incident.current_status = IncidentStatus.ATANDI
    await db.commit()
    await db.refresh(incident)

    await publish_event(
        "incident.assigned",
        IncidentAssigned(
            incident_id=str(incident.id),
            team_id=str(payload.team_id),
            team_name=payload.team_name,
            score=0.0,
            assigned_by=str(current_user.user_id),
            assigned_at=datetime.now(timezone.utc),
        ),
    )

    return {"success": True, "data": _incident_summary(incident), "error": None}
