"""Fetch public-domain / openly licensed control texts (NOT redistributed; only URLs + SHA256 are committed).

The controls give the MS 408 statistics something to be compared with. Texts come from
Project Gutenberg (public domain in the USA), Wikisource (Latin Vulgate 1598 and Arabic
Ibn Khaldun, wiki platform text CC BY-SA), Sefaria (Hebrew: ``Tanach with Text Only``,
public domain; Maimonides' Mishneh Torah, ``Torat Emet 363``, public domain) and Tanzil
(Quran, Simple Clean 1.1, CC BY 3.0 but *verbatim copies only, changing the text is not
allowed*). Even so, the downloaded bytes are git-ignored (``data/controls/``); the
repository carries this script and ``data/controls/MANIFEST.json`` (URL, SHA256, size, date)
so anyone can re-fetch and verify them. Our normalisation is applied in memory only
(``controls_text``); no modified copy of the Quran text is stored or distributed.

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
WIKISOURCE_AR_API = "https://ar.wikisource.org/w/api.php"
SEFARIA_API = "https://www.sefaria.org/api/v3/texts/"
TANZIL_URL = "https://tanzil.net/pub/download/index.php?quranType=simple-clean&outType=txt-2&agree=true"


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
    # ---- natural abjad texts (Hebrew, Arabic); the script decides the normaliser
    {"id": "he_tanakh", "file": "he_tanakh_genesis_exodus.txt", "kind": "sefaria", "script": "hebrew",
     "refs": ["Genesis", "Exodus"], "version": "hebrew|Tanach with Text Only",
     "lang": "Hebrew", "desc": "Hebrew Bible, Genesis + Exodus (Sefaria version 'Tanach with Text Only', consonantal, no niqqud/cantillation)",
     "licence": "Sefaria lists this version as Public Domain", "start_regex": None},
    {"id": "he_mishneh_torah", "file": "he_mishneh_torah_madda.txt", "kind": "sefaria", "script": "hebrew",
     "refs": ["Mishneh Torah, Foundations of the Torah", "Mishneh Torah, Human Dispositions",
              "Mishneh Torah, Torah Study", "Mishneh Torah, Foreign Worship and Customs of the Nations",
              "Mishneh Torah, Repentance", "Mishneh Torah, Sabbath"],
     "version": "hebrew|Torat Emet 363",
     "lang": "Hebrew", "desc": "Maimonides, Mishneh Torah (12th c., medieval rabbinic Hebrew prose; Sefaria 'Torat Emet 363', vocalised, vowels stripped on load), 5 Sefer Madda' books + Sabbath",
     "licence": "Sefaria lists this version as Public Domain", "start_regex": None},
    {"id": "ar_quran", "file": "ar_quran_tanzil_simple_clean.txt", "kind": "tanzil", "script": "arabic",
     "lang": "Arabic", "desc": "Quran, Tanzil 'Simple Clean' v1.1 (Classical Arabic, rhymed prose, 78k words; first 35k tokens used)",
     "licence": "Tanzil, CC BY 3.0 with 'verbatim copies only, changing the text is not allowed': only the fetch URL and SHA256 are committed, no copy of the text and no derived text file",
     "start_regex": None},
    {"id": "ar_muqaddimah", "file": "ar_ibn_khaldun_muqaddimah_part1.txt", "kind": "wikisource_ar", "script": "arabic",
     "index_page": "مقدمة ابن خلدون - الجزء الأول", "link_prefix": "مقدمة ابن خلدون/",
     "lang": "Arabic", "desc": "Ibn Khaldun, al-Muqaddimah (14th c., medieval Arabic prose), Part 1 sub-pages in book order, via ar.wikisource.org",
     "licence": "text of a pre-modern work (public domain); Wikisource platform text CC BY-SA 4.0", "start_regex": None},
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


def _flat(x):
    return [x] if isinstance(x, str) else [y for z in x for y in _flat(z)]


def fetch_sefaria(refs: list[str], version: str) -> bytes:
    """Sefaria API v3: one text segment (verse / halakhah) per line, raw (HTML tags kept; stripped on load)."""
    parts = []
    for ref in refs:
        r = _get(SEFARIA_API + ref.replace(" ", "_"), {"version": version})
        d = r.json()
        vs = d.get("versions") or []
        if not vs:
            raise RuntimeError(f"Sefaria returned no version {version!r} for {ref!r}")
        parts += [t.replace("\n", " ") for t in _flat(vs[0]["text"]) if t]
    return ("\n".join(parts) + "\n").encode("utf-8")


def _wikisource_content(api: str, title: str) -> str | None:
    r = _get(api, {"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
                   "titles": title, "format": "json", "formatversion": 2, "redirects": 1})
    pg = r.json()["query"]["pages"][0]
    try:
        return pg["revisions"][0]["slots"]["main"]["content"]
    except (KeyError, IndexError):
        return None


def fetch_wikisource_index(api: str, index_page: str, link_prefix: str) -> bytes:
    """Sub-pages linked from ``index_page`` (whose titles start with ``link_prefix``), in link order."""
    import re
    idx = _wikisource_content(api, index_page)
    if idx is None:
        raise RuntimeError(f"no content for {index_page!r}")
    links = [l.strip() for l in re.findall(r"\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]", idx) if l.strip().startswith(link_prefix)]
    links = list(dict.fromkeys(links))
    parts = [c for c in (_wikisource_content(api, t) for t in links) if c]
    if not parts:
        raise RuntimeError(f"no sub-pages found under {index_page!r}")
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
        elif s["kind"] == "sefaria":
            url = SEFARIA_API + " (version=" + s["version"] + ") " + " | ".join(s["refs"])
            data = fetch_sefaria(s["refs"], s["version"])
        elif s["kind"] == "tanzil":
            url = TANZIL_URL
            data = _get(url).content
        elif s["kind"] == "wikisource_ar":
            url = WIKISOURCE_AR_API + " (prop=revisions) sub-pages linked from " + s["index_page"]
            data = fetch_wikisource_index(WIKISOURCE_AR_API, s["index_page"], s["link_prefix"])
        else:
            url = WIKISOURCE_LA_API + " (prop=revisions) " + " | ".join(s["pages"])
            data = fetch_wikisource(s["pages"])
        (d / s["file"]).write_bytes(data)
        entries.append({"id": s["id"], "file": s["file"], "url": url, "bytes": len(data),
                        "sha256": sha256_bytes(data), "lang": s["lang"], "desc": s["desc"],
                        "licence": s["licence"],
                        "fetched": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    old = {}
    if manifest_path(d).exists():
        old = {e["id"]: e for e in json.loads(manifest_path(d).read_text(encoding="utf-8")).get("files", [])}
    for e in entries:
        old[e["id"]] = e
    order = {s["id"]: i for i, s in enumerate(SOURCES)}
    entries = sorted(old.values(), key=lambda e: order.get(e["id"], 999))
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
