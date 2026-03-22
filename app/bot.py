import logging

import discord
from discord.ext import commands

from app.config import settings

log = logging.getLogger("barkingpuppy")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
    log.info("Connected to %d guild(s):", len(bot.guilds))
    for guild in bot.guilds:
        log.info("  - %s (ID: %s, members: %d)", guild.name, guild.id, guild.member_count)
    log.info("Bot is ready.")


def run():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    bot.run(settings.DISCORD_TOKEN)
