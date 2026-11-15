#!/usr/bin/env python3
"""Validate the whole repository without modifying it.

Checks:
  * required files and generated catalog/game/site outputs are current
  * catalog ids, periods, reliability, fulltext paths and counts
  * texts/index.json against manifests and actual volume files
  * game data schema, unique ids, references and source ids
  * site data copies match their sources

Usage:
    python scripts/validate.py [--strict]

Exit code 0 when no errors; warnings do not fail unless --strict.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TEXTS = ROOT / "texts"
GAME = DATA / "game"
SITE = ROOT / "site"
SCHEMA_PATH = ROOT / "schemas" / "game-data.schema.json"

sys.path.insert(0, str(ROOT / "scripts"))
from build_catalog import load as load_catalog_shards  # noqa: E402
from build_catalog import sort_key as catalog_sort_key  # noqa: E402
from build_catalog import validate as validate_catalog_entries  # noqa: E402

RELIABILITY = {"A", "A/B", "B", "B/C", "B/F", "C", "M", "F", "D"}
EVENT_TYPES = {
    "war", "battle", "rebellion", "coup", "succession", "reform", "treaty",
    "massacre", "migration", "disaster", "cultural", "religious",
    "administrative", "diplomatic",
}
FACTION_TYPES = {
    "empire", "kingdom", "dynasty", "warlord", "regional-regime",
    "tribal-confederation", "rebel", "garrison", "city-state",
}
LOCATION_TYPES = {
    "capital", "city", "fortress", "pass", "region", "river", "port",
    "religious-site", "battlefield",
}
GLOSSARY_CATEGORIES = {
    "institution", "military", "economy", "society", "ethnicity",
    "religion", "culture", "geography", "title", "law",
}

errors: list[str] = []
warnings: list[str] = []


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON: {path.relative_to(ROOT)}: {exc}")
    return None


def require(path: Path) -> bool:
    if not path.exists():
        errors.append(f"missing file: {path.relative_to(ROOT)}")
        return False
    return True


def check_required_files() -> None:
    required = [
        "README.md", "LICENSE", "NOTICE.md", "CLAUDE.md", "AGENTS.md", "llms.txt",
        "data/catalog.json", "data/catalog_stats.json", "data/periods.json",
        "data/locations.json", "data/glossary.json", "data/disambiguation.json",
        "schemas/game-data.schema.json", "texts/index.json",
        "docs/catalog.md", "docs/methodology.md",
        "docs/game-design/README.md", "docs/game-design/worldbuilding.md",
        "docs/game-design/characters-events.md", "docs/game-design/balance-and-sources.md",
        "prompts/history-qa.md", "prompts/game-design.md", "prompts/faction-brief.md",
        "prompts/character-card.md", "prompts/event-card.md", "prompts/source-audit.md",
        "scripts/search.py", "scripts/build_index.py", "scripts/build_catalog.py",
        "scripts/build_game_data.py", "scripts/build_site.py", "scripts/fetch_wikisource.py",
        "scripts/textutil.py", "site/index.html", "site/app.js", "site/style.css",
        "data/variants/ts_characters.txt", "data/variants/OPENCC-LICENSE.txt",
    ]
    for rel in required:
        require(ROOT / rel)


def check_catalog() -> dict:
    actual = load_json(DATA / "catalog.json")
    if actual is None:
        return {}
    if not isinstance(actual, list):
        errors.append("data/catalog.json: expected a JSON array")
        return {}

    ids = [e.get("id") for e in actual]
    for ident, n in Counter(ids).items():
        if n > 1:
            errors.append(f"catalog: duplicate id {ident!r} ({n} times)")

    for e in actual:
        ident = e.get("id", "<no-id>")
        if not ident:
            errors.append("catalog: entry missing id")
            continue
        if e.get("type") not in {"primary", "modern", "fiction", "database"}:
            errors.append(f"catalog {ident}: invalid type {e.get('type')!r}")
        if e.get("reliability") not in RELIABILITY:
            errors.append(f"catalog {ident}: invalid reliability {e.get('reliability')!r}")
        ft = e.get("fulltext") or {}
        status = ft.get("status")
        if status not in {"included", "partial", "external"}:
            errors.append(f"catalog {ident}: invalid fulltext.status {status!r}")
        if status in {"included", "partial"} and ft.get("path"):
            if not (ROOT / ft["path"]).exists():
                errors.append(f"catalog {ident}: fulltext path not found: {ft['path']}")

    # Generated catalog must equal the sorted merge of the source shards.
    shards = load_catalog_shards()
    shard_errors = validate_catalog_entries(shards)
    errors.extend(f"catalog shard: {msg}" for msg in shard_errors)
    shards.sort(key=catalog_sort_key)
    for e in shards:
        e.pop("_source_file", None)
    if shards != actual:
        errors.append("data/catalog.json is stale: run python scripts/build_catalog.py")

    stats = load_json(DATA / "catalog_stats.json")
    if stats is not None:
        expected_stats = {
            "total": len(actual),
            "primary": sum(1 for e in actual if e.get("type") == "primary"),
            "modern": sum(1 for e in actual if e.get("type") == "modern"),
            "fiction": sum(1 for e in actual if e.get("type") == "fiction"),
            "database": sum(1 for e in actual if e.get("type") == "database"),
            "included": sum(1 for e in actual if (e.get("fulltext") or {}).get("status") == "included"),
            "core": sum(1 for e in actual if e.get("priority") == "core"),
            "by_period": dict(Counter(p for e in actual for p in e.get("periods", []))),
        }
        if stats != expected_stats:
            errors.append("data/catalog_stats.json is stale: run python scripts/build_catalog.py")

    site_catalog = SITE / "data" / "catalog.json"
    if site_catalog.exists() and site_catalog.read_text(encoding="utf-8") != (DATA / "catalog.json").read_text(encoding="utf-8"):
        errors.append("site/data/catalog.json differs from data/catalog.json")

    return {e["id"]: e for e in actual if e.get("id")}


def check_texts(catalog: dict) -> dict:
    index = load_json(TEXTS / "index.json")
    if index is None:
        return {}
    books = index.get("books", [])
    if index.get("book_count") != len(books):
        errors.append(f"texts/index.json: book_count {index.get('book_count')} != {len(books)}")
    if index.get("volume_count") != sum(b.get("volume_count", 0) for b in books):
        errors.append("texts/index.json: volume_count does not match books")
    if index.get("chars") != sum(b.get("chars", 0) for b in books):
        errors.append("texts/index.json: chars does not match books")

    by_id = {}
    for book in books:
        ident = book.get("id", "<no-id>")
        slug = book.get("slug", "")
        by_id[ident] = book
        book_dir = ROOT / book.get("path", f"texts/{slug}")
        if not book_dir.exists():
            errors.append(f"texts: missing directory for {ident}: {book.get('path')}")
            continue
        manifest_path = book_dir / "manifest.json"
        manifest = load_json(manifest_path) if manifest_path.exists() else None
        if manifest is None:
            errors.append(f"texts {ident}: missing manifest.json")
            continue
        files = sorted(book_dir.glob("卷*.txt"))
        if len(files) != book.get("volume_count"):
            errors.append(f"texts {ident}: {len(files)} volume files != index {book.get('volume_count')}")
        if manifest.get("volume_count") != book.get("volume_count"):
            errors.append(f"texts {ident}: manifest volume_count != index")
        if manifest.get("chars") != book.get("chars"):
            errors.append(f"texts {ident}: manifest chars != index")
        for vol in manifest.get("volumes", []):
            path = book_dir / vol.get("file", "")
            if not path.exists():
                errors.append(f"texts {ident}: manifest volume missing: {vol.get('file')}")
                continue
            text = path.read_text(encoding="utf-8")
            if len(text) != vol.get("chars"):
                warnings.append(f"texts {ident}: {vol.get('file')} chars differ from manifest")
            if "许可：CC BY-SA 4.0" not in text[:600]:
                errors.append(f"texts {ident}: {vol.get('file')} missing license header")
            for marker in ("◄", "►", "姊妹計劃", "姊妹计划"):
                if marker in text:
                    warnings.append(f"texts {ident}: {vol.get('file')} contains navigation marker {marker!r}")

    for ident, entry in catalog.items():
        ft = entry.get("fulltext") or {}
        if ft.get("status") == "included":
            book = by_id.get(ident)
            if book is None:
                errors.append(f"catalog {ident}: included but missing from texts/index.json")
                continue
            if ft.get("volumes_available") not in (None, book.get("volume_count")):
                errors.append(f"catalog {ident}: volumes_available != texts/index.json")
            if ft.get("chars") not in (None, book.get("chars")):
                errors.append(f"catalog {ident}: chars != texts/index.json")

    return by_id


def check_periods() -> tuple[list[dict], set[str], set[str]]:
    periods = load_json(DATA / "periods.json")
    if periods is None:
        return [], set(), set()
    if not isinstance(periods, list):
        errors.append("data/periods.json: expected a JSON array")
        return [], set(), set()
    names = [p.get("name") for p in periods]
    ids = [p.get("id") for p in periods]
    for name, n in Counter(names).items():
        if n > 1:
            errors.append(f"periods: duplicate name {name!r}")
    for ident, n in Counter(ids).items():
        if n > 1:
            errors.append(f"periods: duplicate id {ident!r}")
    valid_ids = set(ids)
    for p in periods:
        if p.get("start") is None or p.get("end") is None:
            errors.append(f"period {p.get('id')}: missing start/end")
        elif p["start"] > p["end"]:
            errors.append(f"period {p.get('id')}: start > end")
        parent = p.get("parent")
        if parent and parent not in valid_ids:
            errors.append(f"period {p.get('id')}: unknown parent {parent!r}")
        for key in ("summary", "themes", "game_hooks", "key_events", "sources"):
            if key not in p:
                warnings.append(f"period {p.get('id')}: missing {key}")
    return periods, set(names), valid_ids


def check_game(catalog_ids: set[str], period_names: set[str]) -> None:
    bundles = {
        "faction": load_json(GAME / "factions.json"),
        "character": load_json(GAME / "characters.json"),
        "event": load_json(GAME / "events.json"),
        "location": load_json(GAME / "locations.json"),
        "glossary": load_json(GAME / "glossary.json"),
        "disambiguation": load_json(GAME / "disambiguation.json"),
    }
    if any(v is None for v in bundles.values()):
        return
    for name, items in bundles.items():
        if not isinstance(items, list):
            errors.append(f"data/game/{name}.json: expected an array")
            bundles[name] = []
    if any(not isinstance(v, list) for v in bundles.values()):
        return

    # Generated bundles must match their source shards.
    sources = {
        "faction": ("factions/*.json", bundles["faction"]),
        "character": ("characters/*.json", bundles["character"]),
        "event": ("events/*.json", bundles["event"]),
        "location": (None, load_json(DATA / "locations.json")),
        "glossary": (None, load_json(DATA / "glossary.json")),
        "disambiguation": (None, load_json(DATA / "disambiguation.json")),
    }
    for name, (pattern, generated) in sources.items():
        if pattern:
            merged = []
            for path in sorted(DATA.glob(pattern)):
                payload = load_json(path)
                if isinstance(payload, list):
                    merged.extend(payload)
            if merged != generated:
                errors.append(f"data/game/{name}s.json is stale: run python scripts/build_game_data.py")
        elif generated != bundles[name]:
            errors.append(f"data/game/{name}s.json differs from source {name}.json")

    schema = load_json(SCHEMA_PATH)
    if schema:
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            warnings.append("jsonschema not installed; skipped schema validation")
        else:
            for name, items in bundles.items():
                validator = Draft202012Validator({
                    "$schema": schema["$schema"],
                    "$defs": schema["$defs"],
                    "$ref": f"#/$defs/{name}",
                })
                for item in items:
                    ident = item.get("id", "<no-id>")
                    for err in validator.iter_errors(item):
                        loc = "/".join(str(x) for x in err.absolute_path)
                        errors.append(f"{name} {ident}: schema {loc}: {err.message}")

    for name, items in bundles.items():
        for ident, n in Counter(x.get("id") for x in items).items():
            if n > 1:
                errors.append(f"{name}: duplicate id {ident!r} ({n} times)")

    factions = bundles["faction"]
    characters = bundles["character"]
    events = bundles["event"]
    locations = bundles["location"]
    glossary = bundles["glossary"]

    faction_ids = {x["id"] for x in factions}
    character_ids = {x["id"] for x in characters}
    event_ids = {x["id"] for x in events}
    location_ids = {x["id"] for x in locations}

    for f in factions:
        if f.get("type") not in FACTION_TYPES:
            errors.append(f"faction {f['id']}: invalid type {f.get('type')!r}")
        if f.get("period") and f["period"] not in period_names:
            errors.append(f"faction {f['id']}: unknown period {f['period']!r}")
        for key in ("allies", "enemies", "vassals"):
            for target in f.get(key, []):
                if target not in faction_ids:
                    warnings.append(f"faction {f['id']}: {key} target {target!r} not found")

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

    for loc in locations:
        if loc.get("type") not in LOCATION_TYPES:
            errors.append(f"location {loc['id']}: invalid type {loc.get('type')!r}")
        for ev in loc.get("events", []):
            if ev not in event_ids:
                warnings.append(f"location {loc['id']}: unknown event {ev!r}")

    for g in glossary:
        if g.get("category") not in GLOSSARY_CATEGORIES:
            errors.append(f"glossary {g['id']}: invalid category {g.get('category')!r}")

    for name, items in bundles.items():
        for item in items:
            for sid in item.get("sources", []):
                if sid not in catalog_ids:
                    errors.append(f"{name} {item.get('id')}: unknown source {sid!r}")

    index = load_json(GAME / "index.json")
    if index:
        counts = index.get("counts", {})
        expected = {
            "factions": len(factions),
            "characters": len(characters),
            "events": len(events),
            "locations": len(locations),
            "glossary": len(glossary),
            "disambiguation": len(bundles["disambiguation"]),
        }
        for key, value in expected.items():
            if counts.get(key) != value:
                errors.append(f"data/game/index.json: count {key} {counts.get(key)} != {value}")


def check_site() -> None:
    pairs = [
        ("data/periods.json", "site/data/periods.json"),
        ("data/catalog_stats.json", "site/data/catalog_stats.json"),
        ("data/catalog.json", "site/data/catalog.json"),
        ("texts/index.json", "site/data/texts_index.json"),
    ]
    for src, dst in pairs:
        src_path, dst_path = ROOT / src, ROOT / dst
        if src_path.exists() and dst_path.exists():
            if load_json(src_path) != load_json(dst_path):
                errors.append(f"{dst} differs from {src}")
        elif src_path.exists():
            errors.append(f"missing site data: {dst}")

    for name in ("factions", "characters", "events", "locations", "glossary", "disambiguation", "periods", "index"):
        src = GAME / f"{name}.json"
        dst = SITE / "data" / "game" / f"{name}.json"
        if src.exists() and dst.exists():
            if load_json(src) != load_json(dst):
                errors.append(f"site/data/game/{name}.json differs from data/game/{name}.json")
        elif src.exists():
            errors.append(f"missing site data: site/data/game/{name}.json")


def check_index() -> None:
    db = ROOT / "index" / "search.db"
    info_path = ROOT / "index" / "build_info.json"
    if not db.exists():
        warnings.append("index/search.db not built (run python scripts/build_index.py)")
        return
    info = load_json(info_path) if info_path.exists() else None
    if info is None:
        warnings.append("index/build_info.json missing")
        return
    index = load_json(TEXTS / "index.json")
    if index and info.get("volumes") != index.get("volume_count"):
        warnings.append("index/search.db is stale: volume count differs; rebuild with --force")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args()

    check_required_files()
    catalog = check_catalog()
    check_texts(catalog)
    _, period_names, _ = check_periods()
    check_game(set(catalog), period_names)
    check_site()
    check_index()

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
