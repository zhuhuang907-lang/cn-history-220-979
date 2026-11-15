# -*- coding: utf-8 -*-
"""Build the full-text search index.

Usage:
    python scripts/build_index.py [--force] [--db index/search.db]

Outputs:
    index/search.db        SQLite database (FTS5 trigram when available)
    index/volumes.jsonl    Volume metadata, one JSON object per line
    index/build_info.json  Build statistics

The database is a local build artifact and is not committed to git; run this
script after cloning.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import textutil as tu  # noqa: E402

ROOT = tu.ROOT
INDEX = tu.INDEX
DEFAULT_DB = INDEX / "search.db"


def build(db_path: Path, force: bool) -> int:
    if db_path.exists():
        if not force:
            print(f"index exists: {db_path} (use --force to rebuild)")
            return 0
        db_path.unlink()

    INDEX.mkdir(parents=True, exist_ok=True)
    catalog = tu.catalog_map()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.executescript(
        """
        CREATE TABLE books (
            id TEXT PRIMARY KEY,
            title TEXT,
            title_simplified TEXT,
            slug TEXT,
            path TEXT,
            source_url TEXT,
            license TEXT,
            volume_count INTEGER,
            chars INTEGER,
            periods TEXT,
            reliability TEXT,
            genre TEXT,
            type TEXT
        );
        CREATE TABLE volumes (
            id INTEGER PRIMARY KEY,
            book_id TEXT NOT NULL,
            volume INTEGER,
            label TEXT,
            section TEXT,
            title TEXT,
            path TEXT,
            url TEXT,
            chars INTEGER,
            content TEXT NOT NULL,
            content_sim TEXT NOT NULL
        );
        CREATE INDEX idx_volumes_book ON volumes(book_id);
        """
    )

    fts = False
    try:
        conn.execute(
            "CREATE VIRTUAL TABLE volumes_fts USING fts5("
            "content_sim, content='volumes', content_rowid='id', tokenize='trigram')"
        )
        fts = True
    except sqlite3.OperationalError as exc:
        print(f"warning: FTS5 trigram unavailable ({exc}); falling back to LIKE scan")

    started = time.time()
    book_rows = 0
    vol_rows = 0
    chars = 0
    volumes_jsonl = INDEX / "volumes.jsonl"

    with volumes_jsonl.open("w", encoding="utf-8") as jf:
        for book, manifest in tu.iter_books():
            entry = catalog.get(book["id"], {})
            conn.execute(
                "INSERT INTO books VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    book["id"],
                    book.get("title", ""),
                    book.get("title_simplified", ""),
                    book.get("slug", ""),
                    book.get("path", ""),
                    book.get("source_url", ""),
                    book.get("license", ""),
                    book.get("volume_count", 0),
                    book.get("chars", 0),
                    json.dumps(entry.get("periods", []), ensure_ascii=False),
                    entry.get("reliability", ""),
                    entry.get("genre", ""),
                    entry.get("type", ""),
                ),
            )
            book_rows += 1
            for vol in tu.iter_volumes(book, manifest):
                sim = tu.to_simplified(vol["content"])
                cur = conn.execute(
                    "INSERT INTO volumes (book_id, volume, label, section, title, path, url, chars, content, content_sim)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        vol["book_id"],
                        vol["volume"],
                        vol["label"],
                        vol["section"],
                        vol["title"],
                        vol["path"],
                        vol["url"],
                        vol["chars"],
                        vol["content"],
                        sim,
                    ),
                )
                rowid = cur.lastrowid
                if fts:
                    conn.execute(
                        "INSERT INTO volumes_fts(rowid, content_sim) VALUES (?, ?)",
                        (rowid, sim),
                    )
                meta = {k: v for k, v in vol.items() if k not in ("content",)}
                meta["id"] = rowid
                jf.write(json.dumps(meta, ensure_ascii=False) + "\n")
                vol_rows += 1
                chars += vol["chars"]
            print(f"  {book['id']}: {book.get('title', '')}")

    conn.commit()
    conn.execute("PRAGMA optimize")
    conn.close()

    elapsed = round(time.time() - started, 1)
    size_mb = round(db_path.stat().st_size / 1048576, 1)
    info = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "database": db_path.relative_to(ROOT).as_posix(),
        "size_mb": size_mb,
        "books": book_rows,
        "volumes": vol_rows,
        "chars": chars,
        "fts5_trigram": fts,
        "elapsed_seconds": elapsed,
        "sqlite_version": sqlite3.sqlite_version,
    }
    (INDEX / "build_info.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the SQLite full-text index.")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    return build(Path(args.db), args.force)


if __name__ == "__main__":
    raise SystemExit(main())
