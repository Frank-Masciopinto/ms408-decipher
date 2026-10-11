"""The statistics suite applied identically to MS 408 and to every control.

Reuses :mod:`msdecipher.stats` (Zipf, Heaps, H1/h2/h3, within-word shuffle, Sukhotin) and adds
three cheap descriptors that matter for the self-citation / verbose-cipher hypotheses
(positional skew, adjacent repeats, near-repeats). A control or the manuscript is represented as
a flat list of word strings plus a segmenter (raw characters for controls, the configured EVA
unit segmenter for MS 408). Nothing here decodes anything; no metric is decisive.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Callable, Sequence

import numpy as np

from . import stats as S


def edit_distance_le1(a: str, b: str) -> bool:
    """True iff Levenshtein(a, b) <= 1 (including a == b)."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        return sum(x != y for x, y in zip(a, b)) == 1
    if la > lb:
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


def repeat_rates(words: Sequence[str]) -> tuple[float, float]:
    """(share of adjacent token pairs that are identical, share at edit distance exactly 1)."""
    n = len(words) - 1
    if n <= 0:
        return float("nan"), float("nan")
    ident = near = 0
    for a, b in zip(words, words[1:]):
        if a == b:
            ident += 1
        elif edit_distance_le1(a, b):
            near += 1
    return ident / n, near / n


def positional_skew(seqs: Sequence[tuple], min_count: int = 50, ratio: float = 3.0) -> dict:
    """Word-position behaviour of units, over words with >= 3 units.

    * ``pos_jsd_initial_final``: Jensen-Shannon divergence (bits) between the unit distribution at
      word-initial and at word-final position.
    * ``pos_skewed_unit_share``: share of units (>= ``min_count`` occurrences) whose probability
      of being word-initial, or of being word-final, differs from the all-unit baseline by more
      than a factor ``ratio`` (over- or under-represented)."""
    ini, fin, med = Counter(), Counter(), Counter()
    n_words = 0
    for s in seqs:
        if len(s) < 3:
            continue
        n_words += 1
        ini[s[0]] += 1
        fin[s[-1]] += 1
        med.update(s[1:-1])
    if n_words == 0:
        return {"pos_jsd_initial_final": float("nan"), "pos_skewed_unit_share": float("nan")}
    tot = Counter()
    for c in (ini, fin, med):
        tot.update(c)
    n_units = sum(tot.values())
    base_i = n_words / n_units
    skew = used = 0
    for u, v in tot.items():
        if v < min_count:
            continue
        used += 1
        ri, rf = (ini[u] / v) / base_i, (fin[u] / v) / base_i
        if any(r > ratio or r < 1 / ratio for r in (ri, rf)):
            skew += 1
    return {"pos_jsd_initial_final": S.js_divergence(ini, fin),
            "pos_skewed_unit_share": skew / used if used else float("nan")}


def metrics(words: Sequence[str], segmenter: Callable[[str], tuple] | None = None, seed: int = 1,
            n_shuffles: int = 5) -> dict:
    """Flat metric dictionary for one token list."""
    seg = segmenter or (lambda w: tuple(w))
    words = [w for w in words if w]
    ws = S.word_stats(words, seg, seed)
    seqs = [tuple(seg(w)) for w in words]
    ep = S.entropy_profile(seqs, seed, n_shuffles=n_shuffles)
    vow, _ = S.sukhotin(seqs, min_count=20)
    lens = np.array([len(s) for s in seqs], dtype=float)
    ident, near = repeat_rates(words)
    out = {
        "n_tokens": ws["n_tokens"], "n_types": ws["n_types"],
        "type_token_ratio": ws["type_token_ratio"],
        "hapax_share_of_types": ws["hapax_share_of_types"],
        "top10_token_coverage": ws["top10_token_coverage"],
        "word_entropy_H1": ws["word_entropy_H1"],
        "zipf_mle_s_r10_1000": ws["zipf_mle_s_r10_1000"],
        "zipf_ols_slope_r10_1000": ws["zipf_ols_slope_r10_1000"],
        "heaps_beta_in_order": ws["heaps_beta_in_order"],
        "heaps_beta_shuffled": ws["heaps_beta_shuffled"],
        "mean_word_length_units": float(lens.mean()) if len(lens) else float("nan"),
        "word_length_sd_units": float(lens.std()) if len(lens) else float("nan"),
        "alphabet_size_ge20": ep["alphabet_size_ge20"],
        "unit_H1": ep["H1"], "unit_h2": ep["h2"], "unit_h3": ep["h3"],
        "unit_h2_within_word_shuffle": ep["h2_within_word_shuffle"],
        "shuffle_gap_h2": ep["h2_within_word_shuffle"] - ep["h2"],
        "sukhotin_vowel_like_count": len(vow),
        "sukhotin_vowel_like_share": (len(vow) / ep["alphabet_size_ge20"]) if ep["alphabet_size_ge20"] else float("nan"),
        "adjacent_identical_rate": ident, "adjacent_edit1_rate": near,
    }
    out.update(positional_skew(seqs))
    return out


# metric -> (label, tolerance used for the "within the family's range" verdict, group)
# Tolerances are rough, round numbers (NOT statistical confidence intervals).
METRIC_INFO: dict[str, tuple[str, float, str]] = {
    "type_token_ratio": ("type/token ratio", 0.05, "lexicon"),
    "hapax_share_of_types": ("hapax share of types", 0.05, "lexicon"),
    "top10_token_coverage": ("top-10 token coverage", 0.03, "lexicon"),
    "word_entropy_H1": ("word entropy H1 (bits)", 0.5, "lexicon"),
    "zipf_mle_s_r10_1000": ("Zipf exponent s (MLE r10-1000)", 0.1, "lexicon"),
    "heaps_beta_in_order": ("Heaps beta (text order)", 0.05, "lexicon"),
    "heaps_beta_shuffled": ("Heaps beta (shuffled tokens)", 0.05, "lexicon"),
    "mean_word_length_units": ("mean word length (units)", 0.5, "word shape"),
    "word_length_sd_units": ("word length SD (units)", 0.3, "word shape"),
    "unit_H1": ("unit entropy H1 (bits)", 0.15, "letter statistics"),
    "unit_h2": ("conditional entropy h2 (bits)", 0.15, "letter statistics"),
    "unit_h3": ("conditional entropy h3 (bits)", 0.15, "letter statistics"),
    "shuffle_gap_h2": ("h2 rise after within-word shuffle (bits)", 0.2, "letter statistics"),
    "sukhotin_vowel_like_share": ("Sukhotin vowel-like share of alphabet", 0.05, "letter statistics"),
    "pos_jsd_initial_final": ("word-initial vs final unit JSD (bits)", 0.05, "positional"),
    "pos_skewed_unit_share": ("share of positionally skewed units", 0.1, "positional"),
    "adjacent_identical_rate": ("adjacent identical-token rate", 0.01, "repetition"),
    "adjacent_edit1_rate": ("adjacent edit-distance-1 rate", 0.02, "repetition"),
}


def verdict(target: float, lo: float, hi: float, tol: float) -> str:
    """'≈' if the target lies within [lo - tol, hi + tol] of a family's observed range,
    '↑' if the target is above that band, '↓' if below, '–' if undefined."""
    if any(isinstance(x, float) and math.isnan(x) for x in (target, lo, hi)):
        return "–"
    if target > hi + tol:
        return "↑"
    if target < lo - tol:
        return "↓"
    return "≈"
