import discord
from discord.ext import commands

from app.config import settings

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


def run():
    bot.run(settings.DISCORD_TOKEN)
