import os

from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN: str = os.environ["DISCORD_TOKEN"]
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db")
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# XP defaults (admins can override per-guild via /config)
DEFAULT_XP_MIN = 15
DEFAULT_XP_MAX = 25
DEFAULT_XP_COOLDOWN = 60  # seconds between XP-earning messages
DEFAULT_DAILY_XP = 500
