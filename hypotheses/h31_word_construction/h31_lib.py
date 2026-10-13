"""h31: unsupervised morphology of MS 408 vs natural and generated controls (PREREG.md). No meaning claims."""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "hypotheses" / "h19_heldout_likelihood"))


# ------------------------------------------------------------------ segmenters -> {type: (stem, suffix, morphs)}
def seg_morfessor(types: Counter, seed=0):
    import morfessor
    import random
    random.seed(seed)
    m = morfessor.BaselineModel(); m.load_data([(1, w) for w in types]); m.train_batch()
    out = {}
    for w in types:
        ms = m.viterbi_segment(w)[0]
        out[w] = ("".join(ms[:-1]), ms[-1], ms) if len(ms) > 1 else (w, "", ms)
    return out, m


class BayesStemSuffix:
    """Collapsed Gibbs over split points; DP(alpha) priors on stems and suffixes; base = geom(len) x char unigram."""

    def __init__(self, alpha=1.0, p_len=0.5, sweeps=300, seed=0):
        self.a, self.pl, self.sweeps, self.rng = alpha, p_len, sweeps, np.random.default_rng(seed)

    def base(self, s, empty_ok):
        if not s: return self.pe if empty_ok else 0.0
        v = (1 - self.pe if empty_ok else 1.0) * self.pl * (1 - self.pl) ** (len(s) - 1)
        for c in s: v *= self.cu.get(c, 1e-6)
        return v

    def fit(self, types):
        self.types = list(types); ch = Counter("".join(self.types)); n = sum(ch.values()); self.cu = {c: k / n for c, k in ch.items()}
        self.pe = 0.3
        self.split = {w: int(self.rng.integers(1, len(w) + 1)) for w in self.types}
        self.S, self.X = Counter(), Counter()
        for w, k in self.split.items(): self.S[w[:k]] += 1; self.X[w[k:]] += 1
        for _ in range(self.sweeps):
            for w in self.rng.permutation(self.types):
                k = self.split[w]; self.S[w[:k]] -= 1; self.X[w[k:]] -= 1
                ns = nx = len(self.types) - 1
                pr = np.array([(self.S[w[:j]] + self.a * self.base(w[:j], False)) / (ns + self.a) *
                               (self.X[w[j:]] + self.a * self.base(w[j:], True)) / (nx + self.a) for j in range(1, len(w) + 1)])
                j = int(self.rng.choice(len(pr), p=pr / pr.sum())) + 1
                self.split[w] = j; self.S[w[:j]] += 1; self.X[w[j:]] += 1
        return self

    def segment(self, w):
        if w in self.split: k = self.split[w]
        else:
            ns, nx = sum(self.S.values()), sum(self.X.values())
            k = 1 + int(np.argmax([(self.S[w[:j]] + self.a * self.base(w[:j], False)) * (self.X[w[j:]] + self.a * self.base(w[j:], True)) for j in range(1, len(w) + 1)]))
        return w[:k], w[k:]


def seg_bayes(types, seed=0, sweeps=300):
    b = BayesStemSuffix(seed=seed, sweeps=sweeps).fit(types)
    return {w: (*b.segment(w), [x for x in b.segment(w) if x]) for w in types}, b


def seg_affix(types):
    from msdecipher.slot_grammar import AffixModel
    m = AffixModel(); m.fit({tuple(w): float(k) for w, k in types.items()})
    out = {}
    for w in types:
        core, p, s = m._best_split(tuple(w)); stem = "".join(p) + "".join(core); suf = "".join(s)
        out[w] = (stem, suf, [x for x in ("".join(p), "".join(core), suf) if x])
    return out, m


# ------------------------------------------------------------------ metrics
def H(c: Counter):
    n = sum(c.values()); p = np.array(list(c.values()), float) / n
    return float(-(p * np.log2(p)).sum())


def mi(pairs):
    j = Counter(pairs); a = Counter(x for x, _ in pairs); b = Counter(y for _, y in pairs)
    return H(a) + H(b) - H(j)


