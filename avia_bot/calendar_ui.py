"""Inline calendar model (pure): month grid of (label, callback_data).

Kept free of python-telegram-bot so it can be unit-tested. Callback scheme:

- ``cal:nav:YYYY-MM`` — show that month
- ``cal:day:YYYY-MM-DD`` — pick a day
- ``cal:trip:ow`` / ``cal:trip:rt`` — one-way / round-trip
- ``cal:today`` / ``cal:tomorrow`` — jump to today / tomorrow
- ``cal:plus:N`` — departure = today + N days
- ``cal:clear`` — reset dates
- ``cal:done`` — finish selection
- ``cal:x`` — inert cell (header / padding)
"""

from __future__ import annotations

import calendar as _cal
import datetime as _dt
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

Row = List[Tuple[str, str]]

MONTHS_RU = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]
WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


@dataclass(frozen=True)
class Labels:
    """Button copy; bot passes i18n, tests use Russian defaults."""

    ow: str = "➝  одна"
    rt: str = "⇄  туда-обратно"
    today: str = "Сегодня"
    tomorrow: str = "Завтра"
    plus3: str = "+3 дня"
    plus7: str = "+7 дней"
    clear: str = "Сбросить"
    done: str = "Найти билеты"
    weekdays: Tuple[str, ...] = field(default_factory=lambda: tuple(WEEKDAYS_RU))
    months: Tuple[str, ...] = field(default_factory=lambda: tuple(MONTHS_RU))


def shift_month(year: int, month: int, delta: int) -> Tuple[int, int]:
    index = (year * 12 + (month - 1)) + delta
    return index // 12, index % 12 + 1


def _mark(text: str, on: bool) -> str:
    return f"{text}  ✓" if on else text


def _day_label(
    date: _dt.date,
    *,
    today: _dt.date,
    dep: Optional[_dt.date],
    ret: Optional[_dt.date],
    roundtrip: bool,
) -> str:
    day = date.day
    if dep and date == dep and ret and date == ret:
        return f"⇄{day}"
    if dep and date == dep:
        return f"→{day}" if roundtrip else f"✓{day}"
    if ret and date == ret:
        return f"←{day}"
    if dep and ret and dep < date < ret:
        return f"·{day}"
    if date == today:
        return f"{day}•"
    return str(day)


def build_calendar(
    year: int,
    month: int,
    selected: Sequence[_dt.date] = (),
    *,
    roundtrip: bool = False,
    today: Optional[_dt.date] = None,
    dep: Optional[_dt.date] = None,
    ret: Optional[_dt.date] = None,
    labels: Optional[Labels] = None,
    done_label: Optional[str] = None,
) -> List[Row]:
    labels = labels or Labels()
    today = today or _dt.date.today()
    sel = [d for d in selected if d]
    if dep is None and sel:
        dep = sel[0]
    if ret is None and len(sel) > 1:
        ret = sel[1]
    prev_y, prev_m = shift_month(year, month, -1)
    next_y, next_m = shift_month(year, month, 1)
    months = labels.months if len(labels.months) > month else MONTHS_RU
    weekdays = labels.weekdays if len(labels.weekdays) == 7 else WEEKDAYS_RU
    done = done_label or labels.done

    rows: List[Row] = [
        [(_mark(labels.ow, not roundtrip), "cal:trip:ow"),
         (_mark(labels.rt, roundtrip), "cal:trip:rt")],
        [
            ("‹", f"cal:nav:{prev_y:04d}-{prev_m:02d}"),
            (f"{months[month]} {year}", "cal:x"),
            ("›", f"cal:nav:{next_y:04d}-{next_m:02d}"),
        ],
        [(wd, "cal:x") for wd in weekdays],
    ]

    for week in _cal.Calendar(firstweekday=0).monthdayscalendar(year, month):
        row: Row = []
        for day in week:
            if day == 0:
                row.append((" ", "cal:x"))
            else:
                date = _dt.date(year, month, day)
                label = _day_label(date, today=today, dep=dep, ret=ret, roundtrip=roundtrip)
                row.append((label, f"cal:day:{date.isoformat()}"))
        rows.append(row)

    rows.append([(labels.today, "cal:today"), (labels.tomorrow, "cal:tomorrow")])
    rows.append([(labels.plus3, "cal:plus:3"), (labels.plus7, "cal:plus:7")])
    rows.append([(labels.clear, "cal:clear"), (done, "cal:done")])
    return rows
