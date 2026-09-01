import datetime as dt

from avia_bot import charts
from avia_bot.flights import FlightService
from avia_bot.pricing import Passengers
from avia_bot.tracking import PriceTracker

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
DATE = dt.date(2026, 9, 17)


def test_render_range_chart_png():
    svc = FlightService()
    points = svc.search_range("MOW", "LBD", DATE, DATE + dt.timedelta(days=5), tick=1000)
    png = charts.render_range_chart("Москва", "Худжанд", points)
    assert png.startswith(PNG_MAGIC) and len(png) > 1000


def test_render_history_chart_png():
    svc = FlightService()
    tracker = PriceTracker(svc)
    tracker.add(1, "MOW", "LBD", DATE, pax=Passengers(), tick=1)
    tracker.poll(2)
    tracker.poll(3)
    png = charts.render_history_chart(tracker.list_for(1)[0])
    assert png.startswith(PNG_MAGIC) and len(png) > 1000
