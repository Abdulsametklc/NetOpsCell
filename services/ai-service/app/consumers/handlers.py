import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accuracy_feedback import AccuracyFeedback
from app.models.team import TeamProfile, TeamWorkload
from app.schemas.contracts import FaultType


async def handle_personnel_upserted(db: AsyncSession, event: dict) -> None:
    """identity.personnel.upserted -> team_profile read-model cache'ini gunceller
    (bkz. ARCHITECTURE.md SS7 - AI Service, atama skorlamasi icin Identity'nin DB'sine
    dogrudan erismek yerine kendi yerel kopyasini event ile senkron tutar)."""
    team_id = uuid.UUID(event["user_id"])
    team = await db.get(TeamProfile, team_id)

    specializations = [FaultType(s) for s in event.get("specializations", [])]
    if team is None:
        team = TeamProfile(
            id=team_id,
            name=event["name"],
            specializations=specializations,
            regions=event.get("regions", []),
            base_lat=event["base_lat"],
            base_lon=event["base_lon"],
            is_active=event.get("is_active", True),
        )
        db.add(team)
    else:
        team.name = event["name"]
        team.specializations = specializations
        team.regions = event.get("regions", [])
        team.base_lat = event["base_lat"]
        team.base_lon = event["base_lon"]
        team.is_active = event.get("is_active", True)

    await db.commit()


async def handle_incident_assigned(db: AsyncSession, event: dict) -> None:
    """incident.assigned -> ilgili ekibin aktif is yukunu +1 artirir (bosluk_orani girdisi)."""
    team_id = uuid.UUID(event["team_id"])
    workload = await db.get(TeamWorkload, team_id)
    if workload is None:
        workload = TeamWorkload(team_id=team_id, active_incident_count=1)
        db.add(workload)
    else:
        workload.active_incident_count += 1
    await db.commit()


async def handle_incident_resolved(db: AsyncSession, event: dict) -> None:
    """incident.resolved -> ilgili ekibin aktif is yukunu -1 azaltir (0'in altina inmez)."""
    team_id = uuid.UUID(event["team_id"])
    workload = await db.get(TeamWorkload, team_id)
    if workload is not None and workload.active_incident_count > 0:
        workload.active_incident_count -= 1
        await db.commit()


async def handle_type_changed(db: AsyncSession, event: dict) -> None:
    """incident.type_changed -> NOC/Supervizor AI'nin atadigi turu degistirdi, bu "yanlis
    siniflandirma" olarak kaydedilir (bkz. ARCHITECTURE.md SS8.8, GET /ai/accuracy)."""
    db.add(
        AccuracyFeedback(
            incident_id=uuid.UUID(event["incident_id"]),
            original_fault_type=FaultType(event["original_fault_type"]),
            corrected_fault_type=FaultType(event["new_fault_type"]),
            corrected_by=uuid.UUID(event["changed_by"]),
            is_correct=False,
        )
    )
    await db.commit()
