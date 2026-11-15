# -*- coding: utf-8 -*-
"""Search the corpus: full texts, catalog metadata, and game data.

Examples:
    python scripts/search.py 關羽
    python scripts/search.py 关羽 --book SANGUOZHI --limit 5
    python scripts/search.py 节度使 --period 晚唐 --reliability A
    python scripts/search.py --catalog 五代 --type primary
    python scripts/search.py --game 高平
    python scripts/search.py --show SANGUOZHI 36
    python scripts/search.py --stats
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import textutil as tu  # noqa: E402

ROOT = tu.ROOT
DEFAULT_DB = tu.INDEX / "search.db"
GAME = tu.DATA / "game"


def split_arg(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


# ---------------------------------------------------------------- full text
def fulltext(args) -> int:
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"index not found: {db_path}\nrun: python scripts/build_index.py", file=sys.stderr)
        return 2
    q = tu.normalize_query(args.query or "")
    if not q:
        print("empty query", file=sys.stderr)
        return 2
    q_sim = tu.to_simplified(q)

    books = split_arg(args.book)
    periods = split_arg(args.period)
    rels = split_arg(args.reliability)
    types = split_arg(args.type)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    where = []
    params: list = []
    if books:
        where.append(f"v.book_id IN ({','.join('?' * len(books))})")
        params += books
    if rels:
        where.append(f"b.reliability IN ({','.join('?' * len(rels))})")
        params += rels
    if types:
        where.append(f"b.type IN ({','.join('?' * len(types))})")
        params += types
    if periods:
        period_books = tu.books_for_periods(periods)
        if not period_books:
            print(f"no books cover period(s): {', '.join(periods)}", file=sys.stderr)
            return 1
        where.append(f"v.book_id IN ({','.join('?' * len(period_books))})")
        params += sorted(period_books)
    where_sql = (" AND " + " AND ".join(where)) if where else ""

    rows = []
    fts_used = False
    try:
        info = tu.read_json(tu.INDEX / "build_info.json") if (tu.INDEX / "build_info.json").exists() else {}
    except Exception:
        info = {}
    if len(q_sim) >= 3 and info.get("fts5_trigram", True):
        match = '"' + q_sim.replace('"', '""') + '"'
        sql = (
            "SELECT v.*, b.title AS book_title, b.reliability, b.periods, b.type AS book_type, "
            "bm25(volumes_fts) AS rank FROM volumes_fts "
            "JOIN volumes v ON v.id = volumes_fts.rowid "
            "JOIN books b ON b.id = v.book_id "
            f"WHERE volumes_fts MATCH ?{where_sql} ORDER BY rank LIMIT ?"
        )
        try:
            rows = conn.execute(sql, [match] + params + [args.limit]).fetchall()
            fts_used = True
        except sqlite3.OperationalError:
            rows = []

    if not rows:
        sql = (
            "SELECT v.*, b.title AS book_title, b.reliability, b.periods, b.type AS book_type, 0 AS rank "
            "FROM volumes v JOIN books b ON b.id = v.book_id "
            f"WHERE v.content_sim LIKE ?{where_sql} LIMIT 400"
        )
        rows = conn.execute(sql, [f"%{q_sim}%"] + params).fetchall()
        scored = []
        for r in rows:
            hits = tu.count_occurrences(r["content_sim"], q_sim)
            scored.append((hits, r))
        scored.sort(key=lambda x: (-x[0], 0 if x[1]["reliability"] == "A" else 1, -x[1]["chars"]))
        rows = [r for _, r in scored[: args.limit]]

    results = []
    for r in rows:
        results.append(
            {
                "book_id": r["book_id"],
                "book_title": r["book_title"],
                "volume": r["volume"],
                "label": r["label"],
                "section": r["section"],
                "title": r["title"],
                "path": r["path"],
                "url": r["url"],
                "reliability": r["reliability"],
                "periods": json.loads(r["periods"] or "[]"),
                "hits": tu.count_occurrences(r["content_sim"], q_sim),
                "snippet": tu.snippet(r["content"], r["content_sim"], q_sim, args.context),
            }
        )
    conn.close()

    if args.json:
        print(json.dumps({"query": q, "query_simplified": q_sim, "fts": fts_used,
                          "count": len(results), "results": results}, ensure_ascii=False, indent=2))
        return 0

    print(f"查询「{q}」 → {len(results)} 卷（limit={args.limit}{'，FTS' if fts_used else '，LIKE'}）\n")
    for i, r in enumerate(results, 1):
        cite = tu.format_citation(r["book_title"], r["label"] or r["volume"], r["section"])
        print(f"[{i}] {cite}")
        print(f"    {r['book_id']} · {r['path']} · {r['reliability'] or '?'} · 命中 {r['hits']} 次")
        print(f"    {r['snippet']}")
        if r["url"]:
            print(f"    {r['url']}")
        print()
    if results:
        print("引用示例：")
        r = results[0]
        print(f"  {tu.format_citation(r['book_title'], r['label'] or r['volume'], r['section'])}，"
              f"Wikisource 转录（CC BY-SA 4.0），{r['url']}")
    return 0


# ---------------------------------------------------------------- catalog
def catalog(args) -> int:
    entries = tu.read_json(tu.DATA / "catalog.json")
    q = (args.catalog or "").strip()
    q_sim = tu.to_simplified(q)
    periods = split_arg(args.period)
    rels = split_arg(args.reliability)
    types = split_arg(args.type)

    out = []
    for e in entries:
        if types and e.get("type") not in types:
            continue
        if rels and e.get("reliability") not in rels:
            continue
        if periods and not set(periods) & set(e.get("periods") or []):
            continue
        if q:
            blob = " ".join(
                [
                    e.get("id", ""),
                    e.get("title", ""),
                    e.get("title_trad", ""),
                    e.get("title_en", ""),
                    " ".join(e.get("aliases") or []),
                    " ".join(a.get("name", "") for a in e.get("authors") or []),
                    e.get("summary", ""),
                    e.get("genre", ""),
                    " ".join(e.get("tags") or []),
                ]
            )
            if q_sim not in tu.to_simplified(blob) and q not in blob:
                continue
        out.append(e)

    order = {"primary": 0, "modern": 1, "fiction": 2, "database": 3}
    out.sort(key=lambda e: (order.get(e.get("type"), 9), 0 if e.get("priority") == "core" else 1, e.get("title", "")))
    out = out[: args.limit]

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print(f"目录检索「{q or '*'}」 → {len(out)} 条\n")
    for i, e in enumerate(out, 1):
        ft = e.get("fulltext") or {}
        status = ft.get("status", "external")
        print(f"[{i}] {e.get('title')}（{e.get('id')}）")
        print(f"    {e.get('type')} · {e.get('priority')} · 可信度 {e.get('reliability')} · "
              f"{'/'.join(e.get('periods') or [])} · {e.get('genre', '')}")
        authors = "、".join(a.get("name", "") for a in e.get("authors") or [])
        if authors:
            print(f"    作者：{authors} · {e.get('structure', '')}")
        if status in ("included", "partial"):
            extra = f"（{ft.get('volumes_available')} 卷 / {ft.get('chars', 0):,} 字）"
            print(f"    全文：{status} {ft.get('path')}{extra}")
        else:
            print(f"    全文：外链 {((e.get('links') or {}).get('wikisource') or '')}")
        print(f"    {e.get('summary', '')[:160]}")
        print()
    return 0


# ---------------------------------------------------------------- game data
def game(args) -> int:
    q = (args.game or "").strip()
    q_sim = tu.to_simplified(q)
    bundles = [
        ("faction", "factions.json"),
        ("character", "characters.json"),
        ("event", "events.json"),
        ("location", "locations.json"),
        ("glossary", "glossary.json"),
        ("disambiguation", "disambiguation.json"),
    ]
    results = []
    for kind, name in bundles:
        path = GAME / name
        if not path.exists():
            continue
        for item in tu.read_json(path):
            if kind == "glossary":
                fields = [item.get("term", ""), item.get("term_en", ""), " ".join(item.get("aliases") or []),
                          item.get("definition", "")]
            elif kind == "disambiguation":
                fields = [item.get("term", ""), " ".join(c.get("name", "") for c in item.get("conflicts") or []),
                          item.get("guidance", "")]
            else:
                fields = [item.get("name", ""), item.get("name_en", ""), " ".join(item.get("aliases") or []),
                          item.get("summary", ""), " ".join(item.get("tags") or []),
                          " ".join(item.get("game_hooks") or [])]
            blob = " ".join(str(x) for x in fields if x)
            if q and q_sim not in tu.to_simplified(blob) and q not in blob:
                continue
            primary = item.get("name") or item.get("term") or ""
            aliases = " ".join(item.get("aliases") or [])
            if not q:
                score = 3
            elif q_sim in tu.to_simplified(primary):
                score = 0
            elif q_sim in tu.to_simplified(aliases):
                score = 1
            else:
                score = 2
            results.append((score, kind, item))

    kind_order = {"event": 0, "character": 1, "faction": 2, "location": 3, "glossary": 4, "disambiguation": 5}
    results.sort(key=lambda x: (x[0], kind_order.get(x[1], 9), x[2].get("year") or 0))
    results = [(kind, item) for _, kind, item in results]

    if args.json:
        print(json.dumps([{"kind": k, "item": v} for k, v in results[: args.limit]], ensure_ascii=False, indent=2))
        return 0

    print(f"游戏数据检索「{q or '*'}」 → {len(results)} 条（显示 {min(len(results), args.limit)}）\n")
    for kind, item in results[: args.limit]:
        name = item.get("term") or item.get("name")
        ident = item.get("id", "")
        summary = item.get("summary") or item.get("definition") or item.get("guidance") or ""
        print(f"[{kind}] {name}（{ident}）")
        if kind == "event":
            print(f"    {item.get('year')} · {item.get('type')} · {item.get('period') or ''}")
        elif kind == "character":
            print(f"    {item.get('period')} · {item.get('faction_id')} · {'/'.join(item.get('roles') or [])}")
        elif kind == "faction":
            print(f"    {item.get('period')} · {item.get('type')} · {item.get('start')}–{item.get('end')}")
        elif kind == "location":
            print(f"    {item.get('modern_name')} · {item.get('type')}")
        print(f"    {summary[:160]}")
        print()
    return 0


# ---------------------------------------------------------------- show / stats
def show(args) -> int:
    book_id, vol = args.show
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"index not found: {db_path}\nrun: python scripts/build_index.py", file=sys.stderr)
        return 2
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = None
    if str(vol).isdigit():
        row = conn.execute(
            "SELECT * FROM volumes WHERE book_id = ? AND volume = ?", (book_id, int(vol))
        ).fetchone()
    if row is None:
        row = conn.execute(
            "SELECT * FROM volumes WHERE book_id = ? AND label = ?", (book_id, str(vol))
        ).fetchone()
    if row is None:
        print(f"volume not found: {book_id} {vol}", file=sys.stderr)
        return 1
    print(f"# {row['title']}")
    print(f"# {row['path']} · {row['url']}")
    print()
    print(row["content"])
    conn.close()
    return 0


def stats(args) -> int:
    info = tu.read_json(tu.INDEX / "build_info.json") if (tu.INDEX / "build_info.json").exists() else None
    texts = tu.read_json(tu.TEXTS / "index.json")
    catalog = tu.read_json(tu.DATA / "catalog.json")
    game_index = tu.read_json(GAME / "index.json") if (GAME / "index.json").exists() else {}

    print("== 全文 ==")
    print(f"书目：{texts.get('book_count')} 部，{texts.get('volume_count')} 卷，{texts.get('chars', 0):,} 字")
    if info:
        print(f"索引：{info.get('database')}（{info.get('size_mb')} MB，FTS5={info.get('fts5_trigram')}，"
              f"{info.get('volumes')} 卷）")
    else:
        print("索引：未构建（python scripts/build_index.py）")
    print("\n== 目录 ==")
    by_type: dict[str, int] = {}
    for e in catalog:
        by_type[e.get("type", "?")] = by_type.get(e.get("type", "?"), 0) + 1
    print(f"条目：{len(catalog)}（" + "，".join(f"{k}={v}" for k, v in sorted(by_type.items())) + "）")
    print("\n== 游戏数据 ==")
    counts = game_index.get("counts", {})
    print("，".join(f"{k}={v}" for k, v in counts.items()))
    return 0


def list_books(args) -> int:
    catalog = tu.catalog_map()
    texts = tu.read_json(tu.TEXTS / "index.json")
    print(f"{'ID':32} {'书名':20} {'卷':>5} {'字':>10} 可信度  时代")
    for b in sorted(texts.get("books", []), key=lambda x: x["id"]):
        e = catalog.get(b["id"], {})
        print(f"{b['id']:32} {b.get('title_simplified') or b.get('title'):20} {b.get('volume_count', 0):>5} "
              f"{b.get('chars', 0):>10,} {e.get('reliability', '?'):>6}  {'/'.join(e.get('periods') or [])}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Search the cn-history corpus.")
    ap.add_argument("query", nargs="?", default=None, help="full-text query")
    ap.add_argument("--book", help="book id(s), comma separated")
    ap.add_argument("--period", help="period name(s), comma separated")
    ap.add_argument("--reliability", help="reliability code(s), comma separated")
    ap.add_argument("--type", help="catalog type(s): primary,modern,fiction,database")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--context", type=int, default=70, help="snippet width in characters")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--catalog", metavar="QUERY", help="search catalog metadata")
    ap.add_argument("--game", metavar="QUERY", help="search game data bundles")
    ap.add_argument("--show", nargs=2, metavar=("BOOK_ID", "VOLUME"), help="print one volume")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--list-books", action="store_true")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    args = ap.parse_args()

    if args.stats:
        return stats(args)
    if args.list_books:
        return list_books(args)
    if args.show:
        return show(args)
    if args.catalog is not None:
        return catalog(args)
    if args.game is not None:
        return game(args)
    return fulltext(args)


if __name__ == "__main__":
    raise SystemExit(main())
