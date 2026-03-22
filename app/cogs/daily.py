from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from app.database import async_session
from app.services.leveling import get_guild_config, get_or_create_user

DAILY_COOLDOWN = timedelta(hours=24)
STREAK_EXPIRY = timedelta(hours=48)

STREAK_BONUS = {
    1: 1.0,
    2: 1.2,
    3: 1.4,
    4: 1.6,
    5: 1.8,
    6: 2.0,
}
MAX_STREAK_MULTIPLIER = 2.5  # day 7+


def streak_multiplier(streak: int) -> float:
    if streak >= 7:
        return MAX_STREAK_MULTIPLIER
    return STREAK_BONUS.get(streak, 1.0)


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
                        f"⏳ Come back in **{hours}h {minutes}m**. "
                        f"(🔥 streak: **{user.daily_streak}**)",
                        ephemeral=True,
                    )
                    return

                if now > last + STREAK_EXPIRY:
                    user.daily_streak = 0

            user.daily_streak += 1
            mult = streak_multiplier(user.daily_streak)
            reward = int(cfg.daily_points * mult)

            user.points += reward
            user.last_daily_at = now.replace(tzinfo=None)
            await session.commit()

        embed = discord.Embed(
            title="Daily Reward",
            color=discord.Color.green(),
        )
        embed.add_field(name="Points earned", value=f"+{reward:,}", inline=True)
        embed.add_field(name="Streak", value=f"🔥 {user.daily_streak} day(s)", inline=True)
        embed.add_field(name="Total points", value=f"{user.points:,}", inline=True)
        if user.daily_streak < 7:
            next_mult = streak_multiplier(user.daily_streak + 1)
            next_reward = int(cfg.daily_points * next_mult)
            embed.set_footer(text=f"Come back tomorrow for {next_reward} pts!")
        else:
            embed.set_footer(text="Max streak! Keep it going!")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DailyCog(bot))
