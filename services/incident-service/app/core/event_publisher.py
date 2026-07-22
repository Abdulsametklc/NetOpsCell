from pydantic import BaseModel

from app.core.redis_client import redis_client

# Stream key = event_type; tuketiciler kendi consumer group'lariyla XREADGROUP ile okur
# (bkz. docs/CONTRACTS.md SS3 - Redis Streams topolojisi, ARCHITECTURE.md SS6.1).
# Payload tek bir "data" alaninda JSON olarak tasinir (nested/typed alanlari flat stream
# field'larina bolmek yerine).


async def publish_event(stream: str, payload: BaseModel) -> None:
    await redis_client.xadd(stream, {"data": payload.model_dump_json()})
