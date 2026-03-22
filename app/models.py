from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    discord_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    points: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=0)
    last_daily_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class GuildConfig(Base):
    __tablename__ = "guild_configs"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    xp_min: Mapped[int] = mapped_column(Integer, default=15)
    xp_max: Mapped[int] = mapped_column(Integer, default=25)
    message_cooldown: Mapped[int] = mapped_column(Integer, default=60)
    daily_points: Mapped[int] = mapped_column(Integer, default=100)
    hourly_xp_cap: Mapped[int] = mapped_column(Integer, default=300)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.xp_min is None:
            self.xp_min = 15
        if self.xp_max is None:
            self.xp_max = 25
        if self.message_cooldown is None:
            self.message_cooldown = 60
        if self.daily_points is None:
            self.daily_points = 100
        if self.hourly_xp_cap is None:
            self.hourly_xp_cap = 300


class LevelRole(Base):
    __tablename__ = "level_roles"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    level_required: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(BigInteger)


class NoXPChannel(Base):
    __tablename__ = "no_xp_channels"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
