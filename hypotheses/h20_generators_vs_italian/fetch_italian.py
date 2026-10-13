"""Download the h20 Italian reference texts (public domain; NOT redistributed).

Texts land in data/controls/italian/ (git-ignored). URLs + SHA256 go to data/ITALIAN_MANIFEST.json (committed).
Run: python fetch_italian.py  (re-running overwrites; a SHA mismatch means the upstream text changed)."""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "data" / "controls" / "italian"; MAN = HERE / "data" / "ITALIAN_MANIFEST.json"
UA = "msdecipher/0.1 (research tool; +https://github.com/Frank-Masciopinto/ms408-decipher)"
WS = "https://it.wikisource.org/w/api.php"
NUM = ["prima", "seconda", "terza", "quarta", "quinta", "sesta", "settima", "ottava", "nona", "decima"]

SOURCES = [
    dict(id="it_boccaccio", kind="ws", file="boccaccio_decameron_g1_g2.txt", century="14th", genre="prose novellas",
         titles=[f"Decameron/Giornata {g}/" + p for g in ("prima", "seconda") for p in ["Introduzione"] + [f"Novella {n}" for n in NUM]],
         desc="Boccaccio, Decameron, Giornate I-II (it.wikisource, transcluded edition text)", licence="medieval text, public domain; Wikisource platform text CC BY-SA 4.0"),
    dict(id="it_cennini", kind="ws_prefix", file="cennini_libro_dell_arte.txt", century="c.1400", genre="workshop recipes",
         prefix="Il libro dell'arte/Capitolo ", desc="Cennino Cennini, Il libro dell'arte (1859 ed., it.wikisource), all chapters",
         licence="medieval text, public domain; Wikisource platform text CC BY-SA 4.0"),
    dict(id="it_fioretti", kind="ws_prefix", file="fioretti_san_francesco.txt", century="14th", genre="religious prose",
         prefix="Fioretti di San Francesco/Capitolo ", desc="I Fioretti di San Francesco (Cesari 1860 ed., it.wikisource)",
         licence="medieval text, public domain; Wikisource platform text CC BY-SA 4.0"),
    dict(id="it_cucina", kind="pg", pg=33954, file="pg33954.txt", century="14th", genre="ricettario (cookery recipes)",
         start=r"^INCOMINCIASI IL LIBRO DE LA COCINA", end=r"^TAVOLA\s*$", desc="Il libro della cucina del sec. XIV (Zambrini 1863 ed.; PG #33954)",
         licence="Project Gutenberg, public domain in the USA"),
    dict(id="it_vitanuova", kind="pg", pg=71218, file="pg71218.txt", century="13th", genre="prose + verse",
         start=r"^In quella parte del libro della mia memoria", end=r"^INDICE DEL VOLUME", desc="Dante, La vita nuova (PG #71218)",
         licence="Project Gutenberg, public domain in the USA"),
    dict(id="it_villani", kind="pg", pg=69898, file="pg69898.txt", century="14th", genre="chronicle prose",
         start=r"^Esaminando nell", end=r"^TAVOLA DEI CAPITOLI", desc="Matteo Villani, Cronica vol. 1 (PG #69898)",
         licence="Project Gutenberg, public domain in the USA"),
]


def _get(url, params=None):
    for k in range(4):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=120); r.raise_for_status(); return r
        except requests.RequestException:
            if k == 3: raise
            time.sleep(2 + 3 * k)


def ws_html(title):
    r = _get(WS, dict(action="parse", page=title, prop="text", format="json", formatversion=2, redirects=1)).json()
    return r.get("parse", {}).get("text", "")


def ws_prefix_titles(prefix):
    r = _get(WS, dict(action="query", list="allpages", apprefix=prefix, aplimit=500, format="json")).json()
    return [p["title"] for p in r["query"]["allpages"]]


def html_to_text(h):
    h = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", h, flags=re.S)
    h = re.sub(r'<span[^>]*class="[^"]*(pagenum|numeropagina|reference)[^"]*"[^>]*>.*?</span>', " ", h, flags=re.S)
    h = re.sub(r"<sup[^>]*>.*?</sup>", " ", h, flags=re.S)
    h = re.sub(r'<(div|table)[^>]*class="[^"]*(intestazione|references|noprint|ws-noexport)[^"]*".*?</\1>', " ", h, flags=re.S)
    h = re.sub(r"<ol class=\"references\".*?</ol>", " ", h, flags=re.S)
    h = re.sub(r"<br\s*/?>|</p>|</div>", "\n", h)
    return html.unescape(re.sub(r"<[^>]+>", " ", h))


def fetch(only=None):
    OUT.mkdir(parents=True, exist_ok=True); man = json.loads(MAN.read_text()) if MAN.exists() else {"files": []}
    old = {e["id"]: e for e in man["files"]}
    for s in SOURCES:
        if only and s["id"] not in only: continue
        if s["kind"] == "pg":
            url = f"https://www.gutenberg.org/cache/epub/{s['pg']}/pg{s['pg']}.txt"; data = _get(url).content
        else:
            titles = s["titles"] if s["kind"] == "ws" else [t for t in ws_prefix_titles(s["prefix"])]
            titles = sorted(titles, key=roman_order) if s["id"] == "it_cennini" else titles
            parts = [ws_html(t) for t in titles]
            data = ("\n<!-- page -->\n".join(p for p in parts if p.strip())).encode("utf-8"); url = WS + " (action=parse) " + (" | ".join(titles[:3]) + f" ... ({len(titles)} pages)")
        (OUT / s["file"]).write_bytes(data)
        old[s["id"]] = dict(id=s["id"], file=s["file"], url=url, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), desc=s["desc"], century=s["century"],
                            genre=s["genre"], licence=s["licence"], fetched=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        print("fetched", s["id"], len(data))
    MAN.parent.mkdir(exist_ok=True)
    MAN.write_text(json.dumps({"note": "h20 Italian texts: downloaded bytes are git-ignored (data/controls/italian/); only URL + SHA256 here.", "files": list(old.values())}, indent=1, ensure_ascii=False) + "\n")


def roman_order(t):
    m = re.search(r"Capitolo ([IVXLC]+)$", t)
    if not m: return 10 ** 6
    v = dict(I=1, V=5, X=10, L=50, C=100); s = m.group(1); n = 0
    for i, c in enumerate(s): n += -v[c] if i + 1 < len(s) and v[s[i + 1]] > v[c] else v[c]
    return n


def load_italian(cid, n_tokens=None):
    """normalised tokens (same normaliser as the other controls)."""
    from msdecipher.controls_text import normalise_word_text, strip_gutenberg
    s = next(x for x in SOURCES if x["id"] == cid); raw = (OUT / s["file"]).read_text(encoding="utf-8", errors="replace")
    if s["kind"] == "pg":
        raw = strip_gutenberg(raw); m = re.search(s["start"], raw, flags=re.M); raw = raw[m.start():] if m else raw
        e = re.search(s["end"], raw, flags=re.M); raw = raw[:e.start()] if e else raw
        raw = "\n".join(l for l in raw.splitlines() if not re.match(r"^\s+[¹²³⁴⁵⁶⁷⁸⁹\d]", l))
        raw = re.sub(r"\[\d+\]", " ", raw)
    else:
        raw = html_to_text(raw)
    return normalise_word_text(raw, latin=False)[:n_tokens]


if __name__ == "__main__":
    fetch(sys.argv[1:] or None)
