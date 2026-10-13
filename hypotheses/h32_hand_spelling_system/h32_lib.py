"""h32: context-dependent unit transducer between scribal hands; same-content tests (PREREG.md)."""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h11_hand_language_model"))
import h11_lib as H11  # noqa: E402

UNIT2CH = {"cth": "T", "ckh": "K", "cph": "P", "cfh": "F", "ch": "C", "sh": "S"}
CH2UNIT = {v: k for k, v in UNIT2CH.items()}
_UNIT_RE = re.compile("|".join(sorted(UNIT2CH, key=len, reverse=True)))
jsd = H11.jsd


def enc(w: str) -> str:
    """collapsed EVA units -> one char per unit"""
    return _UNIT_RE.sub(lambda m: UNIT2CH[m.group(0)], w)


def dec(s: str) -> str:
    return "".join(CH2UNIT.get(c, c) for c in s)


def enc_counter(c: Counter) -> Counter:
    out = Counter()
    for w, k in c.items(): out[enc(w)] += k
    return out


# ------------------------------------------------------------------ data
def load():
    """pages table (h11), page word bags, page token sequences (P/C/R loci in file order)."""
    q, bags = H11.load()
    lo = H11.H10.H9.parse(); seqs = defaultdict(list)
    for r in lo.itertuples():
        if r.gtype in ("P", "C", "R"): seqs[r.folio].extend(r.words)
    return q, bags, dict(seqs)


def pages(q, hl, section):
    return list(q[(q.HL == hl) & (q.section == section)].page)


# ------------------------------------------------------------------ edit alignment
def lev(a: str, b: str) -> int:
    return _lev(a, b)


