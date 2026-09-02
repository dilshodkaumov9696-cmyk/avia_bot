#!/usr/bin/env python3
"""Rebuild avia_bot/data/airports.json.gz from OurAirports CSVs.

    python3 scripts/build_airports.py /tmp/airports-src
"""

from __future__ import annotations

import csv
import gzip
import json
import sys
from pathlib import Path

KEEP = {"large_airport": "L", "medium_airport": "M", "small_airport": "S"}


def main(src: Path, dest: Path) -> None:
    countries = {}
    with (src / "countries.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            countries[row["code"]] = row["name"]

    by_iata: dict[str, dict] = {}
    with (src / "airports.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            iata = (row.get("iata_code") or "").strip().upper()
            typ = row.get("type") or ""
            if len(iata) != 3 or not iata.isalpha() or typ not in KEEP:
                continue
            if typ == "small_airport" and row.get("scheduled_service") != "yes":
                continue
            rec = {
                "i": iata,
                "o": (row.get("gps_code") or "").strip().upper()[:8],
                "n": (row.get("name") or "").strip(),
                "c": (row.get("municipality") or "").strip(),
                "cc": (row.get("iso_country") or "").strip().upper(),
                "t": KEEP[typ],
                "kw": (row.get("keywords") or "").strip(),
            }
            prev = by_iata.get(iata)
            rank = {"L": 0, "M": 1, "S": 2}
            if prev and rank[prev["t"]] <= rank[rec["t"]]:
                continue
            by_iata[iata] = rec

    airports = sorted(by_iata.values(), key=lambda r: (r["t"], r["i"]))
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"countries": countries, "airports": airports},
                         ensure_ascii=False, separators=(",", ":"))
    with gzip.open(dest, "wt", encoding="utf-8") as fh:
        fh.write(payload)
    print(f"wrote {len(airports)} airports -> {dest} ({dest.stat().st_size} bytes)")


if __name__ == "__main__":
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/airports-src")
    dest = Path(__file__).resolve().parents[1] / "avia_bot" / "data" / "airports.json.gz"
    main(src, dest)
