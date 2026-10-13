"""h20: generators and Italian-based encodings vs the MS 408 likelihood fingerprint (PREREG.md). No meaning claims."""
from __future__ import annotations

import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h19_heldout_likelihood")); sys.path.insert(0, str(ROOT / "src"))
import h19_lib as L19  # noqa: E402

VOW = "aeiouàèéìíòóùú"
DELTA = dict(D1=0.10, D2=0.10, D3=0.015, D4=0.10, D5=0.15)


# ---- PCLM: position-conditioned char LM; the short/long flag is generated first (deficient: mass on length-inconsistent strings is lost)
class PosCharLM:
    def __init__(self, order=3, max_pos=8):
        self.n, self.P = order, max_pos

    def _ctx(self, w):
        lg = int(len(w) > 4); s = "^" * (self.n - 1) + w + "$"
        for i in range(self.n - 1, len(s)):
            pos = min(i - (self.n - 1), self.P)
            yield (pos, lg), s[i - self.n + 1:i], s[i]

    def fit(self, words):
        self.c = defaultdict(Counter); alph = set(); cw = Counter(words)
        for w, k in cw.items():
            alph.update(w)
            for (pos, lg), h, ch in self._ctx(w):
                self.c[()][ch] += k
                self.c[(pos,)][ch] += k
                for o in range(0, self.n):
                    self.c[(pos, lg, h[len(h) - o:] if o else "")][ch] += k
        nl = sum(k for w, k in cw.items() if len(w) > 4); N = sum(cw.values()); self.plg = {1: (nl + 1) / (N + 2), 0: (N - nl + 1) / (N + 2)}
        self.V = len(alph) + 2; self.tot = {k: (sum(v.values()), len(v)) for k, v in self.c.items()}; self.cache = {}
        return self

    def _p(self, pos, lg, h, ch):
        N0 = self.tot[()][0]; p = (self.c[()].get(ch, 0) + 1) / (N0 + self.V)
        for key in [(pos,)] + [(pos, lg, h[len(h) - o:] if o else "") for o in range(0, self.n)]:
            t = self.tot.get(key)
            if not t: continue
            C, T = t; p = (self.c[key].get(ch, 0) + T * p) / (C + T)
        return p

    def logp(self, w):
        v = self.cache.get(w)
        if v is None:
            v = math.log2(self.plg[int(len(w) > 4)]) + sum(math.log2(self._p(pos, lg, h, ch)) for (pos, lg), h, ch in self._ctx(w)); self.cache[w] = v
        return v


# ---------------------------------------------------------------- Italian encodings
def syllables(w):
    """rough Italian syllabification: onset consonants + vowel nucleus; trailing consonants join the last syllable."""
    parts = re.findall(rf"[^{VOW}]*[{VOW}]+", w)
    if not parts: return [w]
    rest = w[sum(map(len, parts)):]
    parts[-1] += rest
    return parts


def ms_codes(ms_words, seg, max_n=3):
    """MS within-word unit 1-3-grams ranked by frequency, as EVA strings (distinct)."""
    c = Counter()
    for w in ms_words:
        u = seg(w)
        for n in range(1, max_n + 1):
            for i in range(len(u) - n + 1): c["".join(u[i:i + n])] += 1
    return [g for g, _ in c.most_common()]


def syllabic_cipher(tokens, codes):
    sc = Counter(s for w in tokens for s in syllables(w)); book = {s: codes[i % len(codes)] for i, (s, _) in enumerate(sc.most_common())}
    return [("".join(book[s] for s in syllables(w))) for w in tokens], book


def remove_vowels(w):
    if not w: return w
    out = w[0] + "".join(ch for ch in w[1:] if ch not in VOW)
    return out or w[0]


def suspend(w):
    return w[:3] + w[-1] if len(w) > 5 else w


# ---------------------------------------------------------------- fingerprint
def dstats(bits, glyphs_per_word, lam5):
    word = min(bits[m] for m in ["KN1", "KN2", "KN3", "COPY1", "COPY3"]); char = min(bits["G"], bits["PCLM"])
    return dict(D1=bits["KN1"] - min(bits["KN2"], bits["KN3"]), D2=bits["KN1"] - bits["COPY1"], D3=lam5, D4=word - char, D5=char / glyphs_per_word)


def match(stats, ms_rows):
    out = {}; dist = 0.0
    for k, d in DELTA.items():
        lo = min(r[k] for r in ms_rows) - d; hi = max(r[k] for r in ms_rows) + d; mu = np.mean([r[k] for r in ms_rows])
        out[k] = bool(lo <= stats[k] <= hi); dist += ((stats[k] - mu) / d) ** 2
    out["n_match"] = int(sum(out[k] for k in DELTA)); out["reproduces"] = out["n_match"] == 5; out["distance"] = float(dist)
    return out
