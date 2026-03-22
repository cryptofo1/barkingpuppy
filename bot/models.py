from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserXP(Base):
    """Per-user, per-guild XP and level tracking."""

    __tablename__ = "user_xp"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=0)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)


class GuildConfig(Base):
    """Per-guild bot configuration set by admins."""

    __tablename__ = "guild_config"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    xp_min: Mapped[int] = mapped_column(Integer, default=15)
    xp_max: Mapped[int] = mapped_column(Integer, default=25)
    xp_cooldown: Mapped[int] = mapped_column(Integer, default=60)
    daily_xp: Mapped[int] = mapped_column(Integer, default=500)


class LevelRole(Base):
    """Maps a level threshold to a Discord role for a guild."""

    __tablename__ = "level_roles"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    level: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(BigInteger)
    role_name: Mapped[str] = mapped_column(String(100))
