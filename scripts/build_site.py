#!/usr/bin/env python3
"""Copy catalog and game data into the static site.

The site itself is plain HTML/CSS/JS and can be opened from disk or served by
GitHub Pages.  This script only refreshes the JSON payloads under site/data/.

Usage:
    python scripts/build_site.py
    python scripts/build_site.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
GAME = DATA / "game"
SITE_DATA = ROOT / "site" / "data"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if site data is stale")
    args = ap.parse_args(argv)

    catalog = read(DATA / "catalog.json")
    stats = read(DATA / "catalog_stats.json")
    periods = read(DATA / "periods.json")
    texts_index = read(ROOT / "texts" / "index.json")
    game_index = read(GAME / "index.json")

    payloads = {
        SITE_DATA / "catalog.json": catalog,
        SITE_DATA / "catalog_stats.json": stats,
        SITE_DATA / "periods.json": periods,
        SITE_DATA / "texts_index.json": texts_index,
    }
    for name in ("factions", "characters", "events", "locations", "glossary", "disambiguation", "periods", "index"):
        payloads[SITE_DATA / "game" / f"{name}.json"] = read(GAME / f"{name}.json")

    manifest = {
        "project": "cn-history-220-979",
        "catalog_entries": stats.get("total"),
        "fulltext_books": stats.get("included"),
        "periods": len(periods),
        "texts": {
            "books": texts_index.get("book_count"),
            "volumes": texts_index.get("volume_count"),
            "chars": texts_index.get("chars"),
        },
        "game": game_index.get("counts", {}),
        "files": sorted(str(p.relative_to(SITE_DATA)).replace("\\", "/") for p in payloads),
    }
    payloads[SITE_DATA / "manifest.json"] = manifest

    stale = []
    for path, payload in payloads.items():
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    if args.check:
        if stale:
            print("stale site data: " + ", ".join(stale), file=sys.stderr)
            return 1
        print("site data is up to date")
        return 0

    print(f"site data: {len(payloads)} files under {SITE_DATA.relative_to(ROOT)}")
    print(f"catalog={stats.get('total')} included={stats.get('included')} periods={len(periods)}")
    for key, value in game_index.get("counts", {}).items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
