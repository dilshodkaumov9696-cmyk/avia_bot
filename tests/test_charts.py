import datetime as dt

from avia_bot import charts
from avia_bot.flights import FlightService
from avia_bot.tracking import PriceTracker

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_render_range_chart_returns_png():
    service = FlightService()
    offers = service.search_range("LON", "NYC", dt.date(2026, 9, 1), dt.date(2026, 9, 6), tick=1000)
    png = charts.render_range_chart(offers)
    assert png.startswith(PNG_MAGIC)
    assert len(png) > 1000


def test_render_history_chart_returns_png():
    service = FlightService()
    tracker = PriceTracker(service)
    tracker.add(1, "LON", "PAR", dt.date(2026, 9, 5), tick=1)
    tracker.poll(2)
    tracker.poll(3)
    track = tracker.list_for(1)[0]
    png = charts.render_history_chart(track)
    assert png.startswith(PNG_MAGIC)
    assert len(png) > 1000
