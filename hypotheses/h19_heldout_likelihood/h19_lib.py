"""h19: held-out likelihood comparison of mechanisms (PREREG.md). Pure-python models; no meaning claims.

Every model scores a token as log2 P(w_t | earlier tokens on the same page)."""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
try:
    from rapidfuzz.distance import Levenshtein as _LV
except ImportError:  # pragma: no cover - slow pure-python fallback
    _LV = None

LOG2 = math.log(2)
ONSETS = ("d", "s", "t", "p", "k", "f")


# ---------------------------------------------------------------- char LM (Witten-Bell, order 4)
class CharLM:
    def __init__(self, order: int = 4):
        self.n = order

    def fit(self, words):
        self.c = [defaultdict(Counter) for _ in range(self.n)]
        cw = Counter(words)
        alph = set()
        for w, k in cw.items():
            s = "^" * (self.n - 1) + w + "$"; alph.update(w)
            for i in range(self.n - 1, len(s)):
                for o in range(self.n):
                    self.c[o][s[i - o:i]][s[i]] += k
        self.V = len(alph) + 2  # + end + unknown
        self.N0 = sum(self.c[0][""].values())
        self.tot = [{h: (sum(v.values()), len(v)) for h, v in co.items()} for co in self.c]
        self.cache = {}
        return self

    def _p(self, h, ch):
        p = (self.c[0][""].get(ch, 0) + 1) / (self.N0 + self.V)
        for o in range(1, self.n):
            hh = h[len(h) - o:]
            t = self.tot[o].get(hh)
            if not t: continue
            C, T = t
            p = (self.c[o][hh].get(ch, 0) + T * p) / (C + T)
        return p

    def logp(self, w):
        v = self.cache.get(w)
        if v is None:
            s = "^" * (self.n - 1) + w + "$"
            v = sum(math.log2(self._p(s[i - self.n + 1:i], s[i])) for i in range(self.n - 1, len(s)))
            self.cache[w] = v
        return v


# ---------------------------------------------------------------- interpolated Kneser-Ney (n = 1..3) over G
class KN:
    def __init__(self, n: int, G: CharLM, d: float = 0.75):
        self.n, self.G, self.d = n, G, d

    def fit(self, pages):
        self.c1 = Counter(); self.c2 = Counter(); self.c3 = Counter()
        for ws in pages:
            s = ["<s>", "<s>"] + list(ws)
            for i in range(2, len(s)):
                self.c1[s[i]] += 1; self.c2[(s[i - 1], s[i])] += 1; self.c3[(s[i - 2], s[i - 1], s[i])] += 1
        self.N = sum(self.c1.values()); self.T = len(self.c1)
        # continuation counts
        self.cc1 = Counter(w for (_, w) in self.c2)                     # N1+(. w)
        self.cc1_tot = len(self.c2)
        self.cc2 = Counter((v, w) for (_, v, w) in self.c3)             # N1+(. v w)
        self.ctx2 = Counter(); self.ctx2_types = Counter()               # for level-2 as top (raw) and as middle (cont.)
        for (v, w), k in self.c2.items(): self.ctx2[v] += k; self.ctx2_types[v] += 1
        self.cc2_ctx = Counter(); self.cc2_types = Counter()
        for (v, w), k in self.cc2.items(): self.cc2_ctx[v] += k; self.cc2_types[v] += 1
        self.ctx3 = Counter(); self.ctx3_types = Counter()
        for (u, v, w), k in self.c3.items(): self.ctx3[(u, v)] += k; self.ctx3_types[(u, v)] += 1
        return self

    def p1(self, w, cont):
        g = 2.0 ** self.G.logp(w)
        if cont:
            return max(self.cc1.get(w, 0) - self.d, 0) / self.cc1_tot + self.d * len(self.cc1) / self.cc1_tot * g
        return max(self.c1.get(w, 0) - self.d, 0) / self.N + self.d * self.T / self.N * g

    def p2(self, v, w, cont):
        lo = self.p1(w, True)
        if cont:
            C = self.cc2_ctx.get(v, 0)
            return lo if C == 0 else max(self.cc2.get((v, w), 0) - self.d, 0) / C + self.d * self.cc2_types[v] / C * lo
        C = self.ctx2.get(v, 0)
        return lo if C == 0 else max(self.c2.get((v, w), 0) - self.d, 0) / C + self.d * self.ctx2_types[v] / C * lo

    def prob(self, w, hist):
        h = ["<s>", "<s>"] + list(hist[-2:]); u, v = h[-2], h[-1]
        if self.n == 1: return self.p1(w, False)
        if self.n == 2: return self.p2(v, w, False)
        lo = self.p2(v, w, True); C = self.ctx3.get((u, v), 0)
        return lo if C == 0 else max(self.c3.get((u, v, w), 0) - self.d, 0) / C + self.d * self.ctx3_types[(u, v)] / C * lo

    def logp(self, w, hist):
        return math.log2(self.prob(w, hist))


