import logging
import random

import discord
from discord.ext import commands

from app.database import async_session
from app.models import NoXPChannel
from app.services.cooldown import (
    can_gain_xp,
    check_hourly_cap,
    get_diminishing_multiplier,
    is_duplicate,
    is_spam_locked,
    track_spam,
)
from app.services.level_roles import apply_level_roles
from app.services.leveling import add_xp, get_guild_config

log = logging.getLogger("barkingpuppy.xp")

MIN_MSG_LENGTH = 4


def length_multiplier(content: str) -> float:
    """Scale XP by message length."""
    length = len(content)
    if length <= 20:
        return 0.5
    if length <= 100:
        return 1.0
    return 1.2


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

        async with async_session() as session:
            if await session.get(NoXPChannel, (guild_id, message.channel.id)):
                return
            cfg = await get_guild_config(session, guild_id)

        if len(content) < MIN_MSG_LENGTH:
            return

        if await is_spam_locked(user_id, guild_id):
            return

        if await track_spam(user_id, guild_id):
            log.info("Spam lock: user %s in guild %s", user_id, guild_id)
            return

        if await is_duplicate(user_id, guild_id, content):
            return

        if not await can_gain_xp(user_id, guild_id, cooldown=cfg.message_cooldown):
            return

        diminishing = await get_diminishing_multiplier(user_id, guild_id)
        length_mult = length_multiplier(content)

        raw_xp = random.randint(cfg.xp_min, cfg.xp_max)
        xp = int(raw_xp * diminishing * length_mult)
        if xp <= 0:
            return

        xp = await check_hourly_cap(user_id, guild_id, xp, cap=cfg.hourly_xp_cap)
        if xp <= 0:
            return

        async with async_session() as session:
            user, leveled_up = await add_xp(session, user_id, guild_id, xp)

            if leveled_up:
                await message.channel.send(
                    f"🎉 {message.author.mention} reached **level {user.level}**!"
                )
                await apply_level_roles(session, message.author, guild_id, user.level)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(XPCog(bot))
