"""Entry point for the BarkingPuppy Discord bot."""

import logging

import discord
from discord.ext import commands

from bot.config import DISCORD_TOKEN
from bot.database import init_db
from bot.redis_client import close_redis, init_redis

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("barkingpuppy")

COGS = [
    "bot.cogs.xp",
    "bot.cogs.daily",
    "bot.cogs.leaderboard",
    "bot.cogs.admin",
    "bot.cogs.roles",
]


class BarkingPuppy(commands.Bot):
    async def setup_hook(self) -> None:
        log.info("Initialising database …")
        await init_db()

        log.info("Connecting to Redis …")
        await init_redis()

        for cog in COGS:
            await self.load_extension(cog)
            log.info("Loaded cog: %s", cog)

        log.info("Syncing slash commands …")
        await self.tree.sync()
        log.info("Bot is ready.")

    async def close(self) -> None:
        await close_redis()
        await super().close()


def main() -> None:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = BarkingPuppy(command_prefix="!", intents=intents)
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
