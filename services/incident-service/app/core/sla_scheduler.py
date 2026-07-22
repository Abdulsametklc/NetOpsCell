import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import async_session
from app.core.event_publisher import publish_event
from app.models.incident import Incident
from app.schemas.contracts import IncidentSlaBreached, IncidentStatus

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 30
TERMINAL_STATUSES = (IncidentStatus.COZULDU, IncidentStatus.KAPANDI)


async def _check_once() -> None:
    now = datetime.now(timezone.utc)
    breached: list[Incident] = []

    async with async_session() as db:
        result = await db.execute(
            select(Incident).where(
                Incident.sla_due_at.is_not(None),
                Incident.sla_due_at < now,
                Incident.sla_status == "ACTIVE",
                Incident.current_status.notin_(TERMINAL_STATUSES),
            )
        )
        breached = list(result.scalars().all())
        for incident in breached:
            incident.sla_status = "BREACHED"
        if breached:
            await db.commit()

    for incident in breached:
        await publish_event(
            "incident.sla_breached",
            IncidentSlaBreached(
                incident_id=str(incident.id),
                team_id=str(incident.assigned_team_id) if incident.assigned_team_id else None,
                priority=incident.priority,
                sla_due_at=incident.sla_due_at,
                breached_at=now,
            ),
        )


async def run_scheduler() -> None:
    """30sn periyodik: SLA'si gecmis ve hala aktif olan vakalari BREACHED isaretler +
    incident.sla_breached yayinlar (bkz. ARCHITECTURE.md SS4.2.2, case Bolum 4.4)."""
    while True:
        try:
            await _check_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("SLA scheduler dongusu basarisiz oldu")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
