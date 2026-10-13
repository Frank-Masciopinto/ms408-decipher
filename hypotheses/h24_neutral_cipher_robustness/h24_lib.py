"""h24: neutral (non-MS) ciphers and a generic copy layer (PREREG.md). No meaning claims."""
from __future__ import annotations

import random
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h23_copy_rule_variants"))
import h23_lib as L23  # noqa: E402
from h23_lib import L20, OPS  # noqa: E402

# made-up glyph alphabet: Greek + Cyrillic lower-case letters (not EVA, not MS-derived)
GLYPHS = [chr(c) for c in range(0x3B1, 0x3CA) if c != 0x3C2] + [chr(c) for c in range(0x430, 0x450)] + [chr(c) for c in range(0x4E0, 0x500, 2)] + [chr(c) for c in range(0x561, 0x587)]
CIPHERS = ["homo2", "homo4", "verb8", "verb12", "nomen", "verb8null"]


def clean(words):
    out = []
    for w in words:
        w = "".join(ch for ch in unicodedata.normalize("NFKD", str(w).lower()) if "a" <= ch <= "z")
        if w: out.append(w)
    return out


def _codebook(letters, A, rng, lo=1, hi=3):
    al = GLYPHS[:A]; book, used = {}, set()
    for l in letters:
        while True:
            s = "".join(rng.choice(al) for _ in range(rng.randint(lo, hi)))
            if s not in used: used.add(s); book[l] = s; break
    return book


def encipher(plain, cipher, seed):
    """plain: cleaned words. Returns cipher tokens (one per plaintext word)."""
    rng = random.Random(seed); letters = sorted({ch for w in plain for ch in w})
    if cipher.startswith("homo"):
        K = int(cipher[4:]); g = GLYPHS[:]; rng.shuffle(g); assert len(g) >= K * len(letters)
        tab = {l: g[i * K:(i + 1) * K] for i, l in enumerate(letters)}
        return ["".join(rng.choice(tab[ch]) for ch in w) for w in plain]
    if cipher.startswith("verb"):
        A = int(cipher[4:].replace("null", "")); book = _codebook(letters, A, rng)
        return ["".join(book[ch] for ch in w) for w in plain]
    if cipher == "nomen":
        book = _codebook(letters, 10, rng); top = [w for w, _ in Counter(plain).most_common(100)]
        al = GLYPHS[:10]; codes, used = {}, set(book.values())
        for w in top:
            while True:
                s = "".join(rng.choice(al) for _ in range(rng.randint(2, 4)))
                if s not in used: used.add(s); codes[w] = s; break
        return [codes.get(w) or "".join(book[ch] for ch in w) for w in plain]
    raise ValueError(cipher)


class _CPools:
    def __init__(self, seg): self.seg = seg; self.c = {k: Counter() for k in ("init", "final", "any")}

    def add(self, w):
        u = self.seg(w)
        if not u: return
        self.c["init"][u[0]] += 1; self.c["final"][u[-1]] += 1
        for x in u: self.c["any"][x] += 1

    def draw(self, kind, rng):
        c = self.c[kind]
        return rng.choices(list(c), weights=list(c.values()))[0] if c else None


def _edit(u, op, draw, rng):
    """generic: suffix = last unit, prefix = first unit, inner = any unit; replace / add / remove."""
    u = list(u); kind = rng.choice(("replace", "add", "remove"))
    if op in ("suffix", "prefix"):
        if kind == "remove" and len(u) > 1: return u[:-1] if op == "suffix" else u[1:]
        x = draw("final" if op == "suffix" else "init")
        if x is None: return None
        if op == "suffix": return u[:-1] + [x] if kind == "replace" else u + [x]
        return [x] + u[1:] if kind == "replace" else [x] + u
    x = draw("any"); j = rng.randrange(len(u))
    return None if x is None else u[:j] + [x] + u[j + 1:]


def copy_variant(toks, labs, c, variant, seed, seg=tuple, W=20, line=9):
    if c <= 0: return list(toks), list(labs), 0
    rng = random.Random(seed); pools = _CPools(seg); out, ol = [], []; n = 0
    draw = lambda k: pools.draw(k, rng)  # noqa: E731
    for i, (t, l) in enumerate(zip(toks, labs)):
        pos = i % line; w = None
        if out and rng.random() < c:
            cand = (out[len(out) - pos:] if pos else []) if variant == "inline" else out[-W:]
            if cand:
                src = cand[rng.randrange(len(cand))]; su = list(seg(src))
                if variant == "inline":
                    op = L23._pick(OPS, rng); w = src
                    if op != "exact":
                        for _ in range(4):
                            e = _edit(su, op, draw, rng)
                            if e: w = "".join(e); break
                elif variant == "swap":
                    w = src
                    for _ in range(6):
                        x = pools.draw("final", rng)
                        if x and x != su[-1]: w = "".join(su[:-1]) + x; break
                elif variant == "unit":
                    u = list(seg(t)); j = rng.randrange(len(u)); w = "".join(u[:j] + [su[rng.randrange(len(su))]] + u[j + 1:])
                    if w == t: w = None
        if w is None: out.append(t); ol.append(l)
        else: out.append(w); ol.append(None); n += 1
        pools.add(out[-1])
    return out, ol, n


def add_nulls(toks, labs, r, rng):
    cc = Counter(toks); words = list(cc); p = np.array([cc[w] for w in words], float); p /= p.sum()
    sys.path.insert(0, str(ROOT / "hypotheses" / "h22_italian_cipher_plus_copy")); import h22_lib
    return h22_lib.null_insert(toks, labs, r, words, p, rng)


def tci(x):
    x = np.asarray(x, float); n = len(x)
    if n < 2: return (float(x.mean()), float("nan"), float("nan"))
    from scipy import stats
    h = stats.t.ppf(.975, n - 1) * x.std(ddof=1) / np.sqrt(n); return (float(x.mean()), float(x.mean() - h), float(x.mean() + h))