# ---------------------------------------------------------------- copy-and-modify edit channel
def edit_stats(src: str, tgt: str, max_d: int = 3):
    """(nk, ns, nd, ni, gaps, emitted chars) on one optimal alignment, or None if distance > max_d."""
    if _LV is not None:
        if _LV.distance(src, tgt, score_cutoff=max_d) > max_d: return None
        ops = _LV.editops(src, tgt)
        ns = nd = ni = 0; em = []
        for op in ops:
            if op.tag == "replace": ns += 1; em.append(tgt[op.dest_pos])
            elif op.tag == "delete": nd += 1
            else: ni += 1; em.append(tgt[op.dest_pos])
        return len(src) - ns - nd, ns, nd, ni, len(src) + 1, "".join(em)
    raise RuntimeError("rapidfuzz required")  # pragma: no cover


class CopyData:
    """precomputed copy candidates for a list of pages: token arrays + pair arrays (lag <= Wmax, distance <= 3)."""

    def __init__(self, pages, Wmax=100):
        self.tok_page, self.tok_pos, self.words = [], [], []
        P = defaultdict(list); cache = {}
        t = 0
        for pi, ws in enumerate(pages):
            for i, w in enumerate(ws):
                self.tok_page.append(pi); self.tok_pos.append(i); self.words.append(w)
                for lag in range(1, min(Wmax, i) + 1):
                    s = ws[i - lag]; key = (s, w)
                    if key not in cache: cache[key] = edit_stats(s, w)
                    st = cache[key]
                    if st is None: continue
                    P["t"].append(t); P["lag"].append(lag)
                    for k, v in zip(("nk", "ns", "nd", "ni", "gaps"), st[:5]): P[k].append(v)
                    P["em"].append(st[5])
                t += 1
        self.n = t; self.pos = np.array(self.tok_pos)
        self.pairs = {k: np.array(v) for k, v in P.items() if k != "em"}; self.em = P["em"]
        if not len(self.pairs.get("t", [])): self.pairs = {k: np.zeros(0, int) for k in ("t", "lag", "nk", "ns", "nd", "ni", "gaps")}

    def logu(self, lu: dict):
        default = min(lu.values()) if lu else -10
        return np.array([sum(lu.get(c, default) for c in e) for e in self.em]) * LOG2 if self.em else np.zeros(0)


def char_unigram_log(words):
    c = Counter(ch for w in words for ch in w); n = sum(c.values()); V = len(c) + 1
    return {ch: math.log((k + 1) / (n + V)) for ch, k in c.items()}


