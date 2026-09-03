from avia_bot import geo


def test_world_airport_count():
    assert geo.airport_count() > 4000


def test_search_moscow_lists_metro_and_airports():
    options = geo.search_cities("Москва")
    codes = [a.code for a in options]
    assert codes[0] == "MOW"
    for c in ["SVO", "VKO", "DME", "ZIA"]:
        assert c in codes


def test_search_by_alias():
    assert any(a.code == "MOW" for a in geo.search_cities("moscow"))
    assert any(a.code == "TAS" for a in geo.search_cities("tashkent"))


def test_search_substring():
    assert any(a.code == "LBD" for a in geo.search_cities("худж"))


def test_search_by_iata():
    hits = geo.search_cities("LED")
    assert hits and hits[0].code == "LED"


def test_search_by_airport_name():
    codes = [a.code for a in geo.search_cities("Шереметьево")]
    assert "SVO" in codes


def test_search_by_country():
    hits = geo.search_cities("Япония")
    assert hits
    assert all(a.country == "JP" or a.is_metro for a in hits)


def test_search_london_has_metro():
    codes = [a.code for a in geo.search_cities("Лондон")]
    assert "LON" in codes
    assert "LHR" in codes


def test_resolve_metro_expands_to_airports():
    assert set(geo.resolve_airports("MOW")) == {"SVO", "VKO", "DME", "ZIA"}


def test_resolve_single_airport():
    assert geo.resolve_airports("LBD") == ["LBD"]


def test_airport_and_city_of():
    assert geo.airport("SVO").city_ru == "Москва" or geo.airport("SVO").display_city == "Москва"
    assert geo.city_of("LBD") == "Худжанд"


def test_unknown_city_returns_empty():
    assert geo.search_cities("Атлантида") == []


def test_button_label_has_flag_and_is_short():
    svo = geo.airport("SVO")
    assert svo.option_text.startswith("🇷🇺")
    assert "SVO" in svo.option_text
    assert "Шереметьево" in svo.option_text
    assert len(svo.option_text) <= 64


def test_flag_emoji():
    assert geo.flag_emoji("RU") == "🇷🇺"
    assert geo.flag_emoji("TJ") == "🇹🇯"
    assert geo.flag_emoji("GB") == "🇬🇧"
    assert geo.flag_emoji("") == "🏳️"
