"""h36: glyph-level similarity-preserving re-spelling (PREREG.md). Statistics only, no meaning claims."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses/h34_boundary_rule_generator"))
sys.path.insert(0, str(ROOT / "hypotheses/h35_word_shape_model"))
MINB = 30


def cls(w, i):
    return "F" if i == len(w) - 1 else ("I" if i == 0 else "M")


def counts(words, ctx=False):
    c = {}
    for w in words:
        for i, g in enumerate(w):
            k = (cls(w, i), w[i - 1] if (ctx and i) else "")
            c.setdefault(k, Counter())[g] += 1
    return c


def rank_map(src: Counter, tgt: Counter):
    t = [g for g, _ in tgt.most_common()]
    return {g: t[min(j, len(t) - 1)] for j, (g, _) in enumerate(src.most_common())}


def fit_map(gen_words, ms_words, ctx=False, rng=None):
    """Per-class (and optionally per previous-glyph) rank map gen glyph -> MS glyph. rng => shuffled-control bijection."""
    gc = counts(gen_words); mc = counts(ms_words); maps = {}
    for k in gc:
        tgt = mc.get(k, Counter())
        if rng is not None:
            gs = list(tgt); perm = list(rng.permutation(gs)); tgt = Counter({g: tgt[p] for g, p in zip(gs, perm)})
        maps[k] = rank_map(gc[k], tgt)
    if ctx:
        gcc = counts(gen_words, True); mcc = counts(ms_words, True)
        for k, c in gcc.items():
            if sum(c.values()) >= MINB and sum(mcc.get(k, Counter()).values()) >= MINB: maps[k] = rank_map(c, mcc[k])
    return maps


def apply_map(w, maps):
    out = []
    for i, g in enumerate(w):
        k = (cls(w, i), w[i - 1] if i else "")
        m = maps.get(k) or maps.get((k[0], ""), {})
        out.append(m.get(g, g))
    return "".join(out)


def respell(tokens, maps):
    cache = {}
    return [cache.setdefault(t, apply_map(t, maps)) for t in tokens]


def lev(a, b):
    p = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        c = [i]
        for j, y in enumerate(b, 1): c.append(min(p[j] + 1, c[j - 1] + 1, p[j - 1] + (x != y)))
        p = c
    return p[-1]


def edit_preservation(tokens, out, top=2000):
    """Share of base type pairs at edit distance 1 (top types) whose re-spellings are at distance <= 1."""
    mp = dict(zip(tokens, out)); ty = [t for t, _ in Counter(tokens).most_common(top)]
    by = {}
    for t in ty: by.setdefault(len(t), []).append(t)
    n = k = 0
    for t in ty:
        for L in (len(t), len(t) + 1):
            for u in by.get(L, []):
                if u != t and (L > len(t) or u > t) and lev(t, u) == 1:
                    n += 1; k += lev(mp[t], mp[u]) <= 1
    return k / n if n else float("nan"), n
