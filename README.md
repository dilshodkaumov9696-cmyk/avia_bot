# avia_bot

Telegram-бот поиска авиабилетов. Работает офлайн без API: цены и рейсы
симулируются, слой данных изолирован — живой провайдер можно подключить позже.

## Что умеет

- **Поиск аэропортов мира** — 5300+ аэропортов: страна, город, название, IATA (`LED`)
- **Карточка билета** — цена, таймлайн `SVO 09:40 ——— 5ч ——— 16:00 LBD`, бронь / трекинг
- Меню как в старом боте: найти билеты, куда дешево, алерты, календарь цен, кабинет, подписка
- Календарь: туда / туда-обратно, сегодня / завтра
- 9 языков и валюты, отслеживание цены, горящие направления

## Запуск

```bash
pip install --break-system-packages -r requirements-dev.txt
python -m avia_bot.demo
pytest
export TELEGRAM_BOT_TOKEN=...
python -m avia_bot.bot
```

База аэропортов: OurAirports (`avia_bot/data/airports.json.gz`).
Пересборка: `python3 scripts/build_airports.py /path/to/ourairports-csvs`.
