# -*- coding: utf-8 -*-
"""Catalog consistency tests (no network, no full-text index required)."""

from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TEXTS = ROOT / "texts"

VALID_TYPES = {"primary", "modern", "fiction", "database"}
VALID_RELIABILITY = {"A", "A/B", "B", "B/C", "B/F", "C", "M", "F", "D"}
VALID_STATUS = {"included", "partial", "external"}


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = load(DATA / "catalog.json")
        cls.stats = load(DATA / "catalog_stats.json")
        cls.texts = load(TEXTS / "index.json")
        cls.by_id = {entry["id"]: entry for entry in cls.entries}

    def test_catalog_is_a_non_empty_list(self):
        self.assertIsInstance(self.entries, list)
        self.assertGreaterEqual(len(self.entries), 100)

    def test_ids_are_unique_and_present(self):
        ids = [entry.get("id") for entry in self.entries]
        self.assertTrue(all(ids), "every catalog entry needs an id")
        duplicates = [ident for ident, count in Counter(ids).items() if count > 1]
        self.assertEqual(duplicates, [], f"duplicate catalog ids: {duplicates}")

    def test_required_fields_and_enums(self):
        for entry in self.entries:
            ident = entry["id"]
            with self.subTest(ident=ident):
                self.assertIn(entry.get("type"), VALID_TYPES)
                self.assertIn(entry.get("priority"), {"core", "extended", "reference"})
                self.assertIn(entry.get("reliability"), VALID_RELIABILITY)
                self.assertTrue(entry.get("title"))
                self.assertTrue(entry.get("periods"), "periods must not be empty")
                fulltext = entry.get("fulltext") or {}
                self.assertIn(fulltext.get("status"), VALID_STATUS)

    def test_period_vocabulary_is_known(self):
        allowed = {
            "先秦", "秦汉", "两汉", "东汉末", "三国", "西晋", "东晋", "两晋",
            "魏晋", "十六国", "南朝", "北朝", "南北朝", "隋", "唐", "初唐",
            "盛唐", "中唐", "晚唐", "五代", "十国", "宋", "宋初", "跨期",
        }
        for entry in self.entries:
            for period in entry.get("periods", []):
                with self.subTest(ident=entry["id"], period=period):
                    self.assertIn(period, allowed)

    def test_modern_and_fiction_have_no_local_fulltext(self):
        for entry in self.entries:
            if entry.get("type") in {"modern", "fiction"}:
                status = (entry.get("fulltext") or {}).get("status")
                with self.subTest(ident=entry["id"]):
                    self.assertNotIn(status, {"included", "partial"})

    def test_stats_match_catalog(self):
        expected = {
            "total": len(self.entries),
            "primary": sum(1 for e in self.entries if e.get("type") == "primary"),
            "modern": sum(1 for e in self.entries if e.get("type") == "modern"),
            "fiction": sum(1 for e in self.entries if e.get("type") == "fiction"),
            "database": sum(1 for e in self.entries if e.get("type") == "database"),
            "included": sum(
                1 for e in self.entries if (e.get("fulltext") or {}).get("status") == "included"
            ),
            "core": sum(1 for e in self.entries if e.get("priority") == "core"),
            "by_period": dict(Counter(p for e in self.entries for p in e.get("periods", []))),
        }
        self.assertEqual(self.stats, expected)

    def test_included_fulltext_matches_texts_index(self):
        books = {book["id"]: book for book in self.texts.get("books", [])}
        for entry in self.entries:
            fulltext = entry.get("fulltext") or {}
            if fulltext.get("status") != "included":
                continue
            ident = entry["id"]
            with self.subTest(ident=ident):
                self.assertIn(ident, books, "included fulltext missing from texts/index.json")
                book = books[ident]
                if fulltext.get("volumes_available") is not None:
                    self.assertEqual(fulltext["volumes_available"], book["volume_count"])
                if fulltext.get("chars") is not None:
                    self.assertEqual(fulltext["chars"], book["chars"])
                self.assertTrue((ROOT / fulltext["path"]).is_dir())

    def test_partial_fulltext_paths_exist(self):
        for entry in self.entries:
            fulltext = entry.get("fulltext") or {}
            if fulltext.get("status") == "partial" and fulltext.get("path"):
                with self.subTest(ident=entry["id"]):
                    self.assertTrue((ROOT / fulltext["path"]).is_dir())

    def test_documented_core_books_exist(self):
        for ident in ("SANGUOZHI", "JINSHU", "ZIZHITONGJIAN", "JIUWUDAISHI", "XINWUDAISHI", "SHIGUOCHUNQIU"):
            with self.subTest(ident=ident):
                self.assertIn(ident, self.by_id)


if __name__ == "__main__":
    unittest.main()
