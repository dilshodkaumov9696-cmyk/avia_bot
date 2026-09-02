"""World airports: search by country, city, airport name or IATA/ICAO.

Data is OurAirports (large/medium + scheduled small, with IATA), shipped as
``data/airports.json.gz``. Russian names and metro-areas come from
:mod:`avia_bot.names_ru`.
"""

from __future__ import annotations

import gzip
import json
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from . import names_ru

_DATA = Path(__file__).resolve().parent / "data" / "airports.json.gz"

# Cheap ASCII fold + ё→е so "москва" matches regardless of yo.
_YO = str.maketrans({"ё": "е", "Ё": "е"})


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").translate(_YO).casefold().strip()
    return " ".join(text.split())


@dataclass(frozen=True)
class Airport:
    code: str
    icao: str
    name: str
    name_ru: str
    city: str
    city_ru: str
    country: str
    country_name: str
    country_name_ru: str
    kind: str  # L / M / S / metro
    is_metro: bool = False
    aliases: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def display_city(self) -> str:
        return self.city_ru or self.city

    @property
    def display_name(self) -> str:
        return self.name_ru or self.name

    @property
    def display_country(self) -> str:
        return self.country_name_ru or self.country_name or self.country

    @property
    def option_text(self) -> str:
        """Short button label: ``SVO · Шереметьево, Москва``."""

        if self.is_metro:
            return f"{self.code} · {self.display_city}, все аэропорты"
        name = self.display_name
        city = self.display_city
        if name and city and name.casefold() != city.casefold():
            label = f"{self.code} · {name}, {city}"
        else:
            label = f"{self.code} · {city}"
        return label[:64]


