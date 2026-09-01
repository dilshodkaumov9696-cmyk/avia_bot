from avia_bot.pricing import Passengers
from avia_bot.search_flow import adjust_pax, cycle_cabin, paginate


def test_adjust_pax_clamps():
    pax = Passengers(1, 0, 0)
    assert adjust_pax(pax, "adults", -1).adults == 1        # min 1 adult
    assert adjust_pax(pax, "children", -1).children == 0    # min 0
    assert adjust_pax(pax, "adults", 1).adults == 2


def test_adjust_pax_infant_not_exceed_adults():
    pax = Passengers(1, 0, 0)
    pax = adjust_pax(pax, "infants", 1)
    pax = adjust_pax(pax, "infants", 1)  # would be 2 infants for 1 adult
    assert pax.infants <= pax.adults


def test_adjust_pax_total_cap():
    pax = Passengers(9, 0, 0)
    assert adjust_pax(pax, "children", 1) == pax  # cannot exceed 9 total


def test_cycle_cabin():
    pax = Passengers(cabin="economy")
    assert cycle_cabin(pax, 1).cabin == "business"
    assert cycle_cabin(cycle_cabin(pax, 1), 1).cabin == "economy"


def test_paginate():
    items = list(range(5))
    page_items, page, total = paginate(items, 2, per_page=1)
    assert page_items == [2] and page == 2 and total == 5
    # clamps out of range
    assert paginate(items, 99, per_page=1)[1] == 4
    assert paginate(items, -3, per_page=1)[1] == 0
