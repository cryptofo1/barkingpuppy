from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


def xp_needed(level: int) -> int:
    return 5 * level * level + 50 * level + 100


def _get_or_create(session: AsyncSession, user: User | None, user_id: int, guild_id: int) -> User:
    if user is not None:
        return user
    user = User(discord_user_id=user_id, guild_id=guild_id, xp=0, points=0, level=0)
    session.add(user)
    return user


async def add_xp(session: AsyncSession, user_id: int, guild_id: int, amount: int) -> tuple[User, bool]:
    """Add XP to a user. Returns (user, leveled_up)."""
    user = await session.get(User, (user_id, guild_id))
    user = _get_or_create(session, user, user_id, guild_id)

    user.xp += amount
    leveled_up = False

    while user.xp >= xp_needed(user.level):
        user.xp -= xp_needed(user.level)
        user.level += 1
        leveled_up = True

    await session.commit()
    return user, leveled_up


async def add_points(session: AsyncSession, user_id: int, guild_id: int, amount: int) -> User:
    """Add points to a user. Returns the user."""
    user = await session.get(User, (user_id, guild_id))
    user = _get_or_create(session, user, user_id, guild_id)

    user.points += amount
    await session.commit()
    return user
