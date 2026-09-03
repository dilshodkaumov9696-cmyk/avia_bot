"""Airline catalog: IATA code, display names, bundled logo PNG.

Logos live in ``data/logos/{IATA}.png`` (Kiwi / AVS tiles, rebuilt by
``scripts/fetch_logos.py``). The ticket card and the live bot both read
from this catalog so a carrier never shows as a bare string.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

_LOGO_DIR = Path(__file__).resolve().parent / "data" / "logos"


@dataclass(frozen=True)
class Airline:
    iata: str
    name: str
    name_ru: str

    def display(self, lang: str = "ru") -> str:
        if (lang or "").startswith("en"):
            return self.name
        return self.name_ru or self.name


# Carriers that appear on CIS / Asia / Europe routes we simulate.
AIRLINES: List[Airline] = [
    Airline("SU", "Aeroflot", "Аэрофлот"),
    Airline("S7", "S7 Airlines", "S7 Airlines"),
    Airline("DP", "Pobeda", "Победа"),
    Airline("U6", "Ural Airlines", "Уральские авиалинии"),
    Airline("UT", "Utair", "Utair"),
    Airline("FV", "Rossiya", "Россия"),
    Airline("N4", "Nordwind", "Nordwind"),
    Airline("WZ", "Red Wings", "Red Wings"),
    Airline("5N", "Smartavia", "Smartavia"),
    Airline("A4", "Azimuth", "Азимут"),
    Airline("SZ", "Somon Air", "Somon Air"),
    Airline("HY", "Uzbekistan Airways", "Uzbekistan Airways"),
    Airline("KC", "Air Astana", "Air Astana"),
    Airline("IQ", "Qazaq Air", "Qazaq Air"),
    Airline("B2", "Belavia", "Belavia"),
    Airline("J2", "Azerbaijan Airlines", "AZAL"),
    Airline("TK", "Turkish Airlines", "Turkish Airlines"),
    Airline("PC", "Pegasus", "Pegasus"),
    Airline("FZ", "flydubai", "flydubai"),
    Airline("EK", "Emirates", "Emirates"),
    Airline("QR", "Qatar Airways", "Qatar Airways"),
    Airline("EY", "Etihad", "Etihad"),
    Airline("LH", "Lufthansa", "Lufthansa"),
    Airline("AF", "Air France", "Air France"),
    Airline("KL", "KLM", "KLM"),
    Airline("BA", "British Airways", "British Airways"),
    Airline("AY", "Finnair", "Finnair"),
    Airline("LO", "LOT", "LOT"),
    Airline("W6", "Wizz Air", "Wizz Air"),
    Airline("FR", "Ryanair", "Ryanair"),
]

_BY_IATA: Dict[str, Airline] = {a.iata: a for a in AIRLINES}
_BY_NAME: Dict[str, Airline] = {}
for a in AIRLINES:
    _BY_NAME[a.name.casefold()] = a
    _BY_NAME[a.name_ru.casefold()] = a


def get(code_or_name: str) -> Optional[Airline]:
    if not code_or_name:
        return None
    raw = code_or_name.strip()
    hit = _BY_IATA.get(raw.upper())
    if hit:
        return hit
    return _BY_NAME.get(raw.casefold())


def display_name(code_or_name: str, lang: str = "ru") -> str:
    air = get(code_or_name)
    return air.display(lang) if air else code_or_name


def iata_of(code_or_name: str) -> str:
    air = get(code_or_name)
    return air.iata if air else (code_or_name or "")[:2].upper()


def logo_path(code_or_name: str) -> Optional[Path]:
    air = get(code_or_name)
    if not air:
        return None
    path = _LOGO_DIR / f"{air.iata}.png"
    return path if path.exists() else None


@lru_cache(maxsize=64)
def logo_png(code_or_name: str) -> Optional[bytes]:
    path = logo_path(code_or_name)
    if path is None:
        return None
    return path.read_bytes()


def all_iata() -> List[str]:
    return [a.iata for a in AIRLINES]
