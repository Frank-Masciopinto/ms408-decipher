"""Descriptive statistics for unit / word sequences.

All functions are plain, dependency-light (numpy) and operate on already-segmented data:

* a *unit sequence* is a tuple of units for one word (see :mod:`msdecipher.segment`)
* a *word list* is the list of word strings in manuscript order

These are DESCRIPTIONS of a transcription. They do not decode anything, and on their own
they do not distinguish language from cipher or from meaningless text (see docs/STATS_NOTE.md).
"""
from __future__ import annotations

import math
import random
from collections import Counter
from typing import Iterable, Sequence

import numpy as np

LN2 = math.log(2.0)


# ---------------------------------------------------------------- entropy

def entropy_counts(counts: Iterable[int], miller_madow: bool = False) -> float:
    """Shannon entropy in bits from counts (plug-in; optional Miller-Madow bias correction)."""
    c = [v for v in counts if v > 0]
    n = sum(c)
    if n == 0:
        return 0.0
    h = -sum(v / n * math.log2(v / n) for v in c)
    if miller_madow:
        h += (len(c) - 1) / (2.0 * n * LN2)
    return h


def _ngram_counts(seqs: Iterable[Sequence], n: int) -> Counter:
    c: Counter = Counter()
    for s in seqs:
        for i in range(len(s) - n + 1):
            c[tuple(s[i:i + n])] += 1
    return c


def block_entropy(seqs: Sequence[Sequence], n: int, miller_madow: bool = False) -> float:
    """Entropy of n-grams taken inside each sequence (never across sequences)."""
    return entropy_counts(_ngram_counts(seqs, n).values(), miller_madow)


def conditional_entropy(seqs: Sequence[Sequence], order: int, miller_madow: bool = False) -> float:
    """H(X_t | X_{t-order+1..t-1}) = H(order-grams) - H((order-1)-grams *that precede an
    order-gram*). order=2 -> h2, order=3 -> h3. Windows never cross a sequence (word) boundary.
    """
    if order < 2:
        raise ValueError("order must be >= 2")
    joint = _ngram_counts(seqs, order)
    ctx: Counter = Counter()
    for gram, v in joint.items():
        ctx[gram[:-1]] += v
    return entropy_counts(joint.values(), miller_madow) - entropy_counts(ctx.values(), miller_madow)


def with_boundaries(seqs: Sequence[Sequence], bos="^", eos="$") -> list[tuple]:
    return [(bos, *s, eos) for s in seqs]


def entropy_profile(seqs: Sequence[Sequence], seed: int = 1, n_shuffles: int = 10) -> dict:
    """H1, h2, h3 (plug-in and Miller-Madow), h2 with word-boundary symbols, and h2 after
    shuffling the units inside each word (destroys within-word order, keeps H1)."""
    seqs = [tuple(s) for s in seqs if len(s) > 0]
    prof = {
        "n_units": sum(len(s) for s in seqs),
        "alphabet_size": len({u for s in seqs for u in s}),
        "alphabet_size_ge20": sum(1 for v in Counter(u for s in seqs for u in s).values() if v >= 20),
        "H1": block_entropy(seqs, 1),
        "H1_mm": block_entropy(seqs, 1, True),
        "h2": conditional_entropy(seqs, 2),
        "h2_mm": conditional_entropy(seqs, 2, True),
        "h3": conditional_entropy(seqs, 3),
        "h3_mm": conditional_entropy(seqs, 3, True),
        "h2_with_word_boundaries": conditional_entropy(with_boundaries(seqs), 2),
    }
    rng = random.Random(seed)
    vals = []
    for _ in range(n_shuffles):
        sh = []
        for s in seqs:
            l = list(s)
            rng.shuffle(l)
            sh.append(tuple(l))
        vals.append(conditional_entropy(sh, 2))
    prof["h2_within_word_shuffle"] = float(np.mean(vals)) if vals else float("nan")
    return prof


def word_entropy(words: Sequence[str], miller_madow: bool = False) -> float:
    return entropy_counts(Counter(words).values(), miller_madow)


# ---------------------------------------------------------------- Zipf / Heaps

def rank_frequency(words: Iterable[str]) -> np.ndarray:
    """Counts sorted descending (index 0 = rank 1)."""
    return np.array(sorted(Counter(words).values(), reverse=True), dtype=float)


