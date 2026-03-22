import logging

import discord
from discord import app_commands
from discord.ext import commands

from app.database import async_session
from app.models import GuildConfig, NoXPChannel
from app.services.leveling import add_points

log = logging.getLogger("barkingpuppy.admin")


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="add_points", description="Give points to a user")
    @app_commands.describe(user="Target user", amount="Points to add")
    @app_commands.default_permissions(administrator=True)
    async def add_points_cmd(
        self, interaction: discord.Interaction, user: discord.Member, amount: int
    ) -> None:
        assert interaction.guild is not None

        if amount <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return

        async with async_session() as session:
            u = await add_points(session, user.id, interaction.guild.id, amount)

        log.info(
            "%s gave %d points to %s in guild %s",
            interaction.user, amount, user, interaction.guild.id,
        )
        await interaction.response.send_message(
            f"✅ Gave **{amount:,}** points to {user.mention}. They now have **{u.points:,}**."
        )

    @app_commands.command(name="config_set_xp", description="Set XP per message range")
    @app_commands.describe(min_xp="Minimum XP per message", max_xp="Maximum XP per message")
    @app_commands.default_permissions(administrator=True)
    async def config_set_xp(
        self, interaction: discord.Interaction, min_xp: int, max_xp: int
    ) -> None:
        assert interaction.guild is not None

        if min_xp < 1 or max_xp < 1:
            await interaction.response.send_message("Values must be at least 1.", ephemeral=True)
            return
        if min_xp > max_xp:
            await interaction.response.send_message("Min cannot be greater than max.", ephemeral=True)
            return

        async with async_session() as session:
            cfg = await session.get(GuildConfig, interaction.guild.id)
            if cfg is None:
                cfg = GuildConfig(guild_id=interaction.guild.id)
                session.add(cfg)
            cfg.xp_min = min_xp
            cfg.xp_max = max_xp
            await session.commit()

        log.info(
            "%s set XP range to %d–%d in guild %s",
            interaction.user, min_xp, max_xp, interaction.guild.id,
        )
        await interaction.response.send_message(
            f"✅ XP per message set to **{min_xp}–{max_xp}**.", ephemeral=True
        )

    @app_commands.command(name="config_set_daily", description="Set daily points reward")
    @app_commands.describe(amount="Points awarded by /daily")
    @app_commands.default_permissions(administrator=True)
    async def config_set_daily(
        self, interaction: discord.Interaction, amount: int
    ) -> None:
        assert interaction.guild is not None

        if amount < 1:
            await interaction.response.send_message("Amount must be at least 1.", ephemeral=True)
            return

        async with async_session() as session:
            cfg = await session.get(GuildConfig, interaction.guild.id)
            if cfg is None:
                cfg = GuildConfig(guild_id=interaction.guild.id)
                session.add(cfg)
            cfg.daily_points = amount
            await session.commit()

        log.info(
            "%s set daily points to %d in guild %s",
            interaction.user, amount, interaction.guild.id,
        )
        await interaction.response.send_message(
            f"✅ Daily reward set to **{amount:,}** points.", ephemeral=True
        )

    @app_commands.command(name="config_add_noxpchannel", description="Disable XP in a channel")
    @app_commands.describe(channel="Channel to disable XP in")
    @app_commands.default_permissions(administrator=True)
    async def config_add_noxpchannel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        assert interaction.guild is not None

        async with async_session() as session:
            existing = await session.get(NoXPChannel, (interaction.guild.id, channel.id))
            if existing:
                await interaction.response.send_message(
                    f"{channel.mention} is already a no-XP channel.", ephemeral=True
                )
                return
            session.add(NoXPChannel(guild_id=interaction.guild.id, channel_id=channel.id))
            await session.commit()

        log.info(
            "%s disabled XP in #%s (%s) in guild %s",
            interaction.user, channel.name, channel.id, interaction.guild.id,
        )
        await interaction.response.send_message(
            f"✅ XP disabled in {channel.mention}.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
