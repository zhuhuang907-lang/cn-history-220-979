# -*- coding: utf-8 -*-
"""Merge and validate the game-data shards.

Usage:
    python scripts/build_game_data.py [--strict]

Outputs:
    data/game/factions.json
    data/game/characters.json
    data/game/events.json
    data/game/locations.json
    data/game/glossary.json
    data/game/disambiguation.json
    data/game/periods.json
    data/game/index.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "game"
SCHEMA_PATH = ROOT / "schemas" / "game-data.schema.json"
CATALOG_PATH = DATA / "catalog.json"

RELIABILITY = {"A", "A/B", "B", "B/C", "C", "M", "F", "D"}
EVENT_TYPES = {
    "war", "battle", "rebellion", "coup", "succession", "reform", "treaty",
    "massacre", "migration", "disaster", "cultural", "religious",
    "administrative", "diplomatic",
}


def load(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def shard_files(pattern: str):
    return sorted(DATA.glob(pattern))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    periods = load(DATA / "periods.json")
    period_names = {p.get("name") for p in periods}
    period_ids = {p.get("id") for p in periods}

    factions = []
    for fp in shard_files("factions/*.json"):
        factions.extend(load(fp))
    characters = []
    for fp in shard_files("characters/*.json"):
        characters.extend(load(fp))
    events = []
    for fp in shard_files("events/*.json"):
        events.extend(load(fp))
    locations = load(DATA / "locations.json")
    glossary = load(DATA / "glossary.json")
    disambiguation = load(DATA / "disambiguation.json")

    bundles = {
        "faction": factions,
        "character": characters,
        "event": events,
        "location": locations,
        "glossary": glossary,
        "disambiguation": disambiguation,
    }

    # ---- schema validation ----
    schema = load(SCHEMA_PATH)
    for name, items in bundles.items():
        validator = Draft202012Validator({"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": f"#/$defs/{name}"})
        for item in items:
            ident = item.get("id", "<no-id>")
            for err in validator.iter_errors(item):
                loc = "/".join(str(x) for x in err.absolute_path)
                errors.append(f"{name} {ident}: schema: {loc}: {err.message}")

    # ---- unique ids ----
    for name, items in bundles.items():
        counts = Counter(x.get("id") for x in items)
        for ident, n in counts.items():
            if n > 1:
                errors.append(f"{name}: duplicate id {ident!r} ({n} times)")

    faction_ids = {x["id"] for x in factions}
    character_ids = {x["id"] for x in characters}
    event_ids = {x["id"] for x in events}
    location_ids = {x["id"] for x in locations}

    # ---- references ----
    for f in factions:
        for key in ("allies", "enemies", "vassals"):
            for target in f.get(key, []):
                if target not in faction_ids:
                    warnings.append(f"faction {f['id']}: {key} target {target!r} not found")
        if f.get("period") and f["period"] not in period_names:
            errors.append(f"faction {f['id']}: unknown period {f['period']!r}")

    for c in characters:
        if c.get("faction_id") not in faction_ids:
            errors.append(f"character {c['id']}: unknown faction_id {c.get('faction_id')!r}")
        if c.get("period") and c["period"] not in period_names:
            errors.append(f"character {c['id']}: unknown period {c['period']!r}")
        for ev in c.get("events", []):
            if ev not in event_ids:
                errors.append(f"character {c['id']}: unknown event {ev!r}")
        for rel in c.get("relationships", []):
            if rel.get("target") not in character_ids:
                warnings.append(f"character {c['id']}: relationship target {rel.get('target')!r} not found")

    for e in events:
        if e.get("type") not in EVENT_TYPES:
            errors.append(f"event {e['id']}: invalid type {e.get('type')!r}")
        if e.get("period") and e["period"] not in period_names:
            errors.append(f"event {e['id']}: unknown period {e['period']!r}")
        if e.get("location_id") and e["location_id"] not in location_ids:
            errors.append(f"event {e['id']}: unknown location_id {e['location_id']!r}")
        for fid in e.get("factions", []):
            if fid not in faction_ids:
                errors.append(f"event {e['id']}: unknown faction {fid!r}")
        for cid in e.get("characters", []):
            if cid not in character_ids:
                errors.append(f"event {e['id']}: unknown character {cid!r}")

    for g in glossary:
        if g.get("category") not in {
            "institution", "military", "economy", "society", "ethnicity",
            "religion", "culture", "geography", "title", "law",
        }:
            errors.append(f"glossary {g['id']}: invalid category {g.get('category')!r}")

    # ---- source ids ----
    catalog_ids = {x["id"] for x in load(CATALOG_PATH)}
    for name, items in bundles.items():
        for item in items:
            for sid in item.get("sources", []):
                if sid not in catalog_ids:
                    errors.append(f"{name} {item.get('id')}: unknown source {sid!r}")

    # ---- write bundles ----
    OUT.mkdir(parents=True, exist_ok=True)

    def dump(name, payload):
        (OUT / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    dump("factions.json", factions)
    dump("characters.json", characters)
    dump("events.json", events)
    dump("locations.json", locations)
    dump("glossary.json", glossary)
    dump("disambiguation.json", disambiguation)
    dump("periods.json", periods)

    index = {
        "counts": {
            "factions": len(factions),
            "characters": len(characters),
            "events": len(events),
            "locations": len(locations),
            "glossary": len(glossary),
            "disambiguation": len(disambiguation),
            "periods": len(periods),
        },
        "periods": [{"id": p.get("id"), "name": p.get("name"), "start": p.get("start"), "end": p.get("end")} for p in periods],
        "event_types": sorted({e["type"] for e in events}),
        "faction_types": sorted({f["type"] for f in factions}),
        "reliability_levels": sorted({x.get("reliability") for x in factions + characters + events + locations if x.get("reliability")}),
        "files": {
            "factions": "data/game/factions.json",
            "characters": "data/game/characters.json",
            "events": "data/game/events.json",
            "locations": "data/game/locations.json",
            "glossary": "data/game/glossary.json",
            "disambiguation": "data/game/disambiguation.json",
            "periods": "data/game/periods.json",
        },
    }
    dump("index.json", index)

    print(f"factions={len(factions)} characters={len(characters)} events={len(events)} "
          f"locations={len(locations)} glossary={len(glossary)} disambiguation={len(disambiguation)}")
    print(f"wrote {OUT.relative_to(ROOT)}/")

    for w in warnings:
        print("WARNING:", w)
    for e in errors:
        print("ERROR:", e)

    if errors or (args.strict and warnings):
        print(f"FAILED: {len(errors)} errors, {len(warnings)} warnings", file=sys.stderr)
        return 1
    print(f"OK: {len(errors)} errors, {len(warnings)} warnings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
