# AGENTS.md

## Cursor Cloud specific instructions

### Overview

BarkingPuppy is a Discord gamification bot (Python 3.12, discord.py, async SQLAlchemy + asyncpg, Redis, pydantic-settings).

### Dependencies

- `pip install -r requirements.txt` installs: discord.py, python-dotenv, sqlalchemy, asyncpg, redis, pydantic-settings.
- PostgreSQL must be running for database features (default: `localhost:5432/barkingpuppy`).
- Redis must be running for cooldown features (default: `localhost:6379`).

### Required env vars

All four are required in `.env` (see `.env.example`). The bot exits with a clear error listing any missing fields.

| Variable | Type | Example |
|----------|------|---------|
| `DISCORD_BOT_TOKEN` | str | Bot token from Developer Portal |
| `DATABASE_URL` | str | `postgresql+asyncpg://postgres:postgres@localhost:5432/barkingpuppy` |
| `REDIS_URL` | str | `redis://localhost:6379/0` |
| `DISCORD_GUILD_ID` | int | `123456789012345678` |

### Running / Testing

- **Run bot:** `python3 -m app.bot`
- **Lint:** `python3 -m ruff check .` (install ruff separately: `pip install ruff`)
- **Create tables:** `python create_tables.py` (requires running Postgres)

### Non-obvious caveats

- The env var is `DISCORD_BOT_TOKEN` (not `DISCORD_TOKEN`). The Cursor secret is named `DISCORD_TOKEN` — the `.env` file maps it to `DISCORD_BOT_TOKEN`.
- `ruff` is not in `requirements.txt` — install as dev tool. Invoke via `python3 -m ruff` since `~/.local/bin` may not be on `PATH`.
- `.env` is gitignored; copy `.env.example` and fill in real values.
- The bot requires **Message Content Intent** enabled in the Discord Developer Portal (Bot → Privileged Gateway Intents).
- PyNaCl/davey warnings at startup are harmless — voice is not used.