def metrics(tokens, pages, seg, rng, n_null=200):
    st = [seg[w][0] for w in tokens]; sx = [seg[w][1] for w in tokens]
    types = list(dict.fromkeys(tokens)); N = len(tokens)
    morphs = {m for w in types for m in seg[w][2]}
    I1 = len(morphs) / len(types); n_suf = len({seg[w][1] for w in types})
    # P1
    ps = Counter(st); px = Counter(sx)
    a = np.array(list(ps.values()), float) / N; b = np.array(list(px.values()), float) / N
    E = float((1 - (1 - np.outer(a, b)) ** N).sum()); O = len({(seg[w][0], seg[w][1]) for w in types})
    # C1
    obs = mi(list(zip(st, sx))); sxa = np.array(sx, dtype=object)
    nul = [mi(list(zip(st, rng.permutation(sxa)))) for _ in range(n_null)]
    C1 = (obs - np.mean(nul)) / max(H(px), 1e-9); C1z = (obs - np.mean(nul)) / (np.std(nul) + 1e-12)
    # R1
    sets = defaultdict(set)
    for w in types: sets[seg[w][0]].add(seg[w][1])
    multi = {s: frozenset(v) for s, v in sets.items() if len(v) >= 2}
    def reuse(d):
        c = Counter(d.values()); return np.mean([c[v] >= 2 for v in d.values()]) if d else np.nan
    r_obs = reuse(multi); tf = Counter(seg[w][1] for w in types); sufs = list(tf); pw = np.array([tf[s] for s in sufs], float); pw /= pw.sum()
    r_null = [reuse({s: frozenset(rng.choice(sufs, len(v), replace=False, p=pw)) for s, v in multi.items() if len(v) <= len(sufs)}) for _ in range(n_null)]
    R1 = r_obs / np.mean(r_null) if np.mean(r_null) > 0 else float("nan")
    # A1 / A1'
    def adj(key, pg):
        return [(key(p[i]), p[i + 1][0]) for p in pg for i in range(len(p) - 1)]
    def a_excess(key):
        o = mi(adj(key, pages)); nl = [mi(adj(key, [list(rng.permutation(p)) for p in pages])) for _ in range(n_null // 4)]
        return o - np.mean(nl), (o - np.mean(nl)) / (np.std(nl) + 1e-12)
    A1, A1z = a_excess(lambda w: seg[w][1]); A1c, A1cz = a_excess(lambda w: w[-1])
    return dict(I1=I1, n_suffix=n_suf, n_morph=len(morphs), n_types=len(types), P1=O / E, P1_obs=O, P1_exp=E, C1=C1, C1z=C1z,
                R1=R1, R1_obs=r_obs, n_multi_stems=len(multi), A1=A1, A1z=A1z, A1_lastchar=A1c, A1_lastchar_z=A1cz)


# ------------------------------------------------------------------ held-out morph LM
class MorphLM:
    """P(w) = sum over segmentations prod q(m) * (1-rho)^(k-1) rho; q = CRP over token-weighted training morphs, char base."""

    def __init__(self, train_tokens, seg_fn, alpha=1.0, max_k=5):
        self.c = Counter(); ks = []
        for w in train_tokens:
            ms = seg_fn(w); self.c.update(ms); ks.append(len(ms))
        self.N = sum(self.c.values()); self.a = alpha; self.max_k = max_k
        self.rho = 1 / np.mean(ks); ch = Counter("".join(train_tokens)); n = sum(ch.values()); self.cu = {x: k / n for x, k in ch.items()}
        self.V = len(ch) + 1; self.cache = {}

    def base(self, m):
        v = 0.5 ** len(m)
        for x in m: v *= self.cu.get(x, 1 / (len(self.cu) * 100))
        return v

    def q(self, m): return (self.c.get(m, 0) + self.a * self.base(m)) / (self.N + self.a)

    def logp(self, w):
        if w in self.cache: return self.cache[w]
        n = len(w); f = [np.zeros(self.max_k + 1) for _ in range(n + 1)]; f[0][0] = 1.0
        for i in range(1, n + 1):
            for j in range(max(0, i - 12), i):
                qm = self.q(w[j:i])
                f[i][1:] += f[j][:-1] * qm
        tot = sum(f[n][k] * (1 - self.rho) ** (k - 1) * self.rho for k in range(1, self.max_k + 1))
        v = math.log2(max(tot, 1e-300)); self.cache[w] = v; return v
