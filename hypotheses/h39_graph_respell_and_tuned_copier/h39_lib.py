"""h39: graph-preserving joint slot re-spelling (A) and tuned native copier (B) (PREREG.md). Statistics only."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
for h in ("h33_word_boundary_resegmentation", "h34_boundary_rule_generator", "h35_word_shape_model",
          "h36_similarity_preserving_respell", "h37_copy_aware_respell", "h38_family_respell_and_native_copier"):
    sys.path.insert(0, str(ROOT / "hypotheses" / h))
import h33_lib  # noqa: E402
import h36_lib as S36  # noqa: E402
import h38_lib as S38  # noqa: E402

SLOTS = ("0", "1", "2", "mid", "-3", "-2", "-1")
lev = S36.lev; js_final = S38.js_final


def slot(i, n):
    if i == n - 1: return "-1"
    if i == 0: return "0"
    if i == n - 2: return "-2"
    if i == 1: return "1"
    if i == n - 3: return "-3"
    if i == 2: return "2"
    return "mid"


def slot_counts(words):
    c = {k: Counter() for k in SLOTS}
    for w in words:
        for i, g in enumerate(w): c[slot(i, len(w))][g] += 1
    return c


def init_maps(gen_words, ms_words):
    gc = slot_counts(gen_words); mc = slot_counts(ms_words)
    return {k: S36.rank_map(gc[k], mc[k] or Counter(gc[k])) for k in SLOTS}


def apply(w, maps):
    n = len(w); return "".join(maps[slot(i, n)].get(g, g) for i, g in enumerate(w))


def _js(ca, cb):
    g = sorted(set(ca) | set(cb))
    p = np.array([ca[x] for x in g], float) + 1e-9; q = np.array([cb[x] for x in g], float) + 1e-9
    p /= p.sum(); q /= q.sum(); m = (p + q) / 2
    return float(.5 * np.sum(p * np.log2(p / m)) + .5 * np.sum(q * np.log2(q / m)))


def space_S(tokens, L=9):
    return h33_lib.space_predict([tokens[i:i + L] for i in range(0, len(tokens) - L + 1, L)])["entropy_removed"]


def edges(types):
    nb = S38.neighbours(types); return [(a, b) for a in types for b in nb[a] if a < b]


def E_of(edge_list, maps):
    if not edge_list: return 1.0
    return sum(lev(apply(a, maps), apply(b, maps)) <= 1 for a, b in edge_list) / len(edge_list)


class Target:
    def __init__(self, ms_words, ms_lines):
        self.fin = Counter(w[-1] for w in ms_words); self.slots = slot_counts(ms_words)
        self.S = h33_lib.space_predict(ms_lines)["entropy_removed"]
        self.inv = {k: sorted(c) for k, c in self.slots.items()}


def objective(sample, edge_list, maps, tgt):
    out = [apply(w, maps) for w in sample]
    S = space_S(out); F = _js(Counter(w[-1] for w in out), tgt.fin); sc = slot_counts(out)
    J = float(np.mean([_js(sc[k], tgt.slots[k]) for k in SLOTS if sc[k] and tgt.slots[k]])); E = E_of(edge_list, maps)
    return abs(S - tgt.S) + F + .5 * J + 2 * max(0., .9 - E), dict(S=S, F=F, JSslot=J, E=E)


def anneal(base, tgt, ms_words, rng, steps=1500, t0=.02, t1=.0005, nsample=4000, ntop=800):
    sample = base[:nsample]; types = [t for t, _ in Counter(base).most_common(ntop)]; el = edges(types)
    maps = init_maps(base, ms_words); cur, info = objective(sample, el, maps, tgt); best = (cur, {k: dict(v) for k, v in maps.items()}, info)
    gglyphs = {k: sorted(slot_counts(base)[k]) for k in SLOTS}; acc = 0
    for it in range(steps):
        T = t0 * (t1 / t0) ** (it / max(1, steps - 1)); k = SLOTS[rng.integers(len(SLOTS))]
        if not gglyphs[k] or not tgt.inv[k]: continue
        g = gglyphs[k][rng.integers(len(gglyphs[k]))]; old = maps[k].get(g, g); new = tgt.inv[k][rng.integers(len(tgt.inv[k]))]
        if new == old: continue
        maps[k][g] = new; val, inf = objective(sample, el, maps, tgt)
        if val <= cur or rng.random() < np.exp((cur - val) / T):
            cur, info = val, inf; acc += 1
            if val < best[0]: best = (val, {kk: dict(v) for kk, v in maps.items()}, inf)
        else: maps[k][g] = old
    return best[1], dict(obj=best[0], accepted=acc, **best[2])


def copy_proxy(tokens, back=5):
    return float(np.mean([any(lev(tokens[i], tokens[j]) <= 1 for j in range(max(0, i - back), i)) for i in range(back, len(tokens))]))


def tuned_copier(n, m, fd, rng, feed=None, p_fresh=.15, window=50, p0=.25):
    """h38 native copier with free fresh rate, window and edit distribution (rest split .8/.2 one/two edits)."""
    p1 = p0 + (1 - p0) * .8; out = []; fi = 0
    for _ in range(n):
        if len(out) < window or rng.random() < p_fresh:
            if feed is not None: w = feed[fi % len(feed)]; fi += 1
            else:
                w = ""
                while not w: w = S38.S35.sample_word(m, rng)
        else:
            w = out[-1 - rng.integers(window)]; u = rng.random()
            for _ in range(0 if u < p0 else 1 if u < p1 else 2): w = S38.mutate(w, m, rng, fd)
        out.append(w)
    return out
