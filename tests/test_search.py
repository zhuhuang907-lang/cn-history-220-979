# -*- coding: utf-8 -*-
"""Search helper and CLI tests. Full-text cases skip when search.db is absent."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DB = ROOT / "index" / "search.db"

sys.path.insert(0, str(SCRIPTS))
import textutil as tu  # noqa: E402


def run_cli(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "search.py"), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


class TextUtilTests(unittest.TestCase):
    def test_traditional_to_simplified(self):
        self.assertEqual(tu.to_simplified("錢鏐"), "钱镠")
        self.assertEqual(tu.to_simplified("關羽"), "关羽")

    def test_normalize_query(self):
        self.assertEqual(tu.normalize_query("  錢鏐  "), "錢鏐")
        self.assertEqual(tu.normalize_query("钱　镠"), "钱 镠")

    def test_strip_header_removes_navigation(self):
        raw = (
            "# 十國春秋 卷077\n\n"
            "> 来源：Wikisource\n> 许可：CC BY-SA 4.0\n\n"
            "---\n\n"
            "吳越一  ◄\n"
            "►  吳越二\n"
            "姊妹計劃: 數據項\n"
            "維基百科條目：錢鏐\n"
            "武肅王世家上\n"
            "武肅王姓錢，名鏐。\n"
        )
        body = tu.strip_header(raw)
        self.assertNotIn("◄", body)
        self.assertNotIn("►", body)
        self.assertNotIn("姊妹計劃", body)
        self.assertIn("武肅王姓錢", body)
        self.assertNotIn("# 十國春秋", body)

    def test_count_occurrences_and_snippet(self):
        self.assertEqual(tu.count_occurrences("钱镠钱镠", "钱镠"), 2)
        content = "武肅王姓錢鏐字具美"
        content_sim = "武肃王姓钱镠字具美"
        snippet = tu.snippet(content, content_sim, "钱镠", width=6)
        self.assertIn("錢", snippet)
        self.assertIn("鏐", snippet)


class CatalogCliTests(unittest.TestCase):
    def test_catalog_json(self):
        result = run_cli("--catalog", "五代", "--type", "primary", "--json", "--limit", "10")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIsInstance(payload, list)
        self.assertTrue(payload)
        for entry in payload:
            self.assertEqual(entry["type"], "primary")
        self.assertTrue(any("五代" in json.dumps(entry, ensure_ascii=False) for entry in payload))

    def test_game_json(self):
        result = run_cli("--game", "高平", "--json", "--limit", "10")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIsInstance(payload, list)
        self.assertTrue(any(item["item"].get("id") == "gaoping" for item in payload))

    def test_stats(self):
        result = run_cli("--stats")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("全文", result.stdout)
        self.assertIn("目录", result.stdout)


@unittest.skipUnless(DB.exists(), "index/search.db not built")
class FulltextCliTests(unittest.TestCase):
    def test_traditional_query_hits_simplified_index(self):
        result = run_cli("錢鏐", "--book", "SHIGUOCHUNQIU", "--limit", "3", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertGreaterEqual(payload["count"], 1)
        for item in payload["results"]:
            self.assertEqual(item["book_id"], "SHIGUOCHUNQIU")
            self.assertNotIn("◄", item["snippet"])
            self.assertNotIn("姊妹計劃", item["snippet"])

    def test_period_and_reliability_filters(self):
        result = run_cli("節度使", "--period", "晚唐", "--reliability", "A", "--limit", "3", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["results"])
        for item in payload["results"]:
            self.assertEqual(item["reliability"], "A")

if __name__ == "__main__":
    unittest.main()
