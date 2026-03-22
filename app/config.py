import sys

from pydantic import ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DISCORD_BOT_TOKEN: str
    DATABASE_URL: str
    REDIS_URL: str
    DISCORD_GUILD_ID: int

    class Config:
        env_file = ".env"


try:
    settings = Settings()
except ValidationError as e:
    print("ERROR: Missing or invalid environment variables:\n")
    for err in e.errors():
        field = err["loc"][0]
        print(f"  - {field}: {err['msg']}")
    print("\nCheck your .env file. See .env.example for reference.")
    sys.exit(1)
