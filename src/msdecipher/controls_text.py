"""Turn raw control texts into normalised token lists of a target size.

Normalisation is deliberately crude and is itself a tokenisation choice that affects every
statistic: lower-case; diacritics removed (NFKD); ligatures expanded (æ->ae, œ->oe, ß->ss);
Latin ``j->i`` and ``v->u`` (classical convention); apostrophes split words (Italian elisions);
only ``a-z`` kept; whitespace-delimited tokens. Digits, verse numbers, footnote brackets,
Gutenberg boilerplate and wiki markup are removed first.

Abjad texts (Hebrew, Arabic; ``script`` in the source table) use :func:`normalise_abjad_text`:
points/vowel signs/cantillation/tatweel are removed, only consonant letters are kept, and **every
letter stays one native Unicode code point = one unit** (so the single-character segmenter of
:mod:`controls_metrics` applies unchanged; a 1-to-1 Latin transliteration would give identical
numbers, which a test checks). Variants (``variant="folded"``): Hebrew final forms
(ך ם ן ף ץ) folded into the medial letters; Arabic hamza-carriers / alif maqsura / ta marbuta folded
into a reduced alphabet. See docs/CONTROLS.md.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .controls_fetch import SOURCES, controls_dir

TARGET_TOKENS = 35000   # about the size of the MS 408 running text (34,977 readable tokens in ZL 3b)

_LIG = {"æ": "ae", "Æ": "AE", "œ": "oe", "Œ": "OE", "ß": "ss", "ſ": "s"}


def strip_gutenberg(raw: str) -> str:
    m = re.search(r"\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\n", raw)
    if m:
        raw = raw[m.end():]
    m = re.search(r"\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG EBOOK", raw)
    if m:
        raw = raw[:m.start()]
    return raw


def clean_wikitext(raw: str) -> str:
    raw = re.sub(r"\{\{[^{}]*\}\}", " ", raw)
    raw = re.sub(r"<sup>.*?</sup>", " ", raw, flags=re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = re.sub(r"^=+.*?=+\s*$", " ", raw, flags=re.M)
    raw = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", raw)
    return raw


def normalise_word_text(text: str, latin: bool = False) -> list[str]:
    for a, b in _LIG.items():
        text = text.replace(a, b)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    if latin:
        text = text.replace("j", "i").replace("v", "u")
    text = re.sub(r"[’'`´]", " ", text)
    text = re.sub(r"\[[^\]]*\]|\{[^}]*\}", " ", text)   # footnote / page markers
    text = re.sub(r"[^a-z]+", " ", text)
    return text.split()


# ----------------------------------------------------------------------------- abjad texts

_HEB_MARKS = re.compile("[\u0591-\u05BD\u05BF\u05C1\u05C2\u05C4\u05C5\u05C7]")   # cantillation, niqqud, points (maqaf/paseq/sof pasuq handled apart)
_HEB_FINAL = str.maketrans("ךםןףץ", "כמנפצ")
_HEB_KEEP = re.compile("[^\u05D0-\u05EA]+")
_AR_MARKS = re.compile("[\u064B-\u065F\u0670\u0640\u06D6-\u06ED\u08D3-\u08FF\u200c-\u200f\u0610-\u061A]")
_AR_PERSIAN = str.maketrans({"ک": "ك", "ی": "ي", "ە": "ه", "ۀ": "ه", "ہ": "ه"})
_AR_ALEF = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"})
_AR_REDUCE = str.maketrans({"ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي", "ء": None})
_AR_KEEP = re.compile("[^\u0621-\u064A]+")

# 1-to-1 single-character Latin transliterations (Hebrew: ad hoc; Arabic: Buckwalter). Metrics are
# label-free, so using these instead of native code points cannot change any number (tested).
HEBREW_TRANSLIT = {"א": "a", "ב": "b", "ג": "g", "ד": "d", "ה": "h", "ו": "w", "ז": "z", "ח": "H", "ט": "T",
                   "י": "y", "כ": "k", "ך": "K", "ל": "l", "מ": "m", "ם": "M", "נ": "n", "ן": "N", "ס": "s",
                   "ע": "e", "פ": "p", "ף": "P", "צ": "c", "ץ": "C", "ק": "q", "ר": "r", "ש": "S", "ת": "t"}
ARABIC_TRANSLIT = {"ء": "'", "ا": "A", "ب": "b", "ة": "p", "ت": "t", "ث": "v", "ج": "j", "ح": "H", "خ": "x",
                   "د": "d", "ذ": "*", "ر": "r", "ز": "z", "س": "s", "ش": "$", "ص": "S", "ض": "D", "ط": "T",
                   "ظ": "Z", "ع": "E", "غ": "g", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n",
                   "ه": "h", "و": "w", "ى": "Y", "ي": "y", "ؤ": "&", "ئ": "}"}


def strip_html(raw: str) -> str:
    """Remove HTML tags; contents of <small> (Sefaria scripture citations), <sup> and footnote <i> are dropped."""
    raw = re.sub(r"<small>.*?</small>|<sup[^>]*>.*?</sup>|<i class=\"footnote\">.*?</i>", " ", raw, flags=re.S)
    raw = re.sub(r"<[^>]+>|&[a-z]+;|&#\d+;", " ", raw)
    return raw


def clean_wikitext_ar(raw: str) -> str:
    for _ in range(6):                                   # nested templates
        new = re.sub(r"\{\{[^{}]*\}\}", " ", raw)
        if new == raw:
            break
        raw = new
    raw = re.sub(r"\[\[(?:تصنيف|Category|[a-z]{2,3}):[^\]]*\]\]", " ", raw)
    raw = re.sub(r"\{\|.*?\|\}", " ", raw, flags=re.S)
    return clean_wikitext(raw)


def normalise_abjad_text(text: str, script: str, variant: str = "main") -> list[str]:
    """Tokens of a Hebrew or Arabic text: consonant letters only, one native code point per unit."""
    text = text.lower()
    if script == "hebrew":
        text = re.sub(r"\[[^\]]*\]|\{[^}]*\}", " ", text)           # {פ} {ס} paragraph marks, editorial brackets
        text = text.replace("\u05be", " ")                            # maqaf: hyphen-like joiner -> word boundary
        text = _HEB_MARKS.sub("", text)
        text = _HEB_KEEP.sub(lambda m: " ", text)
        if variant == "folded":
            text = text.translate(_HEB_FINAL)
    elif script == "arabic":
        text = re.sub(r"\[[^\]]*\]|\{[^}]*\}", " ", text)
        text = _AR_MARKS.sub("", text).translate(_AR_PERSIAN).translate(_AR_ALEF)
        if variant == "folded":
            text = text.translate(_AR_REDUCE)
        text = _AR_KEEP.sub(" ", text)
    else:
        raise ValueError(script)
    return text.split()


def transliterate(tokens: list[str], script: str) -> list[str]:
    """1-to-1 Latin (single-character) transliteration; raises KeyError on an unmapped letter."""
    table = HEBREW_TRANSLIT if script == "hebrew" else ARABIC_TRANSLIT
    return ["".join(table[c] for c in t) for t in tokens]


_TEI = "{http://www.tei-c.org/ns/1.0}"


def perseus_book_text(xml_bytes: bytes, books: list[int]) -> str:
    """Plain text of the given books of a Perseus TEI edition (<div subtype="book" n=...>); apparatus
    (<note>) elements are dropped, their tail text is kept."""
    import io
    import xml.etree.ElementTree as ET
    root = ET.parse(io.BytesIO(xml_bytes)).getroot()
    want = {str(b) for b in books}
    found = {d.get("n"): d for d in root.iter(_TEI + "div") if d.get("subtype") == "book" and d.get("n") in want}

    def text(el):
        out = []
        if el.tag != _TEI + "note":
            out.append(el.text or "")
            for ch in el:
                out.append(text(ch))
        out.append(el.tail or "")
        return "".join(out)
    parts = []
    for b in books:
        el = found.get(str(b))
        if el is None:
            continue
        el = ET.fromstring(ET.tostring(el))      # detach (drop the tail of the book div itself)
        el.tail = None
        parts.append(text(el))
    return "\n".join(parts)


def source_by_id(cid: str) -> dict:
    for s in SOURCES:
        if s["id"] == cid:
            return s
    raise KeyError(cid)


def load_tokens(cid: str, n_tokens: int | None = TARGET_TOKENS, directory: Path | None = None,
                variant: str = "main") -> list[str]:
    """First ``n_tokens`` normalised tokens of control ``cid`` (fewer if the text is shorter; ``None`` = the whole text).
    ``variant="folded"`` only changes abjad texts (see module docstring)."""
    s = source_by_id(cid)
    p = (directory or controls_dir()) / s["file"]
    if not p.exists():
        raise FileNotFoundError(f"{p} not found; run `python -m msdecipher controls-fetch` first")
    raw = p.read_text(encoding="utf-8", errors="replace") if s["kind"] != "perseus" else ""
    script = s.get("script")
    if s["kind"] == "perseus":
        raw = perseus_book_text(p.read_bytes(), s["books"])
        return normalise_word_text(raw, latin=True)[:n_tokens]
    if script:
        if s["kind"] == "tanzil":
            raw = "\n".join(l.split("|", 2)[2] for l in raw.splitlines() if l and not l.startswith("#") and l.count("|") >= 2)
        elif s["kind"] == "wikisource_ar":
            raw = clean_wikitext_ar(raw)
        else:
            raw = strip_html(raw)
        return normalise_abjad_text(raw, script, variant)[:n_tokens]
    if s["kind"] == "gutenberg":
        raw = strip_gutenberg(raw)
    else:
        raw = clean_wikitext(raw)
    if s.get("start_regex"):
        m = re.search(s["start_regex"], raw, flags=re.M)
        if m:
            raw = raw[m.start():]
    toks = normalise_word_text(raw, latin=s["lang"] == "Latin")
    return toks[:n_tokens]


def load_windows(cid: str, n_tokens: int = TARGET_TOKENS, max_windows: int | None = None,
                 variant: str = "main", directory: Path | None = None,
                 min_share: float = 0.8) -> list[list[str]]:
    """Consecutive, NON-overlapping windows of ``n_tokens`` tokens from the start of the text
    (size-matched samples). A trailing remainder shorter than ``min_share * n_tokens`` is dropped;
    a text shorter than one window gives a single, shorter window (callers must flag it as
    undersized). ``max_windows`` defaults to the source's ``max_windows`` entry (3 if absent)."""
    s = source_by_id(cid)
    mw = max_windows if max_windows is not None else s.get("max_windows", 3)
    toks = load_tokens(cid, None, directory=directory, variant=variant)
    out = []
    for i in range(mw):
        w = toks[i * n_tokens:(i + 1) * n_tokens]
        if len(w) >= min_share * n_tokens or (i == 0 and w):
            out.append(w)
    return out
