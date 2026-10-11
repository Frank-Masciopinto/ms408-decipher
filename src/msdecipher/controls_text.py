"""Turn raw control texts into normalised token lists of a target size.

Normalisation is deliberately crude and is itself a tokenisation choice that affects every
statistic: lower-case; diacritics removed (NFKD); ligatures expanded (æ->ae, œ->oe, ß->ss);
Latin ``j->i`` and ``v->u`` (classical convention); apostrophes split words (Italian elisions);
only ``a-z`` kept; whitespace-delimited tokens. Digits, verse numbers, footnote brackets,
Gutenberg boilerplate and wiki markup are removed first.
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


def source_by_id(cid: str) -> dict:
    for s in SOURCES:
        if s["id"] == cid:
            return s
    raise KeyError(cid)


def load_tokens(cid: str, n_tokens: int = TARGET_TOKENS, directory: Path | None = None) -> list[str]:
    """First ``n_tokens`` normalised tokens of control ``cid`` (fewer if the text is shorter)."""
    s = source_by_id(cid)
    p = (directory or controls_dir()) / s["file"]
    if not p.exists():
        raise FileNotFoundError(f"{p} not found; run `python -m msdecipher controls-fetch` first")
    raw = p.read_text(encoding="utf-8", errors="replace")
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
