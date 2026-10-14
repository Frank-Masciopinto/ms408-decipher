"""h38: family re-spelling (A) and native-shape copier (B) (PREREG.md). Statistics only, no meaning claims."""
from __future__ import annotations

import sys
from collections import Counter, deque
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
for h in ("h34_boundary_rule_generator", "h35_word_shape_model", "h36_similarity_preserving_respell", "h37_copy_aware_respell"):
    sys.path.insert(0, str(ROOT / "hypotheses" / h))
import h35_lib as S35  # noqa: E402
import h36_lib as S36  # noqa: E402
import h37_lib as S37  # noqa: E402

lev = S36.lev


def final_dist(words):
    c = Counter(w[-1] for w in words if w); g = sorted(c); p = np.array([c[x] for x in g], float); return g, p / p.sum()


def neighbours(types):
    keys = {}
    for t in types:
        for k in {t[:i] + t[i + 1:] for i in range(len(t))} | {t}: keys.setdefault(k, set()).add(t)
    nb = {t: set() for t in types}
    for t in types:
        for k in {t[:i] + t[i + 1:] for i in range(len(t))} | {t}:
            for u in keys.get(k, ()):
                if u != t and lev(u, t) == 1: nb[t].add(u)
    return nb


def families(types):
    """types by desc freq -> list of (root, [(parent, child) BFS edges]) over edit-1 connected components."""
    nb = neighbours(types); rank = {t: k for k, t in enumerate(types)}; seen = set(); out = []
    for t in types:
        if t in seen: continue
        seen.add(t); edges = []; q = deque([t])
        while q:
            p = q.popleft()
            for c in sorted(nb[p], key=rank.get):
                if c not in seen: seen.add(c); edges.append((p, c)); q.append(c)
        out.append((t, edges))
    return out


def slot(i, n):
    return i if i <= n - 1 - i else -(n - i)  # signed: from start, or negative from end


def draw(m, left, rng, final, fd, exclude=None):
    if final:
        g, p = fd
        for _ in range(20):
            x = g[rng.choice(len(g), p=p)]
            if x != exclude: return x
    return S37.draw_glyph(m, left, rng, exclude=exclude)


def apply_shared(op, p, q, m, rng, fd, fmap):
    kind, i, g = op; n = len(p)
    if kind == "d":
        if len(q) <= 1: return None
        j = S37.rel_index(i, n, len(q)); return q[:j] + q[j + 1:]
    if kind == "s":
        if not q: return None
        j = S37.rel_index(i, n, len(q)); key = ("s", slot(i, n), g); fin = j == len(q) - 1
        x = fmap.get(key)
        if x is None or x == q[j]: x = draw(m, q[:j], rng, fin, fd, exclude=q[j]); fmap.setdefault(key, x)
        return q[:j] + x + q[j + 1:]
    j = S37.rel_index(i, n, len(q), insert=True); key = ("i", slot(i, n + 1), g); fin = j == len(q)
    x = fmap.get(key) or draw(m, q[:j], rng, fin, fd); fmap.setdefault(key, x); return q[:j] + x + q[j:]


def fam_respell(tokens, m, fd, rng, tries=50):
    types = [t for t, _ in Counter(tokens).most_common()]; used = set(); mp = {}; st = Counter()

    def fresh(t):
        w = None
        for _ in range(200):
            c = S35.sample_word(m, rng)
            if c and c not in used: w = c
            if w and abs(len(w) - len(t)) <= 1: break
        return w or f"{t}_{len(mp)}"
    for root, edges in families(types):
        fmap = {}; w = fresh(root); used.add(w); mp[root] = w; st["root"] += 1
        for p, c in edges:
            op = S37.edit_op(p, c); w = None
            for k in range(tries):
                x = apply_shared(op, p, mp[p], m, rng, fd, fmap if k == 0 else {})
                if x and x not in used: w = x; break
            st["derived_ok" if w else "derived_fail"] += 1
            w = w or fresh(c); used.add(w); mp[c] = w
    return [mp[t] for t in tokens], st


def mutate(w, m, rng, fd):
    k = rng.integers(3)
    if k == 0 and len(w) > 1:
        j = rng.integers(len(w)); return w[:j] + w[j + 1:]
    if k == 1 and w:
        j = rng.integers(len(w)); return w[:j] + draw(m, w[:j], rng, j == len(w) - 1, fd, exclude=w[j]) + w[j + 1:]
    j = rng.integers(len(w) + 1); return w[:j] + draw(m, w[:j], rng, j == len(w), fd) + w[j:]


def native_copier(n, m, fd, rng, feed=None, p_fresh=.15, window=50):
    out = []; fi = 0
    for _ in range(n):
        if len(out) < window or rng.random() < p_fresh:
            if feed is not None: w = feed[fi % len(feed)]; fi += 1
            else:
                w = ""
                while not w: w = S35.sample_word(m, rng)
        else:
            w = out[-1 - rng.integers(window)]; u = rng.random()
            for _ in range(0 if u < .25 else 1 if u < .85 else 2): w = mutate(w, m, rng, fd)
        out.append(w)
    return out


def js_final(a_words, b_words):
    ca = Counter(w[-1] for w in a_words if w); cb = Counter(w[-1] for w in b_words if w); g = sorted(set(ca) | set(cb))
    p = np.array([ca[x] for x in g], float); q = np.array([cb[x] for x in g], float); p /= p.sum(); q /= q.sum(); mm = (p + q) / 2
    kl = lambda a, b: float(np.sum(a[a > 0] * np.log2(a[a > 0] / b[a > 0])))
    return .5 * kl(p, mm) + .5 * kl(q, mm)
