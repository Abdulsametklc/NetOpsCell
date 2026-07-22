import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_client import AIServiceUnavailable, predict
from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_db
from app.core.sequence import generate_incident_number
from app.core.state_machine import InvalidTransition, UnauthorizedTransition, validate_transition
from app.models.incident import Incident, IncidentStatusHistory, TelemetryReading
from app.schemas.contracts import FaultType, IncidentStatus, Priority, Suggestion, TelemetryInput
from app.schemas.incident import StatusChangeRequest

router = APIRouter(prefix="/api/v1", tags=["incidents"])


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
    )
    db.add(incident)
    await db.flush()
    reading.incident_id = incident.id
    return incident


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
        # manuel atama kuyruguna duser (assigned_team_id null kaldigi surece kuyrukta sayilir).
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

    # NOT (CP4): COZULDU icin cozum notu zorunlulugu + incident.resolved event yayini
    # burada eklenecek (bkz. TASK_SPLIT.md Kisi 2 gorev listesi).
    history = IncidentStatusHistory(
        incident_id=incident.id,
        from_status=incident.current_status,
        to_status=payload.to_status,
        changed_by=current_user.user_id,
        note=payload.note,
    )
    db.add(history)
    incident.current_status = payload.to_status
    await db.commit()
    await db.refresh(incident)

    return {"success": True, "data": _incident_summary(incident), "error": None}
