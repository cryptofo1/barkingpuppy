"""Leaderboard cog — /leaderboard shows top users by XP."""

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from bot.database import async_session
from bot.models import UserXP


class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Show the server XP leaderboard")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None

        async with async_session() as session:
            result = await session.execute(
                select(UserXP)
                .where(UserXP.guild_id == interaction.guild.id)
                .order_by(UserXP.xp.desc())
                .limit(10)
            )
            rows = result.scalars().all()

        if not rows:
            await interaction.response.send_message(
                "No one has earned XP yet!", ephemeral=True
            )
            return

        lines: list[str] = []
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows):
            prefix = medals[i] if i < 3 else f"**{i + 1}.**"
            member = interaction.guild.get_member(row.user_id)
            name = member.display_name if member else f"User {row.user_id}"
            lines.append(f"{prefix} {name} — Level {row.level} · {row.xp:,} XP")

        embed = discord.Embed(
            title=f"🏆 {interaction.guild.name} Leaderboard",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leaderboard(bot))
