# -*- coding: utf-8 -*-
"""Static-site payload and build tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
GAME = DATA / "game"
SITE = ROOT / "site"
SITE_DATA = SITE / "data"


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class SiteDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load(SITE_DATA / "manifest.json")

    def test_required_assets_exist(self):
        for name in ("index.html", "app.js", "style.css", "favicon.svg", "data/manifest.json"):
            with self.subTest(file=name):
                self.assertTrue((SITE / name).exists())

    def test_payloads_match_sources(self):
        pairs = [
            (DATA / "catalog.json", SITE_DATA / "catalog.json"),
            (DATA / "catalog_stats.json", SITE_DATA / "catalog_stats.json"),
            (DATA / "periods.json", SITE_DATA / "periods.json"),
            (ROOT / "texts" / "index.json", SITE_DATA / "texts_index.json"),
        ]
        for source, copy in pairs:
            with self.subTest(file=copy.name):
                self.assertTrue(copy.exists())
                self.assertEqual(load(source), load(copy))

    def test_game_payloads_match_sources(self):
        for name in (
            "factions", "characters", "events", "locations",
            "glossary", "disambiguation", "periods", "index",
        ):
            with self.subTest(bundle=name):
                copy = SITE_DATA / "game" / f"{name}.json"
                self.assertTrue(copy.exists())
                self.assertEqual(load(GAME / f"{name}.json"), load(copy))

    def test_manifest_summary(self):
        texts = load(ROOT / "texts" / "index.json")
        stats = load(DATA / "catalog_stats.json")
        game = load(GAME / "index.json")
        self.assertEqual(self.manifest["catalog_entries"], stats["total"])
        self.assertEqual(self.manifest["fulltext_books"], stats["included"])
        self.assertEqual(self.manifest["texts"]["volumes"], texts["volume_count"])
        self.assertEqual(self.manifest["texts"]["chars"], texts["chars"])
        self.assertEqual(self.manifest["game"], game["counts"])
        for name in self.manifest["files"]:
            with self.subTest(file=name):
                self.assertTrue((SITE_DATA / name).exists())

    def test_html_links_assets(self):
        html = (SITE / "index.html").read_text(encoding="utf-8")
        self.assertIn("app.js", html)
        self.assertIn("style.css", html)
        self.assertIn('lang="zh-CN"', html)

    def test_build_site_check(self):
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_site.py"), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_javascript_syntax(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        result = subprocess.run(
            [node, "--check", str(SITE / "app.js")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
