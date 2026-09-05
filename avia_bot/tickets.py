"""Visual ticket card: airline logo + price + route, as PNG bytes."""

from __future__ import annotations

import io
from typing import Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.offsetbox import AnnotationBbox, OffsetImage  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
import matplotlib.image as mpimg  # noqa: E402

from . import airlines, geo, i18n, responses
from .flights import Priced
from .i18n import fmt_date_short, fmt_time, money, t


def _city(code: str) -> str:
    apt = geo.airport(code)
    return apt.display_city if apt else code


def _apt(code: str) -> str:
    apt = geo.airport(code)
    if not apt:
        return code
    if apt.is_metro:
        return apt.display_city
    name = apt.display_name
    if name and name.casefold() != apt.display_city.casefold():
        return f"{name} · {code}"
    return f"{apt.display_city} · {code}"


def _load_logo(iata: str):
    path = airlines.logo_path(iata)
    if path is None:
        return None
    try:
        return mpimg.imread(path)
    except Exception:  # noqa: BLE001
        return None


def render_ticket(lang: str, priced: Priced, back: Optional[Priced] = None,
                  page: Optional[int] = None, total: Optional[int] = None) -> bytes:
    """Paint a compact receipt card with a small airline logo."""

    it = priced.itinerary
    air = airlines.get(it.airline_iata) or airlines.get(it.airline)
    iata = air.iata if air else it.airline_iata
    name = air.display(lang) if air else it.airline
    raw_fn = it.flight_no
    flight = f"{iata} {raw_fn[len(iata):]}" if iata and raw_fn.startswith(iata) else raw_fn
    tags = []
    if priced.is_cheapest:
        tags.append(t(lang, "tag_cheapest"))
    if priced.is_fastest:
        tags.append(t(lang, "tag_fastest"))

    fig, ax = plt.subplots(figsize=(7.1, 3.55), dpi=140)
    fig.patch.set_facecolor("#e8edf4")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(FancyBboxPatch(
        (0.018, 0.035), 0.964, 0.93,
        boxstyle="round,pad=0.01,rounding_size=0.035",
        linewidth=0, facecolor="#ffffff",
    ))

    logo = _load_logo(iata)
    if logo is not None:
        imagebox = OffsetImage(logo, zoom=0.52)
        ax.add_artist(AnnotationBbox(imagebox, (0.085, 0.86), frameon=False))
        name_x = 0.155
    else:
        ax.add_patch(FancyBboxPatch(
            (0.05, 0.79), 0.07, 0.12,
            boxstyle="round,pad=0.004,rounding_size=0.015",
            linewidth=0, facecolor="#1d3557",
        ))
        ax.text(0.085, 0.85, iata or "✈", ha="center", va="center",
                fontsize=8, color="white", fontweight="bold")
        name_x = 0.155

    ax.text(name_x, 0.895, name, ha="left", va="center",
            fontsize=11, color="#1d3557")
    ax.text(name_x, 0.805, flight, ha="left", va="center",
            fontsize=8.5, color="#6c757d")
    right = []
    if page is not None and total:
        right.append(f"{page} / {total}")
    if tags:
        right.append(" · ".join(tags))
    if right:
        ax.text(0.94, 0.86, "   ".join(right), ha="right", va="center",
                fontsize=8.5, color="#2a9d8f")

    ax.text(0.055, 0.64, money(lang, priced.price_total),
            ha="left", va="center", fontsize=20, color="#1d3557", fontweight="bold")

    arrow = "⇄" if back is not None else "→"
    ax.text(0.055, 0.48, _city(it.origin), ha="left", va="center", fontsize=11, color="#212529")
    ax.text(0.50, 0.48, arrow, ha="center", va="center", fontsize=14, color="#457b9d")
    ax.text(0.945, 0.48, _city(it.destination), ha="right", va="center", fontsize=11, color="#212529")

    ax.text(0.055, 0.355, fmt_time(it.dep), ha="left", va="center",
            fontsize=15, color="#1d3557", fontweight="bold")
    ax.text(0.945, 0.355, fmt_time(it.arr), ha="right", va="center",
            fontsize=15, color="#1d3557", fontweight="bold")
    ax.text(0.055, 0.27, _apt(it.origin), ha="left", va="center", fontsize=8, color="#6c757d")
    ax.text(0.945, 0.27, _apt(it.destination), ha="right", va="center", fontsize=8, color="#6c757d")

    stop = t(lang, "direct") if it.is_direct else t(lang, "stops_n", n=it.stops)
    mid = f"{it.duration_str}  ·  {stop}"
    ax.plot([0.30, 0.70], [0.36, 0.36], color="#ced4da", linewidth=1.0)
    ax.text(0.50, 0.295, mid, ha="center", va="center", fontsize=8.5, color="#6c757d")

    bag = t(lang, "bag_yes") if it.baggage else t(lang, "bag_no")
    date_s = fmt_date_short(lang, it.dep.date())
    if back is not None:
        date_s += f"  →  {fmt_date_short(lang, back.itinerary.dep.date())}"
    if priced.pax.total > 1:
        date_s += f"  ·  {responses.pax_summary(lang, priced.pax)}"
    footer = f"{date_s}  ·  {bag}"
    ax.text(0.055, 0.13, footer, ha="left", va="center", fontsize=8.5, color="#495057")
    if back is not None:
        b = back.itinerary
        ax.text(0.945, 0.13, f"{t(lang, 'label_return')}  {fmt_time(b.dep)}–{fmt_time(b.arr)}",
                ha="right", va="center", fontsize=8, color="#495057")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()
