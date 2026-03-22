"""Roles cog — /levelrole add/remove/list lets admins map levels to roles."""

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import delete, select

from bot.database import async_session
from bot.models import LevelRole


class Roles(commands.GroupCog, group_name="levelrole"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="add", description="Assign a role reward for reaching a level")
    @app_commands.describe(level="Level threshold", role="Role to grant")
    @app_commands.default_permissions(administrator=True)
    async def add(
        self, interaction: discord.Interaction, level: int, role: discord.Role
    ) -> None:
        assert interaction.guild is not None
        async with async_session() as session:
            lr = await session.get(LevelRole, (interaction.guild.id, level))
            if lr is None:
                lr = LevelRole(
                    guild_id=interaction.guild.id,
                    level=level,
                    role_id=role.id,
                    role_name=role.name,
                )
                session.add(lr)
            else:
                lr.role_id = role.id
                lr.role_name = role.name
            await session.commit()

        await interaction.response.send_message(
            f"✅ Level **{level}** → {role.mention}", ephemeral=True
        )

    @app_commands.command(name="remove", description="Remove a level-role mapping")
    @app_commands.describe(level="Level to remove the role reward from")
    @app_commands.default_permissions(administrator=True)
    async def remove(self, interaction: discord.Interaction, level: int) -> None:
        assert interaction.guild is not None
        async with async_session() as session:
            await session.execute(
                delete(LevelRole).where(
                    LevelRole.guild_id == interaction.guild.id,
                    LevelRole.level == level,
                )
            )
            await session.commit()

        await interaction.response.send_message(
            f"✅ Removed role reward for level **{level}**.", ephemeral=True
        )

    @app_commands.command(name="list", description="List all level-role mappings")
    async def list_roles(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        async with async_session() as session:
            result = await session.execute(
                select(LevelRole)
                .where(LevelRole.guild_id == interaction.guild.id)
                .order_by(LevelRole.level)
            )
            rows = result.scalars().all()

        if not rows:
            await interaction.response.send_message(
                "No level roles configured.", ephemeral=True
            )
            return

        lines = [f"Level **{r.level}** → <@&{r.role_id}>" for r in rows]
        embed = discord.Embed(
            title="Level Roles",
            description="\n".join(lines),
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Roles(bot))
