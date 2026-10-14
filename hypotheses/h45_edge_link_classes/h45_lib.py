"""h45: how much of the last-glyph link is a vowel/consonant class (PREREG.md).

Pairs are consecutive words on one line: (last unit, first unit of the next word).
Sukhotin is fit on within-word adjacent units of that same stream. Mutual information
is the plug-in estimate in bits. share = MI_class / MI_glyph.
"""
from __future__ import annotations

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import math
import platform
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _rel in (
    "src",
    "hypotheses/h09_image_context_cribs",
    "hypotheses/h13_top_word_context",
    "hypotheses/h14_line_position_controls",
    "hypotheses/h20_generators_vs_italian",
    "hypotheses/h34_boundary_rule_generator",
):
    _path = str(ROOT / _rel)
    if _path not in sys.path:
        sys.path.insert(0, _path)

import h13_lib
import h14_lib
import h34_lib
from fetch_italian import OUT as IT_OUT
from fetch_italian import SOURCES as IT_SOURCES
from fetch_italian import html_to_text
from fetch_italian import load_italian
from msdecipher.controls_fetch import controls_dir
from msdecipher.controls_text import clean_wikitext
from msdecipher.controls_text import load_tokens
from msdecipher.controls_text import normalise_word_text
from msdecipher.controls_text import perseus_book_text
from msdecipher.controls_text import source_by_id
from msdecipher.controls_text import strip_gutenberg
from msdecipher.stats import sukhotin

N_STREAM = 10500
C1_MIN = 0.25
GAP_SEED = 45
GAP_STRENGTH = 1.0
HANDS = ("1A", "2B", "3B")
MS_KEYS = tuple(f"MS_{hand}" for hand in HANDS)
CONTROL_KEYS = ("boccaccio", "cucina", "pliny", "macer")
STREAM_ORDER = MS_KEYS + CONTROL_KEYS + ("self_citation", "gap_rule")
SELF_CITATION = ROOT / "data" / "mechanisms" / "selfcitation" / "fitted_s1.txt"
_BRACKET = re.compile(r"\[[^\]]*\]|\{[^}]*\}")
_H14_TABLE = h14_lib.table
_TABLE_CACHE: dict[str, object] = {}


def _cached_table():
    cached = _TABLE_CACHE.get("table")
    if cached is None:
        cached = _H14_TABLE()
        _TABLE_CACHE["table"] = cached
    return cached


def _mismatch(got: list[str], expected: list[str]) -> str:
    n = min(len(got), len(expected))
    for i in range(n):
        if got[i] != expected[i]:
            return f"index {i}: {got[i]!r} != {expected[i]!r} (lengths {len(got)} vs {len(expected)})"
    return f"lengths {len(got)} vs {len(expected)}"


def token_lines(text: str, latin: bool) -> list[list[str]]:
    """Loader tokens grouped by source line.

    The normaliser deletes a bracket span even when the span contains a newline.
    Those spans are removed on the whole text first. Each remaining line then goes
    through normalise_word_text. The flat token list must match that normaliser.
    """
    stripped = _BRACKET.sub(" ", text)
    lines: list[list[str]] = []
    for line in stripped.split("\n"):
        words = normalise_word_text(line, latin=latin)
        if words:
            lines.append(words)
    got = [word for line in lines for word in line]
    expected = normalise_word_text(text, latin=latin)
    if got != expected:
        raise RuntimeError("line tokenisation diverges from normalise_word_text: " + _mismatch(got, expected))
    return lines


def take_tokens(lines: list[list[str]], n: int) -> list[list[str]]:
    """First n tokens, cutting inside the last line. Line breaks stay put."""
    if n < 0:
        raise ValueError("n must be non-negative")
    out: list[list[str]] = []
    seen = 0
    for line in lines:
        if seen >= n:
            break
        room = n - seen
        if len(line) <= room:
            out.append(list(line))
            seen += len(line)
        else:
            out.append(list(line[:room]))
            seen = n
    return out


