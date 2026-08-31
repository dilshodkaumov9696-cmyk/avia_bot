"""Price charts rendered to PNG bytes with matplotlib (headless Agg backend).

Used for two things the bot shows in chat:
- a price-by-date chart for a date-range search, and
- a price-history chart for a tracked route.
"""

from __future__ import annotations

import io
from typing import List, Sequence

import matplotlib

matplotlib.use("Agg")  # no display in a server/CI environment
import matplotlib.pyplot as plt  # noqa: E402  (must follow backend selection)

from .pricing import Quote  # noqa: E402
from .tracking import Track  # noqa: E402


def _finish(fig) -> bytes:
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=110)
    plt.close(fig)
    return buffer.getvalue()


def render_range_chart(quotes: Sequence[Quote]) -> bytes:
    """Bar chart of the cheapest price per date; the minimum is highlighted."""

    dates = [q.date.strftime("%m-%d") for q in quotes]
    prices = [q.price_total for q in quotes]
    cheapest = min(range(len(prices)), key=lambda i: prices[i]) if prices else -1
    colors = ["#2a9d8f" if i == cheapest else "#8ecae6" for i in range(len(prices))]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(dates, prices, color=colors)
    if prices:
        route = f"{quotes[0].origin} \u2192 {quotes[0].destination}"
        ax.set_title(f"Cheapest fare by date \u2014 {route} ({quotes[0].passengers} pax)")
        for rect, price in zip(bars, prices):
            ax.text(
                rect.get_x() + rect.get_width() / 2,
                rect.get_height(),
                f"${price}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    ax.set_ylabel("Price, USD")
    ax.set_xlabel("Date")
    ax.margins(y=0.15)
    plt.xticks(rotation=45, ha="right")
    return _finish(fig)


def render_history_chart(track: Track) -> bytes:
    """Line chart of observed prices over time for a tracked route."""

    xs: List[int] = list(range(len(track.history)))
    prices = [p for _, p in track.history]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(xs, prices, marker="o", color="#e76f51")
    ax.set_title(
        f"Price history \u2014 {track.origin} \u2192 {track.destination} "
        f"on {track.date.isoformat()} ({track.passengers} pax)"
    )
    ax.set_ylabel("Price, USD")
    ax.set_xlabel("Check #")
    if prices:
        lo = min(range(len(prices)), key=lambda i: prices[i])
        ax.annotate(
            f"min ${prices[lo]}",
            xy=(lo, prices[lo]),
            xytext=(0, -18),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            color="#2a9d8f",
        )
    ax.margins(y=0.2)
    return _finish(fig)
