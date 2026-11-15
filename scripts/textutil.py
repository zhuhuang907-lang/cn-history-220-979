# -*- coding: utf-8 -*-
"""Shared helpers for the cn-history-220-979 corpus.

No third-party dependencies. All functions are pure Python and operate on
UTF-8 files under the repository root.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TEXTS = ROOT / "texts"
INDEX = ROOT / "index"

HEADER_SEP = re.compile(r"^-{3,}\s*$")


def read_json(path: Path):
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_ts_map() -> dict[str, str]:
    """Traditional -> simplified single-character map (OpenCC TSCharacters)."""
    path = DATA / "variants" / "ts_characters.txt"
    mapping: dict[str, str] = {}
    if not path.exists():
        return mapping
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            key = parts[0]
            val = parts[1].split(" ")[0]
            if key and val:
                mapping[key] = val
    return mapping


def to_simplified(text: str) -> str:
    m = load_ts_map()
    if not m:
        return text
    return "".join(m.get(ch, ch) for ch in text)


def strip_header(text: str) -> str:
    """Drop the generated header and Wikisource navigation debris."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if HEADER_SEP.match(line.strip()):
            lines = lines[i + 1:]
            break
    else:
        i = 0
        while i < len(lines) and (lines[i].startswith("#") or lines[i].startswith(">") or not lines[i].strip()):
            i += 1
        lines = lines[i:]

    cleaned = []
    for line in lines:
        line = line.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        if stripped.startswith("../") or stripped in {"◄", "►", "←", "→", "歷史", "姊妹计划: 数据项", "姊妹計劃: 數據項"}:
            continue
        if any(marker in stripped for marker in ("◄", "►", "←", "→")):
            continue
        if stripped.startswith(("姊妹计划", "姊妹計劃", "维基百科条目", "維基百科條目", "数据项", "數據項")):
            continue
        cleaned.append(line.rstrip())

    body = "\n".join(cleaned).lstrip("\n")
    return re.sub(r"\n{3,}", "\n\n", body)


def iter_books():
    """Yield (book_meta, manifest) for every fetched book."""
    index_path = TEXTS / "index.json"
    if not index_path.exists():
        return
    idx = read_json(index_path)
    for book in idx.get("books", []):
        manifest_path = ROOT / book["path"] / "manifest.json"
        manifest = read_json(manifest_path) if manifest_path.exists() else {}
        yield book, manifest


def iter_volumes(book: dict, manifest: dict):
    """Yield volume dicts with resolved text, in volume order."""
    meta_by_file = {v.get("file"): v for v in manifest.get("volumes", [])}
    folder = ROOT / book["path"]
    files = sorted(folder.glob("卷*.txt"))
    for path in files:
        raw = path.read_text(encoding="utf-8")
        meta = meta_by_file.get(path.name, {})
        first = raw.splitlines()[0] if raw else ""
        title = first.lstrip("# ").strip() if first.startswith("#") else path.stem
        body = strip_header(raw)
        yield {
            "book_id": book["id"],
            "book_title": book.get("title", book["id"]),
            "slug": book.get("slug", ""),
            "path": path.relative_to(ROOT).as_posix(),
            "file": path.name,
            "volume": meta.get("volume") or _volume_number(path.stem),
            "label": meta.get("volume_label") or path.stem.replace("卷", ""),
            "section": meta.get("section") or "",
            "page_title": meta.get("page_title") or "",
            "url": meta.get("url") or book.get("source_url", ""),
            "title": title,
            "chars": len(body),
            "content": body,
        }


def _volume_number(stem: str) -> int | None:
    m = re.search(r"(\d+)", stem)
    return int(m.group(1)) if m else None


def catalog_map() -> dict[str, dict]:
    path = DATA / "catalog.json"
    if not path.exists():
        return {}
    entries = read_json(path)
    return {e["id"]: e for e in entries}


def period_ranges() -> dict[str, tuple[int, int]]:
    """Map period name -> (start, end). Missing bounds become wide ranges."""
    path = DATA / "periods.json"
    if not path.exists():
        return {}
    out = {}
    for p in read_json(path):
        name = p.get("name")
        if not name:
            continue
        start = p.get("start")
        end = p.get("end")
        out[name] = (start if isinstance(start, int) else -1000,
                     end if isinstance(end, int) else 3000)
    return out


def book_periods(book_id: str, catalog: dict[str, dict] | None = None) -> list[str]:
    catalog = catalog if catalog is not None else catalog_map()
    entry = catalog.get(book_id) or {}
    return list(entry.get("periods") or [])


def book_reliability(book_id: str, catalog: dict[str, dict] | None = None) -> str:
    catalog = catalog if catalog is not None else catalog_map()
    return (catalog.get(book_id) or {}).get("reliability", "")


def books_for_periods(periods: list[str], catalog: dict[str, dict] | None = None) -> set[str]:
    """Books whose catalog period list or cover range overlaps the requested periods."""
    catalog = catalog if catalog is not None else catalog_map()
    ranges = period_ranges()
    wanted = [ranges[p] for p in periods if p in ranges]
    out: set[str] = set()
    for book_id, entry in catalog.items():
        if set(periods) & set(entry.get("periods") or []):
            out.add(book_id)
            continue
        if not wanted:
            continue
        start = entry.get("cover_start")
        end = entry.get("cover_end")
        if start is None and end is None:
            continue
        start = start if isinstance(start, int) else -3000
        end = end if isinstance(end, int) else 3000
        for p_start, p_end in wanted:
            if start <= p_end and end >= p_start:
                out.add(book_id)
                break
    return out


def normalize_query(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip())


def snippet(content: str, content_sim: str, q_sim: str, width: int = 70) -> str:
    """Return a readable window around the first match, preserving original text."""
    idx = content_sim.find(q_sim)
    if idx < 0:
        return content_sim[: width * 2].replace("\n", " ")
    same_len = len(content_sim) == len(content)
    src = content if same_len else content_sim
    start = max(0, idx - width)
    end = min(len(src), idx + len(q_sim) + width)
    piece = src[start:end].replace("\n", " ")
    return ("…" if start > 0 else "") + piece + ("…" if end < len(src) else "")


def count_occurrences(haystack: str, needle: str) -> int:
    if not needle:
        return 0
    n = 0
    i = haystack.find(needle)
    while i >= 0:
        n += 1
        i = haystack.find(needle, i + len(needle))
    return n


def format_citation(book_title: str, label: str, section: str = "") -> str:
    vol = f"卷{label}" if label and not str(label).startswith("卷") else str(label)
    tail = f"·{section}" if section else ""
    return f"《{book_title}》{vol}{tail}"
