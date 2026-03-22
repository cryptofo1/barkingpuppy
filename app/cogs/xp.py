import logging
import random

import discord
from discord.ext import commands

from app.database import async_session
from app.services.cooldown import (
    can_gain_xp,
    check_hourly_cap,
    get_diminishing_multiplier,
    is_duplicate,
    is_spam_locked,
    track_spam,
)
from app.services.level_roles import apply_level_roles
from app.services.leveling import add_xp

log = logging.getLogger("barkingpuppy.xp")

XP_MIN = 15
XP_MAX = 25
MIN_MSG_LENGTH = 4


class XPCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        user_id = message.author.id
        guild_id = message.guild.id
        content = message.content.strip()

        # Too short
        if len(content) < MIN_MSG_LENGTH:
            return

        # Spam locked
        if await is_spam_locked(user_id, guild_id):
            return

        # Track spam — lock if threshold exceeded
        if await track_spam(user_id, guild_id):
            log.info("Spam lock: user %s in guild %s", user_id, guild_id)
            return

        # Duplicate message
        if await is_duplicate(user_id, guild_id, content):
            return

        # 60s cooldown
        if not await can_gain_xp(user_id, guild_id):
            return

        # Diminishing returns
        multiplier = await get_diminishing_multiplier(user_id, guild_id)
        if multiplier <= 0:
            return

        # Roll XP and apply multiplier
        raw_xp = random.randint(XP_MIN, XP_MAX)
        xp = int(raw_xp * multiplier)
        if xp <= 0:
            return

        # Hourly cap
        xp = await check_hourly_cap(user_id, guild_id, xp)
        if xp <= 0:
            return

        # Grant XP
        async with async_session() as session:
            user, leveled_up = await add_xp(session, user_id, guild_id, xp)

            if leveled_up:
                await message.channel.send(
                    f"🎉 {message.author.mention} reached **level {user.level}**!"
                )
                await apply_level_roles(session, message.author, guild_id, user.level)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(XPCog(bot))
