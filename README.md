# avia_bot

A simple **flight-search Telegram bot**. Users ask for flights between cities and
`avia_bot` replies with the cheapest available options.

The application is structured so its core (flight search + reply formatting) is
made of pure, synchronous functions. That means the whole thing can be run and
tested offline — no Telegram token and no external API required.

## Project layout

| Path | Purpose |
| --- | --- |
| `avia_bot/flights.py` | Flight data model and the in-memory search service. |
| `avia_bot/responses.py` | Pure builders turning parsed input into reply text. |
| `avia_bot/bot.py` | Thin Telegram wiring + `python -m avia_bot.bot` entry point. |
| `avia_bot/demo.py` | Offline CLI that drives the same logic as the bot. |
| `tests/` | `pytest` unit tests for the search core and responses. |

## Requirements

- Python 3.10+
- Runtime: `python-telegram-bot` (only needed to run the live bot)
- Dev/test: `pytest`

## Setup

```bash
# Ubuntu 24.04 ships an externally-managed Python, hence --break-system-packages.
pip install --break-system-packages -r requirements-dev.txt
```

## Run

### Offline demo (no token needed)

```bash
python -m avia_bot.demo               # scripted conversation
python -m avia_bot.demo --interactive # type your own commands
```

### Tests

```bash
pytest
```

### Live Telegram bot

```bash
cp .env.example .env      # then paste your token from @BotFather
export TELEGRAM_BOT_TOKEN=...
python -m avia_bot.bot
```

## Commands

- `/start` — welcome message
- `/help` — list commands
- `/cities` — supported cities
- `/search <from> <to> [YYYY-MM-DD]` — find flights, e.g. `/search LON NYC 2026-09-05`

Cities can be given as names (`Tashkent`, `New York`) or codes (`TAS`, `NYC`).
