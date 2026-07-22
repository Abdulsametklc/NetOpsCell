import time

from app.core.redis_client import redis_client


async def check_rate_limit(ip: str, bucket: str, limit_per_minute: int) -> bool:
    """Sabit pencereli (fixed-window) sayaç. True -> istek serbest, False -> limit
    aşıldı (caller 429 dönmeli). TASK_SPLIT.md §4 (CP3): login IP başına 10/dk,
    genel trafik IP başına 100/dk."""
    window = int(time.time() // 60)
    key = f"ratelimit:{bucket}:{ip}:{window}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, 65)
    return count <= limit_per_minute