def _load_raw() -> dict:
    with gzip.open(_DATA, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def _build() -> Tuple[List[Airport], Dict[str, Airport], Dict[str, Airport], Dict[str, List[Airport]]]:
    raw = _load_raw()
    countries_en: Dict[str, str] = raw["countries"]
    by_code: Dict[str, Airport] = {}
    by_icao: Dict[str, Airport] = {}

    for rec in raw["airports"]:
        code = rec["i"]
        city_en = rec.get("c") or ""
        cc = rec.get("cc") or ""
        name_en = rec.get("n") or ""
        city_local = names_ru.CITY_BY_IATA.get(code) or names_ru.city_ru(city_en, city_en)
        name_local = names_ru.airport_ru(code, "")
        aliases = tuple(
            a for a in (
                rec.get("kw") or "",
                city_en,
                city_local,
                name_en,
                name_local,
            ) if a
        )
        apt = Airport(
            code=code,
            icao=rec.get("o") or "",
            name=name_en,
            name_ru=name_local,
            city=city_en,
            city_ru=city_local,
            country=cc,
            country_name=countries_en.get(cc, cc),
            country_name_ru=names_ru.country_ru(cc, countries_en.get(cc, cc)),
            kind=rec.get("t") or "M",
            aliases=aliases,
        )
        by_code[code] = apt
        if apt.icao:
            by_icao.setdefault(apt.icao, apt)

    for metro, members in names_ru.METROS.items():
        if metro in by_code:
            continue  # do not overwrite a real IATA code (IST, DXB, …)
        present = [by_code[c] for c in members if c in by_code]
        if len(present) < 2:
            continue
        seed = present[0]
        by_code[metro] = Airport(
            code=metro,
            icao="",
            name=f"{seed.city} all airports",
            name_ru=seed.city_ru or seed.city,
            city=seed.city,
            city_ru=seed.city_ru or seed.city,
            country=seed.country,
            country_name=seed.country_name,
            country_name_ru=seed.country_name_ru,
            kind="L",
            is_metro=True,
            aliases=(seed.city, seed.city_ru, metro),
        )

    by_country: Dict[str, List[Airport]] = {}
    for apt in by_code.values():
        if apt.is_metro:
            continue
        by_country.setdefault(apt.country, []).append(apt)
    rank = {"L": 0, "M": 1, "S": 2}
    for cc, items in by_country.items():
        items.sort(key=lambda a: (rank.get(a.kind, 9), a.display_city, a.code))

    ordered = list(by_code.values())
    return ordered, by_code, by_icao, by_country


_ALL, _BY_CODE, _BY_ICAO, _BY_COUNTRY = _build()

# Alias -> airport code (IATA or metro).
_ALIASES: Dict[str, str] = { _norm(k): v for k, v in names_ru.ALIASES.items() }
for apt in _ALL:
    _ALIASES.setdefault(_norm(apt.code), apt.code)
    if apt.icao:
        _ALIASES.setdefault(_norm(apt.icao), apt.code)


def airport(code: str) -> Optional[Airport]:
    if not code:
        return None
    return _BY_CODE.get(code.upper())


def city_of(code: str) -> Optional[str]:
    apt = airport(code)
    return apt.display_city if apt else None


def resolve_airports(code: str) -> List[str]:
    """Expand a metro code to member IATA codes; otherwise ``[code]`` if known."""

    code = (code or "").upper()
    members = names_ru.METROS.get(code)
    if members:
        found = [c for c in members if c in _BY_CODE and not _BY_CODE[c].is_metro]
        return found or [code]
    return [code] if code in _BY_CODE else []


def _is_military(apt: Airport) -> bool:
    blob = f"{apt.name} {apt.name_ru}".lower()
    return any(tok in blob for tok in ("air base", "air force", " afb", "raf ", "авиабаза", "airbase"))


def _country_hits(query: str) -> List[Airport]:
    """If the query names a country, return that country's airports (large first)."""

    q = _norm(query)
    if len(q) == 2 and q.upper() in _BY_COUNTRY:
        return list(_BY_COUNTRY[q.upper()])
    hits: List[Airport] = []
    for cc, items in _BY_COUNTRY.items():
        if not items:
            continue
        sample = items[0]
        names = {_norm(cc), _norm(sample.country_name), _norm(sample.country_name_ru)}
        if q in names or any(n.startswith(q) or q in n for n in names if len(q) >= 3):
            # Prefer exact / startswith country name.
            exact = q in names or any(n == q for n in names)
            if exact or (len(q) >= 4 and any(q in n or n.startswith(q) for n in names)):
                hits = items
                if exact:
                    return [a for a in hits if not _is_military(a)]
    return hits


def _score(apt: Airport, q: str) -> Optional[int]:
    """Lower is better. None = no match."""

    code = _norm(apt.code)
    icao = _norm(apt.icao)
    if q == code or (icao and q == icao):
        return 0
    fields = [
        _norm(apt.city_ru), _norm(apt.city),
        _norm(apt.name_ru), _norm(apt.name),
        _norm(apt.display_country),
    ]
    fields.extend(_norm(a) for a in apt.aliases if a)
    best: Optional[int] = None
    for field in fields:
        if not field:
            continue
        if field == q:
            best = 1 if best is None else min(best, 1)
        elif field.startswith(q):
            best = 2 if best is None else min(best, 2)
        elif q in field:
            best = 3 if best is None else min(best, 3)
        elif len(q) >= 4 and field in q:
            best = 4 if best is None else min(best, 4)
    return best


def search_cities(query: str, limit: int = 8) -> List[Airport]:
    """Ranked airport options for a typed query (city / country / name / IATA)."""

    q = _norm(query)
    if not q:
        return []

    alias = _ALIASES.get(q)
    if alias and alias in _BY_CODE:
        # Expand metro alias to metro + members.
        head = [_BY_CODE[alias]]
        extra = []
        if head[0].is_metro:
            extra = [airport(c) for c in names_ru.METROS.get(alias, ()) if airport(c)]
        rest = [a for a in extra if a and a.code != alias]
        return (head + rest)[:limit]

    # Country query → airports of that country (large first), metro first if any.
    country = _country_hits(query)
    if country and len(q) >= 2:
        # If it also matches a city more tightly, mix; else return country list.
        city_like = [a for a in _ALL if _score(a, q) in (0, 1, 2)]
        if not city_like:
            metros = [a for a in _ALL if a.is_metro and a.country == country[0].country]
            merged = metros + [a for a in country if not _is_military(a)]
            # unique by code
            seen = set()
            out = []
            for a in merged:
                if a.code in seen:
                    continue
                seen.add(a.code)
                out.append(a)
            return out[:limit]

    ranked: List[Tuple[int, Airport]] = []
    for apt in _ALL:
        sc = _score(apt, q)
        if sc is None:
            continue
        if _is_military(apt) and sc != 0:
            continue
        ranked.append((sc, apt))
    ranked.sort(key=lambda p: (
        p[0],
        0 if p[1].is_metro else 1,
        0 if p[1].city_ru != p[1].city else 1,
        p[1].kind,
        p[1].code,
    ))

    seen = set()
    out: List[Airport] = []
    for _, apt in ranked:
        if apt.code in seen:
            continue
        seen.add(apt.code)
        city_n = _norm(apt.city_ru) or _norm(apt.city)
        name_n = _norm(apt.name_ru) or _norm(apt.name)
        city_match = bool(city_n) and (city_n == q or city_n.startswith(q) or q in city_n)
        name_only = bool(name_n) and (name_n == q or q in name_n) and not city_match
        if not apt.is_metro and not name_only:
            for metro, members in names_ru.METROS.items():
                if apt.code in members and metro in _BY_CODE and metro not in seen:
                    out.append(_BY_CODE[metro])
                    seen.add(metro)
                    if len(out) >= limit:
                        return out
        out.append(apt)
        if len(out) >= limit:
            break
    return out


def airports_in_country(cc: str, limit: int = 12) -> List[Airport]:
    return list(_BY_COUNTRY.get((cc or "").upper(), []))[:limit]


def all_airports() -> Iterable[Airport]:
    return (a for a in _ALL if not a.is_metro)


@lru_cache(maxsize=1)
def airport_count() -> int:
    return sum(1 for _ in all_airports())
