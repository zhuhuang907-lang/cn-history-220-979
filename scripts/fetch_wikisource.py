#!/usr/bin/env python3
"""Fetch public-domain classical Chinese histories from Chinese Wikisource.

The script is deliberately dependency-free (Python standard library only).
It discovers volume subpages through the MediaWiki API, caches raw responses,
converts wikitext to readable plain text, and records provenance in a manifest.

Examples
--------
    python scripts/fetch_wikisource.py --discover --all-core
    python scripts/fetch_wikisource.py --book SANGUOZHI
    python scripts/fetch_wikisource.py --book SANGUOZHI --limit 3 --force
    python scripts/fetch_wikisource.py --all-core --delay 1.2

License note: the source transcriptions are contributed by Wikisource
editors and are generally licensed CC BY-SA 4.0.  Each output file keeps the
source URL, revision id, and license notice.  This script only downloads
public-domain classical texts, never modern copyrighted editions.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "manifests" / "wikisource_books.json"
TEXTS_DIR = ROOT / "texts"
CACHE_DIR = ROOT / "cache" / "wikisource"
API = "https://zh.wikisource.org/w/api.php"
USER_AGENT = (
    "cn-history-220-979/0.1 "
    "(https://github.com/zhuhuang907-lang/cn-history-220-979; educational dataset)"
)


# ---------------------------------------------------------------------------
# HTTP / API helpers
# ---------------------------------------------------------------------------

def api_get(params: dict, retries: int = 5, timeout: int = 90) -> dict:
    params = dict(params)
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    url = API + "?" + urllib.parse.urlencode(params)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "zh-Hant,zh;q=0.9,en;q=0.5",
    }
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if "error" in payload:
                raise RuntimeError(payload["error"])
            return payload
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            wait = min(2 ** attempt, 20)
            print(f"  ! request failed ({exc}); retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"API request failed after {retries} attempts: {url}") from last_error


def cache_key(title: str) -> str:
    return hashlib.sha1(title.encode("utf-8")).hexdigest()


def read_cache(title: str) -> dict | None:
    path = CACHE_DIR / f"{cache_key(title)}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def write_cache(title: str, payload: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{cache_key(title)}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Volume discovery
# ---------------------------------------------------------------------------

CN_DIGITS = {
    "〇": 0, "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
CN_UNITS = {"十": 10, "百": 100, "千": 1000}
CN_NUMERAL = "〇零一二两三四五六七八九十百千"

VOLUME_RE = re.compile(rf"卷\s*第?\s*0*(\d+|[{CN_NUMERAL}]+)")
PART_RE = re.compile(rf"卷\s*第?\s*(?:\d+|[{CN_NUMERAL}]+)\s*([上中下])")
PART_ORDER = {"": 0, "上": 1, "中": 2, "下": 3}


def chinese_to_int(value: str) -> int:
    """Convert a simple Chinese numeral (一 … 一百二十) to an integer."""
    total = 0
    current = 0
    for char in value:
        if char in CN_DIGITS:
            current = CN_DIGITS[char]
        elif char in CN_UNITS:
            unit = CN_UNITS[char]
            total += (current or 1) * unit
            current = 0
        else:
            raise ValueError(f"not a Chinese numeral: {value!r}")
    return total + current


def parse_volume_number(title: str) -> int | None:
    match = VOLUME_RE.search(title)
    if not match:
        return None
    token = match.group(1)
    if token.isdigit():
        return int(token)
    try:
        return chinese_to_int(token)
    except ValueError:
        return None


def parse_volume_part(title: str) -> str:
    match = PART_RE.search(title)
    return match.group(1) if match else ""


def discover_volumes(book: dict) -> list[dict]:
    """Enumerate namespace-0 subpages of a book index page."""
    page_title = book.get("page_title") or book["title"]

    # Works organized by named chapters (e.g. 世說新語) use an explicit list so
    # that reading order and volume numbers stay stable.
    if book.get("chapters"):
        volumes = []
        for number, chapter in enumerate(book["chapters"], start=1):
            volumes.append({
                "title": f"{page_title}/{chapter}",
                "pageid": None,
                "volume": number,
                "part": "",
                "volume_key": f"{number:03d}",
            })
        return volumes

    prefixes = [page_title + "/"]
    for alias in book.get("aliases", []):
        candidate = alias + "/"
        if candidate not in prefixes:
            prefixes.append(candidate)

    pages: dict[str, dict] = {}
    for prefix in prefixes:
        cont: dict = {}
        while True:
            params = {
                "action": "query",
                "list": "allpages",
                "apnamespace": "0",
                "apprefix": prefix,
                "aplimit": "max",
            }
            params.update(cont)
            try:
                payload = api_get(params)
            except RuntimeError as exc:
                print(f"  ! discovery failed for {prefix}: {exc}", file=sys.stderr)
                break
            for item in payload.get("query", {}).get("allpages", []):
                pages.setdefault(item["title"], {"title": item["title"], "pageid": item.get("pageid")})
            if "continue" in payload:
                cont = payload["continue"]
            else:
                break
            time.sleep(0.15)

    volumes = []
    for item in pages.values():
        number = parse_volume_number(item["title"])
        if number is None:
            continue
        part = parse_volume_part(item["title"])
        volumes.append({**item, "volume": number, "part": part, "volume_key": f"{number:03d}{part}"})

    # Some works use a single index page without volume subpages.
    if not volumes and book.get("single_page"):
        volumes.append({"title": page_title, "pageid": None, "volume": 1, "part": "", "volume_key": "001"})

    volumes.sort(key=lambda v: (v["volume"], PART_ORDER.get(v["part"], 9), v["title"]))
    # De-duplicate by volume *and* part: many histories split 卷17 into 卷17上/卷17下.
    deduped: dict[str, dict] = {}
    for vol in volumes:
        deduped.setdefault(vol["volume_key"], vol)
    volumes = [deduped[k] for k in sorted(deduped, key=lambda x: (int(re.match(r"\d+", x).group()), PART_ORDER.get(x[3:], 9)))]

    vmin = book.get("volume_min")
    vmax = book.get("volume_max")
    if vmin is not None:
        volumes = [v for v in volumes if v["volume"] >= vmin]
    if vmax is not None:
        volumes = [v for v in volumes if v["volume"] <= vmax]
    return volumes


# ---------------------------------------------------------------------------
# Wikitext conversion
# ---------------------------------------------------------------------------

def find_matching(text: str, start: int, open_token: str = "{{", close_token: str = "}}") -> int:
    depth = 0
    i = start
    while i < len(text):
        if text.startswith(open_token, i):
            depth += 1
            i += len(open_token)
        elif text.startswith(close_token, i):
            depth -= 1
            if depth == 0:
                return i
            i += len(close_token)
        else:
            i += 1
    return -1


def split_top_level(text: str, sep: str = "|") -> list[str]:
    parts: list[str] = []
    curly = 0
    bracket = 0
    last = 0
    i = 0
    while i < len(text):
        if text.startswith("{{", i):
            curly += 1
            i += 2
            continue
        if text.startswith("}}", i):
            curly = max(0, curly - 1)
            i += 2
            continue
        if text.startswith("[[", i):
            bracket += 1
            i += 2
            continue
        if text.startswith("]]", i):
            bracket = max(0, bracket - 1)
            i += 2
            continue
        if text[i] == sep and curly == 0 and bracket == 0:
            parts.append(text[last:i])
            last = i + 1
        i += 1
    parts.append(text[last:])
    return parts


def param_value(part: str) -> str:
    """Return the value of a named template parameter, or the part unchanged."""
    if "=" in part:
        key, value = part.split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_\- ]+", key.strip()):
            return value
    return part


def render_template(inner: str, depth: int = 0) -> str:
    if depth > 25:
        return ""
    parts = split_top_level(inner)
    if not parts:
        return ""
    name = parts[0].strip()
    lower = name.lower()
    args = parts[1:]

    if name.startswith("#"):
        return ""

    if lower in {"header", "headertemplate"}:
        return ""
    if lower in {
        "textquality", "proofread", "not proofread", "sic", "?", "citation needed",
        "reflist", "references", "defaultsort", "toc", "notoc", "pd-old",
        "pd-old-100", "pd-old-70", "pd-old-50", "pd-us", "cc-by-sa-4.0",
        "cc-by-sa-3.0", "gfdl", "license", "copyright", "authority control",
    }:
        return ""
    if lower in {"*", "注", "note", "notetag"}:
        content = "|".join(args)
        return "（注：" + expand_templates(content, depth + 1) + "）"
    if lower in {"yl", "年号"}:
        year = args[0].strip() if args else ""
        gregorian = args[1].strip() if len(args) > 1 else ""
        year = expand_templates(year, depth + 1)
        gregorian = expand_templates(gregorian, depth + 1)
        return year + (f"（{gregorian}）" if gregorian else "")
    if lower in {"ruby", "注音"}:
        base = args[0] if args else ""
        ruby = args[1] if len(args) > 1 else ""
        return f"{expand_templates(base, depth + 1)}（{expand_templates(ruby, depth + 1)}）"
    if lower in {"link", "link-zh", "内部链接"}:
        return expand_templates(args[1] if len(args) > 1 else (args[0] if args else ""), depth + 1)
    if lower in {"fn", "efn", "footnote"}:
        return "（注：" + expand_templates("|".join(args), depth + 1) + "）"
    if lower in {"cite", "citation", "sfn", "harvnb", "harvtxt", "r"}:
        return ""
    if lower in {
        "nowrap", "small", "big", "center", "right", "left", "楷体", "仿宋",
        "serif", "sans-serif", "monospace", "quote", "blockquote", "poem",
        "center block", "lang", "lang-zh", "zh", "sup", "sub", "abbr",
        "tooltip", "color", "font color", "fontcolor", "background color",
        "smaller", "larger", "u", "underline", "strike", "s", "del",
    }:
        return expand_templates(args[0] if args else "", depth + 1)
    if lower in {"wikt", "w"}:
        return expand_templates(args[0] if args else "", depth + 1)
    if lower in {"math", "chem"}:
        return expand_templates(args[0] if args else "", depth + 1)
    if lower in {"sfn", "harv"}:
        return ""

    # Generic template: keep textual parameter values, drop bare template names.
    values = []
    for arg in args:
        value = param_value(arg).strip()
        if not value:
            continue
        value = expand_templates(value, depth + 1).strip()
        if value:
            values.append(value)
    if not values:
        return ""
    return " ".join(values)


def expand_templates(text: str, depth: int = 0) -> str:
    if depth > 25 or "{{" not in text:
        return text
    out: list[str] = []
    i = 0
    while i < len(text):
        if text.startswith("{{", i):
            end = find_matching(text, i)
            if end == -1:
                out.append(text[i:])
                break
            inner = text[i + 2:end]
            out.append(render_template(inner, depth + 1))
            i = end + 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def extract_header(text: str) -> dict:
    match = re.search(r"\{\{\s*header\b", text, flags=re.IGNORECASE)
    if not match:
        return {}
    start = match.start()
    end = find_matching(text, start)
    if end == -1:
        return {}
    header = text[start:end + 2]
    data: dict[str, str] = {}
    for key in ("title", "section", "author", "previous", "next", "notes", "edition"):
        m = re.search(rf"\|\s*{key}\s*=\s*([^\n|]*)", header)
        if m:
            value = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", m.group(1)).strip()
            value = re.sub(r"\{\{[^}]*\}\}", "", value).strip()
            if value:
                data[key] = value
    return data


def remove_header(text: str) -> str:
    match = re.search(r"\{\{\s*header\b", text, flags=re.IGNORECASE)
    if not match:
        return text
    end = find_matching(text, match.start())
    if end == -1:
        return text
    return text[:match.start()] + text[end + 2:]


def wikitext_to_text(raw: str) -> tuple[str, dict]:
    header = extract_header(raw)
    text = remove_header(raw)

    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<noinclude>.*?</noinclude>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<includeonly>.*?</includeonly>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"</?onlyinclude>", "", text, flags=re.IGNORECASE)

    # Preserve footnotes/annotations as readable parenthetical text.
    text = re.sub(r"<ref[^>]*>(.*?)</ref>", r"（注：\1）", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<ref[^>]*/\s*>", "", text, flags=re.IGNORECASE)

    text = expand_templates(text)

    # Internal links: [[target|label]] / [[target]]
    def repl_link(match: re.Match) -> str:
        inner = match.group(1)
        target, _, label = inner.partition("|")
        target = target.strip()
        label = label.strip() or target
        if re.match(r"(?:File|Image|Category|文件|檔案|分类|分類):", target, flags=re.IGNORECASE):
            return ""
        if target.startswith("#"):
            return label
        return label

    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"\[\[([^\[\]]+?)\]\]", repl_link, text)

    # External links: [https://example.org label]
    text = re.sub(r"\[https?://[^\s\]]+\s*([^\]]*)\]", r"\1", text)
    text = re.sub(r"\[https?://[^\]]+\]", "", text)

    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"__[A-Z]+__", "", text)

    # Table markup: keep cell text, drop structural punctuation.
    text = re.sub(r"^\s*\{\|.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\|\}.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\|-.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*!\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\|\s*", "", text, flags=re.MULTILINE)

    # Headings
    text = re.sub(r"^\s*(={2,6})\s*(.*?)\s*\1\s*$", lambda m: "\n" + "#" * len(m.group(1)) + " " + m.group(2) + "\n", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*----+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[:\*#]+\s?", "", text, flags=re.MULTILINE)

    # Emphasis / residual wiki markup
    text = text.replace("'''", "").replace("''", "")
    text = re.sub(r"\{\{|\}\}", "", text)
    text = re.sub(r"\[\[|\]\]", "", text)

    # Whitespace cleanup
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    return text, header


# ---------------------------------------------------------------------------
# Fetch / save
# ---------------------------------------------------------------------------

def fetch_page(title: str, force: bool = False) -> dict:
    if not force:
        cached = read_cache(title)
        if cached and cached.get("wikitext"):
            return cached

    payload = api_get({
        "action": "parse",
        "page": title,
        "prop": "wikitext|revid|displaytitle",
        "redirects": "1",
    })
    if "parse" not in payload:
        raise RuntimeError(f"page not parseable: {title}")
    parse = payload["parse"]
    result = {
        "title": parse.get("title", title),
        "pageid": parse.get("pageid"),
        "revid": parse.get("revid"),
        "wikitext": parse.get("wikitext", ""),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    write_cache(title, result)
    return result


def fetch_rendered(title: str, force: bool = False) -> dict:
    """Fetch rendered HTML for pages that transclude ProofreadPage content.

    Some Wikisource works keep the body in the Page: namespace and transclude
    it with ``<pages index="..." />``.  The wikitext then contains only the
    transclusion tag, so the rendered HTML is the only practical source.
    """
    key = title + "::rendered"
    if not force:
        cached = read_cache(key)
        if cached and cached.get("html"):
            return cached
    payload = api_get({
        "action": "parse",
        "page": title,
        "prop": "text|revid",
        "disableeditsection": "1",
        "disabletoc": "1",
        "redirects": "1",
    })
    if "parse" not in payload:
        raise RuntimeError(f"page not renderable: {title}")
    parse = payload["parse"]
    result = {
        "title": parse.get("title", title),
        "revid": parse.get("revid"),
        "html": parse.get("text", ""),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    write_cache(key, result)
    return result


BLOCK_TAG_RE = re.compile(
    r"</?(?:p|div|br|li|tr|h[1-6]|table|blockquote|section|pages|dl|dt|dd)[^>]*>",
    re.IGNORECASE,
)
NAV_LINES = {"◄", "►", "←", "→", "姊妹计划: 数据项", "姊妹計劃: 數據項"}
NAV_PREFIXES = ("姊妹计划", "姊妹計劃", "维基百科条目", "維基百科條目", "数据项", "數據項")
VOLUME_LINE_RE = re.compile(r"^卷[〇零一二三四五六七八九十百0-9]+(?:——.*)?$")


def is_nav_line(line: str) -> bool:
    """True for Wikisource header/footer navigation chrome (not body text)."""
    return (
        not line
        or line in NAV_LINES
        or "◄" in line
        or "►" in line
        or line.startswith(NAV_PREFIXES)
        or bool(VOLUME_LINE_RE.match(line))
    )


def html_to_text(raw_html: str) -> str:
    """Convert rendered MediaWiki HTML to readable plain text."""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<sup[^>]*class="reference"[^>]*>.*?</sup>', "", text, flags=re.DOTALL | re.IGNORECASE)
    text = BLOCK_TAG_RE.sub("\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace("\u00a0", " ")
    lines: list[str] = []
    for line in text.splitlines():
        line = line.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "").strip()
        if is_nav_line(line):
            continue
        lines.append(line)
    return "\n".join(lines)


def safe_slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\-]+", "-", value)
    return value.strip("-") or "book"


def save_book(book: dict, volumes: list[dict], delay: float, force: bool) -> dict:
    slug = book.get("slug") or safe_slug(book["id"])
    out_dir = TEXTS_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    total_chars = 0

    print(f"\n== {book['title']} ({book['id']}) -> {out_dir} ==")
    for index, vol in enumerate(volumes, start=1):
        page_title = vol["title"]
        volume_label = f"{vol['volume']:03d}{vol.get('part', '')}"
        out_file = out_dir / f"卷{volume_label}.txt"
        if out_file.exists() and not force:
            existing = out_file.read_text(encoding="utf-8")
            total_chars += len(existing)
            entries.append({
                "file": out_file.name,
                "page_title": page_title,
                "volume": vol["volume"],
                "part": vol.get("part", ""),
                "volume_label": volume_label,
                "section": "",
                "revid": None,
                "url": f"https://zh.wikisource.org/wiki/{urllib.parse.quote(page_title.replace(' ', '_'))}",
                "chars": len(existing),
                "skipped": True,
            })
            print(f"  [{index}/{len(volumes)}] {out_file.name} exists, skipped")
            continue

        try:
            page = fetch_page(page_title, force=force)
        except Exception as exc:
            print(f"  ! [{index}/{len(volumes)}] {page_title}: {exc}", file=sys.stderr)
            continue

        text, header = wikitext_to_text(page.get("wikitext", ""))
        if "<pages" in page.get("wikitext", "").lower():
            try:
                rendered = fetch_rendered(page_title, force=force)
                rendered_text = html_to_text(rendered.get("html", ""))
                if rendered_text.strip():
                    text = rendered_text
                    if rendered.get("revid"):
                        page["revid"] = rendered["revid"]
            except Exception as exc:
                print(f"  ! [{index}/{len(volumes)}] {page_title}: rendered fetch failed: {exc}", file=sys.stderr)
        if not text.strip():
            print(f"  ! [{index}/{len(volumes)}] {page_title}: empty after conversion", file=sys.stderr)
            continue

        section = header.get("section", "").strip()
        title_line = f"# {book['title']} 卷{volume_label}"
        if section:
            title_line += f" · {section}"
        url = "https://zh.wikisource.org/wiki/" + urllib.parse.quote(page_title.replace(" ", "_"))
        front = (
            f"{title_line}\n\n"
            f"> 来源：Wikisource《{page_title}》  \n"
            f"> 修订号：{page.get('revid') or '未知'}  \n"
            f"> 许可：CC BY-SA 4.0（Wikisource 贡献者整理；古籍原文为公有领域）  \n"
            f"> 抓取日期：{page.get('fetched_at', '')[:10]}  \n"
            f"> 原始链接：{url}\n\n---\n\n"
        )
        content = front + text + "\n"
        out_file.write_text(content, encoding="utf-8")
        total_chars += len(content)
        entries.append({
            "file": out_file.name,
            "page_title": page_title,
            "volume": vol["volume"],
            "part": vol.get("part", ""),
            "volume_label": volume_label,
            "section": section,
            "revid": page.get("revid"),
            "url": url,
            "chars": len(content),
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        })
        print(f"  [{index}/{len(volumes)}] {out_file.name} {len(content):,} chars {section}")
        time.sleep(delay)

    manifest = {
        "source_id": book["id"],
        "title": book["title"],
        "title_simplified": book.get("title_simplified", ""),
        "slug": slug,
        "page_title": book.get("page_title", book["title"]),
        "source_url": "https://zh.wikisource.org/wiki/" + urllib.parse.quote(book.get("page_title", book["title"]).replace(" ", "_")),
        "license": "CC BY-SA 4.0 (Wikisource transcription); classical text is public domain",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "volume_count": len(entries),
        "chars": total_chars,
        "volumes": entries,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def rebuild_global_index() -> dict:
    books = []
    for manifest_path in sorted(TEXTS_DIR.glob("*/manifest.json")):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        books.append({
            "id": data.get("source_id"),
            "title": data.get("title"),
            "title_simplified": data.get("title_simplified", ""),
            "slug": data.get("slug", manifest_path.parent.name),
            "path": f"texts/{data.get('slug', manifest_path.parent.name)}",
            "source_url": data.get("source_url"),
            "license": data.get("license"),
            "volume_count": data.get("volume_count", 0),
            "chars": data.get("chars", 0),
        })
    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "book_count": len(books),
        "volume_count": sum(b["volume_count"] for b in books),
        "chars": sum(b["chars"] for b in books),
        "books": books,
    }
    (TEXTS_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index


def load_books() -> list[dict]:
    if not MANIFEST_PATH.exists():
        raise SystemExit(f"manifest not found: {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))


def select_books(all_books: list[dict], args: argparse.Namespace) -> list[dict]:
    if args.all_core:
        selected = [b for b in all_books if b.get("priority") == "core"]
    elif args.book:
        wanted = {x.upper() for x in args.book}
        selected = [b for b in all_books if b["id"].upper() in wanted or b.get("slug", "").upper() in wanted]
    else:
        selected = all_books
    if not selected:
        raise SystemExit("no matching books; check --book or manifests/wikisource_books.json")
    return selected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--book", action="append", help="book id or slug, repeatable")
    parser.add_argument("--all-core", action="store_true", help="fetch every book marked priority=core")
    parser.add_argument("--discover", action="store_true", help="only list discovered volumes, do not download")
    parser.add_argument("--limit", type=int, default=0, help="limit volumes per book (for testing)")
    parser.add_argument("--force", action="store_true", help="re-download and overwrite existing files")
    parser.add_argument("--delay", type=float, default=0.8, help="seconds between page downloads (default 0.8)")
    args = parser.parse_args(argv)

    all_books = load_books()
    selected = select_books(all_books, args)

    if args.discover:
        for book in selected:
            volumes = discover_volumes(book)
            if args.limit:
                volumes = volumes[: args.limit]
            print(f"{book['id']:24s} {book['title']:8s} volumes={len(volumes):4d} "
                  f"first={volumes[0]['title'] if volumes else '-'} last={volumes[-1]['title'] if volumes else '-'}")
        return 0

    manifests = []
    for book in selected:
        volumes = discover_volumes(book)
        if args.limit:
            volumes = volumes[: args.limit]
        if not volumes:
            print(f"! no volumes discovered for {book['title']} ({book['id']})", file=sys.stderr)
            continue
        manifests.append(save_book(book, volumes, delay=args.delay, force=args.force))

    index = rebuild_global_index()
    print(f"\nDone. books={index['book_count']} volumes={index['volume_count']:,} chars={index['chars']:,}")
    print(f"Index: {TEXTS_DIR / 'index.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
