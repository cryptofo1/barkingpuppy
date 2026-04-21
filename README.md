# BarkingPuppy

Discord gamification bot — Python, discord.py, SQLAlchemy (asyncpg), Redis.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in your values
python create_tables.py
```

## Run

```bash
python -c "from app.bot import run; run()"
```

## Structure

```
├── .env
├── .env.example
├── requirements.txt
├── create_tables.py
├── app/
│   ├── __init__.py
│   ├── bot.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── cogs/
│   │   └── __init__.py
│   └── services/
│       └── __init__.py
```
