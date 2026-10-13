"""h30: the line as a unit (PREREG.md). Statistics only, no meaning claims."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
CTRL = ROOT / "data" / "controls"
CONTROLS = {"dante": ("pg1000.txt", "verse"), "ariosto": ("pg3747.txt", "verse"), "macer": ("la_macer_floridus.txt", "verse"),
            "augustine": ("pg33849.txt", "prose"), "manzoni": ("pg45334.txt", "prose"), "sidrach": ("pg44549.txt", "prose"),
            "cucina": ("italian/pg33954.txt", "recipe")}
NBIN = 5


# ------------------------------------------------------------------ loading
def load_control(fname, ntok=10000, skip=0.25, block=50):
    raw = (CTRL / fname).read_text(encoding="utf-8", errors="ignore").splitlines()
    s = next((i for i, l in enumerate(raw) if "*** START OF" in l), 0); e = next((i for i, l in enumerate(raw) if "*** END OF" in l), len(raw))
    raw = raw[s + 1:e]; raw = raw[int(len(raw) * skip):]
    lines, para_first, n, k = [], True, 0, 0
    for l in raw:
        l = re.sub(r"\{\{[^}]*\}\}|<[^>]*>|\[[^\]]*\]|==[^=]*==", " ", l)
        ws = [w.lower() for w in re.findall(r"[^\W\d_]+", l)]
        if not ws:
            para_first = True; continue
        if l.strip().isupper(): continue
        lines.append(dict(words=ws, page=f"b{k // block}", stratum=f"b{k // block}", para_first=para_first, unit=list))
        para_first = False; k += 1; n += len(ws)
        if n >= ntok: break
    return lines


def load_ms(hand):
    import sys
    sys.path.insert(0, str(ROOT / "hypotheses" / "h19_heldout_likelihood")); import run_h19  # noqa: F401
    import h14_lib as L14
    sys.path.insert(0, str(ROOT / "hypotheses" / "h13_top_word_context")); import h13_lib
    d = L14.table(); d = d[d.HL == hand].sort_values(["folio", "line", "pos"], kind="stable"); lines = []
    order = {f: i for i, f in enumerate(dict.fromkeys(L14.table().folio))}
    for (lid), g in sorted(d.groupby("lid"), key=lambda x: (order[x[1].folio.iloc[0]], x[1].line.iloc[0])):
        g = g.sort_values("pos"); lines.append(dict(words=g.w.tolist(), page=g.folio.iloc[0], stratum=f"{hand}|{g.quire.iloc[0]}", quire=str(g.quire.iloc[0]),
                                                   para_first=bool(g.para_initial.iloc[0]), unit=lambda w: list(h13_lib.SEG(w))))
    return lines


# ------------------------------------------------------------------ classes
def classes(lines, k_type=30, k_unit=10):
    ws = [w for l in lines for w in l["words"]]; u = lines[0]["unit"]
    top = {w for w, _ in Counter(ws).most_common(k_type)}
    on = Counter(u(w)[0] for w in ws); en = Counter(u(w)[-1] for w in ws)
    ton = {x for x, _ in on.most_common(k_unit)}; ten = {x for x, _ in en.most_common(k_unit)}
    f = dict(TYPE=lambda w: w if w in top else "OTHER", ONSET=lambda w: (lambda x: x if x in ton else "OTHER")(u(w)[0]),
             END=lambda w: (lambda x: x if x in ten else "OTHER")(u(w)[-1]))
    return {c: [[fn(w) for w in l["words"]] for l in lines] for c, fn in f.items()}


def pos_bin(i, n):
    return 0 if i == 0 else NBIN - 1 if i == n - 1 else 1 if i == 1 else NBIN - 2 if i == n - 2 else 2


def mi(pairs):
    pj = Counter(pairs); n = sum(pj.values())
    if n == 0: return 0.0
    pa = Counter(a for a, _ in pairs); pb = Counter(b for _, b in pairs)
    return sum(v / n * math.log2(v * n / (pa[a] * pb[b])) for (a, b), v in pj.items())


def pos_pairs(cl):
    return [(pos_bin(i, len(l)), c) for l in cl if len(l) >= 4 for i, c in enumerate(l)]


def pos_contrib(cl):
    """MI contribution per position bin: p(b) KL(P(c|b) || P(c))."""
    pr = pos_pairs(cl); n = len(pr); pc = Counter(c for _, c in pr); out = {}
    for b in range(NBIN):
        cb = Counter(c for bb, c in pr if bb == b); nb = sum(cb.values())
        out[b] = sum(v / n * math.log2((v / nb) / (pc[c] / n)) for c, v in cb.items()) if nb else 0.0
    return out


def permute_within(lines, cl, rng):
    """words permuted across lines within stratum, line lengths kept."""
    idx = defaultdict(list)
    for i, l in enumerate(lines): idx[l["stratum"]].append(i)
    out = [None] * len(cl)
    for s, ii in idx.items():
        pool = [c for i in ii for c in cl[i]]; rng.shuffle(pool); k = 0
        for i in ii: out[i] = pool[k:k + len(cl[i])]; k += len(cl[i])
    return out


def within_pairs(cl): return [(l[i], l[i + 1]) for l in cl for i in range(len(l) - 1)]


def across_pairs(lines, cl, order=None, a_cl=None, b_cl=None):
    a_cl = a_cl or cl; b_cl = b_cl or cl; order = order or list(range(len(lines))); out = []
    for x, y in zip(order, order[1:]):
        if lines[x]["page"] == lines[y]["page"]: out.append((a_cl[x][-1], b_cl[y][0]))
    return out


def shuffle_order(lines, rng):
    by = defaultdict(list)
    for i, l in enumerate(lines): by[l["page"]].append(i)
    order = []
    for p in dict.fromkeys(l["page"] for l in lines):
        ii = by[p][:]; rng.shuffle(ii); order += ii
    return order


def js(p, q):
    keys = set(p) | set(q); P = np.array([p.get(k, 0) for k in keys], float); Q = np.array([q.get(k, 0) for k in keys], float)
    P /= P.sum(); Q /= Q.sum(); M = (P + Q) / 2
    kl = lambda a, b: float(np.sum(a[a > 0] * np.log2(a[a > 0] / b[a > 0])))  # noqa: E731
    return .5 * kl(P, M) + .5 * kl(Q, M)


# ------------------------------------------------------------------ held-out line models
def _p(counter, V, a=.5):
    tot = sum(counter.values()); return lambda c: (counter.get(c, 0) + a) / (tot + a * V)


def model_bits(train, test, V):
    """bits/token on test for bag, positional unigram, within-line bigram, HMM."""
    out = {}
    bag = _p(Counter(c for l in train for c in l), V)
    out["bag"] = -np.mean([math.log2(bag(c)) for l in test for c in l])
    pc = defaultdict(Counter)
    for l in train:
        for i, c in enumerate(l): pc[pos_bin(i, len(l)) if len(l) >= 4 else ("s", i, len(l))][c] += 1
    def pp(i, n, c):
        k = pos_bin(i, n) if n >= 4 else ("s", i, n)
        return _p(pc[k], V)(c) if k in pc else bag(c)
    out["positional"] = -np.mean([math.log2(pp(i, len(l), c)) for l in test for i, c in enumerate(l)])
    bg = defaultdict(Counter)
    for l in train:
        for a, b in zip(["<s>"] + l, l): bg[a][b] += 1
    out["bigram"] = -np.mean([math.log2(.7 * _p(bg[a], V)(b) + .3 * bag(b)) for l in test for a, b in zip(["<s>"] + l, l)])
    out["hmm"] = hmm_bits(train, test, V)
    return out


def hmm_bits(train, test, V, S=4, iters=25, seed=0):
    voc = sorted({c for l in train + test for c in l}); ix = {c: i for i, c in enumerate(voc)}; M = len(voc)
    rng = np.random.default_rng(seed); A = rng.dirichlet(np.ones(S), S); B = rng.dirichlet(np.ones(M), S); pi = np.ones(S) / S
    tr = [np.array([ix[c] for c in l]) for l in train if l]
    for _ in range(iters):
        An = np.full((S, S), .1); Bn = np.full((S, M), .1); pin = np.full(S, .1)
        for o in tr:
            T = len(o); al = np.zeros((T, S)); be = np.ones((T, S)); c = np.zeros(T)
            al[0] = pi * B[:, o[0]]; c[0] = al[0].sum(); al[0] /= c[0]
            for t in range(1, T): al[t] = (al[t - 1] @ A) * B[:, o[t]]; c[t] = al[t].sum(); al[t] /= c[t]
            for t in range(T - 2, -1, -1): be[t] = (A @ (B[:, o[t + 1]] * be[t + 1])) / c[t + 1]
            g = al * be; pin += g[0]
            for t in range(T): Bn[:, o[t]] += g[t]
            for t in range(T - 1): An += (al[t][:, None] * A * (B[:, o[t + 1]] * be[t + 1])[None, :]) / c[t + 1]
        A = An / An.sum(1, keepdims=True); B = Bn / Bn.sum(1, keepdims=True); pi = pin / pin.sum()
    tot, n = 0.0, 0
    for l in test:
        o = [ix[x] for x in l]; al = pi * B[:, o[0]]; s = al.sum(); tot += math.log2(s); al /= s
        for t in range(1, len(o)): al = (al @ A) * B[:, o[t]]; s = al.sum(); tot += math.log2(s); al /= s
        n += len(o)
    return -tot / n
