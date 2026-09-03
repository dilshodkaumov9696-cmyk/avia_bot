import datetime as dt

from avia_bot import calendar_ui


def test_build_calendar_structure():
    rows = calendar_ui.build_calendar(2026, 9, today=dt.date(2026, 9, 1))
    assert rows[0][0][1] == "cal:trip:ow"
    assert rows[0][1][1] == "cal:trip:rt"
    header = rows[1]
    assert header[0][1].startswith("cal:nav:")
    assert "Сентябрь 2026" in header[1][0]
    assert header[2][1].startswith("cal:nav:")
    assert [c[0] for c in rows[2]] == list(calendar_ui.WEEKDAYS_RU)
    assert ("Сегодня", "cal:today") in rows[-3]
    assert ("Завтра", "cal:tomorrow") in rows[-3]
    assert ("+3 дня", "cal:plus:3") in rows[-2]
    assert ("+7 дней", "cal:plus:7") in rows[-2]
    assert rows[-1][0][1] == "cal:clear"
    assert rows[-1][1][1] == "cal:done"


def test_day_callback_and_selection_mark():
    selected = [dt.date(2026, 9, 17)]
    rows = calendar_ui.build_calendar(2026, 9, selected, today=dt.date(2026, 9, 1))
    flat = [cell for row in rows for cell in row]
    assert ("✓17", "cal:day:2026-09-17") in flat
    assert ("5", "cal:day:2026-09-05") in flat
    assert ("1•", "cal:day:2026-09-01") in flat


def test_roundtrip_toggle_and_range_marks():
    ow = calendar_ui.build_calendar(2026, 9, roundtrip=False)
    rt = calendar_ui.build_calendar(2026, 9, roundtrip=True)
    assert "✓" in ow[0][0][0]
    assert "⇄" in rt[0][1][0]
    assert "✓" in rt[0][1][0]

    rows = calendar_ui.build_calendar(
        2026, 9, roundtrip=True, today=dt.date(2026, 9, 1),
        dep=dt.date(2026, 9, 10), ret=dt.date(2026, 9, 14),
    )
    flat = dict(cell for row in rows for cell in row)
    assert flat["→10"] == "cal:day:2026-09-10"
    assert flat["←14"] == "cal:day:2026-09-14"
    assert flat["·12"] == "cal:day:2026-09-12"


def test_shift_month_wraps_year():
    assert calendar_ui.shift_month(2026, 12, 1) == (2027, 1)
    assert calendar_ui.shift_month(2026, 1, -1) == (2025, 12)


def test_done_label_override():
    rows = calendar_ui.build_calendar(2026, 9, done_label="Найти · 17 сентября")
    assert rows[-1][1][0] == "Найти · 17 сентября"
