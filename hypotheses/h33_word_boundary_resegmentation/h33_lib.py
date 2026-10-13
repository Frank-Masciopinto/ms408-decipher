"""h33: word-boundary resegmentation (PREREG.md). Statistics only, no meaning claims."""
from __future__ import annotations

import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
for p in ("src", "hypotheses/h19_heldout_likelihood", "hypotheses/h30_line_structure", "hypotheses/h31_word_construction"):
    sys.path.insert(0, str(ROOT / p))
TRANSFORMS = ["orig", "join2", "shift+1", "shift+2", "shift-1", "shift-2", "morf"]


# ------------------------------------------------------------------ transforms (one line = list of words)
def join2(line): return ["".join(line[i:i + 2]) for i in range(0, len(line), 2)]


def shift(line, k):
    """k>0: last k glyphs of each word move to the next word; k<0: first |k| glyphs of the next word move back."""
    w = list(line)
    for i in range(len(w) - 1):
        if k > 0:
            t = w[i][-k:] if len(w[i]) > k else w[i][1:]; w[i] = w[i][:len(w[i]) - len(t)]; w[i + 1] = t + w[i + 1]
        else:
            t = w[i + 1][:-k] if len(w[i + 1]) > -k else w[i + 1][:-1]; w[i] = w[i] + t; w[i + 1] = w[i + 1][len(t):]
    return [x for x in w if x]


def morf_lines(lines, seed=0):
    import morfessor
    random.seed(seed); s = ["".join(l) for l in lines]
    m = morfessor.BaselineModel(); m.load_data([(1, x) for x in Counter(s)]); m.train_batch()
    return [m.viterbi_segment(x)[0] for x in s]


def transform(lines, name):
    if name == "orig": return [list(l) for l in lines]
    if name == "join2": return [join2(l) for l in lines]
    if name == "morf": return morf_lines(lines)
    return [shift(l, int(name[5:])) for l in lines]


# ------------------------------------------------------------------ metrics
def ttr(units, n=5000): u = units[:n]; return len(set(u)) / max(len(u), 1)


def zipf(units, top=500):
    f = np.array(sorted(Counter(units).values(), reverse=True)[:top], float); r = np.arange(1, len(f) + 1)
    return float(np.polyfit(np.log(r), np.log(f), 1)[0])


def morphs_per_type(units):
    import h31_lib
    ty = Counter(units); seg, _ = h31_lib.seg_morfessor(ty)
    return len({m for w in ty for m in seg[w][2]}) / len(ty)


def mi(pairs):
    n = len(pairs); a = Counter(x for x, _ in pairs); b = Counter(y for _, y in pairs); j = Counter(pairs)
    return sum(c / n * math.log2(c * n / (a[x] * b[y])) for (x, y), c in j.items()) if n else 0.0


def junction(lines, rng, nsh=50):
    pr = lambda L: [(l[i][-1], l[i + 1][0]) for l in L for i in range(len(l) - 1)]
    obs = mi(pr(lines)); null = []
    for _ in range(nsh):
        sh = []
        for l in lines: l = list(l); rng.shuffle(l); sh.append(l)
        null.append(mi(pr(sh)))
    return float(obs - np.mean(null))


def ngram_gain(lines, k=5):
    import h19_lib as H
    n = len(lines); fl = [min(k - 1, i * k // n) for i in range(n)]; b1 = b3 = 0.0; N = 0
    for f in range(k):
        tr = [l for l, x in zip(lines, fl) if x != f]; te = [l for l, x in zip(lines, fl) if x == f]
        G = H.CharLM(4).fit([w for l in tr for w in l]); K1 = H.KN(1, G).fit(tr); K3 = H.KN(3, G).fit(tr)
        for l in te:
            for i, w in enumerate(l): b1 -= K1.logp(w, l[:i]); b3 -= K3.logp(w, l[:i]); N += 1
    return float((b1 - b3) / N), float(b3 / N)


def space_predict(lines, k=5):
    """Predict boundary at each inter-glyph slot of space-stripped lines from 2 glyphs left + 2 right."""
    data = []
    for l in lines:
        s = "".join(l); cut = set(np.cumsum([len(w) for w in l])[:-1]); s2 = "##" + s + "##"
        data.append([(s2[i:i + 2], s2[i + 2:i + 4], int(i in cut)) for i in range(1, len(s))])
    n = len(data); fl = [min(k - 1, i * k // n) for i in range(n)]; Hb = Hc = 0.0; tp = fp = fn = 0; N = 0
    for f in range(k):
        tr = [x for d, q in zip(data, fl) if q != f for x in d]; te = [x for d, q in zip(data, fl) if q == f for x in d]
        p0 = (sum(y for *_, y in tr) + 1) / (len(tr) + 2)
        cs = [defaultdict(lambda: [0, 0]) for _ in range(4)]
        keys = lambda L, R: [(L, R), (L[1], R), (L, R[0]), (L[1], R[0])]
        for L, R, y in tr:
            for c, kk in zip(cs, keys(L, R)): c[kk][y] += 1
        for L, R, y in te:
            p = p0
            for c, kk in zip(reversed(cs), reversed(keys(L, R))):   # back-off chain: coarse -> fine
                if kk in c: a, b = c[kk]; p = (b + 2 * p) / (a + b + 2)
            p = min(max(p, 1e-6), 1 - 1e-6)
            Hc -= math.log2(p if y else 1 - p); Hb -= math.log2(p0 if y else 1 - p0); N += 1
            g = p > .5; tp += g and y; fp += g and not y; fn += (not g) and y
    return dict(entropy_removed=float(1 - Hc / Hb), f1=float(2 * tp / max(2 * tp + fp + fn, 1)), boundary_rate=float(p0))


def all_metrics(lines, rng, morph=True):
    u = [w for l in lines for w in l]; g, b3 = ngram_gain(lines)
    return dict(n_units=len(u), mean_len=float(np.mean([len(w) for w in u])), M1_ttr=ttr(u), M2_zipf=zipf(u),
                M3_morphs_per_type=morphs_per_type(u) if morph else None, M4_ngram_gain=g, M4_trigram_bits=b3, M5_junction=junction(lines, rng))
