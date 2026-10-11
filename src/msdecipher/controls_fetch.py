"""Fetch public-domain control texts (NOT redistributed; only URLs + SHA256 are committed).

The controls give the MS 408 statistics something to be compared with. Every text is either
on Project Gutenberg (public domain in the USA) or on Wikisource (text of a 1598 edition,
wiki platform content CC BY-SA 4.0). Even so, the downloaded bytes are git-ignored
(``data/controls/``); the repository carries this script and ``data/controls/MANIFEST.json``
(URL, SHA256, size, date) so anyone can re-fetch and verify them.

Each source records ``start_regex`` (where the real text starts after the front matter) and
``strip`` hints used by :mod:`msdecipher.controls_text`.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path

import requests

from .paths import repo_root

USER_AGENT = "msdecipher/0.1 (research tool; +https://github.com/Frank-Masciopinto/ms408-decipher)"
WIKISOURCE_LA_API = "https://la.wikisource.org/w/api.php"


def controls_dir() -> Path:
    return repo_root() / "data" / "controls"


def pg_url(n: int) -> str:
    return f"https://www.gutenberg.org/cache/epub/{n}/pg{n}.txt"


# language / era are descriptive labels used in reports; "family" groups hypotheses.
SOURCES = [
    {"id": "la_vulgate", "file": "la_vulgate_genesis_exodus.txt", "kind": "wikisource",
     "pages": ["Vulgata Clementina/Liber Genesis", "Vulgata Clementina/Liber Exodus"],
     "lang": "Latin", "desc": "Vulgata Clementina (1598 ed.), Genesis + Exodus, via la.wikisource.org",
     "licence": "text of a 1598 edition (public domain); Wikisource platform text CC BY-SA 4.0",
     "start_regex": None},
    {"id": "la_augustine", "file": "pg33849.txt", "kind": "gutenberg", "pg": 33849,
     "lang": "Latin", "desc": "Augustine, Confessiones (Project Gutenberg #33849; Rivington 1838 ed.)",
     "licence": "Project Gutenberg, public domain in the USA",
     "start_regex": r"^LIBER PRIMUS\."},
    {"id": "it_dante", "file": "pg1000.txt", "kind": "gutenberg", "pg": 1000,
     "lang": "Italian", "desc": "Dante, La Divina Commedia (Project Gutenberg #1000), verse",
     "licence": "Project Gutenberg, public domain in the USA",
     "start_regex": r"^Nel mezzo del cammin di nostra vita"},
    {"id": "it_manzoni", "file": "pg45334.txt", "kind": "gutenberg", "pg": 45334,
     "lang": "Italian", "desc": "Manzoni, I promessi sposi (Project Gutenberg #45334), 19th-c. prose",
     "licence": "Project Gutenberg, public domain in the USA",
     "start_regex": r"^Quel ramo del lago di Como"},
    {"id": "de_walther_mhg", "file": "pg35795.txt", "kind": "gutenberg", "pg": 35795,
     "lang": "Middle High German", "desc": "Walther von der Vogelweide, Gedichte und Sprüche in Auswahl (PG #35795); only ~12k words, SMALLER than MS 408",
     "licence": "Project Gutenberg, public domain in the USA",
     "start_regex": r"^\s*Sô die bluomen"},
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def manifest_path(directory: Path | None = None) -> Path:
    return (directory or controls_dir()) / "MANIFEST.json"


def _get(url: str, params: dict | None = None) -> requests.Response:
    r = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=120)
    r.raise_for_status()
    return r


def fetch_wikisource(pages: list[str]) -> bytes:
    """Raw wikitext of Wikisource pages (MediaWiki API, prop=revisions); cleaned later."""
    parts = []
    for title in pages:
        r = _get(WIKISOURCE_LA_API, {"action": "query", "prop": "revisions", "rvprop": "content",
                                     "rvslots": "main", "titles": title, "format": "json",
                                     "formatversion": 2, "redirects": 1})
        pg = r.json()["query"]["pages"][0]
        try:
            txt = pg["revisions"][0]["slots"]["main"]["content"]
        except (KeyError, IndexError):
            raise RuntimeError(f"no content for {title!r}") from None
        parts.append(txt)
    return ("\n\n".join(parts)).encode("utf-8")


def fetch_all(directory: Path | None = None, only: list[str] | None = None) -> dict:
    d = directory or controls_dir()
    d.mkdir(parents=True, exist_ok=True)
    entries = []
    for s in SOURCES:
        if only and s["id"] not in only:
            continue
        if s["kind"] == "gutenberg":
            url = pg_url(s["pg"])
            data = _get(url).content
        else:
            url = WIKISOURCE_LA_API + " (prop=revisions) " + " | ".join(s["pages"])
            data = fetch_wikisource(s["pages"])
        (d / s["file"]).write_bytes(data)
        entries.append({"id": s["id"], "file": s["file"], "url": url, "bytes": len(data),
                        "sha256": sha256_bytes(data), "lang": s["lang"], "desc": s["desc"],
                        "licence": s["licence"],
                        "fetched": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    man = {"note": "Downloaded control texts are git-ignored; this manifest records where they come from. "
                   "Project Gutenberg/Wikisource texts may be updated upstream, so a SHA256 mismatch after "
                   "re-fetching means the upstream text changed (re-run the controls and update the manifest).",
           "files": entries}
    manifest_path(d).write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return man


def verify(directory: Path | None = None) -> list[tuple[str, str]]:
    d = directory or controls_dir()
    mp = manifest_path(d)
    if not mp.exists():
        return []
    out = []
    for e in json.loads(mp.read_text(encoding="utf-8"))["files"]:
        p = d / e["file"]
        if not p.exists():
            out.append((e["file"], "missing"))
        else:
            out.append((e["file"], "ok" if sha256_bytes(p.read_bytes()) == e["sha256"] else "SHA256 MISMATCH"))
    return out
