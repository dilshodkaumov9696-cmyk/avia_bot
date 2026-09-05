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

## Reply keyboard = chrome

The 2-column reply keyboard is the product shell. Keep it **persistent**
(`is_persistent=True`) so it stays on screen while the user picks an airport
from the inline list under a message. One icon per button, names stay stable:

| 🔎 Найти билеты | 🌍 Куда улететь |
| 🔔 Мои алерты   | 📅 Календарь цен |
| 👤 Кабинет      | ⭐ Подписка      |
| 🌐 Язык         | ❓ Помощь        |

Airport choices are **inline buttons under the message**, not a text dump and
not a replacement for this chrome.

## Airport search

Users type whatever they remember: city, country, airport name, IATA (`LED`),
sometimes ICAO. Results are short **flag + code + name** buttons:

`🇷🇺 SVO · Шереметьево`

Not: `Москва Шереметьево, Россия (SVO)`.

Country queries list that country’s main airports (large first), paginated.
Empty state says *what* to type, with one example — not “error”.

## Ticket card (most important)

A ticket card is a **receipt**, not a log line and not a monospace test dump.

Required order:

1. **Price** — one bold line (`5 979 ₽`), optional tag (`самый дешёвый`) under it.
2. **Route** — cities with flags: `🇷🇺 Москва → 🇹🇯 Худжанд`. Round-trip uses `⇄`.
3. **Date** — short (`чт, 17 сен`), passengers only if more than one adult.
4. **Times** — human lines, not `SVO ——— 5ч ——— LBD`:
   `09:40  Шереметьево (SVO)` / `16:00  Худжанд (LBD)` / `в пути 5ч 20м · прямой`.
5. **Airline** — a *small* logo on the ticket photo (icon, not a poster), plus
   `Аэрофлот · SU 142 · багаж` in the caption. Show `2 / 15` on the card so
   pagination is obvious. Never a bare carrier string without IATA.

Filters under the card: direct / with stops, with bags / no bags.

Never stack more than one emoji per line. Prefer typography over emoji.
Do not prefix every line with an icon (`💰 🛫 📅 🕐 🧳`).
Do not print a “cache / not an offer” debug footnote on the card.

Buttons under the card, in this order:

- pagination `‹  2 / 8  ›`
- primary CTA: `Забронировать · 5 979 ₽`
- secondary: `Отслеживать` · `Новый поиск`

The buy button is the only “loud” control. Filters and ±3 days live one tap
behind, not on the first row.

## Calendar

Search calendar shows **dates only** — a number, a check, today/tomorrow,
+3 / +7, clear, and a search CTA. Do **not** cram prices into day cells.

Always offer one-way / round-trip as a toggle **with ➝ / ⇄**, not as a
separate conversation step.

Marks: `✓17` one-way, `→10` outbound, `←14` return, `·12` days in between.

Prices belong in **Календарь цен** as a list + chart, not inside the date grid.

## Copy

- Russian default; keep other languages in the same tone.
- Short sentences. No stack traces, no “engine”, no “TJS base fare”.
- Passenger step is a summary card (`Взрослые 1 · Эконом · 1/9`), not a form.

## When editing UI

Re-read this skill, then change `responses.py` (what the user sees) before
`bot.py` (how it is wired). If a string looks like a variable name or a log
line, it does not ship.
