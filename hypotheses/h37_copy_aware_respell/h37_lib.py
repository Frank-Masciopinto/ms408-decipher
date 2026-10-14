"""h37: copy-aware re-spelling (PREREG.md). Statistics only, no meaning claims."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
for h in ("h34_boundary_rule_generator", "h35_word_shape_model", "h36_similarity_preserving_respell"):
    sys.path.insert(0, str(ROOT / "hypotheses" / h))
import h35_lib as S35  # noqa: E402
import h36_lib as S36  # noqa: E402

lev = S36.lev


def edit_op(p, c):
    """One-edit op turning p into c: ('s', i, g) | ('i', i, g) | ('d', i, None). Indices in p."""
    if len(p) == len(c):
        i = next(k for k in range(len(p)) if p[k] != c[k]); return ("s", i, c[i])
    if len(c) == len(p) + 1:
        i = next((k for k in range(len(p)) if p[k] != c[k]), len(p)); return ("i", i, c[i])
    i = next((k for k in range(len(c)) if p[k] != c[k]), len(c)); return ("d", i, None)


def rel_index(i, n_old, n_new, insert=False):
    """Position-relative index: keep distance from the nearer end of the word, clipped to the new word."""
    top = n_new if insert else n_new - 1
    j = i if i <= (n_old - (0 if insert else 1)) - i else top - ((n_old - (0 if insert else 1)) - i)
    return int(min(max(j, 0), max(top, 0)))


def draw_glyph(m, left, rng, exclude=None):
    h = ("^" * (S35.ORDER - 1) + left)[-(S35.ORDER - 1):]; syms = [s for s in m["syms"] if s != "$" and s != exclude]
    c = m["cnt"].get(h, {}); p = np.array([c.get(x, 0) + S35.ADDK for x in syms]); return syms[rng.choice(len(syms), p=p / p.sum())]


def replay(op, q, n_old, m, rng):
    kind, i, _ = op
    if kind == "d":
        if len(q) <= 1: return None
        j = rel_index(i, n_old, len(q)); return q[:j] + q[j + 1:]
    if kind == "s":
        if not q: return None
        j = rel_index(i, n_old, len(q)); return q[:j] + draw_glyph(m, q[:j], rng, exclude=q[j]) + q[j + 1:]
    j = rel_index(i, n_old, len(q), insert=True); return q[:j] + draw_glyph(m, q[:j], rng) + q[j:]


def parents(types):
    """types sorted by desc frequency -> {child: parent} using deletion keys (parent = most frequent edit-1 type)."""
    rank = {t: k for k, t in enumerate(types)}; keys = {}
    for t in types:
        for k in {t} | {t[:i] + t[i + 1:] for i in range(len(t))}: keys.setdefault(k, []).append(t)
    par = {}
    for t in types:
        best = None
        for k in {t} | {t[:i] + t[i + 1:] for i in range(len(t))}:
            for u in keys.get(k, []):
                if rank[u] < rank[t] and (best is None or rank[u] < rank[best]) and lev(u, t) == 1: best = u
        if best is not None: par[t] = best
    return par


def respell_map(types, m, rng, tries=50):
    par = parents(types); used = set(); mp = {}; stats = Counter()
    for t in types:
        w = None
        if t in par:
            p = par[t]; op = edit_op(p, t)
            for _ in range(tries):
                c = replay(op, mp[p], len(p), m, rng)
                if c and c not in used: w = c; break
            stats["derived_ok" if w else "derived_fail"] += 1
        else: stats["root"] += 1
        if w is None:
            for _ in range(200):
                c = S35.sample_word(m, rng)
                if c and c not in used: w = c
                if w and abs(len(w) - len(t)) <= 1: break
            w = w or f"{t}_{len(mp)}"
        used.add(w); mp[t] = w
    return mp, stats


def respell(tokens, m, rng):
    types = [t for t, _ in Counter(tokens).most_common()]; mp, st = respell_map(types, m, rng)
    return [mp[t] for t in tokens], st
