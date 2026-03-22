from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GuildConfig, User


def xp_needed(level: int) -> int:
    return 5 * level * level + 50 * level + 100


async def get_or_create_user(
    session: AsyncSession, user_id: int, guild_id: int
) -> User:
    user = await session.get(User, (user_id, guild_id))
    if user is None:
        user = User(discord_user_id=user_id, guild_id=guild_id, xp=0, points=0, level=0)
        session.add(user)
    return user


async def get_guild_config(session: AsyncSession, guild_id: int) -> GuildConfig:
    """Return the guild config, or a default-valued transient instance."""
    cfg = await session.get(GuildConfig, guild_id)
    if cfg is None:
        cfg = GuildConfig(guild_id=guild_id)
    return cfg


async def get_or_create_config(
    session: AsyncSession, guild_id: int
) -> GuildConfig:
    """Return the guild config, creating and persisting it if missing."""
    cfg = await session.get(GuildConfig, guild_id)
    if cfg is None:
        cfg = GuildConfig(guild_id=guild_id)
        session.add(cfg)
    return cfg


async def add_xp(
    session: AsyncSession, user_id: int, guild_id: int, amount: int
) -> tuple[User, bool]:
    """Add XP to a user. Returns (user, leveled_up)."""
    user = await get_or_create_user(session, user_id, guild_id)

    user.xp += amount
    leveled_up = False

    while user.xp >= xp_needed(user.level):
        user.xp -= xp_needed(user.level)
        user.level += 1
        leveled_up = True

    await session.commit()
    return user, leveled_up


async def add_points(
    session: AsyncSession, user_id: int, guild_id: int, amount: int
) -> User:
    """Add points to a user. Returns the user."""
    user = await get_or_create_user(session, user_id, guild_id)
    user.points += amount
    await session.commit()
    return user
