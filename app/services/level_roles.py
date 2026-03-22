import logging

import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LevelRole

log = logging.getLogger("barkingpuppy.roles")


async def apply_level_roles(
    session: AsyncSession,
    member: discord.Member,
    guild_id: int,
    level: int,
) -> None:
    """Assign the highest eligible level role and remove lower ones."""
    result = await session.execute(
        select(LevelRole)
        .where(LevelRole.guild_id == guild_id)
        .order_by(LevelRole.level_required.desc())
    )
    all_roles = result.scalars().all()

    if not all_roles:
        return

    level_role_ids = {lr.role_id for lr in all_roles}

    # Find the highest role the user qualifies for
    highest = None
    for lr in all_roles:
        if lr.level_required <= level:
            highest = lr
            break

    for lr in all_roles:
        role = member.guild.get_role(lr.role_id)
        if role is None:
            continue

        if highest and lr.role_id == highest.role_id:
            if role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"Reached level {level}")
                    log.info("Assigned role %s to %s", role.name, member)
                except discord.Forbidden:
                    log.warning("Missing permissions to assign role %s", role.name)
        else:
            if role in member.roles and lr.role_id in level_role_ids:
                try:
                    await member.remove_roles(role, reason="No longer highest level role")
                    log.info("Removed role %s from %s", role.name, member)
                except discord.Forbidden:
                    log.warning("Missing permissions to remove role %s", role.name)
