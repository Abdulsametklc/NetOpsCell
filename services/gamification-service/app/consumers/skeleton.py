import asyncio
import logging

from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

CONSUMER_GROUP = "gamification-service"

# CP1: sadece stream + consumer group altyapisi kuruluyor, mesajlar ack'lenip loglaniyor.
# Puan ekleme / rozet kontrolu / seviye hesaplama mantigi CP4-CP5'te buraya eklenecek
# (bkz. TASK_SPLIT.md Kisi 2 gorev listesi, docs/CONTRACTS.md SS3.1 yayinci/tuketici tablosu).
STREAMS = [
    "incident.created",
    "incident.resolved",
    "incident.evaluated",
    "incident.sla_breached",
]


async def _ensure_group(stream: str) -> None:
    try:
        await redis_client.xgroup_create(name=stream, groupname=CONSUMER_GROUP, id="0", mkstream=True)
    except Exception as exc:  # Redis stream zaten grubuyla varsa "BUSYGROUP" hatasi firlatir, yok sayilir.
        if "BUSYGROUP" not in str(exc):
            raise


async def _consume_loop(stream: str) -> None:
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
                # TODO (CP4/CP5): event tipine gore puan/rozet/seviye mantigini burada isle.
                logger.info("Event alindi [%s]: %s -> %s", stream, message_id, fields)
                await redis_client.xack(stream, CONSUMER_GROUP, message_id)


async def start_consumers() -> list[asyncio.Task]:
    tasks: list[asyncio.Task] = []
    for stream in STREAMS:
        await _ensure_group(stream)
        tasks.append(asyncio.create_task(_consume_loop(stream)))
    return tasks
