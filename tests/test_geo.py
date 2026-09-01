from avia_bot import geo


def test_search_moscow_lists_metro_and_airports():
    options = geo.search_cities("Москва")
    codes = [a.code for a in options]
    assert codes[0] == "MOW"  # metro option first
    for c in ["SVO", "VKO", "DME", "ZIA"]:
        assert c in codes


def test_search_by_alias():
    assert any(a.code == "MOW" for a in geo.search_cities("moscow"))
    assert any(a.code == "TAS" for a in geo.search_cities("tashkent"))


def test_search_substring():
    assert any(a.code == "LBD" for a in geo.search_cities("худж"))


def test_resolve_metro_expands_to_airports():
    assert set(geo.resolve_airports("MOW")) == {"SVO", "VKO", "DME", "ZIA"}


def test_resolve_single_airport():
    assert geo.resolve_airports("LBD") == ["LBD"]


def test_airport_and_city_of():
    assert geo.airport("SVO").city == "Москва"
    assert geo.city_of("LBD") == "Худжанд"


def test_unknown_city_returns_empty():
    assert geo.search_cities("Атлантида") == []
