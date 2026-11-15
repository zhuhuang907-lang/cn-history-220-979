# -*- coding: utf-8 -*-
"""Download OpenCC TSCharacters dictionary used for traditional->simplified search."""
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "variants"
OUT.mkdir(parents=True, exist_ok=True)

URLS = {
    "ts_characters.txt": "https://raw.githubusercontent.com/BYVoid/OpenCC/master/data/dictionary/TSCharacters.txt",
    "OPENCC-LICENSE.txt": "https://raw.githubusercontent.com/BYVoid/OpenCC/master/LICENSE",
}
for name, url in URLS.items():
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read()
    (OUT / name).write_bytes(data)
    print(name, len(data))