@lru_cache(maxsize=None)
def _lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def align_ops(a: str, b: str):
    """edit blocks turning a into b: list of (start, end, replacement) on a (contiguous edits merged)."""
    n, m = len(a), len(b); D = np.zeros((n + 1, m + 1), int); D[:, 0] = range(n + 1); D[0, :] = range(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = min(D[i - 1, j] + 1, D[i, j - 1] + 1, D[i - 1, j - 1] + (a[i - 1] != b[j - 1]))
    i, j, path = n, m, []
    while i or j:
        if i and j and D[i, j] == D[i - 1, j - 1] + (a[i - 1] != b[j - 1]):
            path.append((i - 1, i, b[j - 1], a[i - 1] == b[j - 1])); i -= 1; j -= 1
        elif i and D[i, j] == D[i - 1, j] + 1:
            path.append((i - 1, i, "", False)); i -= 1
        else:
            path.append((i, i, b[j - 1], False)); j -= 1
    path.reverse(); blocks = []; cur = None
    for s, e, t, same in path:
        if same:
            if cur: blocks.append(cur); cur = None
            continue
        cur = [s, e, t] if cur is None else [cur[0], e, cur[2] + t]
    if cur: blocks.append(cur)
    return [tuple(b) for b in blocks]


# ------------------------------------------------------------------ rules
class Rule:
    """L s R -> t on '^word$' strings; L/R may be '' (no context)."""
    __slots__ = ("L", "s", "R", "t", "rx")

    def __init__(self, L, s, R, t):
        self.L, self.s, self.R, self.t = L, s, R, t
        lb = f"(?<={re.escape(L)})" if L else ""; la = f"(?={re.escape(R)})" if R else ""
        self.rx = re.compile(lb + re.escape(s) + la)

    def key(self): return (self.L, self.s, self.R, self.t)

    def apply(self, w: str) -> str:
        return self.rx.sub(self.t, w) if (self.s or self.L or self.R) else w

    def context_free(self): return not self.L and not self.R

    def __repr__(self):
        f = lambda x: dec(x).replace("^", "#").replace("$", "#")
        return f"{f(self.L)}[{f(self.s) or '∅'}→{f(self.t) or '∅'}]{f(self.R)}"


def wrap(c: Counter) -> Counter:
    return Counter({f"^{w}$": k for w, k in c.items()})


def candidates(cB: Counter, cA: Counter, top_src=400, top_tgt=1500, max_d=2, n_keep=200, context=True):
    """edit blocks from nearest-target alignment of frequent source types, with their contexts."""
    T = [w for w, _ in cA.most_common(top_tgt)]; Aset = set(cA); byl = defaultdict(list)
    for w in T: byl[len(w)].append(w)
    score = Counter()
    for b, k in cB.most_common(top_src):
        if b in Aset and cA[b] >= cB[b] * 0.5: continue
        best = None
        for L in range(len(b) - max_d, len(b) + max_d + 1):
            for a in byl.get(L, ()):
                d = lev(b, a)
                if 0 < d <= max_d and (best is None or (d, -cA[a]) < (best[0], -cA[best[1]])): best = (d, a)
        if best is None: continue
        wb = f"^{b}$"; wa = f"^{best[1]}$"
        for s, e, t in align_ops(wb, wa):
            src = wb[s:e]
            if len(src) > 3 or len(t) > 3 or "^" in src + t or "$" in src + t: continue
            Lc, Rc = wb[s - 1] if s > 0 else "", wb[e] if e < len(wb) else ""
            ctxs = [(Lc, Rc), (Lc, ""), ("", Rc), ("", "")] if context else [("", "")]
            for L, R in ctxs:
                if not src and not (L and R) and context: continue  # insertions need both sides
                if not src and not context: continue
                score[(L, src, R, t)] += k
    return [Rule(*key) for key, _ in score.most_common(n_keep)]


def rewrite(c: Counter, rules) -> Counter:
    out = Counter()
    for w, k in c.items():
        for r in rules: w = r.apply(w)
        out[w] += k
    return out


def greedy(cB: Counter, cA: Counter, cand, max_rules=30):
    cur = Counter(cB); base = jsd(cur, cA); rules, trace = [], [base]
    for _ in range(max_rules):
        best = None
        for r in cand:
            hit = [w for w in cur if r.rx.search(w)]
            if not hit: continue
            nxt = Counter(cur)
            for w in hit:
                k = nxt.pop(w); nxt[r.apply(w)] += k
            v = jsd(nxt, cA)
            if best is None or v < best[1]: best = (r, v, nxt)
        if best is None or best[1] >= base - 1e-4: break
        rules.append(best[0]); cur = best[2]; base = best[1]; trace.append(base)
    return rules, trace


def split(A, B, seed):
    """identical page halving to h11.gap_closure"""
    rng = np.random.default_rng(seed); A = list(rng.permutation(A)); B = list(rng.permutation(B))
    return A[: len(A) // 2], A[len(A) // 2:], B[: len(B) // 2], B[len(B) // 2:]


def bag(bags, pg) -> Counter:
    return wrap(enc_counter(sum((bags[p] for p in pg), Counter())))


def transducer_closure(bags, A, B, seed=0, max_rules=30, context=True, ks=(1, 5, 10, 20, 30)):
    A1, A2, B1, B2 = split(A, B, seed)
    cA1, cA2, cB1, cB2 = bag(bags, A1), bag(bags, A2), bag(bags, B1), bag(bags, B2)
    cand = full_candidates(cB1, cA1, context=context)
    rules, _ = greedy(cB1, cA1, cand, max_rules)
    before = jsd(cB2, cA2); out = dict(js_before=before, n_rules=len(rules))
    for k in ks:
        out[f"closed_{k}"] = (before - jsd(rewrite(cB2, rules[:k]), cA2)) / before
    out["rules"] = " ; ".join(map(repr, rules))
    return out, rules


# ------------------------------------------------------------------ Smith-Waterman
def map_tokens(tokens, rules):
    out = []
    for w in tokens:
        s = f"^{enc(w)}$"
        for r in rules: s = r.apply(s)
        out.append(s[1:-1])
    return out


def score_matrix(x, y, match=2.0, near=1.0, mis=-1.0):
    S = np.full((len(x), len(y)), mis)
    for i, a in enumerate(x):
        for j, b in enumerate(y):
            if a == b: S[i, j] = match
            elif abs(len(a) - len(b)) <= 1 and lev(a, b) == 1: S[i, j] = near
    return S


def sw_batch(S, gap=-2.0):
    """S: (batch, n, m) -> best local alignment score per batch item (linear gap)."""
    bsz, n, m = S.shape; prev = np.zeros((bsz, m + 1)); best = np.zeros(bsz)
    for i in range(n):
        cur = np.zeros((bsz, m + 1)); diag = prev[:, :-1] + S[:, i, :]; up = prev[:, 1:] + gap
        base = np.maximum(0, np.maximum(diag, up))
        for j in range(1, m + 1):
            cur[:, j] = np.maximum(base[:, j - 1], cur[:, j - 1] + gap)
        best = np.maximum(best, cur.max(1)); prev = cur
    return best


def sw_test(x, y, n_shuf=200, seed=0):
    S = score_matrix(x, y); rng = np.random.default_rng(seed)
    perms = np.stack([np.arange(len(x))] + [rng.permutation(len(x)) for _ in range(n_shuf)])
    sc = sw_batch(S[perms]); obs = sc[0]
    return obs, float((1 + np.sum(sc[1:] >= obs)) / (1 + n_shuf)), float(sc[1:].mean())


def bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p); q = np.empty(n)
    q[o] = np.minimum.accumulate((p[o] * n / np.arange(1, n + 1))[::-1])[::-1]
    return np.minimum(q, 1)


def h11_candidates(cB: Counter, cA: Counter):
    """h11's positional n-gram candidates expressed as unit rules (so the transducer nests h11's rule space)."""
    strip = lambda c: Counter({w[1:-1]: k for w, k in c.items()})
    out = []
    for pos, s, t in H11.candidate_rules(strip(cB), strip(cA)):
        if pos == "end": out.append(Rule("", s, "$", t))
        elif pos == "start": out.append(Rule("^", s, "", t))
        else: out.append(Rule("", s, "", t))
    return out


def full_candidates(cB, cA, context=True):
    c = candidates(cB, cA, top_src=800, max_d=3, n_keep=600, context=context)
    if context: c += h11_candidates(cB, cA)
    seen, out = set(), []
    for r in c:
        if r.key() not in seen and (r.s or r.t): seen.add(r.key()); out.append(r)
    return out
