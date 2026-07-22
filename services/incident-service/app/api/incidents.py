import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_client import AIServiceUnavailable, assign, predict
from app.core.auth import CurrentUser, get_current_user
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
    Priority,
    Suggestion,
    TelemetryInput,
)
from app.schemas.incident import EvaluationCreate, MessageCreate, ResolutionNoteCreate, StatusChangeRequest

router = APIRouter(prefix="/api/v1", tags=["incidents"])

MESSAGING_ROLES = {"SAHA_TEKNISYENI", "NOC_OPERATORU"}


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
async def list_incidents(db: AsyncSession = Depends(get_db)):
    """CP2 iskelet: rol bazli scope ve filtreler CP6+ icinde eklenecek (bkz. TASK_SPLIT.md)."""
    result = await db.execute(select(Incident).order_by(Incident.created_at.desc()))
    incidents = result.scalars().all()
    return {"success": True, "data": [_incident_summary(i) for i in incidents], "error": None}


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    incident = await db.get(Incident, incident_id)
    if incident is None:
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
async def list_messages(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    incident = await db.get(Incident, incident_id)
    if incident is None:
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
