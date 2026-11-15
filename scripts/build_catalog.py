#!/usr/bin/env python3
"""Merge, validate, and render the source catalog.

Source of truth: data/catalog/*.json (one file per category).
Outputs:
  data/catalog.json          merged machine-readable catalog
  site/data/catalog.json     copy for the static browser
  docs/catalog.md            human-readable tables
  data/catalog_stats.json    counts used by README and CI

Usage:
    python scripts/build_catalog.py
    python scripts/build_catalog.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "data" / "catalog"
OUT = ROOT / "data" / "catalog.json"
SITE_OUT = ROOT / "site" / "data" / "catalog.json"
DOCS_OUT = ROOT / "docs" / "catalog.md"
STATS_OUT = ROOT / "data" / "catalog_stats.json"

PERIODS = [
    "先秦", "秦汉", "两汉", "东汉末", "三国", "西晋", "东晋", "两晋", "魏晋", "十六国",
    "南朝", "北朝", "南北朝", "隋", "唐", "初唐", "盛唐", "中唐", "晚唐",
    "五代", "十国", "宋", "宋初", "跨期",
]
RELIABILITY = {"A", "A/B", "B", "B/C", "B/F", "C", "M", "F", "D", "?"}
TYPES = {"primary", "modern", "fiction", "database"}
TYPE_ORDER = {"primary": 0, "modern": 1, "fiction": 2, "database": 3}
PRIORITY_ORDER = {"core": 0, "extended": 1, "reference": 2}


def normalize(entry: dict, source_file: str) -> dict:
    e = dict(entry)
    e.setdefault("title_trad", e.get("title", ""))
    e.setdefault("title_en", "")
    e.setdefault("aliases", [])
    e.setdefault("authors", [])
    e.setdefault("periods", [])
    e.setdefault("cover_start", None)
    e.setdefault("cover_end", None)
    e.setdefault("genre", "")
    e.setdefault("structure", "")
    e.setdefault("reliability", "?")
    e.setdefault("summary", "")
    e.setdefault("game_use", "")
    e.setdefault("caveats", "")
    e.setdefault("links", {})
    e.setdefault("fulltext", {"status": "external", "path": None})
    e.setdefault("tags", [])
    e.setdefault("priority", "extended")
    e.setdefault("copyright", "")
    e["_source_file"] = source_file
    return e


def load() -> list[dict]:
    files = sorted(CATALOG_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"no catalog files under {CATALOG_DIR}")
    entries = []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
        if not isinstance(data, list):
            raise SystemExit(f"{path}: expected a JSON array")
        for item in data:
            entries.append(normalize(item, path.name))
    return entries


def validate(entries: list[dict]) -> list[str]:
    errors: list[str] = []
    seen: dict[str, str] = {}
    for e in entries:
        ident = e.get("id", "")
        if not ident:
            errors.append(f"{e['_source_file']}: entry missing id ({e.get('title', '?')})")
            continue
        if ident in seen:
            errors.append(f"duplicate id {ident}: {seen[ident]} and {e['_source_file']}")
        seen[ident] = e["_source_file"]
        if e.get("type") not in TYPES:
            errors.append(f"{ident}: invalid type {e.get('type')!r}")
        if e.get("reliability") not in RELIABILITY:
            errors.append(f"{ident}: invalid reliability {e.get('reliability')!r}")
        if not e.get("title"):
            errors.append(f"{ident}: missing title")
        if not isinstance(e.get("periods"), list):
            errors.append(f"{ident}: periods must be a list")
        for p in e.get("periods", []):
            if p not in PERIODS:
                errors.append(f"{ident}: unknown period {p!r}")
        for key, value in (e.get("links") or {}).items():
            if value and not str(value).startswith(("http://", "https://")):
                errors.append(f"{ident}: link {key} is not an http(s) URL: {value}")
        ft = e.get("fulltext") or {}
        if ft.get("status") not in {"included", "external", "partial"}:
            errors.append(f"{ident}: invalid fulltext.status {ft.get('status')!r}")
        if ft.get("status") == "included" and ft.get("path"):
            path = ROOT / ft["path"]
            if not path.exists():
                # Text downloads may still be in progress; warn, do not fail.
                print(f"warning: {ident}: fulltext path not found yet: {ft['path']}", file=sys.stderr)
    return errors


def sort_key(e: dict):
    return (
        TYPE_ORDER.get(e.get("type"), 9),
        PRIORITY_ORDER.get(e.get("priority"), 9),
        e.get("cover_start") if e.get("cover_start") is not None else 9999,
        e.get("title", ""),
    )


def fmt_range(e: dict) -> str:
    start, end = e.get("cover_start"), e.get("cover_end")
    if start is None and end is None:
        return ""
    if start is None:
        return f"–{end}"
    if end is None:
        return f"{start}–"
    return f"{start}–{end}"


def md_table(rows: list[dict]) -> str:
    lines = [
        "| ID | 书名 | 作者 | 成书/版本 | 覆盖 | 可信度 | 全文 |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in rows:
        authors = "、".join(a.get("name", "") for a in e.get("authors", [])) or "—"
        fulltext = e.get("fulltext", {})
        ft = "库内" if fulltext.get("status") == "included" else ("部分" if fulltext.get("status") == "partial" else "外链")
        if fulltext.get("path"):
            ft = f"库内 `{fulltext['path']}`"
        lines.append(
            f"| `{e['id']}` | **{e['title']}**<br>{e.get('title_trad', '')} | {authors} | "
            f"{e.get('date', '—')} | {fmt_range(e) or '—'} | {e.get('reliability', '?')} | {ft} |"
        )
    return "\n".join(lines)


def render_docs(entries: list[dict], stats: dict) -> str:
    by_type = defaultdict(list)
    for e in entries:
        by_type[e.get("type")].append(e)

    lines = [
        "# 史料目录",
        "",
        "> 本文件由 `scripts/build_catalog.py` 自动生成，请修改 `data/catalog/*.json` 后重新生成。",
        "",
        "## 统计",
        "",
        f"- 条目总数：**{stats['total']}**",
        f"- 原始史料：**{stats['primary']}**（其中库内全文：**{stats['included']}** 条）",
        f"- 现代研究：**{stats['modern']}**（版权作品，仅元数据与外链）",
        f"- 小说/游戏参考：**{stats['fiction']}**",
        f"- 数据库/工具：**{stats['database']}**",
        "",
        "## 可信度标记",
        "",
        "| 标记 | 含义 |",
        "|---|---|",
        "| **A** | 正史、编年史、政书、同时代原始文献；仍需注意立场与回护 |",
        "| **A/B** | 基本可靠，但有删润、回护或成书较晚的问题 |",
        "| **B** | 别史、方志、笔记、文集、碑志；有偏见或传闻 |",
        "| **B/C** | 后世汇编、类书、辑本；需查原始出处 |",
        "| **C** | 类书、总集、后世考证；转引与删改较多 |",
        "| **M** | 现代研究；有解释框架与学术争议，版权保护 |",
        "| **F** | 小说、演义、影视/游戏设定；不作史实依据 |",
        "| **D** | 数据库、工具书、地图集；注意许可与版本 |",
        "",
        "## 正史与核心史料",
        "",
        md_table(sorted(by_type["primary"], key=sort_key)),
        "",
        "## 现代研究（版权作品，仅元数据）",
        "",
        "> 以下著作受版权保护。本库只提供书目信息与外链，不包含正文。",
        "",
        md_table(sorted(by_type["modern"], key=sort_key)),
        "",
        "## 小说、演义与游戏参考",
        "",
        "> 可信度标记为 **F**。可用于人物形象、叙事桥段、台词风格与氛围，不可当作史实。",
        "",
        md_table(sorted(by_type["fiction"], key=sort_key)),
        "",
        "## 数据库与工具",
        "",
        md_table(sorted(by_type["database"], key=sort_key)),
        "",
        "## 按时代索引",
        "",
    ]

    for period in PERIODS:
        rows = [e for e in entries if period in e.get("periods", [])]
        if not rows:
            continue
        lines.append(f"### {period}")
        lines.append("")
        lines.append("、".join(f"[{e['title']}](catalog.md#{e['id'].lower()})" for e in sorted(rows, key=sort_key)))
        lines.append("")

    lines.extend([
        "## 使用建议",
        "",
        "1. 先查本目录确定史料层级与可信度，再读原文。",
        "2. 正史之间对读：`旧唐书` ↔ `新唐书` ↔ `资治通鉴`；`旧五代史` ↔ `新五代史` ↔ `十国春秋`。",
        "3. 笔记、类书、总集只作补充；引用时尽量回溯到原始出处。",
        "4. 小说与演义只用于叙事与氛围，不用于事实断言。",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated outputs are stale")
    args = parser.parse_args(argv)

    entries = load()
    errors = validate(entries)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    entries.sort(key=sort_key)
    for e in entries:
        e.pop("_source_file", None)

    stats = {
        "total": len(entries),
        "primary": sum(1 for e in entries if e["type"] == "primary"),
        "modern": sum(1 for e in entries if e["type"] == "modern"),
        "fiction": sum(1 for e in entries if e["type"] == "fiction"),
        "database": sum(1 for e in entries if e["type"] == "database"),
        "included": sum(1 for e in entries if e.get("fulltext", {}).get("status") == "included"),
        "core": sum(1 for e in entries if e.get("priority") == "core"),
        "by_period": dict(Counter(p for e in entries for p in e.get("periods", []))),
    }

    catalog_text = json.dumps(entries, ensure_ascii=False, indent=2) + "\n"
    stats_text = json.dumps(stats, ensure_ascii=False, indent=2) + "\n"
    docs_text = render_docs(entries, stats)

    outputs = {
        OUT: catalog_text,
        SITE_OUT: catalog_text,
        STATS_OUT: stats_text,
        DOCS_OUT: docs_text,
    }

    if args.check:
        stale = []
        for path, text in outputs.items():
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(str(path.relative_to(ROOT)))
        if stale:
            print("stale generated files: " + ", ".join(stale), file=sys.stderr)
            return 1
        print("catalog outputs are up to date")
        return 0

    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    print(f"catalog: {stats['total']} entries "
          f"({stats['primary']} primary, {stats['modern']} modern, {stats['fiction']} fiction, {stats['database']} database)")
    print(f"included fulltext: {stats['included']}")
    for path in outputs:
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
