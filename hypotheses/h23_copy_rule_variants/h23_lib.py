"""h23: copy-rule variants (PREREG.md). No meaning claims."""
from __future__ import annotations

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h22_italian_cipher_plus_copy"))
import h22_lib as L22  # noqa: E402
from h22_lib import SEG, _edit, _Pools, L20, OPS  # noqa: E402

VARIANTS = ["ref", "heavy", "slot", "swap", "inline", "prevline", "unit"]
LINE = 9


def _pick(ops, rng):
    r = rng.random(); acc = 0
    for op, p in ops:
        acc += p
        if r < acc: return op
    return ops[-1][0]


def _apply(src, op, draw, rng):
    if op == "exact": return src
    for _ in range(4):
        e = _edit(list(SEG(src)), op, draw, rng)
        if e: return "".join(e)
    return src


def copy_variant(toks, labs, c, variant, seed, W=20, line=LINE):
    """Returns (toks, labs, n_altered). Altered tokens get label None."""
    if c <= 0: return list(toks), list(labs), 0
    rng = random.Random(seed); pools = _Pools(); out, ol = [], []; n = 0
    draw = lambda st: pools.draw({"suffix": "final", "prefix": "init", "unigram": "any"}[st], rng)  # noqa: E731
    for i, (t, l) in enumerate(zip(toks, labs)):
        pos = i % line; w = None
        if out and rng.random() < c:
            if variant == "inline":
                cand = out[len(out) - pos:] if pos else []
            elif variant == "prevline":
                s = len(out) - pos; cand = out[max(0, s - line):s]
            else:
                cand = out[-W:]
            if cand:
                src = cand[rng.randrange(len(cand))]
                if variant in ("ref", "inline", "prevline"): w = _apply(src, _pick(OPS, rng), draw, rng)
                elif variant == "heavy":
                    w = src
                    for _ in range(2): w = _apply(w, rng.choice(["suffix", "prefix", "inner"]), draw, rng)
                elif variant == "slot": w = _apply(src, _pick((("suffix", .6), ("prefix", .4)), rng), draw, rng)
                elif variant == "swap":
                    u = list(SEG(src)); w = src
                    for _ in range(6):
                        x = pools.draw("final", rng)
                        if x and x != u[-1]: w = "".join(u[:-1]) + x; break
                elif variant == "unit":
                    u = list(SEG(t)); su = list(SEG(src)); j = rng.randrange(len(u)); x = su[rng.randrange(len(su))]
                    w = "".join(u[:j] + [x] + u[j + 1:])
        if w is None or w == t and variant == "unit":
            out.append(t); ol.append(l)
        else:
            out.append(w); ol.append(None); n += 1
        pools.add(out[-1])
    return out, ol, n


def build(plain, base, codes, naibbe_words, rng, variant, c, seed, r=0.0):
    if base == "syll":
        toks, _ = L20.syllabic_cipher(plain, codes); labs = list(plain)
    else:
        toks = list(naibbe_words); labs = ["#"] * len(toks)
    toks = [str(t) for t in toks]
    if r > 0:
        from collections import Counter
        import numpy as np
        cc = Counter(toks); words = list(cc); p = np.array([cc[w] for w in words], float); p /= p.sum()
        toks, labs = L22.null_insert(toks, labs, r, words, p, rng)
    toks, labs, n = copy_variant(toks, labs, c, variant, seed)
    lines = [toks[i:i + LINE] for i in range(0, len(toks), LINE)]
    return lines, labs, dict(altered_share=n / len(toks))


plaintext_recovery = L22.plaintext_recovery; point_match = L22.point_match