def zipf_ols_slope(freqs: np.ndarray, r_min: int = 10, r_max: int = 1000) -> float:
    """OLS slope of log10(freq) vs log10(rank) over ranks r_min..r_max (a quick look only:
    OLS on log-log is biased; see :func:`zipf_mle_exponent`)."""
    r_max = min(r_max, len(freqs))
    if r_max - r_min < 5:
        return float("nan")
    r = np.arange(r_min, r_max + 1)
    f = freqs[r_min - 1:r_max]
    return float(np.polyfit(np.log10(r), np.log10(f), 1)[0])


def zipf_mle_exponent(freqs: np.ndarray, r_min: int = 1, r_max: int = 1000) -> float:
    """Maximum-likelihood exponent s of a rank-truncated Zipf law p(r) ~ r^-s on ranks
    r_min..r_max, given the observed counts of those ranks (so s>0 here; the OLS slope is
    about -s). Found by golden-section search on the log-likelihood."""
    r_max = min(r_max, len(freqs))
    if r_max - r_min < 5:
        return float("nan")
    r = np.arange(r_min, r_max + 1, dtype=float)
    n = freqs[r_min - 1:r_max]
    lr = np.log(r)
    total = n.sum()
    sum_nlr = float((n * lr).sum())

    def ll(s: float) -> float:
        # log-likelihood; z = sum r^-s
        m = (-s * lr).max()
        z = m + math.log(np.exp(-s * lr - m).sum())
        return -s * sum_nlr - total * z

    lo, hi = 0.01, 4.0
    g = (math.sqrt(5) - 1) / 2
    a, b = lo, hi
    c, d = b - g * (b - a), a + g * (b - a)
    for _ in range(80):
        if ll(c) > ll(d):
            b = d
        else:
            a = c
        c, d = b - g * (b - a), a + g * (b - a)
    return (a + b) / 2


