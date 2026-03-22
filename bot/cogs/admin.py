"""Admin cog — /config lets administrators tune XP settings per-guild."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import DEFAULT_DAILY_XP, DEFAULT_XP_COOLDOWN, DEFAULT_XP_MAX, DEFAULT_XP_MIN
from bot.database import async_session
from bot.models import GuildConfig


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="config", description="View or update server XP settings")
    @app_commands.describe(
        xp_min="Minimum XP per message",
        xp_max="Maximum XP per message",
        xp_cooldown="Seconds between XP-earning messages",
        daily_xp="XP awarded by /daily",
    )
    @app_commands.default_permissions(administrator=True)
    async def config(
        self,
        interaction: discord.Interaction,
        xp_min: int | None = None,
        xp_max: int | None = None,
        xp_cooldown: int | None = None,
        daily_xp: int | None = None,
    ) -> None:
        assert interaction.guild is not None
        guild_id = interaction.guild.id

        async with async_session() as session:
            cfg = await session.get(GuildConfig, guild_id)

            # If no args provided, just display current config
            if all(v is None for v in (xp_min, xp_max, xp_cooldown, daily_xp)):
                embed = discord.Embed(title="Server XP Config", color=discord.Color.blue())
                embed.add_field(name="XP per message", value=f"{cfg.xp_min if cfg else DEFAULT_XP_MIN}–{cfg.xp_max if cfg else DEFAULT_XP_MAX}")
                embed.add_field(name="Cooldown", value=f"{cfg.xp_cooldown if cfg else DEFAULT_XP_COOLDOWN}s")
                embed.add_field(name="Daily XP", value=f"{cfg.daily_xp if cfg else DEFAULT_DAILY_XP:,}")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if cfg is None:
                cfg = GuildConfig(guild_id=guild_id)
                session.add(cfg)

            if xp_min is not None:
                cfg.xp_min = xp_min
            if xp_max is not None:
                cfg.xp_max = xp_max
            if xp_cooldown is not None:
                cfg.xp_cooldown = xp_cooldown
            if daily_xp is not None:
                cfg.daily_xp = daily_xp

            await session.commit()

        await interaction.response.send_message("✅ Config updated!", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
