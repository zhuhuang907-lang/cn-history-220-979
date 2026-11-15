# -*- coding: utf-8 -*-
"""Game-data schema and referential-integrity tests."""

from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
GAME = DATA / "game"

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


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class GameDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = {entry["id"] for entry in load(DATA / "catalog.json")}
        cls.periods = load(DATA / "periods.json")
        cls.period_names = {period["name"] for period in cls.periods}
        cls.bundles = {
            "faction": load(GAME / "factions.json"),
            "character": load(GAME / "characters.json"),
            "event": load(GAME / "events.json"),
            "location": load(GAME / "locations.json"),
            "glossary": load(GAME / "glossary.json"),
            "disambiguation": load(GAME / "disambiguation.json"),
        }
        cls.index = load(GAME / "index.json")
        cls.faction_ids = {item["id"] for item in cls.bundles["faction"]}
        cls.character_ids = {item["id"] for item in cls.bundles["character"]}
        cls.event_ids = {item["id"] for item in cls.bundles["event"]}
        cls.location_ids = {item["id"] for item in cls.bundles["location"]}

    def test_counts_match_index(self):
        counts = self.index.get("counts", {})
        for name, items in self.bundles.items():
            with self.subTest(bundle=name):
                self.assertEqual(counts.get(name + "s", counts.get(name)), len(items))
        self.assertEqual(counts.get("periods"), len(self.periods))

    def test_ids_are_unique(self):
        for name, items in self.bundles.items():
            ids = [item.get("id") for item in items]
            duplicates = [ident for ident, count in Counter(ids).items() if count > 1]
            with self.subTest(bundle=name):
                self.assertTrue(all(ids))
                self.assertEqual(duplicates, [])

    def test_schema_validation(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:  # pragma: no cover - CI installs jsonschema
            self.skipTest("jsonschema not installed")
        schema = load(ROOT / "schemas" / "game-data.schema.json")
        for name, items in self.bundles.items():
            validator = Draft202012Validator({
                "$schema": schema["$schema"],
                "$defs": schema["$defs"],
                "$ref": f"#/$defs/{name}",
            })
            for item in items:
                errors = sorted(validator.iter_errors(item), key=lambda e: list(e.absolute_path))
                with self.subTest(bundle=name, ident=item.get("id")):
                    self.assertEqual([error.message for error in errors], [])

    def test_factions(self):
        for faction in self.bundles["faction"]:
            with self.subTest(ident=faction["id"]):
                self.assertIn(faction.get("type"), FACTION_TYPES)
                self.assertIn(faction.get("period"), self.period_names)
                self.assertLessEqual(faction.get("start", 0), faction.get("end", 0))
                for key in ("allies", "enemies", "vassals"):
                    for target in faction.get(key, []):
                        self.assertIn(target, self.faction_ids, f"{key} target {target}")

    def test_characters(self):
        for character in self.bundles["character"]:
            with self.subTest(ident=character["id"]):
                self.assertIn(character.get("faction_id"), self.faction_ids)
                self.assertIn(character.get("period"), self.period_names)
                for event_id in character.get("events", []):
                    self.assertIn(event_id, self.event_ids)

    def test_events(self):
        for event in self.bundles["event"]:
            with self.subTest(ident=event["id"]):
                self.assertIn(event.get("type"), EVENT_TYPES)
                self.assertIn(event.get("period"), self.period_names)
                if event.get("location_id"):
                    self.assertIn(event["location_id"], self.location_ids)
                for faction_id in event.get("factions", []):
                    self.assertIn(faction_id, self.faction_ids)
                for character_id in event.get("characters", []):
                    self.assertIn(character_id, self.character_ids)

    def test_locations_and_glossary(self):
        for location in self.bundles["location"]:
            with self.subTest(kind="location", ident=location["id"]):
                self.assertIn(location.get("type"), LOCATION_TYPES)
        for term in self.bundles["glossary"]:
            with self.subTest(kind="glossary", ident=term["id"]):
                self.assertIn(term.get("category"), GLOSSARY_CATEGORIES)

    def test_sources_exist_in_catalog(self):
        for name, items in self.bundles.items():
            for item in items:
                for source_id in item.get("sources", []):
                    with self.subTest(bundle=name, ident=item.get("id"), source=source_id):
                        self.assertIn(source_id, self.catalog)

    def test_disambiguation_shape(self):
        # Disambiguation entries may point at historical entities that are not
        # (yet) part of the game bundles, so only validate shape and vocabulary.
        for entry in self.bundles["disambiguation"]:
            with self.subTest(ident=entry["id"]):
                self.assertTrue(entry.get("term"))
                self.assertTrue(entry.get("guidance"))
                self.assertTrue(entry.get("conflicts"))
                for conflict in entry["conflicts"]:
                    self.assertTrue(conflict.get("name"))
                    if conflict.get("entity_id"):
                        self.assertRegex(conflict["entity_id"], r"^[a-z0-9][a-z0-9-]*$")

    def test_generated_bundles_match_shards(self):
        merged = {"faction": [], "character": [], "event": []}
        for name, pattern in (("faction", "factions/*.json"), ("character", "characters/*.json"), ("event", "events/*.json")):
            for path in sorted(DATA.glob(pattern)):
                merged[name].extend(load(path))
            with self.subTest(bundle=name):
                self.assertEqual(merged[name], self.bundles[name])
        for name in ("location", "glossary", "disambiguation"):
            source_file = "locations.json" if name == "location" else f"{name}.json"
            with self.subTest(bundle=name):
                self.assertEqual(load(DATA / source_file), self.bundles[name])


if __name__ == "__main__":
    unittest.main()
