"""h53: paragraph-interior contrast of opening vs closing lines (PREREG.md).

No translation claims. The first and last word of every line are dropped before
the opening line is compared with the closing line.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (
    ROOT / "hypotheses" / "h13_top_word_context",
    ROOT / "hypotheses" / "h30_line_structure",
    ROOT / "hypotheses" / "h47_page_line_generator",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import h13_lib  # noqa: E402
import h30_lib  # noqa: E402
import h47_lib  # noqa: E402

HANDS = ("1A", "2B", "3B")
N_PERM = 200
SEED = 53
MIN_ROLE = 200
EXCESS_MIN = 0.01
GAP_MIN = 0.01
TOP_K = 40
MIN_UNIT = 30


def paragraphs(records: list[dict], split_on_page: bool) -> list[list[list[str]]]:
    """Maximal runs of at least 3 lines. Folio changes split MS and the copier only."""
    groups: list[list[list[str]]] = []
    current: list[list[str]] = []
    page = None
    for rec in records:
        boundary = bool(rec["para_first"]) or (split_on_page and bool(current) and rec["page"] != page)
        if current and boundary:
            groups.append(current)
            current = []
        current.append(list(rec["words"]))
        page = rec["page"]
    if current:
        groups.append(current)
    return [group for group in groups if len(group) >= 3]


def line_interior(words: list[str]) -> list[str]:
    """Drop the first and last word. Lines shorter than 4 words contribute nothing."""
    if len(words) < 4:
        return []
    return list(words[1:-1])


def role_words(para: list[list[str]]) -> tuple[list[str], list[str], list[str]]:
    """Interiors of the opening line, the middle lines, and the closing line."""
    open_words = line_interior(para[0])
    close_words = line_interior(para[-1])
    mid_words = [word for line in para[1:-1] for word in line_interior(line)]
    return open_words, mid_words, close_words


def null_p95(null: np.ndarray) -> float:
    """190th order statistic of 200 draws, index 189 of the sorted sample."""
    ordered = np.sort(np.asarray(null, dtype=float))
    if len(ordered) != N_PERM:
        raise ValueError(f"p95 index is defined for {N_PERM} draws, got {len(ordered)}")
    return float(ordered[189])


def _js(open_labels: list[str], close_labels: list[str]) -> float:
    if not open_labels or not close_labels:
        return float("nan")
    return float(h30_lib.js(Counter(open_labels), Counter(close_labels)))


def _freeze(labels: list[str], top_k: int | None, min_count: int | None) -> dict[str, str]:
    counts = Counter(labels)
    if top_k is not None:
        keep = {word for word, _ in counts.most_common(top_k)}
    else:
        keep = {word for word, n in counts.items() if n >= min_count}
    return {lab: (lab if lab in keep else "OTHER") for lab in counts}


def _apply(words: list[str], mapping: dict[str, str]) -> list[str]:
    return [mapping.get(word, "OTHER") for word in words]


def unit_of(word: str, mode: str, which: str) -> str:
    units = tuple(h13_lib.SEG(word)) if mode == "eva" else tuple(word)
    if not units:
        return "EMPTY"
    if which == "onset":
        return units[0]
    if which == "end":
        return units[-1]
    raise ValueError(which)


def score_paragraphs(paras: list[list[list[str]]], mode: str, n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """Word-class JS of OPEN vs CLOSE, plus onset and end versions on the same shuffles."""
    open0: list[str] = []
    close0: list[str] = []
    all_words: list[str] = []
    for para in paras:
        open_words, mid_words, close_words = role_words(para)
        open0.extend(open_words)
        close0.extend(close_words)
        all_words.extend(open_words)
        all_words.extend(mid_words)
        all_words.extend(close_words)
    word_map = _freeze(all_words, TOP_K, None)
    onset_labels = [unit_of(word, mode, "onset") for word in all_words]
    end_labels = [unit_of(word, mode, "end") for word in all_words]
    onset_map = _freeze(onset_labels, None, MIN_UNIT)
    end_map = _freeze(end_labels, None, MIN_UNIT)

    def contrasts(groups: list[list[list[str]]]) -> dict[str, float]:
        open_words: list[str] = []
        close_words: list[str] = []
        for para in groups:
            o, _, c = role_words(para)
            open_words.extend(o)
            close_words.extend(c)
        return {
            "word": _js(_apply(open_words, word_map), _apply(close_words, word_map)),
            "onset": _js(
                _apply([unit_of(w, mode, "onset") for w in open_words], onset_map),
                _apply([unit_of(w, mode, "onset") for w in close_words], onset_map),
            ),
            "end": _js(
                _apply([unit_of(w, mode, "end") for w in open_words], end_map),
                _apply([unit_of(w, mode, "end") for w in close_words], end_map),
            ),
        }

    observed = contrasts(paras)
    rng = np.random.default_rng(seed)
    null = {key: np.empty(n_perm, dtype=float) for key in ("word", "onset", "end")}
    for draw in range(n_perm):
        shuffled = []
        for para in paras:
            order = para.copy()
            rng.shuffle(order)
            shuffled.append(order)
        draw_s = contrasts(shuffled)
        for key in null:
            null[key][draw] = draw_s[key]
    out = {
        "n_paragraphs": len(paras),
        "n_open": len(open0),
        "n_close": len(close0),
        "scored": bool(len(open0) >= MIN_ROLE and len(close0) >= MIN_ROLE),
    }
    for key in ("word", "onset", "end"):
        samples = null[key]
        mean = float(np.nanmean(samples))
        sd = float(np.nanstd(samples))
        excess = float(observed[key] - mean)
        out[key] = {
            "S": float(observed[key]),
            "null_mean": mean,
            "null_sd": sd,
            "null_p95": null_p95(samples) if n_perm == N_PERM else None,
            "excess": excess,
            "z": float(excess / sd) if sd >= 1e-12 else 0.0,
        }
    return out


def load_ms_records(hand: str) -> list[dict]:
    return h47_lib.load_template(hand)


def load_copier_records(hand: str) -> list[dict]:
    blob = json.loads(
        (ROOT / "hypotheses" / "h47_page_line_generator" / "results" / "streams.json").read_text(encoding="utf-8")
    )
    generated = blob["generated_lines"][f"page_line_copier_{hand}"]
    template = h47_lib.load_template(hand)
    if len(generated) != len(template):
        raise RuntimeError(f"{hand}: line count mismatch")
    records = []
    for rec, words in zip(template, generated):
        if len(words) != len(rec["words"]):
            raise RuntimeError(f"{hand}: line length mismatch")
        copied = dict(rec)
        copied["words"] = list(words)
        records.append(copied)
    return records


def load_cucina_records() -> list[dict]:
    return h30_lib.load_control("italian/pg33954.txt")


def hand_passes(ms: dict, copier: dict) -> bool:
    """A1 cell rule. Uses the word-class contrast only."""
    if not ms["scored"] or not copier["scored"]:
        return False
    word_ms = ms["word"]
    word_c = copier["word"]
    return bool(
        word_ms["S"] > word_ms["null_p95"]
        and word_ms["excess"] >= EXCESS_MIN
        and (word_ms["excess"] - word_c["excess"]) >= GAP_MIN
    )


def cucina_passes(cucina: dict) -> bool:
    if not cucina["scored"]:
        return False
    word = cucina["word"]
    return bool(word["S"] > word["null_p95"] and word["excess"] >= EXCESS_MIN)


def evaluate(streams: dict) -> dict:
    """A1, C1, and the reading named in PREREG.md."""
    passing = [hand for hand in HANDS if hand_passes(streams[f"MS_{hand}"], streams[f"page_line_copier_{hand}"])]
    scored = [hand for hand in HANDS if streams[f"MS_{hand}"]["scored"]]
    a1 = len(passing) >= 2
    c1 = cucina_passes(streams["it_cucina"])
    if a1:
        reading = "paragraph_role"
    elif (not a1) and c1:
        reading = "measure_sees_recipes_ms_does_not"
    else:
        reading = "inconclusive"
    return {"A1": a1, "A1_hands": passing, "scored_hands": scored, "C1": c1, "reading": reading}
