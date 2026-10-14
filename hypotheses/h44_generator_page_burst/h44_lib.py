"""h44 page and quire burst scores (PREREG.md).

Burst is h41_lib.burst: 50 most frequent types, blocks of 200 tokens.
orig is the stream as given. in_page, in_quire, and full are each the mean of
10 shuffles from a fresh numpy Generator seeded with 44.
"""
from __future__ import annotations

import math
import os
import sys
from collections.abc import Sequence
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h41_plaintext_visibility"))

import h41_lib  # noqa: E402

N_STREAM = 10500
N_SHUFFLES = 10
SHUFFLE_SEED = 44
PAGES_PER_QUIRE = 8
POSITIVE_TYPES = 40
POSITIVE_SEED = 1
BLOCK = h41_lib.BLOCK
TOP = h41_lib.TOP

MS_NAMES = ("MS_1A", "MS_2B", "MS_3B")
GENERATOR_NAMES = (
    "fitted_s1",
    "fitted_s2",
    "C0",
    "h06_pool",
    "h06_p0",
    "h39_native_tuned",
    "h39_C0_graph",
)
CONTROL_NAME = "positive_control"
ORDER = MS_NAMES + GENERATOR_NAMES + (CONTROL_NAME,)


def burst(tokens: Sequence[str]) -> float:
    return float(h41_lib.burst(list(tokens)))


def page_len_from_median(median: float) -> int:
    """Whole tokens nearest the median. A tie rounds away from zero."""
    if not math.isfinite(median) or median <= 0:
        raise ValueError("median folio length must be a positive finite number")
    return int(math.floor(float(median) + 0.5))


def layout(n_tokens: int, page_len: int, pages_per_quire: int = PAGES_PER_QUIRE) -> tuple[list[int], list[int]]:
    """Page ids are consecutive blocks of page_len tokens. A quire is pages_per_quire pages.

    The last page is shorter when n_tokens is not a multiple of page_len. The last quire
    is shorter when the page count is not a multiple of pages_per_quire.
    """
    if page_len <= 0 or pages_per_quire <= 0:
        raise ValueError("page_len and pages_per_quire must be positive")
    if n_tokens < 0:
        raise ValueError("n_tokens must be non-negative")
    pages = [i // page_len for i in range(n_tokens)]
    quires = [page // pages_per_quire for page in pages]
    return pages, quires


def positive_control(
    n_tokens: int,
    page_len: int,
    n_types: int = POSITIVE_TYPES,
    seed: int = POSITIVE_SEED,
    pages_per_quire: int = PAGES_PER_QUIRE,
) -> tuple[list[str], list[int], list[int]]:
    """Each page is drawn from its own n_types types, Zipf (1/rank) inside the page.

    No type is shared with another page. The last page may be shorter than page_len and
    still has its own vocabulary.
    """
    if n_types <= 0:
        raise ValueError("n_types must be positive")
    pages, quires = layout(n_tokens, page_len, pages_per_quire)
    rng = np.random.default_rng(seed)
    weights = 1.0 / np.arange(1, n_types + 1, dtype=float)
    probs = weights / weights.sum()
    tokens: list[str] = []
    page_id = 0
    while len(tokens) < n_tokens:
        take = min(page_len, n_tokens - len(tokens))
        vocab = [f"p{page_id}_{i}" for i in range(n_types)]
        draw = rng.choice(vocab, size=take, replace=True, p=probs)
        tokens.extend(str(word) for word in draw)
        page_id += 1
    if page_id != (0 if n_tokens == 0 else pages[-1] + 1):
        raise RuntimeError("positive-control page count does not match the layout")
    return tokens, pages, quires


def shuffle_within(tokens: Sequence[str], groups: Sequence, rng: np.random.Generator) -> list[str]:
    """Permute tokens inside each group. Group order is first appearance in the stream."""
    if len(tokens) != len(groups):
        raise ValueError("tokens and groups must have the same length")
    out = list(tokens)
    buckets: dict = {}
    for index, group in enumerate(groups):
        buckets.setdefault(group, []).append(index)
    for indexes in buckets.values():
        perm = rng.permutation(len(indexes))
        picked = [tokens[indexes[int(j)]] for j in perm]
        for index, word in zip(indexes, picked):
            out[index] = word
    return out


def mean_shuffled_burst(
    tokens: Sequence[str],
    groups: Sequence,
    n_shuffles: int = N_SHUFFLES,
    seed: int = SHUFFLE_SEED,
) -> float:
    """Mean burst of n_shuffles within-group permutations from numpy seed `seed`."""
    if n_shuffles <= 0:
        raise ValueError("n_shuffles must be positive")
    rng = np.random.default_rng(seed)
    total = 0.0
    for _ in range(n_shuffles):
        total += burst(shuffle_within(tokens, groups, rng))
    return total / n_shuffles


def score_stream(tokens: Sequence[str], pages: Sequence, quires: Sequence) -> dict:
    """orig, in_page, in_quire, full, excess, and the quire share of excess."""
    if not (len(tokens) == len(pages) == len(quires)):
        raise ValueError("tokens, pages, and quires must have the same length")
    orig = burst(tokens)
    in_page = mean_shuffled_burst(tokens, pages)
    in_quire = mean_shuffled_burst(tokens, quires)
    full = mean_shuffled_burst(tokens, [0] * len(tokens))
    excess = orig - full
    share = (in_quire - full) / excess if excess > 0.0 else None
    return {
        "n": len(tokens),
        "orig": orig,
        "in_page": in_page,
        "in_quire": in_quire,
        "full": full,
        "excess": excess,
        "share_kept_in_quire": share,
        "n_pages": len(set(pages)),
        "n_quires": len(set(quires)),
    }


def predictions(streams: dict) -> dict:
    """B1–B3 from PREREG.md. Comparisons are strict."""
    missing = [name for name in ORDER if name not in streams]
    if missing:
        raise KeyError("missing streams: " + ", ".join(missing))
    ms_excess = [float(streams[name]["excess"]) for name in MS_NAMES]
    smallest = min(ms_excess)
    largest = max(ms_excess)
    b1_fail = [name for name in GENERATOR_NAMES if not (float(streams[name]["excess"]) < smallest)]
    page_gt = []
    for name in MS_NAMES:
        rec = streams[name]
        page_gap = float(rec["in_page"]) - float(rec["full"])
        quire_gap = float(rec["in_quire"]) - float(rec["full"])
        if page_gap > quire_gap:
            page_gt.append(name)
    return {
        "B1": len(b1_fail) == 0,
        "B1_fail": b1_fail,
        "B2": float(streams[CONTROL_NAME]["excess"]) > largest,
        "B3": len(page_gt) >= 2,
        "B3_hands": page_gt,
        "ms_excess_min": smallest,
        "ms_excess_max": largest,
    }
