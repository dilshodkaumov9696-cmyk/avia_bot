"""Price charts rendered to PNG bytes with matplotlib (headless Agg backend)."""

from __future__ import annotations

import datetime as _dt
import io
from typing import Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .pricing import CURRENCY  # noqa: E402
from .tracking import Track  # noqa: E402


def _finish(fig) -> bytes:
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=110)
    plt.close(fig)
    return buffer.getvalue()


def render_range_chart(origin: str, destination: str,
                       points: Sequence[Tuple[_dt.date, int]]) -> bytes:
    dates = [d.strftime("%m-%d") for d, _ in points]
    prices = [p for _, p in points]
    cheapest = min(range(len(prices)), key=lambda i: prices[i]) if prices else -1
    colors = ["#2a9d8f" if i == cheapest else "#8ecae6" for i in range(len(prices))]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(dates, prices, color=colors)
    ax.set_title(f"Цена по датам — {origin} → {destination}")
    for rect, price in zip(bars, prices):
        ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height(),
                f"{price:,}".replace(",", " "), ha="center", va="bottom", fontsize=8)
    ax.set_ylabel(CURRENCY)
    ax.set_xlabel("Дата")
    ax.margins(y=0.15)
    plt.xticks(rotation=45, ha="right")
    return _finish(fig)


def render_history_chart(track: Track) -> bytes:
    prices = [p for _, p in track.history]
    xs = list(range(len(prices)))

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(xs, prices, marker="o", color="#e76f51")
    ax.set_title(f"История цены — {track.origin} → {track.destination} {track.date.isoformat()}")
    ax.set_ylabel(CURRENCY)
    ax.set_xlabel("Проверка №")
    if prices:
        lo = min(range(len(prices)), key=lambda i: prices[i])
        ax.annotate(f"мин {prices[lo]:,}".replace(",", " "), xy=(lo, prices[lo]),
                    xytext=(0, -18), textcoords="offset points", ha="center",
                    fontsize=9, color="#2a9d8f")
    ax.margins(y=0.2)
    return _finish(fig)
