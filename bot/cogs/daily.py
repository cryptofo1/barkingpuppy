"""Daily reward cog — /daily gives a fixed XP bonus once per 24 h."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import DEFAULT_DAILY_XP
from bot.database import async_session
from bot.models import GuildConfig, UserXP
from bot.redis_client import get_redis
from bot.xp import level_from_xp


class Daily(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def _daily_key(guild_id: int, user_id: int) -> str:
        return f"daily:{guild_id}:{user_id}"

    @app_commands.command(name="daily", description="Claim your daily XP reward")
    async def daily(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        guild_id = interaction.guild.id
        user_id = interaction.user.id
        r = get_redis()

        key = self._daily_key(guild_id, user_id)
        if await r.exists(key):
            ttl = await r.ttl(key)
            hours, remainder = divmod(ttl, 3600)
            minutes = remainder // 60
            await interaction.response.send_message(
                f"⏳ You already claimed your daily! Come back in **{hours}h {minutes}m**.",
                ephemeral=True,
            )
            return

        async with async_session() as session:
            cfg = await session.get(GuildConfig, guild_id)
            daily_xp = cfg.daily_xp if cfg else DEFAULT_DAILY_XP

            user = await session.get(UserXP, (guild_id, user_id))
            if user is None:
                user = UserXP(guild_id=guild_id, user_id=user_id, xp=0, level=0, total_messages=0)
                session.add(user)

            user.xp += daily_xp
            user.level = level_from_xp(user.xp)
            await session.commit()

        await r.set(key, 1, ex=86400)  # 24 hours

        await interaction.response.send_message(
            f"✅ You claimed **{daily_xp:,} XP**! You now have **{user.xp:,} XP** (level {user.level})."
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Daily(bot))
