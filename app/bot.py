import logging

import discord
from discord import app_commands
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


@app_commands.command(name="ping", description="Check if the bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")


async def load_cogs():
    for cog in COGS:
        await bot.load_extension(cog)
        log.info("Loaded cog: %s", cog)


async def sync_commands():
    guild = discord.Object(id=settings.DISCORD_GUILD_ID)
    bot.tree.add_command(ping)
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    log.info("Synced %d slash commands to guild %s", len(synced), settings.DISCORD_GUILD_ID)


def run():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    @bot.event
    async def setup_hook():
        await load_cogs()
        await sync_commands()

    bot.run(settings.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    run()
