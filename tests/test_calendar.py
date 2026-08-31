import datetime as dt

from avia_bot import calendar_ui


def test_build_calendar_structure():
    rows = calendar_ui.build_calendar(2026, 9)
    header = rows[0]
    assert header[0][1].startswith("cal:nav:")
    assert "Сентябрь 2026" in header[1][0]
    assert header[2][1].startswith("cal:nav:")
    assert [c[0] for c in rows[1]] == calendar_ui.WEEKDAYS_RU
    assert rows[-1][0] == ("✅ Готово", "cal:done")


def test_day_callback_and_selection_mark():
    selected = [dt.date(2026, 9, 17)]
    rows = calendar_ui.build_calendar(2026, 9, selected)
    flat = [cell for row in rows for cell in row]
    assert ("✅17", "cal:day:2026-09-17") in flat
    assert ("5", "cal:day:2026-09-05") in flat


def test_shift_month_wraps_year():
    assert calendar_ui.shift_month(2026, 12, 1) == (2027, 1)
    assert calendar_ui.shift_month(2026, 1, -1) == (2025, 12)
