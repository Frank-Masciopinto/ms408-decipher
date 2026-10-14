"""h34: per-hand word-gap rule layered on generators (PREREG.md). Statistics only, no meaning claims."""
from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
for p in ("src", "hypotheses/h19_heldout_likelihood", "hypotheses/h20_generators_vs_italian", "hypotheses/h30_line_structure",
          "hypotheses/h31_word_construction", "hypotheses/h33_word_boundary_resegmentation", "hypotheses/h27_plaintext_ablation",
          "hypotheses/h24_neutral_cipher_robustness", "hypotheses/h25_neutral_hybrid_cipher", "hypotheses/h12_per_hand_copy_modify"):
    sys.path.insert(0, str(ROOT / p))
K_LOOK = 10; STRENGTHS = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0); LINE = 9


def pairs(lines, key=lambda w: w[-1]):
    return [(key(l[i]), l[i + 1][0]) for l in lines for i in range(len(l) - 1)]


def fit_table(lines):
    """r(f|l) = P(f|l)/P(f), add-1 smoothed, from within-line adjacent pairs."""
    pr = pairs(lines); A = sorted({a for a, _ in pr}); B = sorted({b for _, b in pr}); j = Counter(pr)
    fb = Counter(b for _, b in pr); pf = {b: (fb[b] + 1) / (len(pr) + len(B)) for b in B}; r = {}
    for a in A:
        na = sum(j[(a, b)] for b in B)
        r[a] = {b: ((j[(a, b)] + 1) / (na + len(B))) / pf[b] for b in B}
    return r


def shuffle_table(r, rng):
    keys = list(r); perm = list(rng.permutation(keys)); return {k: r[p] for k, p in zip(keys, perm)}


def apply_rule(tokens, r, s, rng, all_gaps=False, line=LINE, n_out=None):
    """Emit lines of `line` words; at each gap pick from the next K queued tokens with weight r(f|l)^s."""
    q = list(tokens); out = []; cur = []; prev = None; n_out = n_out or len(q); pos = 0; k = 0
    while k < n_out and pos < len(q):
        use = s > 0 and prev is not None and (cur or all_gaps)
        if use:
            cand = q[pos:pos + K_LOOK]; row = r.get(prev[-1])
            if row is None: j = 0
            else:
                w = np.array([row.get(c[0], 1.0) ** s for c in cand]); j = int(rng.choice(len(cand), p=w / w.sum()))
            if j: q[pos], q[pos + j] = q[pos + j], q[pos]
        t = q[pos]; pos += 1; k += 1; cur.append(t); prev = t
        if len(cur) == line: out.append(cur); cur = []
    if cur: out.append(cur)
    return out


def mi(pr):
    n = len(pr); a = Counter(x for x, _ in pr); b = Counter(y for _, y in pr); j = Counter(pr)
    return sum(c / n * math.log2(c * n / (a[x] * b[y])) for (x, y), c in j.items()) if n else 0.0


def junction(lines, rng, key=lambda w: w[-1], nsh=30):
    lines = [l for l in lines if len(l) >= 2]; obs = mi(pairs(lines, key)); null = []
    for _ in range(nsh): null.append(mi(pairs([list(rng.permutation(l)) for l in lines], key)))
    return float(obs - np.mean(null))


def endings(lines):
    import h31_lib
    seg, _ = h31_lib.seg_affix(Counter(w for l in lines for w in l)); return lambda w: seg[w][1] or "#"


def pmi_table(lines):
    pr = pairs(lines); n = len(pr); a = Counter(x for x, _ in pr); b = Counter(y for _, y in pr); j = Counter(pr)
    return {k: (math.log2(c * n / (a[k[0]] * b[k[1]])), c) for k, c in j.items()}


def table_agreement(gen_lines, ms_lines, min_n=20):
    g = pmi_table(gen_lines); m = pmi_table(ms_lines)
    ks = [k for k, (_, c) in m.items() if c >= min_n]
    x = [m[k][0] for k in ks]; y = [g[k][0] if k in g else -3.0 for k in ks]
    return float(np.corrcoef(x, y)[0, 1]) if len(ks) > 2 else float("nan")


def interior(lines): return [l[1:-1] for l in lines if len(l) >= 4]


def measures(lines, ms_test, rng):
    import h33_lib
    end = endings(lines); toks = [w for l in lines for w in l]
    return dict(J=junction(lines, rng), J_end=junction(lines, rng, key=end), J_edge=junction(interior(lines), rng),
                T=table_agreement(lines, ms_test) if ms_test else None, S=h33_lib.space_predict(lines)["entropy_removed"],
                types5k=len(set(toks[:5000])), n_tokens=len(toks))
