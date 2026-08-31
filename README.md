# avia_bot

A **flight-search & price-tracking Telegram bot**, inspired by
[@aviagram_bot](https://t.me/aviagram_bot). Users search flights, compare prices
across a date range, book round trips for several passengers, watch a route and
get notified when the fare drops, and view price charts right in the chat.

The core (search, pricing, tracking, chart data) is made of pure, synchronous
functions, so the whole thing runs and is tested **offline** — no Telegram token
and no external API required. Flight data is simulated by a deterministic
in-memory engine; the data layer is isolated so a real provider can be plugged
in later.

## Features

| Feature | Command |
| --- | --- |
| 🔎 Search by route & date | `/search London Dubai 2026-09-05` |
| 📅 Cheapest day in a range | `/range LON NYC 2026-09-01 2026-09-10` |
| 🔁 Round trip | `/rt LON NYC 2026-09-05 2026-09-12` |
| 👥 Passengers (append a number) | `/search LON NYC 2026-09-05 2` |
| 👀 Track price (drop alerts) | `/track LON NYC 2026-09-05` |
| 📊 Price charts | inline **📊 График цен** button / on tracking alerts |
| 🔥 Hot deals | `/hot` |
| 🗂 My tracks | `/mytracks` |

Cities can be names (`Tashkent`, `New York`) or codes (`TAS`, `NYC`).

## Project layout

| Path | Purpose |
| --- | --- |
| `avia_bot/flights.py` | Flight catalogue + search (route, date range, round trip, deals). |
| `avia_bot/pricing.py` | Dynamic pricing engine (prices move over time). |
| `avia_bot/tracking.py` | Price-tracking store + drop detection. |
| `avia_bot/charts.py` | matplotlib price charts (range & history) → PNG. |
| `avia_bot/responses.py` | Pure builders turning parsed input into reply text. |
| `avia_bot/bot.py` | Telegram wiring: inline menu, callbacks, JobQueue tracking. |
| `avia_bot/demo.py` | Offline CLI driving the same logic as the bot. |
| `tests/` | `pytest` unit tests. |

## Setup

```bash
# Ubuntu 24.04 ships an externally-managed Python, hence --break-system-packages.
pip install --break-system-packages -r requirements-dev.txt
```

## Run

### Offline demo (no token)

```bash
python -m avia_bot.demo                      # scripted conversation + tracking sim
python -m avia_bot.demo --charts-dir ./out   # also save example PNG charts
python -m avia_bot.demo --interactive        # type your own commands
```

### Tests

```bash
pytest
```

### Live Telegram bot

```bash
export TELEGRAM_BOT_TOKEN=...                 # from @BotFather
# optional: how often to re-check tracked prices (seconds, default 1800 = 30 min)
export AVIA_TRACK_INTERVAL_SECONDS=1800
python -m avia_bot.bot
```

Price tracking runs on the bot's JobQueue every `AVIA_TRACK_INTERVAL_SECONDS`
(default 30 minutes, matching AviaGram) and messages the chat when a fare drops.
