import redis.asyncio as redis

from bot.config import REDIS_URL

pool: redis.Redis | None = None


async def init_redis() -> redis.Redis:
    global pool
    pool = redis.from_url(REDIS_URL, decode_responses=True)
    await pool.ping()
    return pool


async def close_redis() -> None:
    if pool is not None:
        await pool.aclose()


def get_redis() -> redis.Redis:
    assert pool is not None, "Redis not initialised — call init_redis() first"
    return pool
