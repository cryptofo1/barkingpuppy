import redis.asyncio as redis

from app.config import settings

_redis: redis.Redis | None = None

SPAM_WINDOW = 30
SPAM_THRESHOLD = 5
DIMINISHING_WINDOW = 600  # 10 minutes
DUPLICATE_SIMILARITY = 0.8  # 80% word overlap = duplicate


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def can_gain_xp(user_id: int, guild_id: int, cooldown: int = 30) -> bool:
    """Return True if the user is off cooldown. Sets cooldown if True."""
    r = await get_redis()
    key = f"xp_cd:{guild_id}:{user_id}"
    if await r.exists(key):
        return False
    await r.set(key, 1, ex=cooldown)
    return True


async def is_spam_locked(user_id: int, guild_id: int) -> bool:
    """Return True if the user is locked out for spamming."""
    r = await get_redis()
    return bool(await r.exists(f"xp_lock:{guild_id}:{user_id}"))


async def track_spam(user_id: int, guild_id: int) -> bool:
    """Track message frequency. Progressive lock: 30s → 60s → 120s."""
    r = await get_redis()
    spam_key = f"xp_spam:{guild_id}:{user_id}"
    offense_key = f"xp_offense:{guild_id}:{user_id}"

    count = await r.incr(spam_key)
    if count == 1:
        await r.expire(spam_key, SPAM_WINDOW)

    if count > SPAM_THRESHOLD:
        offense = await r.incr(offense_key)
        if offense == 1:
            await r.expire(offense_key, 600)

        lock_seconds = min(30 * (2 ** (offense - 1)), 120)
        await r.set(f"xp_lock:{guild_id}:{user_id}", 1, ex=lock_seconds)
        return True

    return False


def _word_set(text: str) -> set[str]:
    return {w.strip("!?.,'\"") for w in text.lower().split()} - {""}


async def is_duplicate(user_id: int, guild_id: int, content: str) -> bool:
    """Return True if message is too similar to the user's last message."""
    r = await get_redis()
    key = f"xp_last:{guild_id}:{user_id}"
    last = await r.get(key)
    await r.set(key, content, ex=DIMINISHING_WINDOW)

    if last is None:
        return False

    current_words = _word_set(content)
    last_words = _word_set(last)

    if not current_words or not last_words:
        return last == content

    all_words = current_words | last_words
    overlap = len(current_words & last_words) / len(all_words)
    return overlap >= DUPLICATE_SIMILARITY


async def get_diminishing_multiplier(user_id: int, guild_id: int) -> float:
    """Track messages in a 10-min window. Returns XP multiplier (floor 10%)."""
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
    return 0.1


async def check_hourly_cap(
    user_id: int, guild_id: int, amount: int, cap: int = 300
) -> int:
    """Return the XP the user can actually gain under the hourly cap."""
    r = await get_redis()
    key = f"xp_hr:{guild_id}:{user_id}"
    earned = int(await r.get(key) or 0)
    remaining = max(0, cap - earned)
    granted = min(amount, remaining)
    if granted > 0:
        pipe = r.pipeline()
        pipe.incrby(key, granted)
        pipe.expire(key, 3600)
        await pipe.execute()
    return granted
