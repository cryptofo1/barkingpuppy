import redis.asyncio as redis

from app.config import settings

_redis: redis.Redis | None = None

COOLDOWN_SECONDS = 60


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def can_gain_xp(user_id: int, guild_id: int) -> bool:
    """Return True if the user is off cooldown and can gain XP.

    Sets the cooldown key if True.
    """
    r = await get_redis()
    key = f"xp_cd:{guild_id}:{user_id}"
    if await r.exists(key):
        return False
    await r.set(key, 1, ex=COOLDOWN_SECONDS)
    return True