def copy_em(base_lp2, cd: CopyData, lu, W, iters=100, init=None, tok_weight=None):
    """EM for lambda + edit channel. base_lp2: log2 base prob per token. Returns params, total log2-lik."""
    pr = cd.pairs; m = pr["lag"] <= W if len(pr["lag"]) else np.zeros(0, bool)
    t = pr["t"][m]; nk, ns, nd, ni, gp = (pr[k][m].astype(float) for k in ("nk", "ns", "nd", "ni", "gaps"))
    logu = cd.logu(lu)[m] if len(m) else np.zeros(0)
    k = np.minimum(cd.pos, W).astype(float); hasH = k > 0
    w = np.ones(cd.n) if tok_weight is None else tok_weight
    lb = np.asarray(base_lp2) * LOG2
    th = dict(lam=.1, pk=.8, ps=.1, pd=.1, pi=.05) if init is None else dict(init)
    ll = -np.inf
    for _ in range(iters):
        le = nk * np.log(th["pk"]) + ns * np.log(th["ps"]) + nd * np.log(th["pd"]) + ni * np.log(th["pi"]) + gp * np.log(1 - th["pi"]) + logu
        lc = np.log(th["lam"]) - np.log(np.maximum(k[t], 1)) + le
        fresh = np.where(hasH, np.log(1 - th["lam"]), 0.0) + lb
        mx = np.maximum.reduceat if False else None
        # log-sum-exp per token over fresh + its pairs
        top = fresh.copy(); np.maximum.at(top, t, lc)
        S = np.exp(fresh - top); np.add.at(S, t, np.exp(lc - top[t]))
        tot = top + np.log(S)
        new_ll = float((w * tot).sum() / LOG2)
        rc = np.exp(lc - tot[t]) * w[t]
        Rc = rc.sum(); Rf_h = (w * np.exp(fresh - tot))[hasH].sum()
        lam = Rc / max(Rc + Rf_h, 1e-12)
        a = np.array([(rc * nk).sum(), (rc * ns).sum(), (rc * nd).sum()]) + 1e-3
        a /= a.sum(); pi = ((rc * ni).sum() + 1e-3) / ((rc * (ni + gp)).sum() + 2e-3)
        th = dict(lam=float(np.clip(lam, 1e-6, 1 - 1e-6)), pk=float(a[0]), ps=float(a[1]), pd=float(a[2]), pi=float(np.clip(pi, 1e-6, .99)))
        if abs(new_ll - ll) < 1e-6 * max(1, abs(new_ll)): ll = new_ll; break
        ll = new_ll
    return th, ll


def copy_score(base_lp2, cd: CopyData, lu, W, th):
    pr = cd.pairs; m = pr["lag"] <= W if len(pr["lag"]) else np.zeros(0, bool)
    t = pr["t"][m]; nk, ns, nd, ni, gp = (pr[k][m].astype(float) for k in ("nk", "ns", "nd", "ni", "gaps"))
    logu = cd.logu(lu)[m] if len(m) else np.zeros(0)
    k = np.minimum(cd.pos, W).astype(float); hasH = k > 0
    le = nk * np.log(th["pk"]) + ns * np.log(th["ps"]) + nd * np.log(th["pd"]) + ni * np.log(th["pi"]) + gp * np.log(1 - th["pi"]) + logu
    P = np.where(hasH, 1 - th["lam"], 1.0) * 2.0 ** np.asarray(base_lp2)
    np.add.at(P, t, th["lam"] / np.maximum(k[t], 1) * np.exp(le))
    return np.log2(P)


# ---------------------------------------------------------------- Naibbe cipher likelihood
class LetterLM:
    def __init__(self, order=3):
        self.n = order

    def fit(self, letters: str):
        self.c = [defaultdict(Counter) for _ in range(self.n)]
        for i in range(len(letters)):
            for o in range(self.n):
                if i - o < 0: break
                self.c[o][letters[i - o:i]][letters[i]] += 1
        self.alph = sorted(self.c[0][""]); self.N0 = sum(self.c[0][""].values())
        self.tot = [{h: (sum(v.values()), len(v)) for h, v in co.items()} for co in self.c]; self.cache = {}
        return self

    def p(self, h, ch):
        key = (h, ch); v = self.cache.get(key)
        if v is not None: return v
        p = (self.c[0][""].get(ch, 0) + 1) / (self.N0 + len(self.alph) + 1)
        for o in range(1, self.n):
            hh = h[len(h) - o:] if len(h) >= o else None
            if hh is None: break
            t = self.tot[o].get(hh)
            if not t: continue
            C, T = t; p = (self.c[o][hh].get(ch, 0) + T * p) / (C + T)
        self.cache[key] = p
        return p


