# AGENTS.md

## Cursor Cloud specific instructions

### Overview

BarkingPuppy is a Discord gamification bot (Python 3.12, discord.py, async SQLAlchemy + asyncpg, Redis, pydantic-settings).

### Dependencies

- `pip install -r requirements.txt` installs: discord.py, python-dotenv, sqlalchemy, asyncpg, redis, pydantic-settings.
- PostgreSQL must be running for the database (default: `localhost:5432/barkingpuppy`).
- Redis must be running on `localhost:6379`.

### Running / Testing

- **Lint:** `python3 -m ruff check .` (install ruff separately: `pip install ruff`).
- **Create tables:** `python create_tables.py` (requires a running Postgres instance).
- **Run bot:** `python -c "from app.bot import run; run()"` — requires `DISCORD_TOKEN` in `.env`.
- Config is loaded via pydantic-settings from `.env` — see `.env.example` for required vars.

### Non-obvious caveats

- `asyncpg` is the async Postgres driver; SQLite is not used. A running Postgres instance is required.
- `ruff` is not in `requirements.txt` — install it as a dev tool (`pip install ruff`).
- `.env` is gitignored; copy `.env.example` and fill in real values.
