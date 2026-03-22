import logging

import discord
from discord.ext import commands

from app.config import settings

log = logging.getLogger("barkingpuppy")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

COGS = [
    "app.cogs.xp",
    "app.cogs.daily",
    "app.cogs.leaderboard",
    "app.cogs.rank",
    "app.cogs.admin",
    "app.cogs.voice",
]


@bot.event
async def on_ready():
    log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
    log.info("Connected to %d guild(s):", len(bot.guilds))
    for guild in bot.guilds:
        log.info("  - %s (ID: %s, members: %d)", guild.name, guild.id, guild.member_count)
    log.info("Bot is ready.")


@bot.command()
async def ping(ctx: commands.Context):
    await ctx.send("Pong!")


async def load_cogs():
    for cog in COGS:
        await bot.load_extension(cog)
        log.info("Loaded cog: %s", cog)


def run():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    @bot.event
    async def setup_hook():
        await load_cogs()

    bot.run(settings.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    run()
