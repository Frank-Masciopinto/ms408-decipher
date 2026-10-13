"""h22: Italian cipher + generic copy-and-modify layer (PREREG.md). No meaning claims."""
from __future__ import annotations

import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h21_italian_order_breaking_and_cross_hand")); sys.path.insert(0, str(ROOT / "src"))
import h21_lib as L21  # noqa: E402
from h21_lib import L20  # noqa: E402
from msdecipher.mech_hybrid import SEG, _edit, _Pools  # noqa: E402

OPS = (("exact", .30), ("suffix", .35), ("prefix", .15), ("inner", .20))
LINE = 9


def copy_layer(toks, labs, c, W, seed):
    """Replace each token w.p. c by an edited copy of one of the previous W output tokens. Units for edits come
    from pools of the stream itself. Copies get label None."""
    if c <= 0: return list(toks), list(labs), 0
    rng = random.Random(seed); pools = _Pools(); out, ol = [], []; n = 0
    draw = lambda st: pools.draw({"suffix": "final", "prefix": "init", "unigram": "any"}[st], rng)  # noqa: E731
    for t, l in zip(toks, labs):
        if out and rng.random() < c:
            src = out[-1 - rng.randrange(min(W, len(out)))]; r = rng.random(); acc = 0
            for op, p in OPS:
                acc += p
                if r < acc: break
            w = src
            if op != "exact":
                for _ in range(4):
                    e = _edit(list(SEG(src)), op, draw, rng)
                    if e: w = "".join(e); break
            out.append(w); ol.append(None); n += 1
        else:
            out.append(t); ol.append(l)
        pools.add(out[-1])
    return out, ol, n


def null_insert(toks, labs, r, words, p, rng):
    q = r / (1 + r); ot, ol = [], []
    for t, l in zip(toks, labs):
        ot.append(t); ol.append(l); k = rng.geometric(1 - q) - 1
        if k:
            ot += [str(x) for x in rng.choice(words, size=k, p=p)]; ol += [None] * k
    return ot, ol


def build(plain, base, codes, naibbe_words, rng, shuf=False, r=0.0, nulls="clean", ms_nulls=None, c=0.0, W=5, seed=0):
    if base == "syll":
        toks, _ = L20.syllabic_cipher(plain, codes); labs = list(plain)
    else:
        toks = list(naibbe_words); labs = ["#"] * len(toks)
    toks = [str(t) for t in toks]
    if shuf:
        lt, ll = [], []
        for i in range(0, len(toks), LINE):
            perm = rng.permutation(len(toks[i:i + LINE])); lt += [toks[i + j] for j in perm]; ll += [labs[i + j] for j in perm]
        toks, labs = lt, ll
    if r > 0:
        if nulls == "clean":
            cc = Counter(toks); words = list(cc); p = np.array([cc[w] for w in words], float); p /= p.sum()
        else:
            words, p = ms_nulls
        toks, labs = null_insert(toks, labs, r, words, p, rng)
    n_real = len(toks)
    toks, labs, ncopy = copy_layer(toks, labs, c, W, seed)
    sig = sum(l is not None for l in labs) / len(labs)
    lines = [toks[i:i + LINE] for i in range(0, len(toks), LINE)]
    layers = 1 + bool(shuf) + (r > 0) + (c > 0)
    return lines, labs, dict(signal_share=sig, copy_share=ncopy / len(toks), layers=int(layers), n_pre_copy=n_real)


def plaintext_recovery(toks, labs):
    """Oracle upper bound: map each token type to its most frequent aligned plaintext word (∅ for null/copy);
    accuracy over all tokens counts a token correct only if it carries plaintext and is decoded to it.
    MI(token; label) / H(label), with null/copy labelled ∅."""
    lab = [l if l is not None else "∅" for l in labs]; by = defaultdict(Counter)
    for t, l in zip(toks, lab): by[t][l] += 1
    dec = {t: c.most_common(1)[0][0] for t, c in by.items()}
    acc = sum(dec[t] == l and l != "∅" for t, l in zip(toks, lab)) / len(toks)
    n = len(toks); pl = Counter(lab); pt = Counter(toks); pj = Counter(zip(toks, lab))
    H = -sum(v / n * math.log2(v / n) for v in pl.values())
    mi = sum(v / n * math.log2(v * n / (pt[t] * pl[l])) for (t, l), v in pj.items())
    return dict(oracle_acc=acc, mi_bits=mi, H_plain=H, mi_frac=mi / H if H else 0.0)


point_match = L21.point_match
