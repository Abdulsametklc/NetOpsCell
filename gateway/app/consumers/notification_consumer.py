import asyncio
import json
import logging

from app.core.redis_client import redis_client
from app.core.ws_manager import manager

logger = logging.getLogger(__name__)

CONSUMER_GROUP = "gateway"

# ARCHITECTURE.md §5 madde 4: badge.earned + kendi atanmış incident.assigned + süpervizörler
# için incident.sla_breached, game.points_awarded'ı da ekliyoruz (profil sayfası anlık güncelsin).


async def _handle_badge_earned(event: dict) -> None:
    await manager.send_to_user(event["user_id"], {"type": "badge.earned", "payload": event})


async def _handle_points_awarded(event: dict) -> None:
    await manager.send_to_user(event["user_id"], {"type": "game.points_awarded", "payload": event})


async def _handle_incident_assigned(event: dict) -> None:
    await manager.send_to_user(event["team_id"], {"type": "incident.assigned", "payload": event})


async def _handle_sla_breached(event: dict) -> None:
    await manager.broadcast_to_roles({"SUPERVIZOR", "ADMIN"}, {"type": "incident.sla_breached", "payload": event})


HANDLERS = {
    "badge.earned": _handle_badge_earned,
    "game.points_awarded": _handle_points_awarded,
    "incident.assigned": _handle_incident_assigned,
    "incident.sla_breached": _handle_sla_breached,
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
                    await handler(event)
                except Exception:
                    logger.exception("Event isleme hatasi [%s]: %s", stream, message_id)
                await redis_client.xack(stream, CONSUMER_GROUP, message_id)


async def start_consumers() -> list[asyncio.Task]:
    tasks: list[asyncio.Task] = []
    for stream in HANDLERS:
        await _ensure_group(stream)
        tasks.append(asyncio.create_task(_consume_loop(stream)))
    return tasks
