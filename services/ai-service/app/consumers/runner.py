import asyncio
import json
import logging

from app.core.database import async_session
from app.core.redis_client import redis_client
from app.consumers.handlers import handle_incident_assigned, handle_incident_resolved, handle_personnel_upserted

logger = logging.getLogger(__name__)

CONSUMER_GROUP = "ai-service"

HANDLERS = {
    "identity.personnel.upserted": handle_personnel_upserted,
    "incident.assigned": handle_incident_assigned,
    "incident.resolved": handle_incident_resolved,
}


async def _ensure_group(stream: str) -> None:
    try:
        await redis_client.xgroup_create(name=stream, groupname=CONSUMER_GROUP, id="0", mkstream=True)
    except Exception as exc:  # Redis stream zaten grubuyla varsa "BUSYGROUP" hatasi firlatir.
        if "BUSYGROUP" not in str(exc):
            raise


async def _consume_loop(stream: str) -> None:
    handler = HANDLERS[stream]
    consumer_name = f"{CONSUMER_GROUP}-worker"
    while True:
        try:
            response = await redis_client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=consumer_name,
                streams={stream: ">"},
                count=10,
                block=5000,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Redis stream okuma hatasi: %s", stream)
            await asyncio.sleep(2)
            continue

        if not response:
            continue

        for _stream_name, messages in response:
            for message_id, fields in messages:
                try:
                    event = json.loads(fields["data"])
                    async with async_session() as db:
                        await handler(db, event)
                except Exception:
                    logger.exception("Event isleme hatasi [%s]: %s", stream, message_id)
                await redis_client.xack(stream, CONSUMER_GROUP, message_id)


async def start_consumers() -> list[asyncio.Task]:
    tasks: list[asyncio.Task] = []
    for stream in HANDLERS:
        await _ensure_group(stream)
        tasks.append(asyncio.create_task(_consume_loop(stream)))
    return tasks
