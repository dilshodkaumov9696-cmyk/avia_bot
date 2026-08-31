"""Inline calendar model (pure): builds a month grid of (label, callback_data).

Kept free of python-telegram-bot so it can be unit-tested; the bot converts the
rows into ``InlineKeyboardButton``s. Callback scheme:

- ``cal:nav:YYYY-MM`` — show that month
- ``cal:day:YYYY-MM-DD`` — pick a day
- ``cal:done`` — finish selection
- ``cal:x`` — inert cell (header / padding)
"""

from __future__ import annotations

import calendar as _cal
import datetime as _dt
from typing import List, Sequence, Tuple

Row = List[Tuple[str, str]]

MONTHS_RU = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]
WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def shift_month(year: int, month: int, delta: int) -> Tuple[int, int]:
    index = (year * 12 + (month - 1)) + delta
    return index // 12, index % 12 + 1


def build_calendar(year: int, month: int, selected: Sequence[_dt.date] = ()) -> List[Row]:
    selected_set = set(selected)
    prev_y, prev_m = shift_month(year, month, -1)
    next_y, next_m = shift_month(year, month, 1)

    rows: List[Row] = [
        [
            ("«", f"cal:nav:{prev_y:04d}-{prev_m:02d}"),
            (f"{MONTHS_RU[month]} {year}", "cal:x"),
            ("»", f"cal:nav:{next_y:04d}-{next_m:02d}"),
        ],
        [(wd, "cal:x") for wd in WEEKDAYS_RU],
    ]

    for week in _cal.Calendar(firstweekday=0).monthdayscalendar(year, month):
        row: Row = []
        for day in week:
            if day == 0:
                row.append((" ", "cal:x"))
            else:
                date = _dt.date(year, month, day)
                label = f"✅{day}" if date in selected_set else str(day)
                row.append((label, f"cal:day:{date.isoformat()}"))
        rows.append(row)

    rows.append([("✅ Готово", "cal:done")])
    return rows
