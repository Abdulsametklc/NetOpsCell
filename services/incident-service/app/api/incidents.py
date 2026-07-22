import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.incident import Incident, TelemetryReading
from app.schemas.contracts import TelemetryInput

router = APIRouter(prefix="/api/v1", tags=["incidents"])


@router.post("/telemetry", status_code=status.HTTP_201_CREATED)
async def submit_telemetry(payload: TelemetryInput, db: AsyncSession = Depends(get_db)):
    """CP1 iskelet: telemetriyi kaydeder. AI Service entegrasyonu (tahmin + vaka acma) CP2'de eklenecek."""
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
    await db.commit()
    await db.refresh(reading)
    return {"success": True, "data": {"telemetry_id": str(reading.id)}, "error": None}


@router.get("/incidents")
async def list_incidents(db: AsyncSession = Depends(get_db)):
    """CP1 iskelet: rol bazli scope ve filtreler CP2+ icinde eklenecek."""
    result = await db.execute(select(Incident).order_by(Incident.created_at.desc()))
    incidents = result.scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": str(i.id),
                "incident_number": i.incident_number,
                "station_code": i.station_code,
                "current_status": i.current_status,
                "fault_type": i.fault_type,
                "priority": i.priority,
            }
            for i in incidents
        ],
        "error": None,
    }


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    incident = await db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Vaka bulunamadi"},
        )
    return {
        "success": True,
        "data": {
            "id": str(incident.id),
            "incident_number": incident.incident_number,
            "station_code": incident.station_code,
            "current_status": incident.current_status,
            "fault_type": incident.fault_type,
            "priority": incident.priority,
            "created_at": incident.created_at.isoformat(),
        },
        "error": None,
    }
