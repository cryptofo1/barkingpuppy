import redis.asyncio as redis

from app.config import settings

_redis: redis.Redis | None = None

COOLDOWN_SECONDS = 60
SPAM_WINDOW = 30
SPAM_THRESHOLD = 5
SPAM_LOCK_SECONDS = 120
HOURLY_XP_CAP = 300
DIMINISHING_WINDOW = 600  # 10 minutes


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def can_gain_xp(user_id: int, guild_id: int) -> bool:
    """Return True if the user is off cooldown. Sets cooldown if True."""
    r = await get_redis()
    key = f"xp_cd:{guild_id}:{user_id}"
    if await r.exists(key):
        return False
    await r.set(key, 1, ex=COOLDOWN_SECONDS)
    return True


async def is_spam_locked(user_id: int, guild_id: int) -> bool:
    """Return True if the user is locked out for spamming."""
    r = await get_redis()
    return bool(await r.exists(f"xp_lock:{guild_id}:{user_id}"))


async def track_spam(user_id: int, guild_id: int) -> bool:
    """Track message frequency. Returns True if user just got spam-locked."""
    r = await get_redis()
    key = f"xp_spam:{guild_id}:{user_id}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, SPAM_WINDOW)
    if count > SPAM_THRESHOLD:
        await r.set(f"xp_lock:{guild_id}:{user_id}", 1, ex=SPAM_LOCK_SECONDS)
        return True
    return False


async def is_duplicate(user_id: int, guild_id: int, content: str) -> bool:
    """Return True if the message matches the user's last message."""
    r = await get_redis()
    key = f"xp_last:{guild_id}:{user_id}"
    last = await r.get(key)
    await r.set(key, content, ex=DIMINISHING_WINDOW)
    return last == content


async def get_diminishing_multiplier(user_id: int, guild_id: int) -> float:
    """Track messages in a 10-min window. Returns XP multiplier."""
    r = await get_redis()
    key = f"xp_dim:{guild_id}:{user_id}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, DIMINISHING_WINDOW)

    if count <= 5:
        return 1.0
    if count <= 10:
        return 0.6
    if count <= 15:
        return 0.25
    return 0.0


async def check_hourly_cap(user_id: int, guild_id: int, amount: int) -> int:
    """Return the XP the user can actually gain under the hourly cap."""
    r = await get_redis()
    key = f"xp_hr:{guild_id}:{user_id}"
    earned = int(await r.get(key) or 0)
    remaining = max(0, HOURLY_XP_CAP - earned)
    granted = min(amount, remaining)
    if granted > 0:
        pipe = r.pipeline()
        pipe.incrby(key, granted)
        pipe.expire(key, 3600)
        await pipe.execute()
    return granted
