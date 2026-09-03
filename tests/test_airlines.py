from avia_bot import airlines


def test_catalog_covers_all_logos():
    codes = airlines.all_iata()
    assert len(codes) >= 20
    missing = [c for c in codes if airlines.logo_path(c) is None]
    assert missing == []


def test_lookup_by_iata_and_russian_name():
    assert airlines.get("SU").name_ru == "Аэрофлот"
    assert airlines.get("Аэрофлот").iata == "SU"
    assert airlines.iata_of("Победа") == "DP"
    assert "Аэрофлот" in airlines.display_name("SU", "ru")
    assert airlines.display_name("SU", "en") == "Aeroflot"


def test_logo_png_is_real_png():
    data = airlines.logo_png("TK")
    assert data and data.startswith(b"\x89PNG\r\n\x1a\n")
