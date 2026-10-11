"""PDF page number -> folio index (docs/WORKFLOW.md stage 1; docs/IMAGE_STAGE.md).

The Yale PDF has one scan per PDF page (214 pages). Each page starts with a caption line read
with ``pdftotext``: ``1r``, ``[Front cover]``, ``69v and 70r``, ``70v (part)`` ... The captions
use *physical* folio numbers; the voynich.nu transcription (IVTFF) splits fold-out pages into
sub-folios (``f67r1``/``f67r2``, ``f85r1`` ... ``f86v3``). The mapping produced here is therefore
graded by how certain it is:

* ``exact``                – one caption folio, exactly one transcription folio (usable for
                             aligning the page image with the transcription)
* ``multi_subfolio``       – one caption folio that the transcription splits into several
                             sub-folios on one scan (left/right halves, etc.): which text belongs to
                             which part of the scan is NOT resolved
* ``multi_folio``          – the scan shows more than one folio (``69v and 70r``) or is a ``(part)``
                             of a fold-out: assignment of sub-folios to this scan is NOT resolved
* ``no_transcription``     – a folio caption with no folio in the transcription (e.g. f116v is
                             present but has no P lines; folios that the transcription does not cover)
* ``non_folio``            – covers, spine, edges, flyleaves, the Yale info page

Nothing here reads the manuscript text; it only builds a lookup table.
"""
from __future__ import annotations

import csv
import re
import shutil
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .images import find_parts
from .paths import repo_root

FOLIO_TOKEN = re.compile(r"\b(\d{1,3})([rv])\b")
INDEX_FIELDS = ["pdf_page", "caption", "kind", "caption_folios", "folios", "match", "illustration",
                "language", "hand", "n_p_lines", "text_page_candidate"]


def index_path() -> Path:
    return repo_root() / "data" / "page_index.csv"


def read_captions(source: Path | None = None) -> dict[int, str]:
    """First non-empty line of each PDF page (pdftotext). Page 1 is the Yale information page."""
    if shutil.which("pdftotext") is None:
        raise RuntimeError("pdftotext (poppler-utils) is required")
    caps: dict[int, str] = {}
    for pdf, start in find_parts(source):
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
        n = int(re.search(r"Pages:\s+(\d+)", info).group(1))
        for i in range(1, n + 1):
            txt = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), str(pdf), "-"],
                                 capture_output=True, text=True, check=True).stdout
            first = next((ln.strip() for ln in txt.splitlines() if ln.strip()), "")
            caps[start + i - 1] = first
    return caps


def classify_caption(caption: str) -> tuple[str, list[str]]:
    """-> (kind, caption folio bases such as ['69v','70r'])."""
    c = caption.strip()
    low = c.lower()
    if low.startswith("yale university") or not c:
        return "non_folio", []
    if low.startswith("[") and "flyleaf" in low:
        return "non_folio", []
    if low.startswith("[") and not FOLIO_TOKEN.search(c):
        return "non_folio", []
    toks = [f"{n}{s}" for n, s in FOLIO_TOKEN.findall(c)]
    if not toks:
        return "non_folio", []
    if "foldout" in low or "fold-out" in low:
        return "foldout", toks
    if "(part)" in low:
        return "part", toks
    return ("multi" if len(toks) > 1 else "folio"), toks


def match_folios(base: str, transcription_folios: list[str]) -> list[str]:
    """Transcription folios belonging to caption folio ``base`` (f70r -> f70r, f70r1, f70r2)."""
    pat = re.compile(rf"^f{re.escape(base)}\d*$")
    return [f for f in transcription_folios if pat.match(f)]


@dataclass
class IndexRow:
    pdf_page: int
    caption: str
    kind: str
    caption_folios: str = ""
    folios: str = ""
    match: str = ""
    illustration: str = ""
    language: str = ""
    hand: str = ""
    n_p_lines: int = 0
    text_page_candidate: bool = False


def build_rows(captions: dict[int, str], transcription_folios: list[str] | None = None,
               page_info: dict[str, dict] | None = None) -> list[IndexRow]:
    """Pure function: captions (+ the transcription's folio list and page variables) -> rows."""
    tf = transcription_folios or []
    page_info = page_info or {}
    rows: list[IndexRow] = []
    for pg in sorted(captions):
        cap = captions[pg]
        kind, toks = classify_caption(cap)
        r = IndexRow(pg, cap, kind, ";".join(toks))
        if kind == "non_folio":
            r.match = "non_folio"
        else:
            found = [f for t in toks for f in match_folios(t, tf)]
            r.folios = ";".join(found)
            if not found:
                r.match = "no_transcription"
            elif kind in ("multi", "part", "foldout") or len(toks) > 1:
                r.match = "multi_folio"
            elif len(found) == 1:
                r.match = "exact"
            else:
                r.match = "multi_subfolio"
            if r.match == "exact":
                info = page_info.get(found[0], {})
                r.illustration = info.get("I", "")
                r.language = info.get("L", "")
                r.hand = info.get("H", "")
                r.n_p_lines = int(info.get("n_p_lines", 0))
                # candidates for line/word/glyph segmentation: one scan = one folio, mostly text
                r.text_page_candidate = r.illustration in ("T", "S") and r.n_p_lines > 0
        rows.append(r)
    return rows


def write_index(rows: list[IndexRow], path: Path | None = None) -> Path:
    path = path or index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=INDEX_FIELDS)
        w.writeheader()
        for r in rows:
            d = asdict(r)
            d["text_page_candidate"] = int(r.text_page_candidate)
            w.writerow(d)
    return path


def read_index(path: Path | None = None) -> list[dict]:
    with (path or index_path()).open(newline="") as fh:
        return list(csv.DictReader(fh))


def page_info_from_corpus(corpus) -> tuple[list[str], dict[str, dict]]:
    n_p: dict[str, int] = {}
    for lc in corpus.loci:
        if lc.generic == "P" and lc.locator != "!":
            n_p[lc.folio] = n_p.get(lc.folio, 0) + 1
    info = {f: {**p.vars, "n_p_lines": n_p.get(f, 0)} for f, p in corpus.pages.items()}
    return list(corpus.pages), info


def build_index(captions: dict[int, str] | None = None, corpus=None, path: Path | None = None) -> list[IndexRow]:
    """Build and write ``data/page_index.csv`` (needs pdftotext; the transcription is optional)."""
    captions = captions or read_captions()
    tf, info = (None, None)
    if corpus is None:
        try:
            from .analysis import load_corpus
            corpus = load_corpus()
        except FileNotFoundError:
            corpus = None
    if corpus is not None:
        tf, info = page_info_from_corpus(corpus)
    rows = build_rows(captions, tf, info)
    write_index(rows, path)
    return rows


def summarize(rows: list[IndexRow]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        out[r.match] = out.get(r.match, 0) + 1
    return out