def italian_text(cid: str) -> str:
    spec = next(item for item in IT_SOURCES if item["id"] == cid)
    raw = (IT_OUT / spec["file"]).read_text(encoding="utf-8", errors="replace")
    if spec["kind"] == "pg":
        raw = strip_gutenberg(raw)
        start = re.search(spec["start"], raw, flags=re.M)
        raw = raw[start.start():] if start else raw
        end = re.search(spec["end"], raw, flags=re.M)
        raw = raw[:end.start()] if end else raw
        raw = "\n".join(line for line in raw.splitlines() if not re.match(r"^\s+[¹²³⁴⁵⁶⁷⁸⁹\d]", line))
        raw = re.sub(r"\[\d+\]", " ", raw)
        return raw
    return html_to_text(raw)


def control_text(cid: str) -> tuple[str, bool]:
    spec = source_by_id(cid)
    path = controls_dir() / spec["file"]
    if spec["kind"] == "perseus":
        return perseus_book_text(path.read_bytes(), spec["books"]), True
    raw = path.read_text(encoding="utf-8", errors="replace")
    if spec["kind"] == "gutenberg":
        raw = strip_gutenberg(raw)
    else:
        raw = clean_wikitext(raw)
    start_regex = spec.get("start_regex")
    if start_regex:
        start = re.search(start_regex, raw, flags=re.M)
        if start:
            raw = raw[start.start():]
    return raw, spec["lang"] == "Latin"


def load_control_lines(name: str, n: int = N_STREAM) -> list[list[str]]:
    if name == "boccaccio":
        text = italian_text("it_boccaccio")
        latin = False
        official = list(load_italian("it_boccaccio", n))
    elif name == "cucina":
        text = italian_text("it_cucina")
        latin = False
        official = list(load_italian("it_cucina", n))
    elif name == "pliny":
        text, latin = control_text("la_pliny_herbal")
        official = list(load_tokens("la_pliny_herbal", n))
    elif name == "macer":
        text, latin = control_text("la_macer")
        official = list(load_tokens("la_macer", n))
    else:
        raise ValueError(f"unknown control {name!r}")
    cut = take_tokens(token_lines(text, latin), n)
    got = [word for line in cut for word in line]
    if got != official:
        raise RuntimeError(f"{name} lines diverge from the loader: {_mismatch(got, official)}")
    return cut


def ms_word_lines(hand: str) -> list[list[str]]:
    """Paragraph lines for one hand, via the h14 loader.

    h14.table is the ZL3b paragraph table and a comma is a word space. Line order
    matches h30_lib.load_ms: folio order of first appearance, then line number,
    words in position order. The table is read once and reused.
    """
    h14_lib.table = _cached_table
    table = h14_lib.table()
    order = {folio: i for i, folio in enumerate(dict.fromkeys(table.folio))}
    frame = table[table.HL == hand].sort_values(["folio", "line", "pos"], kind="stable")
    grouped = sorted(
        frame.groupby("lid"),
        key=lambda item: (order[item[1].folio.iloc[0]], item[1].line.iloc[0]),
    )
    lines = []
    for _lid, group in grouped:
        lines.append(group.sort_values("pos").w.tolist())
    return lines


def self_citation_lines(n: int = N_STREAM) -> list[list[str]]:
    text = SELF_CITATION.read_text(encoding="utf-8")
    lines: list[list[str]] = []
    seen = 0
    for raw in text.splitlines():
        words = raw.split()
        if not words or seen >= n:
            continue
        chunk = words[: n - seen]
        lines.append(chunk)
        seen += len(chunk)
    flat = text.split()
    got = [word for line in lines for word in line]
    if got != flat[:n]:
        raise RuntimeError("self-citation lines diverge from the token prefix: " + _mismatch(got, flat[:n]))
    return lines


def as_units(lines: list[list[str]], kind: str) -> list[list[tuple[str, ...]]]:
    if kind == "eva":
        convert = h13_lib.SEG
    elif kind == "char":
        convert = tuple
    else:
        raise ValueError(f"unknown unit kind {kind!r}")
    out: list[list[tuple[str, ...]]] = []
    for line in lines:
        units = [convert(word) for word in line if word]
        if units:
            out.append(units)
    return out


