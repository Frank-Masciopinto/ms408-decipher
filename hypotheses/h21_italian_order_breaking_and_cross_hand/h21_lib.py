"""h21: order-breaking Italian encodings and cross-hand C0 (PREREG.md). No meaning claims."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h20_generators_vs_italian"))
import h20_lib as L20  # noqa: E402

SUFS = ["", "y", "dy", "ol", "ain", "or", "al", "am"]
LINE = 9


def homophones(tokens, K, rng, W=20, p_reuse=.5):
    last = {}; out = []
    for i, w in enumerate(tokens):
        if w in last and i - last[w][0] <= W and rng.random() < p_reuse: j = last[w][1]
        else: j = int(rng.integers(K))
        out.append(w + SUFS[j]); last[w] = (i, j)
    return out


def to_lines(tokens, n=LINE):
    return [tokens[i:i + n] for i in range(0, len(tokens), n)]


def shuffle_lines(lines, rng):
    return [[str(x) for x in rng.permutation(l)] for l in lines]


def insert_nulls(lines, r, null_words, null_p, rng):
    if r <= 0: return lines
    q = r / (1 + r); out = []           # geometric count with mean r: P(k) = (1-q) q^k
    for l in lines:
        nl = []
        for w in l:
            nl.append(w); k = rng.geometric(1 - q) - 1
            nl += [str(x) for x in rng.choice(null_words, size=k, p=null_p)] if k else []
        out.append(nl)
    return out


def encode(plain, base, ms_codes, rng, K=1, shuf=False, r=0.0, null_dist=None, naibbe_words=None):
    """returns (lines, info). base in {'plain','syll','naibbe'}."""
    if base == "plain": toks = list(plain)
    elif base == "syll": toks, _ = L20.syllabic_cipher(plain, ms_codes)
    else: toks = list(naibbe_words)
    if K > 1: toks = homophones(toks, K, rng)
    lines = to_lines(toks)
    if shuf: lines = shuffle_lines(lines, rng)
    n_real = sum(map(len, lines))
    if r > 0: lines = insert_nulls(lines, r, null_dist[0], null_dist[1], rng)
    n_all = sum(map(len, lines))
    layers = 1 + (K > 1) + bool(shuf) + (r > 0)
    return lines, dict(null_share=1 - n_real / n_all, layers=int(layers))


def point_match(stats, target):
    out = {k: bool(abs(stats[k] - target[k]) <= d) for k, d in L20.DELTA.items()}
    out["n_match"] = int(sum(out.values())); out["distance"] = float(sum(((stats[k] - target[k]) / d) ** 2 for k, d in L20.DELTA.items()))
    return out
