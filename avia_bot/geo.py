"""Cities and airports, with fuzzy city search.

AviaGram lets a user type a city name and then pick from matching airports
(e.g. Москва -> MOW / SVO / VKO / DME / ZIA). This module models that: each
city has a "metro" code covering all its airports plus the individual airports,
and :func:`search_cities` returns ranked airport options for a typed query.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Airport:
    code: str          # IATA-like code (metro code for the "all airports" option)
    city: str          # Russian city name
    country: str
    label: str         # display name, e.g. "Москва Шереметьево"
    is_metro: bool = False

    @property
    def option_text(self) -> str:
        return f"{self.label}, {self.country} ({self.code})"


@dataclass(frozen=True)
class City:
    key: str
    name: str
    country: str
    metro: str
    airports: List[Airport]
    aliases: List[str] = field(default_factory=list)


def _city(key, name, country, metro, airports, aliases):
    apts = [Airport(metro, name, country, name, is_metro=True)]
    for code, label in airports:
        apts.append(Airport(code, name, country, label))
    # A city with a single airport does not need a separate metro entry.
    if not airports:
        apts = [Airport(metro, name, country, name)]
    return City(key, name, country, metro, apts, [name.lower(), *aliases])


CITIES: List[City] = [
    _city("moscow", "Москва", "Россия", "MOW",
          [("SVO", "Москва Шереметьево"), ("VKO", "Москва Внуково"),
           ("DME", "Москва Домодедово"), ("ZIA", "Москва Жуковский")],
          ["moscow", "msk", "мск"]),
    _city("spb", "Санкт-Петербург", "Россия", "LED",
          [("LED", "Санкт-Петербург Пулково")],
          ["spb", "питер", "saint petersburg", "petersburg"]),
    _city("khujand", "Худжанд", "Таджикистан", "LBD", [], ["khujand", "hudzhand"]),
    _city("dushanbe", "Душанбе", "Таджикистан", "DYU", [], ["dushanbe"]),
    _city("tashkent", "Ташкент", "Узбекистан", "TAS", [], ["tashkent", "тошкент"]),
    _city("samarkand", "Самарканд", "Узбекистан", "SKD", [], ["samarkand"]),
    _city("novosibirsk", "Новосибирск", "Россия", "OVB", [], ["novosibirsk", "нск"]),
    _city("ufa", "Уфа", "Россия", "UFA", [], ["ufa"]),
    _city("kazan", "Казань", "Россия", "KZN", [], ["kazan"]),
    _city("istanbul", "Стамбул", "Турция", "IST", [], ["istanbul", "стамбул"]),
    _city("dubai", "Дубай", "ОАЭ", "DXB", [], ["dubai", "дубаи"]),
    _city("almaty", "Алматы", "Казахстан", "ALA", [], ["almaty", "алма-ата"]),
    _city("bishkek", "Бишкек", "Киргизия", "FRU", [], ["bishkek"]),
    _city("sochi", "Сочи", "Россия", "AER", [], ["sochi", "адлер"]),
]

_BY_CODE: Dict[str, Airport] = {}
_BY_METRO: Dict[str, City] = {}
for _c in CITIES:
    _BY_METRO[_c.metro] = _c
    for _a in _c.airports:
        _BY_CODE.setdefault(_a.code, _a)


def search_cities(query: str, limit: int = 6) -> List[Airport]:
    """Return airport options matching a typed city query, best matches first."""

    q = (query or "").strip().lower()
    if not q:
        return []
    ranked: List[tuple[int, Airport]] = []
    for city in CITIES:
        names = [city.name.lower(), *city.aliases]
        score = None
        for name in names:
            if name == q:
                score = 0
                break
            if name.startswith(q):
                score = min(1, score if score is not None else 1)
            elif q in name:
                score = min(2, score if score is not None else 2)
        if score is None and (q == city.metro.lower()):
            score = 0
        if score is not None:
            for airport in city.airports:
                ranked.append((score, airport))
    ranked.sort(key=lambda pair: (pair[0], not pair[1].is_metro, pair[1].code))
    return [airport for _, airport in ranked[:limit]]


def airport(code: str) -> Optional[Airport]:
    return _BY_CODE.get(code.upper()) if code else None


def resolve_airports(code: str) -> List[str]:
    """Expand a metro code to all its airport codes; otherwise return [code]."""

    code = (code or "").upper()
    city = _BY_METRO.get(code)
    if city is not None:
        specific = [a.code for a in city.airports if not a.is_metro]
        return specific or [city.metro]
    return [code] if code in _BY_CODE else []


def city_of(code: str) -> Optional[str]:
    apt = airport(code)
    return apt.city if apt else None
