from pydantic import BaseModel

from app.core.redis_client import redis_client

# Stream key = event_type; tüketiciler kendi consumer group'larıyla XREADGROUP ile okur
# (bkz. docs/CONTRACTS.md §3 - Redis Streams topolojisi). incident-service'teki
# app/core/event_publisher.py ile birebir aynı desen (tek "data" alanında JSON).


async def publish_event(stream: str, payload: BaseModel) -> None:
    await redis_client.xadd(stream, {"data": payload.model_dump_json()})
