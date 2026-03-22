from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from app.database import async_session
from app.services.leveling import get_guild_config, get_or_create_user

DAILY_COOLDOWN = timedelta(hours=24)


class DailyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="daily", description="Claim your daily points")
    async def daily(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        now = datetime.now(timezone.utc)

        async with async_session() as session:
            user = await get_or_create_user(session, user_id, guild_id)
            cfg = await get_guild_config(session, guild_id)

            if user.last_daily_at is not None:
                last = user.last_daily_at.replace(tzinfo=timezone.utc)
                next_daily = last + DAILY_COOLDOWN
                if now < next_daily:
                    remaining = next_daily - now
                    hours, rem = divmod(int(remaining.total_seconds()), 3600)
                    minutes = rem // 60
                    await interaction.response.send_message(
                        f"⏳ Come back in **{hours}h {minutes}m**.",
                        ephemeral=True,
                    )
                    return

            user.points += cfg.daily_points
            user.last_daily_at = now.replace(tzinfo=None)
            await session.commit()

        await interaction.response.send_message(
            f"✅ You claimed **{cfg.daily_points:,} points**! Total: **{user.points:,}**."
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DailyCog(bot))
