"""h15: line-initial robustness (meta-analysis) and stem-controlled Procrustes (PREREG.md). No meaning claims."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h14_line_position_controls"))
import h14_lib as L14  # noqa: E402
from h14_lib import L13  # noqa: E402

WORDS = ["daiin", "dain", "saiin", "sain", "sar", "sol", "y"]
ONSETS = ["qok", "qot", "ok", "ot", "ch", "sh", "d", "s"]


def expected(d, words, slot="is_init", strat="S1"):
    """observed, hypergeometric mean and variance of count(words in slot) within strata."""
    S = d.groupby(strat).agg(N=("w", "size"), m=(slot, "sum"))
    K = d[d.w.isin(words)].groupby(strat).size().reindex(S.index, fill_value=0)
    N, m, k = S.N.values.astype(float), S.m.values.astype(float), K.values.astype(float)
    e = (k * m / N).sum(); v = (k * m * (N - k) * (N - m) / (N ** 2 * np.maximum(N - 1, 1))).sum()
    return int((d.w.isin(words) & d[slot]).sum()), float(e), float(v)


def unit_table(d, words, unit):
    rows = []
    for u, s in d.groupby(unit):
        o, e, v = expected(s, words); rows.append(dict(unit=u, o=o, e=e, v=v))
    t = pd.DataFrame(rows); small = t.e < 1
    if small.sum():
        t = pd.concat([t[~small], pd.DataFrame([dict(unit="other", o=t[small].o.sum(), e=t[small].e.sum(), v=t[small].v.sum())])], ignore_index=True)
    t["lr"] = np.log((t.o + .5) / (t.e + .5)); t["var"] = 1 / (t.o + .5) + 1 / (t.e + .5)
    return t


def dersimonian_laird(y, v):
    w = 1 / v; mu_f = (w * y).sum() / w.sum(); Q = float((w * (y - mu_f) ** 2).sum()); k = len(y)
    tau2 = max(0.0, (Q - (k - 1)) / (w.sum() - (w ** 2).sum() / w.sum())) if k > 1 else 0.0
    ws = 1 / (v + tau2); mu = (ws * y).sum() / ws.sum(); se = np.sqrt(1 / ws.sum())
    I2 = max(0.0, (Q - (k - 1)) / Q) if Q > 0 else 0.0
    return dict(ratio=float(np.exp(mu)), lo=float(np.exp(mu - 1.96 * se)), hi=float(np.exp(mu + 1.96 * se)), mu=float(mu), se=float(se),
                Q=Q, Q_p=float(stats.chi2.sf(Q, k - 1)) if k > 1 else 1.0, I2=float(I2), tau2=float(tau2), k=k)


def sign_test(t):
    n_pos = int((t.o > t.e).sum()); n = int((t.o != t.e).sum())
    return n_pos, len(t), float(stats.binomtest(n_pos, n, .5, alternative="greater").pvalue) if n else 1.0


def power(d, words, ratio, n=4000, rng=None):
    """P(reject at .05 two-sided) for the observed-null of sample d if true count ~ Poisson(ratio * e) (Monte Carlo)."""
    rng = rng or np.random.default_rng(15)
    S = d.groupby("S1").agg(N=("w", "size"), m=("is_init", "sum"))
    K = d[d.w.isin(words)].groupby("S1").size().reindex(S.index, fill_value=0)
    null = np.zeros(n)
    for (N, m), k in zip(S[["N", "m"]].values, K.values):
        if k and m: null += rng.hypergeometric(k, N - k, m, size=n)
    lo, hi = np.quantile(null, [.025, .975]); e = null.mean()
    alt = rng.poisson(ratio * e, size=n)
    return float(((alt > hi) | (alt < lo)).mean()), float(e)


def onset(w):
    for o in ONSETS:
        if w.startswith(o): return o
    return None


def pct(s, i, cand):
    cand = [j for j in cand if j != i]
    return float((s[cand] < s[i]).mean()) if cand else np.nan