class NaibbeLM:
    def __init__(self, plain: LetterLM, deck=78):
        from msdecipher.mech_naibbe import CARD_WEIGHTS, NaibbeCipher, P_UNIGRAM_STANDARD, TABLES, ALPHABET
        c = NaibbeCipher(deck=deck); wts = CARD_WEIGHTS[deck]; Z = sum(wts.values()); pi = {t: wts[t] / Z for t in TABLES}
        self.pu = P_UNIGRAM_STANDARD; self.plain = plain
        self.uni = defaultdict(Counter); self.bi = defaultdict(Counter)
        for t in TABLES:
            for L in ALPHABET: self.uni[c.glyph[("unigram", t, L)]][L] += pi[t]
        pre = defaultdict(Counter); suf = defaultdict(Counter)
        for t in TABLES:
            for L in ALPHABET:
                pre[c.glyph[("prefix", t, L)]][L] += pi[t]; suf[c.glyph[("suffix", t, L)]][L] += pi[t]
        for gp, dp in pre.items():
            for gs, ds in suf.items():
                for L1, a in dp.items():
                    for L2, b in ds.items(): self.bi[gp + gs][(L1, L2)] += a * b

    def decodable(self, w):
        return w in self.uni or w in self.bi

    def page_probs(self, ws):
        """P_N(w_t | letters of previous decoded words on page); 0 when undecodable. Context = argmax decoding, reset on failure."""
        out = []; ctx = ""
        for w in ws:
            best, bl, tot = 0.0, None, 0.0
            for L, a in self.uni.get(w, {}).items():
                q = self.pu * a * self.plain.p(ctx[-2:], L); tot += q
                if q > best: best, bl = q, L
            for (L1, L2), a in self.bi.get(w, {}).items():
                q = (1 - self.pu) * a * self.plain.p(ctx[-2:], L1) * self.plain.p((ctx + L1)[-2:], L2); tot += q
                if q > best: best, bl = q, L1 + L2
            out.append(tot); ctx = (ctx + bl)[-2:] if bl else ""
        return np.array(out)


def mix_em(lp_a, lp_b, iters=200):
    """weight eps of component b in (1-eps) A + eps B by EM; inputs log2 probs (A may be -inf)."""
    a = 2.0 ** np.asarray(lp_a); b = 2.0 ** np.asarray(lp_b); e = .1
    for _ in range(iters):
        r = e * b / ((1 - e) * a + e * b); e2 = float(np.clip(r.mean(), 1e-6, 1 - 1e-6))
        if abs(e2 - e) < 1e-8: break
        e = e2
    return e


# ---------------------------------------------------------------- line-start onset feature
def onset_parts(w):
    for o in ONSETS:
        if w.startswith(o) and len(w) - len(o) >= 2: return o, w[len(o):]
    return None, None


def onset_em(lp_w, lp_b, onset_ids, iters=200):
    """P' = (1-th) P(w) + th * pi_o * P(b) for tokens with an onset (others: (1-th) P(w)). Returns th, pi."""
    a = 2.0 ** np.asarray(lp_w); b = np.where(onset_ids >= 0, 2.0 ** np.asarray(lp_b), 0.0); K = len(ONSETS)
    th, pi = .1, np.full(K, 1 / K)
    for _ in range(iters):
        q = th * pi[np.maximum(onset_ids, 0)] * b; den = (1 - th) * a + q; r = np.where(onset_ids >= 0, q / den, 0.0)
        th2 = float(np.clip(r.mean(), 1e-6, 1 - 1e-6)); pi2 = np.bincount(onset_ids[onset_ids >= 0], weights=r[onset_ids >= 0], minlength=K) + 1e-6
        pi2 /= pi2.sum()
        if abs(th2 - th) < 1e-8: th, pi = th2, pi2; break
        th, pi = th2, pi2
    return th, pi


def onset_score(lp_w, lp_b, onset_ids, th, pi):
    a = 2.0 ** np.asarray(lp_w); b = np.where(onset_ids >= 0, 2.0 ** np.asarray(lp_b), 0.0)
    return np.log2((1 - th) * a + th * pi[np.maximum(onset_ids, 0)] * b)
