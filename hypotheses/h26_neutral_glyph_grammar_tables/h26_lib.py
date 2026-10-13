"""h26: Naibbe-structure cipher with tables from word-internal glyph grammars (PREREG.md). No meaning claims."""
from __future__ import annotations

import csv
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h25_neutral_hybrid_cipher"))
import h25_lib as L25  # noqa: E402
from h25_lib import MN, GLYPHS, EVA_UNITS  # noqa: E402

RS_BASE = dict(S=6, alpha=0.5, p_fill=0.7)
RS_VAR = {"rs": {}, "loEnt": dict(alpha=0.15), "hiEnt": dict(alpha=3.0), "loose": dict(p_fill=0.45), "rigid": dict(p_fill=0.9), "short": dict(S=4), "long": dict(S=8)}
LENS = dict(unigram=(2, 7), prefix=(2, 3), suffix=(2, 4))


class SlotGrammar:
    def __init__(self, seed, S=6, alpha=.5, p_fill=.7, A=20):
        rng = np.random.default_rng(seed); al = GLYPHS[:A]; self.slots = []
        for _ in range(S):
            k = int(rng.integers(2, 7)); inv = list(rng.choice(al, size=k, replace=False)); p = rng.dirichlet([alpha] * k)
            self.slots.append((inv, p))
        self.p_fill = p_fill; self.rng = rng; self.S = S

    def sample(self, part):
        sl = self.slots if part == "unigram" else self.slots[: math.ceil(self.S / 2)] if part == "prefix" else self.slots[math.ceil(self.S / 2):]
        while True:
            w = "".join(str(self.rng.choice(inv, p=p)) for inv, p in sl if self.rng.random() < self.p_fill)
            if w: return w


class ChainGrammar:
    """glyph-bigram chain trained on segmented words (tuples of units); start '^' and end '$'."""
    def __init__(self, words, seed, mapping=None):
        self.T = defaultdict(Counter)
        for u in words:
            u = [mapping[x] for x in u] if mapping else list(u); s = ["^"] + u + ["$"]
            for a, b in zip(s, s[1:]): self.T[a][b] += 1
        self.rng = random.Random(seed)

    def _walk(self, n_lo, n_hi, end=False):
        for _ in range(200):
            s, out = "^", []
            while True:
                c = self.T[s]; s = self.rng.choices(list(c), weights=list(c.values()))[0]
                if s == "$": break
                out.append(s)
                if len(out) > 12: break
            if end:
                if len(out) >= n_lo: k = self.rng.randint(n_lo, min(n_hi, len(out))); return "".join(out[-k:])
            elif n_lo <= len(out) <= n_hi or (n_hi <= 3 and len(out) >= n_lo):
                return "".join(out[: self.rng.randint(n_lo, n_hi)] if n_hi <= 3 else out)
        return "".join(out) or "?"

    def sample(self, part):
        lo, hi = LENS[part]
        return self._walk(lo, hi, end=(part == "suffix"))


def latin_words():
    sys.path.insert(0, str(ROOT / "src")); from msdecipher.controls_text import load_tokens
    return [tuple(w) for w in (MN.clean_plaintext(t) for t in load_tokens("la_pliny_herbal", 30000)) if w]


def ms_words():
    sys.path.insert(0, str(ROOT / "hypotheses" / "h19_heldout_likelihood")); import run_h19 as R19
    seg = R19.seg_fn("eva"); ms = R19.ms_cells()
    return [tuple(seg(w)) for p in ms["MS_2B"]["pages"] for w in p["words"]]


def make_grammar(kind, seed, cache={}):
    if kind in RS_VAR: return SlotGrammar(5000 + seed, **{**RS_BASE, **RS_VAR[kind]})
    if kind == "lat":
        if "lat" not in cache: cache["lat"] = latin_words()
        letters = sorted({x for w in cache["lat"] for x in w}); g = GLYPHS[:]; random.Random(6000 + seed).shuffle(g)
        return ChainGrammar(cache["lat"], 6100 + seed, dict(zip(letters, g)))
    if kind == "ms":
        if "ms" not in cache: cache["ms"] = ms_words()
        return ChainGrammar(cache["ms"], 6200 + seed)
    raise ValueError(kind)


def write_tables(path, gram):
    rows = []
    for st in ("unigram", "prefix", "suffix"):
        for t in MN.TABLES:
            used = set()
            for l in MN.ALPHABET:
                for _ in range(100):
                    s = gram.sample(st)
                    if s not in used: break
                used.add(s); rows.append((f"{st}_{t}_{l}", s))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["code", "glyphs"]); w.writerows(rows)
    return path


def glyph_units(kind):
    """units used by a grammar's raw tables: made-up glyphs (rs/lat) or EVA units (ms)."""
    return None if kind == "ms" else GLYPHS


def render_map(seed):
    """made-up glyph -> distinct EVA unit (random, not by MS frequency); 20+ glyphs need >= that many units."""
    return L25.eva_render(seed, len(EVA_UNITS))


def grammar_props(words, seg):
    us = [tuple(seg(w)) for w in words]; c = Counter(x for u in us for x in u); n = sum(c.values())
    H1 = -sum(v / n * math.log2(v / n) for v in c.values())
    pos = defaultdict(Counter)
    for u in us:
        for i, x in enumerate(u): pos[min(i, 7)][x] += 1
    Hc = sum(sum(cc.values()) / n * -sum(v / sum(cc.values()) * math.log2(v / sum(cc.values())) for v in cc.values()) for cc in pos.values())
    return dict(H1=H1, rigidity=1 - Hc / H1 if H1 else 0.0, mean_len=float(np.mean([len(u) for u in us])))
