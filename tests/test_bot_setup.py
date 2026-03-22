"""Test the bot's setup_hook independently (no Discord login needed)."""

import asyncio
import os
import sys

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DISCORD_TOKEN"] = "test-token-not-real"

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import discord
from discord.ext import commands


async def test_setup_hook():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    # Re-use the real setup_hook logic
    from bot.database import init_db
    from bot.redis_client import close_redis, init_redis

    await init_db()
    print("  ✓ Database initialised")

    await init_redis()
    print("  ✓ Redis connected")

    cogs = [
        "bot.cogs.xp",
        "bot.cogs.daily",
        "bot.cogs.leaderboard",
        "bot.cogs.admin",
        "bot.cogs.roles",
    ]
    for cog in cogs:
        await bot.load_extension(cog)
        print(f"  ✓ Loaded cog: {cog}")

    loaded = [c.__class__.__name__ for c in bot.cogs.values()]
    assert set(loaded) == {"XP", "Daily", "Leaderboard", "Admin", "Roles"}, f"Unexpected cogs: {loaded}"
    print(f"\n  All {len(loaded)} cogs loaded: {', '.join(loaded)}")

    await close_redis()
    await bot.close()
    print("\n✅ Bot setup_hook test passed!")


if __name__ == "__main__":
    asyncio.run(test_setup_hook())
