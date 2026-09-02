---
name: telegram-bot-design
description: Visual and UX design rules for this Telegram flight bot. Use when changing messages, ticket cards, calendars, keyboards, or any user-facing copy.
---

# Telegram flight-bot design

Telegram is not a web app. There is no CSS, no custom fonts, no card component.
Design here is **hierarchy, spacing, and restraint** inside a chat bubble.

## Product feel

The bot should feel like a travel product (Aviasales / Aviatour), not like a
debug console. A user glancing at a phone in 2 seconds must see: **price,
route, time**. Everything else is secondary.

Do **not** dump slash-commands, field labels, or internal names (`origin`,
`pax`, `variant 3 of 8`) into the chat.

## Ticket card (most important)

A ticket card is a **receipt**, not a log line.

Required order:

1. **Price** — one bold line, with currency symbol (`5 979 ₽`), optional tiny tag
   (`самый дешёвый` / `самый быстрый`) on the same visual block.
2. **Timeline** — monospace route: `SVO  09:40 ——— 5ч 20м ——— 16:00  LBD`
   City names under the codes, not a separate “— Туда:” heading.
3. **Meta** — airline · direct/stops · baggage, in one quiet line.
4. **Date** — short (`чт, 17 сен`), not a timestamp dump.

Never stack more than one emoji per line. Prefer typography over emoji.
Do not prefix every line with an icon (`💰 🛫 📅 🕐 🧳`).

Buttons under the card, in this order:

- pagination `‹  2 / 8  ›`
- primary CTA: `Забронировать · 5 979 ₽`
- secondary: `Отслеживать` · `Новый поиск`

The buy button is the only “loud” control. Filters and ±3 days live one tap
behind, not on the first row.

## Reply keyboard = chrome

The 2-column reply keyboard is the product shell. Keep it stable:

| Найти билеты | Куда улететь дешево |
| Мои алерты   | Календарь цен       |
| Кабинет      | Подписка            |
| Язык         | Помощь              |

Do not rename these every iteration. Discover, alerts, calendar, cabinet and
premium must be reachable without `/commands`.

## Calendar

Search calendar shows **dates only** — a number, a checkmark, today/tomorrow.
Do **not** cram prices into day cells (they wrap, overlap, and look broken).

Prices belong in **Календарь цен** as a list + chart, not inside the date grid.

Always offer one-way / round-trip as a toggle on the calendar, not as a
separate conversation step.

## Airport search

Users type whatever they remember: city, country, airport name, IATA (`LED`),
sometimes ICAO. Results are short buttons:

`SVO · Шереметьево, Москва`

Not: `Москва Шереметьево, Россия (SVO)`.

Country queries list that country’s main airports (large first), paginated.
Empty state says *what* to type, with one example — not “error”.

## Copy

- Russian default; keep other languages in the same tone.
- Short sentences. No stack traces, no “engine”, no “TJS base fare”.
- Simulated prices: one quiet footnote, not a banner.
- Passenger step is a summary card (`Взрослые 1 · Эконом · 1/9`), not a form.

## When editing UI

Re-read this skill, then change `responses.py` (what the user sees) before
`bot.py` (how it is wired). If a string looks like a variable name or a log
line, it does not ship.
