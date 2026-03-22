# AGENTS.md

## Cursor Cloud specific instructions

### Overview

BarkingPuppy is a Discord gamification bot (Python 3.12, discord.py, async SQLAlchemy + asyncpg, Redis, pydantic-settings).

### Dependencies

- `pip install -r requirements.txt` installs: discord.py, python-dotenv, sqlalchemy, asyncpg, redis, pydantic-settings.
- PostgreSQL must be running for database operations (default: `localhost:5432/barkingpuppy`). Not needed for bot-only startup.
- Redis must be running on `localhost:6379` for cooldown features.

### Running / Testing

- **Lint:** `python3 -m ruff check .` (install ruff separately: `pip install ruff`).
- **Create tables:** `python create_tables.py` (requires a running Postgres instance).
- **Run bot:** `python -c "from app.bot import run; run()"` — requires valid `DISCORD_TOKEN` in `.env` or as env var.
- Config is loaded via pydantic-settings from `.env` — see `.env.example` for required vars.

### Non-obvious caveats

- The bot can start and connect to Discord without Postgres or Redis; those are only needed when cogs/services use them.
- `ruff` is not in `requirements.txt` — install it as a dev tool (`pip install ruff`). Invoke via `python3 -m ruff` since `~/.local/bin` may not be on `PATH`.
- `.env` is gitignored; copy `.env.example` and fill in real values.
- `DISCORD_TOKEN` must be a valid bot token from the Discord Developer Portal (https://discord.com/developers/applications → Bot → Reset Token). If the token returns 401, it has been regenerated or was never valid — a new token must be generated.
- The bot requires **Message Content** and **Server Members** privileged intents enabled in the Discord Developer Portal under the Bot settings page.
- PyNaCl/davey warnings at startup ("voice will NOT be supported") are harmless and expected — voice is not used.
- `DATABASE_URL` is a required config field; even if Postgres isn't running, a placeholder value must be in `.env` for config to load.
