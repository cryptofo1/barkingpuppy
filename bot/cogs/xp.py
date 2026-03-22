"""XP cog — awards XP on messages, enforces cooldown (anti-farm), shows /rank."""

import random

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from bot.database import async_session
from bot.models import GuildConfig, LevelRole, UserXP
from bot.config import DEFAULT_XP_MIN, DEFAULT_XP_MAX, DEFAULT_XP_COOLDOWN
from bot.redis_client import get_redis
from bot.xp import level_from_xp, xp_progress


class XP(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # --- anti-farm cooldown key ---
    @staticmethod
    def _cooldown_key(guild_id: int, user_id: int) -> str:
        return f"xp:cd:{guild_id}:{user_id}"

    # --- message listener ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        guild_id = message.guild.id
        user_id = message.author.id
        r = get_redis()

        # Anti-farm: skip if user is still on cooldown
        cd_key = self._cooldown_key(guild_id, user_id)
        if await r.exists(cd_key):
            return

        async with async_session() as session:
            # Fetch guild config (or use defaults)
            cfg = await session.get(GuildConfig, guild_id)
            xp_min = cfg.xp_min if cfg else DEFAULT_XP_MIN
            xp_max = cfg.xp_max if cfg else DEFAULT_XP_MAX
            cooldown = cfg.xp_cooldown if cfg else DEFAULT_XP_COOLDOWN

            # Fetch or create user row
            user = await session.get(UserXP, (guild_id, user_id))
            if user is None:
                user = UserXP(guild_id=guild_id, user_id=user_id, xp=0, level=0, total_messages=0)
                session.add(user)

            gained = random.randint(xp_min, xp_max)
            user.xp += gained
            user.total_messages += 1
            old_level = user.level
            user.level = level_from_xp(user.xp)
            await session.commit()

        # Set cooldown in Redis
        await r.set(cd_key, 1, ex=cooldown)

        # Level-up announcement
        if user.level > old_level:
            await message.channel.send(
                f"🎉 {message.author.mention} reached **level {user.level}**!"
            )
            await self._assign_level_roles(message.author, guild_id, user.level)

    # --- assign earned level roles ---
    async def _assign_level_roles(
        self, member: discord.Member, guild_id: int, level: int
    ) -> None:
        async with async_session() as session:
            result = await session.execute(
                select(LevelRole).where(
                    LevelRole.guild_id == guild_id,
                    LevelRole.level <= level,
                )
            )
            roles_to_have = result.scalars().all()

        for lr in roles_to_have:
            role = member.guild.get_role(lr.role_id)
            if role and role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"Reached level {lr.level}")
                except discord.Forbidden:
                    pass

    # --- /rank command ---
    @app_commands.command(name="rank", description="Show your current XP and level")
    async def rank(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        async with async_session() as session:
            user = await session.get(
                UserXP, (interaction.guild.id, interaction.user.id)
            )

        if user is None:
            await interaction.response.send_message(
                "You haven't earned any XP yet! Start chatting to earn XP.",
                ephemeral=True,
            )
            return

        current, needed = xp_progress(user.xp, user.level)
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Rank",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Level", value=str(user.level), inline=True)
        embed.add_field(name="Total XP", value=f"{user.xp:,}", inline=True)
        embed.add_field(
            name="Progress", value=f"{current:,} / {needed:,} XP", inline=False
        )
        embed.add_field(name="Messages", value=f"{user.total_messages:,}", inline=True)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(XP(bot))
