import datetime as dt

from avia_bot import i18n


def test_languages_have_currency():
    for lang in i18n.LANGS:
        assert lang in i18n.CURRENCY
        assert i18n.CURRENCY[lang] in i18n.FX
    for named in ["tg", "uz", "ky", "tk", "az", "be", "kk", "en", "ru"]:
        assert named in i18n.LANGS


def test_currency_of():
    assert i18n.currency_of("tg") == "TJS"
    assert i18n.currency_of("uz") == "UZS"
    assert i18n.currency_of("ru") == "RUB"
    assert i18n.currency_of("en") == "USD"


def test_money_conversion():
    assert i18n.money("tg", 3000) == "3\u00a0000 TJS"          # 1:1
    assert i18n.money("en", 3000) == "273 $"                   # 3000 * 0.091
    assert i18n.money("ru", 3000).endswith("₽")


def test_translation_fallback_to_ru():
    # 'hot_none' has no Turkmen entry -> falls back to Russian.
    assert i18n.t("tk", "hot_none") == i18n.t("ru", "hot_none")
    # unknown language normalizes to ru
    assert i18n.t("xx", "welcome") == i18n.t("ru", "welcome")


def test_translation_uses_language_when_present():
    assert i18n.t("en", "kb_search") == "🔎 Find tickets"
    assert i18n.t("uz", "adults") == "Kattalar"


def test_fmt_date_per_language():
    d = dt.date(2026, 9, 17)
    assert i18n.fmt_date("ru", d) == "17 сентября"
    assert i18n.fmt_date("en", d) == "17 Sep"
    assert i18n.fmt_date("uz", d) == "17.09"
