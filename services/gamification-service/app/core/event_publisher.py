from pydantic import BaseModel

from app.core.redis_client import redis_client

# incident-service/identity-service ile ayni desen (bkz. EVENTS.md SS "Tasima Katmani").


async def publish_event(stream: str, payload: BaseModel) -> None:
    await redis_client.xadd(stream, {"data": payload.model_dump_json()})
