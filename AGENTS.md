# AGENTS.md

## Cursor Cloud specific instructions

### Overview

BarkingPuppy is a Discord gamification bot (Python 3.12, discord.py, async SQLAlchemy + asyncpg, Redis, pydantic-settings).

### Dependencies

- `pip install -r requirements.txt` installs: discord.py, python-dotenv, sqlalchemy, asyncpg, redis, pydantic-settings.
- PostgreSQL is needed for database operations but not for bot-only startup (`DATABASE_URL` defaults to empty).
- Redis is needed for cooldown features but not for bot-only startup.

### Running / Testing

- **Run bot:** `python3 -m app.bot` — requires `DISCORD_BOT_TOKEN` in `.env` or as env var.
- **Lint:** `python3 -m ruff check .` (install ruff separately: `pip install ruff`).
- **Create tables:** `python create_tables.py` (requires a running Postgres instance + `DATABASE_URL` set).
- Config is loaded via pydantic-settings from `.env` — see `.env.example` for required vars.

### Non-obvious caveats

- The env var is `DISCORD_BOT_TOKEN` (not `DISCORD_TOKEN`).
- The bot can start without Postgres or Redis; those are only needed when cogs/services use them.
- `ruff` is not in `requirements.txt` — install as dev tool. Invoke via `python3 -m ruff` since `~/.local/bin` may not be on `PATH`.
- `.env` is gitignored; copy `.env.example` and fill in real values.
- The bot requires **Message Content Intent** enabled in the Discord Developer Portal (Bot → Privileged Gateway Intents).
- PyNaCl/davey warnings at startup are harmless — voice is not used.
