# AGENTS.md

## Cursor Cloud specific instructions

### Overview

BarkingPuppy is a Discord gamification bot (Python 3.12 + discord.py + async SQLAlchemy + Redis).

### Dependencies

- **Python packages:** `pip install -r requirements.txt` (discord.py, sqlalchemy[asyncio], aiosqlite, redis, python-dotenv).
- **Redis server:** Must be running on `localhost:6379` (default). Install via `apt-get install redis-server`, start with `redis-server --daemonize yes`.
- **Linter:** `ruff` — install with `pip install ruff`, run with `python3 -m ruff check .`.

### Running / Testing

- **Smoke tests (no Discord token needed):** `python3 tests/test_startup.py` and `python3 tests/test_bot_setup.py`.
- **Lint:** `python3 -m ruff check .`
- **Run the bot:** `python3 main.py` — requires `DISCORD_TOKEN` env var (or `.env` file).
- The bot uses SQLite by default (`bot.db` in the working directory). Set `DATABASE_URL` to override.

### Non-obvious caveats

- `ruff` installs to `~/.local/bin/` which may not be on `PATH`; invoke via `python3 -m ruff` to be safe.
- Redis must be started before the bot; `init_redis()` in `setup_hook` will fail with a connection error otherwise.
- The bot calls `tree.sync()` on startup, which syncs slash commands globally. This can take up to an hour to propagate in Discord. For faster testing, change to guild-specific sync.
- `aiosqlite` is the async driver for SQLite; swap `DATABASE_URL` to `postgresql+asyncpg://…` for Postgres (add `asyncpg` to requirements).
