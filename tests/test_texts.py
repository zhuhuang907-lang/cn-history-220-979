# -*- coding: utf-8 -*-
"""Full-text index/manifest tests. Does not require index/search.db."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TEXTS = ROOT / "texts"

NAV_MARKERS = ("◄", "►", "姊妹計劃", "姊妹计划", "維基百科條目", "维基百科条目")


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class TextIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = load(TEXTS / "index.json")
        cls.books = cls.index.get("books", [])
        cls.catalog = {entry["id"]: entry for entry in load(DATA / "catalog.json")}

    def test_totals_are_consistent(self):
        self.assertEqual(self.index.get("book_count"), len(self.books))
        self.assertEqual(self.index.get("volume_count"), sum(book["volume_count"] for book in self.books))
        self.assertEqual(self.index.get("chars"), sum(book["chars"] for book in self.books))
        self.assertGreaterEqual(len(self.books), 40)

    def test_book_metadata(self):
        for book in self.books:
            with self.subTest(ident=book.get("id")):
                for key in ("id", "title", "slug", "path", "source_url", "license"):
                    self.assertTrue(book.get(key), f"missing {key}")
                self.assertGreater(book["volume_count"], 0)
                self.assertGreater(book["chars"], 0)
                self.assertTrue((ROOT / book["path"]).is_dir())

    def test_manifests_match_index(self):
        for book in self.books:
            book_dir = ROOT / book["path"]
            manifest_path = book_dir / "manifest.json"
            with self.subTest(ident=book["id"]):
                self.assertTrue(manifest_path.exists(), "manifest.json missing")
                manifest = load(manifest_path)
                self.assertEqual(manifest.get("volume_count"), book["volume_count"])
                self.assertEqual(manifest.get("chars"), book["chars"])
                files = sorted(book_dir.glob("卷*.txt"))
                self.assertEqual(len(files), book["volume_count"])
                self.assertEqual(len(manifest.get("volumes", [])), book["volume_count"])

    def test_volume_headers_and_navigation(self):
        for book in self.books:
            book_dir = ROOT / book["path"]
            for path in sorted(book_dir.glob("卷*.txt")):
                text = path.read_text(encoding="utf-8")
                with self.subTest(book=book["id"], file=path.name):
                    self.assertIn("许可：CC BY-SA 4.0", text[:800])
                    for marker in NAV_MARKERS:
                        self.assertNotIn(marker, text)

    def test_shiguochunqiu_is_complete_and_clean(self):
        book = next((b for b in self.books if b["id"] == "SHIGUOCHUNQIU"), None)
        self.assertIsNotNone(book)
        self.assertEqual(book["volume_count"], 114)
        self.assertGreater(book["chars"], 700_000)
        book_dir = ROOT / book["path"]
        first = (book_dir / "卷001.txt").read_text(encoding="utf-8")
        self.assertIn("太祖", first)
        self.assertNotIn("姊妹計劃", first)

    def test_catalog_fulltext_status_matches_index(self):
        indexed = {book["id"] for book in self.books}
        for ident, entry in self.catalog.items():
            status = (entry.get("fulltext") or {}).get("status")
            with self.subTest(ident=ident):
                if status == "included":
                    self.assertIn(ident, indexed)
                elif status == "external":
                    self.assertNotIn(ident, indexed)


if __name__ == "__main__":
    unittest.main()
