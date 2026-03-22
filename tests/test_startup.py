"""Smoke tests: verify DB init, Redis connection, XP math, and cog imports."""

import asyncio
import importlib
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DISCORD_TOKEN", "test-token-not-real")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_xp_math():
    from bot.xp import level_from_xp, xp_for_level, xp_progress

    assert xp_for_level(1) == 155
    assert level_from_xp(0) == 0
    assert level_from_xp(155) == 1
    assert level_from_xp(154) == 0
    cur, needed = xp_progress(155, 1)
    assert cur == 0
    assert needed == xp_for_level(2)
    print("  ✓ XP math OK")


def test_models_import():
    from bot.models import Base, GuildConfig, LevelRole, UserXP  # noqa: F401
    assert len(Base.metadata.tables) == 3
    print("  ✓ Models OK")


async def test_async_components():
    from bot.database import init_db
    await init_db()
    print("  ✓ DB init OK (tables created)")

    from bot.redis_client import close_redis, init_redis
    await init_redis()
    print("  ✓ Redis connect OK")
    await close_redis()
    print("  ✓ Redis disconnect OK")


def test_cog_imports():
    cogs = [
        "bot.cogs.xp",
        "bot.cogs.daily",
        "bot.cogs.leaderboard",
        "bot.cogs.admin",
        "bot.cogs.roles",
    ]
    for cog in cogs:
        importlib.import_module(cog)
    print(f"  ✓ All {len(cogs)} cogs import OK")


if __name__ == "__main__":
    print("Running startup smoke tests …")
    test_xp_math()
    test_models_import()
    asyncio.run(test_async_components())
    test_cog_imports()
    print("\nAll smoke tests passed! ✅")
