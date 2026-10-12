"""h14: line-position effects under layout controls (PREREG.md). Distributional only; no meaning claims."""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h13_top_word_context"))
import h13_lib as L13  # noqa: E402

INIT = ["daiin", "dain", "saiin", "sain", "sar", "sol", "y"]
FINAL = ["am", "dam", "dy"]
INIT_DEP = ['aiin', 'ain', 'al', 'ar', 'chckhy', 'chdy', 'chedy', 'cheey', 'chey', 'chol', 'chor', 'chy', 'cthy', 'dal', 'dam', 'dy', 'l', 'ol', 'otal', 'otar', 'r', 's', 'shedy', 'shey']
FINAL_DEP = ['chol', 'chor', 'l', 'o', 'or', 'qokain', 'qokar', 'qokedy', 'qokeedy', 'qokeey', 'qokol', 'shedy', 'sheey', 'sho', 'shol']


def gap_lines():
    s = set()
    for ln in L13.H9.TR.read_text(encoding="utf-8", errors="replace").splitlines():
        m = L13.LOC.match(ln)
        if m and m.group(4) == "P" and "<->" in m.group(6): s.add((m.group(1), int(m.group(2))))
    return s


def table():
    d = L13.token_table(); d = d[d.gtype == "P"].copy()
    d["ulen"] = [len(L13.SEG(w)) for w in d.w]
    d["lid"] = d.folio + "." + d.line.astype(str)
    g = d.groupby("lid"); d["nread"] = g.w.transform("size"); d["glyphs"] = g.ulen.transform("sum")
    first = d[d.pos == 0].set_index("lid").para_initial if "para_initial" in d else None
    pf = d.groupby("lid").para_initial.max(); d["first_line"] = d.lid.map(pf)
    gl = gap_lines(); d["gap"] = [(f, n) in gl for f, n in zip(d.folio, d.line)]
    med = d.drop_duplicates("lid").groupby("folio").nline.median(); d["short"] = d.nline < 0.6 * d.folio.map(med)
    d["gapshort"] = d.gap | d.short
    d["wbin"] = pd.cut(d.nline, [0, 4, 7, 10, 999], labels=["1-4", "5-7", "8-10", "11+"]).astype(str)
    lg = d.drop_duplicates("lid").glyphs; q = np.quantile(lg, [.25, .5, .75])
    d["gbin"] = np.digitize(d.glyphs, q).astype(str)
    d["lbin"] = np.clip(d.ulen, 2, 5).astype(str)
    d["S1"] = d.HL + "|" + d.wbin + "|" + d.gbin + "|" + d.first_line.astype(str) + "|" + d.gapshort.astype(str)
    d["S1L"] = d.S1 + "|" + d.lbin
    d["is_init"] = d.pos == 0; d["is_final"] = d.pos == d.nline - 1
    return d


def strat_null(d, words, slot, strat, n=10000, rng=None):
    """exact permutation null of count(word in slot) when tokens are permuted within strata: sum of hypergeometrics."""
    rng = rng or np.random.default_rng(14); out = {}
    S = d.groupby(strat).agg(N=("w", "size"), m=(slot, "sum"))
    for w in words:
        K = d[d.w == w].groupby(strat).size().reindex(S.index, fill_value=0)
        tot = np.zeros(n)
        for (N, m), k in zip(S[["N", "m"]].values, K.values):
            if k and m: tot += rng.hypergeometric(k, N - k, m, size=n)
        out[w] = (int(d[(d.w == w) & d[slot]].shape[0]), tot)
    return out


def line_null(d, words, slot, n=10000, rng=None):
    return strat_null(d, words, slot, "lid", n, rng)


def mc_p(obs, null):
    mu = null.mean(); return float((1 + np.sum(np.abs(null - mu) >= abs(obs - mu) - 1e-9)) / (len(null) + 1))


def final_length(d, strat="S1", mask=None):
    """observed mean unit length of final tokens vs exact without-replacement null within strata (z)."""
    x = d if mask is None else d[mask]
    g = x.groupby(strat); exp = var = 0.0; n_tot = 0
    for _, s in g:
        m = int(s.is_final.sum()); N = len(s)
        if m == 0: continue
        mu, sd2 = s.ulen.mean(), s.ulen.var(ddof=0)
        exp += m * mu; var += m * sd2 * (N - m) / max(N - 1, 1); n_tot += m
    obs = x[x.is_final].ulen.sum()
    return dict(obs_mean=obs / n_tot, null_mean=exp / n_tot, z=(obs - exp) / np.sqrt(var) if var > 0 else 0.0, n=n_tot)


def procrustes(d13, top, dim=20):
    from scipy.linalg import orthogonal_procrustes
    A = L13.ppmi(L13.context_matrix(d13, top, rows_filter=d13.HL == "2B")); B = L13.ppmi(L13.context_matrix(d13, top, rows_filter=d13.HL == "1A"))
    ok = (A.sum(1) > 0) & (B.sum(1) > 0); words = [w for w, o in zip(top, ok) if o]; A, B = A[ok], B[ok]
    red = lambda M: (lambda U, S, V: U[:, :dim] * S[:dim])(*np.linalg.svd(M - M.mean(0), full_matrices=False))
    A, B = red(A), red(B); A /= np.linalg.norm(A, axis=1, keepdims=True) + 1e-12; B /= np.linalg.norm(B, axis=1, keepdims=True) + 1e-12
    n = len(words); ranks = []; Rfull = None; sims = np.zeros((n, n))
    for i in range(n):
        m = np.arange(n) != i; Rm, _ = orthogonal_procrustes(A[m], B[m]); s = (A[i] @ Rm) @ B.T; sims[i] = s
        ranks.append(int((s > s[i]).sum()))
    return words, np.array(ranks), sims
