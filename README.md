# BarkingPuppy

A Discord gamification bot built with Python, discord.py, async SQLAlchemy, and Redis.

## Features (Phase 1)

- **XP system** — earn random XP per message
- **Leveling** — quadratic level curve with level-up announcements
- **Daily rewards** — `/daily` gives a fixed XP bonus (24 h cooldown)
- **Leaderboard** — `/leaderboard` shows top 10 by XP
- **Anti-farm** — per-user cooldown prevents XP spam (configurable)
- **Admin config** — `/config` lets admins tune XP range, cooldown, daily amount
- **Level roles** — `/levelrole add/remove/list` maps levels to Discord roles

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy the example env and add your Discord bot token
cp .env.example .env
# edit .env → set DISCORD_TOKEN

# 3. Start Redis
redis-server --daemonize yes

# 4. Run the bot
python main.py
```

## Slash Commands

| Command | Description |
|---------|-------------|
| `/rank` | Show your XP, level, and progress |
| `/daily` | Claim daily XP reward |
| `/leaderboard` | Top 10 users by XP |
| `/config` | View/update server XP settings (admin) |
| `/levelrole add` | Map a level to a role reward (admin) |
| `/levelrole remove` | Remove a level-role mapping (admin) |
| `/levelrole list` | List all level-role mappings |

## Project Structure

```
main.py              # Bot entry point
bot/
  config.py          # Environment config + defaults
  models.py          # SQLAlchemy models (UserXP, GuildConfig, LevelRole)
  database.py        # Async engine + session factory
  redis_client.py    # Redis connection pool
  xp.py              # XP/leveling math
  cogs/
    xp.py            # Message XP + /rank
    daily.py         # /daily
    leaderboard.py   # /leaderboard
    admin.py         # /config
    roles.py         # /levelrole group
tests/
  test_startup.py    # Smoke tests
  test_bot_setup.py  # Cog-loading test
```

## Running Tests

```bash
python tests/test_startup.py
python tests/test_bot_setup.py
```