def edge_pairs(lines: list[list[tuple[str, ...]]]) -> list[tuple[str, str]]:
    """(last unit, first unit) for consecutive words on the same line."""
    pairs: list[tuple[str, str]] = []
    for line in lines:
        for i in range(len(line) - 1):
            left = line[i]
            right = line[i + 1]
            if not left or not right:
                continue
            pairs.append((left[-1], right[0]))
    return pairs


def mutual_info(pairs: list[tuple[str, str]]) -> float:
    """Plug-in mutual information of a pair list, in bits. No pairs -> 0."""
    n = len(pairs)
    if n == 0:
        return 0.0
    joint = Counter(pairs)
    left = Counter(a for a, _ in pairs)
    right = Counter(b for _, b in pairs)
    info = 0.0
    for (a, b), count in joint.items():
        info += (count / n) * math.log2((count * n) / (left[a] * right[b]))
    return float(info)


def score_unit_lines(lines: list[list[tuple[str, ...]]]) -> dict:
    raw_pairs = edge_pairs(lines)
    seqs = [units for line in lines for units in line if units]
    vowels, rows = sukhotin(seqs)
    scored = set(rows)
    vowel_set = set(vowels)
    if not vowel_set <= scored:
        raise RuntimeError("Sukhotin returned a vowel it did not score")
    kept = [(a, b) for a, b in raw_pairs if a in scored and b in scored]
    class_pairs = [
        ("V" if a in vowel_set else "C", "V" if b in vowel_set else "C")
        for a, b in kept
    ]
    mi_glyph = mutual_info(kept)
    mi_class = mutual_info(class_pairs)
    excluded = mi_glyph == 0.0
    share = None if excluded else mi_class / mi_glyph
    return {
        "n_tokens": int(sum(len(line) for line in lines)),
        "n_lines": int(sum(1 for line in lines if line)),
        "n_pairs_raw": int(len(raw_pairs)),
        "n_pairs": int(len(kept)),
        "n_dropped_pairs": int(len(raw_pairs) - len(kept)),
        "MI_glyph": mi_glyph,
        "MI_class": mi_class,
        "share": None if share is None else float(share),
        "excluded": bool(excluded),
        "vowels": [str(unit) for unit in vowels],
        "consonants": [str(unit) for unit in sorted(scored - vowel_set)],
        "n_scored": int(len(scored)),
    }


def score_words(lines: list[list[str]], kind: str) -> dict:
    return score_unit_lines(as_units(lines, kind))


def gap_rule_lines(hand_lines: list[list[str]]) -> list[list[tuple[str, ...]]]:
    """Glyph table from hand 2B, applied to the whole fitted_s1 token stream.

    Words are collapsed EVA units before the table is fit, so the rule's last
    unit and next first unit are the same glyphs the measure uses. Strength 1,
    seed 45, h34 line length and within-line scope.
    """
    table_lines = as_units(hand_lines, "eva")
    rule = h34_lib.fit_table(table_lines)
    if not rule:
        raise RuntimeError("gap-rule table is empty")
    tokens = [h13_lib.SEG(word) for word in SELF_CITATION.read_text(encoding="utf-8").split()]
    rng = np.random.default_rng(GAP_SEED)
    return h34_lib.apply_rule(tokens, rule, GAP_STRENGTH, rng)


def predictions(streams: dict) -> dict:
    shares: list[float] = []
    for key in CONTROL_KEYS:
        share = streams[key]["share"]
        if share is not None:
            shares.append(float(share))
    median = statistics.median(shares) if shares else None
    lowest = min(shares) if shares else None
    c1 = len(shares) == len(CONTROL_KEYS) and median is not None and median >= C1_MIN
    result = {
        "C1": bool(c1),
        "C1_scored": True,
        "C2": None,
        "C2_scored": False,
        "C3": None,
        "C3_scored": False,
        "median_control_share": median,
        "lowest_control_share": lowest,
        "c1_min": C1_MIN,
    }
    if not c1:
        return result
    ms_below = all(
        streams[key]["share"] is not None and float(streams[key]["share"]) < lowest
        for key in MS_KEYS
    )
    self_share = streams["self_citation"]["share"]
    gap_share = streams["gap_rule"]["share"]
    generators_below = (
        self_share is not None
        and gap_share is not None
        and lowest is not None
        and float(self_share) < lowest
        and float(gap_share) < lowest
    )
    result["C2_scored"] = True
    result["C2"] = bool(ms_below)
    result["C3_scored"] = True
    result["C3"] = bool(generators_below)
    return result


