#!/usr/bin/env python3
"""Download square airline-logo tiles into avia_bot/data/logos/.

Tries Kiwi then AVS. Safe to re-run; skips files that already exist
unless --force is passed.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avia_bot.airlines import all_iata  # noqa: E402

OUT = ROOT / "avia_bot" / "data" / "logos"
SOURCES = (
    "https://images.kiwi.com/airlines/64/{code}.png",
    "https://pics.avs.io/200/200/{code}.png",
)


def _fetch(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": "avia_bot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
    except Exception:  # noqa: BLE001
        return None
    if len(data) < 80 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ok = missing = 0
    for code in all_iata():
        dest = OUT / f"{code}.png"
        if dest.exists() and not args.force:
            ok += 1
            continue
        data = None
        for tmpl in SOURCES:
            data = _fetch(tmpl.format(code=code))
            if data:
                break
        if data is None:
            print(f"MISSING {code}", file=sys.stderr)
            missing += 1
            continue
        dest.write_bytes(data)
        print(f"saved {code} ({len(data)} bytes)")
        ok += 1
    print(f"done: {ok} logos, {missing} missing")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