def heaps_curve(words: Sequence[str], points: int = 40, n_min: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """Vocabulary size V(n) after the first n tokens, at log-spaced n."""
    N = len(words)
    if N <= n_min:
        return np.array([]), np.array([])
    ns = np.unique(np.geomspace(n_min, N, points).astype(int))
    seen = set()
    out_n, out_v = [], []
    j = 0
    for i, w in enumerate(words, 1):
        seen.add(w)
        if j < len(ns) and i == ns[j]:
            out_n.append(i)
            out_v.append(len(seen))
            j += 1
    return np.array(out_n), np.array(out_v)


def heaps_exponent(words: Sequence[str], shuffled: bool = False, seed: int = 1, n_shuffles: int = 10,
                   n_min: int = 100) -> tuple[float, float]:
    """(beta, K) of V(n) = K n^beta, OLS in log-log, in manuscript order or averaged over
    random token permutations (which removes topic/section clustering of new words)."""
    def fit(ws):
        n, v = heaps_curve(ws, n_min=n_min)
        if len(n) < 5:
            return float("nan"), float("nan")
        b, a = np.polyfit(np.log(n), np.log(v), 1)
        return float(b), float(math.exp(a))

    if not shuffled:
        return fit(list(words))
    rng = random.Random(seed)
    res = []
    ws = list(words)
    for _ in range(n_shuffles):
        rng.shuffle(ws)
        res.append(fit(ws))
    return float(np.mean([r[0] for r in res])), float(np.mean([r[1] for r in res]))


def word_stats(words: Sequence[str], segmenter=None, seed: int = 1) -> dict:
    """Token-level descriptive profile."""
    cnt = Counter(words)
    freqs = np.array(sorted(cnt.values(), reverse=True), dtype=float)
    N, V = len(words), len(cnt)
    out = {
        "n_tokens": N, "n_types": V,
        "type_token_ratio": V / N if N else float("nan"),
        "hapax_types": sum(1 for v in cnt.values() if v == 1),
        "hapax_share_of_types": (sum(1 for v in cnt.values() if v == 1) / V) if V else float("nan"),
        "top10_token_coverage": float(freqs[:10].sum() / N) if N else float("nan"),
        "top50_token_coverage": float(freqs[:50].sum() / N) if N else float("nan"),
        "word_entropy_H1": entropy_counts(cnt.values()),
        "word_entropy_H1_mm": entropy_counts(cnt.values(), True),
        "zipf_ols_slope_r10_1000": zipf_ols_slope(freqs, 10, 1000),
        "zipf_mle_s_r10_1000": zipf_mle_exponent(freqs, 10, 1000),
        "zipf_mle_s_r1_1000": zipf_mle_exponent(freqs, 1, 1000),
    }
    b, k = heaps_exponent(words)
    out["heaps_beta_in_order"], out["heaps_K_in_order"] = b, k
    b, k = heaps_exponent(words, shuffled=True, seed=seed)
    out["heaps_beta_shuffled"], out["heaps_K_shuffled"] = b, k
    if segmenter is not None and N:
        lens = [len(segmenter(w)) for w in words]
        out["mean_word_length_units"] = float(np.mean(lens))
        out["median_word_length_units"] = float(np.median(lens))
    return out


# ---------------------------------------------------------------- positional

def positional_table(word_lines: Sequence[Sequence[str]], segmenter, line_flags=None):
    """Distribution of every unit over positions.

    word_lines: list of lines; each a list of readable-or-not word strings.
    line_flags: optional list of dicts per line: {'own_line': bool, 'para_start': bool}.
    Returns dict unit -> Counter with keys initial/medial/final/sole (within word) and
    line_initial / line_final / para_initial (first unit of the first word of a line etc.).
    Words containing '?' are skipped for the within-word positions and for line edges.
    """
    tab: dict[str, Counter] = {}
    for li, words in enumerate(word_lines):
        fl = line_flags[li] if line_flags else {"own_line": True, "para_start": False}
        for wi, w in enumerate(words):
            if "?" in w:
                continue
            u = segmenter(w)
            n = len(u)
            for i, x in enumerate(u):
                key = "sole" if n == 1 else "initial" if i == 0 else "final" if i == n - 1 else "medial"
                tab.setdefault(x, Counter())[key] += 1
            if fl["own_line"]:
                if wi == 0:
                    tab.setdefault(u[0], Counter())["line_initial"] += 1
                    if fl["para_start"]:
                        tab[u[0]]["para_initial"] += 1
                if wi == len(words) - 1:
                    tab.setdefault(u[-1], Counter())["line_final"] += 1
    return tab


# ---------------------------------------------------------------- divergence

def js_divergence(c1: Counter, c2: Counter) -> float:
    """Jensen-Shannon divergence (bits, base 2; range 0..1) between two count dictionaries."""
    keys = set(c1) | set(c2)
    n1, n2 = sum(c1.values()), sum(c2.values())
    if not n1 or not n2:
        return float("nan")
    jsd = 0.0
    for k in keys:
        p, q = c1.get(k, 0) / n1, c2.get(k, 0) / n2
        m = (p + q) / 2
        if p > 0:
            jsd += 0.5 * p * math.log2(p / m)
        if q > 0:
            jsd += 0.5 * q * math.log2(q / m)
    return jsd


# ---------------------------------------------------------------- Sukhotin

def sukhotin(seqs: Sequence[Sequence], min_count: int = 1) -> tuple[list, dict]:
    """Sukhotin's vowel/consonant algorithm on adjacent unit pairs *inside* sequences.

    Returns (vowels_in_pick_order, row_sums_after). Units occurring fewer than ``min_count``
    times are ignored. The output is a PROPOSAL about distributional behaviour (vowel-like =
    tends to be adjacent to non-vowel-like units); it is not evidence that the units are
    letters of a language. Always run it AFTER segmentation and check stability."""
    freq = Counter(u for s in seqs for u in s)
    syms = sorted(u for u, v in freq.items() if v >= min_count)
    idx = {u: i for i, u in enumerate(syms)}
    n = len(syms)
    if n == 0:
        return [], {}
    m = np.zeros((n, n), dtype=np.int64)
    for s in seqs:
        for a, b in zip(s, s[1:]):
            if a in idx and b in idx and a != b:
                m[idx[a], idx[b]] += 1
                m[idx[b], idx[a]] += 1
    vowels = sukhotin_matrix(syms, m)
    row = m.sum(axis=1).astype(np.int64)
    for v in vowels:
        row = row - 2 * m[:, syms.index(v)]
    return vowels, {syms[i]: int(row[i]) for i in range(n)}


def sukhotin_matrix(syms: Sequence, m: np.ndarray) -> list:
    """Sukhotin on a precomputed symmetric, zero-diagonal adjacency matrix ``m``."""
    n = len(syms)
    row = m.sum(axis=1).astype(np.int64)
    is_v = np.zeros(n, dtype=bool)
    vowels = []
    while True:
        cand = np.where(~is_v, row, np.iinfo(np.int64).min)
        j = int(np.argmax(cand))
        if is_v[j] or row[j] <= 0:
            break
        is_v[j] = True
        vowels.append(syms[j])
        row = row - 2 * m[:, j]
    return vowels