def _annotate(rec: dict, name: str, unit: str, seconds: float, **extra) -> dict:
    out = dict(rec)
    out["name"] = name
    out["unit"] = unit
    out["seconds"] = float(seconds)
    out.update(extra)
    return out


def run_all() -> dict:
    streams: dict[str, dict] = {}
    hand_lines: dict[str, list[list[str]]] = {}
    for hand in HANDS:
        print(f"load MS {hand}", flush=True)
        t0 = time.perf_counter()
        words = ms_word_lines(hand)
        hand_lines[hand] = words
        n = sum(len(line) for line in words)
        print(f"score MS {hand} n={n} lines={len(words)}", flush=True)
        rec = score_words(words, "eva")
        streams[f"MS_{hand}"] = _annotate(
            rec, f"MS_{hand}", "collapsed_eva", time.perf_counter() - t0,
            hand=hand, whole_hand=True, n_cap=None,
        )
        print(
            f"done MS {hand} share={rec['share']} MI_glyph={rec['MI_glyph']} MI_class={rec['MI_class']} "
            f"vowels={rec['vowels']}",
            flush=True,
        )
    for name in CONTROL_KEYS:
        print(f"load {name}", flush=True)
        t0 = time.perf_counter()
        words = load_control_lines(name, N_STREAM)
        print(f"score {name} n={sum(len(line) for line in words)} lines={len(words)}", flush=True)
        rec = score_words(words, "char")
        streams[name] = _annotate(
            rec, name, "characters", time.perf_counter() - t0, n_cap=N_STREAM,
        )
        print(
            f"done {name} share={rec['share']} MI_glyph={rec['MI_glyph']} MI_class={rec['MI_class']} "
            f"vowels={rec['vowels']}",
            flush=True,
        )
    print("load self-citation", flush=True)
    t0 = time.perf_counter()
    words = self_citation_lines(N_STREAM)
    print(f"score self-citation n={sum(len(line) for line in words)} lines={len(words)}", flush=True)
    rec = score_words(words, "eva")
    streams["self_citation"] = _annotate(
        rec, "self_citation", "collapsed_eva", time.perf_counter() - t0,
        n_cap=N_STREAM, source="fitted_s1",
    )
    print(
        f"done self_citation share={rec['share']} MI_glyph={rec['MI_glyph']} MI_class={rec['MI_class']} "
        f"vowels={rec['vowels']}",
        flush=True,
    )
    print("gap rule: fit hand 2B, apply strength 1 seed 45 to fitted_s1", flush=True)
    t0 = time.perf_counter()
    generated = gap_rule_lines(hand_lines["2B"])
    n_gap = sum(len(line) for line in generated)
    print(f"score gap rule n={n_gap} lines={len(generated)}", flush=True)
    rec = score_unit_lines(generated)
    streams["gap_rule"] = _annotate(
        rec, "gap_rule", "collapsed_eva", time.perf_counter() - t0,
        n_cap=None, source="fitted_s1", table_hand="2B", strength=GAP_STRENGTH, seed=GAP_SEED,
    )
    print(
        f"done gap_rule share={rec['share']} MI_glyph={rec['MI_glyph']} MI_class={rec['MI_class']} "
        f"vowels={rec['vowels']}",
        flush=True,
    )
    pred = predictions(streams)
    print(f"predictions {pred}", flush=True)
    return {
        "n_stream": N_STREAM,
        "c1_min": C1_MIN,
        "gap_seed": GAP_SEED,
        "gap_strength": GAP_STRENGTH,
        "gap_scope": "full fitted_s1 token stream",
        "numpy": np.__version__,
        "python": platform.python_version(),
        "streams": streams,
        "predictions": pred,
    }
