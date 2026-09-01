# avia_bot

A **flight-search & price-tracking Telegram bot**, modelled on
[@aviagram_bot](https://t.me/aviagram_bot). It runs a guided, button-driven
conversation: city **from** → pick airport → city **to** → pick airport →
**passengers & cabin** → **calendar** → animated multi-provider search →
**paginated result cards** with filters, price advice, flexible dates, buy links
and one-tap price tracking.

The engine (cities, itineraries, pricing, tracking, charts) is pure and runnable
**offline** — no token, no external API. Flight data is deterministic and
simulated; the data layer is isolated so a real provider can be plugged in.

## Features

- 🔎 **Guided search** — step-by-step with inline buttons (like AviaGram)
- 🏙 **Multiple airports per city** — Москва → MOW / SVO / VKO / DME / ZIA
- 👥 **Passengers & cabin** — adults / children / infants, Эконом / Бизнес
- 🗓 **Inline calendar** — outbound + optional return, month navigation
- 🔀 **Direct & connecting** itineraries with layover city and duration
- 🧳 Baggage flag, seats left, airline, «🔴 Самый быстрый» / «🟢 Самый дешёвый»
- 💰 Prices in **TJS**, discounts vs list price
- 📄 **Pagination** through all found options
- ⚙️ **Filters** — only direct / with baggage
- 💡 **Price advice** — hint whether the fare is rising or falling
- 📅 **Flexible dates ±3** — cheapest nearby day, with chart
- 🔎🗓 **Range search** — cheapest day across a range (bar chart)
- 👀 **Price tracking** — JobQueue re-checks every 30 min, alerts + history chart
- 🔥 **/hot** — best current discounts
- 🔗 **Buy** — real Aviasales deep-link

## Project layout

| Path | Purpose |
| --- | --- |
| `avia_bot/geo.py` | Cities & airports + fuzzy city search. |
| `avia_bot/flights.py` | Itinerary engine (stops, baggage, seats, filters). |
| `avia_bot/pricing.py` | Market/season/cabin pricing, passenger mix, TJS, trend. |
| `avia_bot/calendar_ui.py` | Inline calendar model. |
| `avia_bot/search_flow.py` | Passenger/cabin math + pagination. |
| `avia_bot/tracking.py` | Price-tracking store + drop detection. |
| `avia_bot/charts.py` | matplotlib range & history charts → PNG. |
| `avia_bot/responses.py` | RU prompts + result cards (rendered to HTML). |
| `avia_bot/bot.py` | ConversationHandler flow, callbacks, tracking job. |
| `avia_bot/demo.py` | Offline walkthrough of the whole scenario. |
| `tests/` | `pytest` unit + async handler tests. |

## Setup

```bash
# Ubuntu 24.04 ships an externally-managed Python, hence --break-system-packages.
pip install --break-system-packages -r requirements-dev.txt
```

## Run

```bash
python -m avia_bot.demo                    # offline walkthrough
python -m avia_bot.demo --charts-dir ./out # + save example charts
pytest                                     # tests

export TELEGRAM_BOT_TOKEN=...              # from @BotFather
export AVIA_TRACK_INTERVAL_SECONDS=1800    # price-check cadence (default 30 min)
python -m avia_bot.bot                      # live bot
```

## Commands & buttons

- `/start` — welcome + reply keyboard (🔎 Поиск · 🔎🗓 По диапазону · ➕👀 Добавить отслеживание)
- `/search` — start the guided search (same as 🔎 Поиск)
- `/hot` — hot deals · `/mytracks` — your tracked routes · `/cancel` — cancel a flow
