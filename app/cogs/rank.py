import discord
from discord import app_commands
from discord.ext import commands

from app.database import async_session
from app.models import User
from app.services.leveling import xp_needed


class RankCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="rank", description="View your level, XP, and points")
    async def rank(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None

        async with async_session() as session:
            user = await session.get(
                User, (interaction.user.id, interaction.guild.id)
            )

        if user is None:
            await interaction.response.send_message(
                "You haven't earned any XP yet!", ephemeral=True
            )
            return

        needed = xp_needed(user.level)
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Rank",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Level", value=str(user.level), inline=True)
        embed.add_field(name="XP", value=f"{user.xp:,} / {needed:,}", inline=True)
        embed.add_field(name="Points", value=f"{user.points:,}", inline=True)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RankCog(bot))
