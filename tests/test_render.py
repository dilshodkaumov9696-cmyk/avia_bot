import datetime as dt

from avia_bot.responses import aviasales_url, render_html, render_plain


def test_render_html_converts_markup():
    assert render_html("*bold*") == "<b>bold</b>"
    assert render_html("`code`") == "<code>code</code>"
    assert render_html("plain") == "plain"


def test_render_html_escapes_special_chars():
    # Angle brackets and ampersands must be escaped so Telegram HTML is valid.
    out = render_html("/search <from> <to> A&B")
    assert "<from>" not in out
    assert "&lt;from&gt;" in out
    assert "&amp;" in out


def test_render_html_is_emoji_safe():
    # The original crash was emoji + markup in legacy Markdown; HTML must be fine.
    out = render_html("\u2708\ufe0f *AviaBot* \U0001f525 `TAS`")
    assert "<b>AviaBot</b>" in out
    assert "<code>TAS</code>" in out
    assert "\u2708" in out  # emoji preserved


def test_render_plain_strips_markup():
    assert render_plain("*bold* and `code`") == "bold and code"


def test_aviasales_url_one_way():
    url = aviasales_url("LON", "NYC", dt.date(2026, 9, 5), passengers=1)
    assert url == "https://www.aviasales.com/search/LON0509NYC1"


def test_aviasales_url_round_trip():
    url = aviasales_url("LON", "NYC", dt.date(2026, 9, 5), back_date=dt.date(2026, 9, 12), passengers=2)
    assert url == "https://www.aviasales.com/search/LON0509NYC12092"
