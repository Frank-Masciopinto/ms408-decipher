"""h16: onset hypothesis for line-initial words; open line-edge search (PREREG.md). No meaning claims."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h14_line_position_controls"))
import h14_lib as L14  # noqa: E402
from h14_lib import L13  # noqa: E402

PRIMARY = ("d", "s")
SECONDARY = ("ch", "sh", "d", "s", "o", "y", "q")


def onset(w, ons=PRIMARY):
    for o in sorted(ons, key=len, reverse=True):
        if w.startswith(o): return o
    return None


def strip(w, ons=PRIMARY):
    o = onset(w, ons)
    if o is None: return None
    r = w[len(o):]
    return r if len(r) >= 2 else None


def attr_test(d, attr, slot="is_init", strat="S1"):
    """sum of attribute over slot vs exact within-stratum permutation mean/variance."""
    a = d[attr].astype(float); obs = float(a[d[slot]].sum()); E = V = 0.0
    for _, s in d.assign(_a=a).groupby(strat):
        m = int(s[slot].sum()); N = len(s)
        if m == 0 or N < 2: continue
        E += m * s._a.mean(); V += m * s._a.var(ddof=0) * (N - m) / (N - 1)
    z = (obs - E) / np.sqrt(V) if V > 0 else 0.0
    return dict(obs=obs, exp=E, ratio=obs / E if E else np.nan, z=float(z), p=float(2 * stats.norm.sf(abs(z))), n_slot=int(d[slot].sum()))


def add_attrs(d, ons=PRIMARY):
    d = d.copy(); d["has_on"] = [onset(w, ons) is not None for w in d.w]; d["stripped"] = [strip(w, ons) for w in d.w]
    d["nxt"] = d.groupby("lid").w.shift(-1)
    d["a2"] = False; d["a4"] = 0.0
    for hl, s in d.groupby("HL"):
        mid = s[~s.is_init & ~s.is_final].w.value_counts(); common = set(s[~s.is_init].w.value_counts().head(200).index)
        d.loc[s.index, "a2"] = s.stripped.isin(common).values
        d.loc[s.index, "a4"] = np.log1p(s.stripped.map(mid).fillna(0)).values
    d["a3"] = (d.stripped.notna() & (d.stripped == d.nxt)).values
    return d


def open_search(d, min_tok=20, strat="S1"):
    rows = []
    vc = d.w.value_counts(); ws = vc[vc >= min_tok].index
    for slot in ["is_init", "is_final"]:
        S = d.groupby(strat).agg(N=("w", "size"), m=(slot, "sum"))
        Nn, mm = S.N.values.astype(float), S.m.values.astype(float)
        Kt = d[d.w.isin(ws)].groupby(["w", strat]).size().unstack(fill_value=0).reindex(columns=S.index, fill_value=0)
        O = d[d[slot] & d.w.isin(ws)].w.value_counts()
        for w, k in Kt.iterrows():
            k = k.values.astype(float); e = (k * mm / Nn).sum(); v = (k * mm * (Nn - k) * (Nn - mm) / (Nn ** 2 * np.maximum(Nn - 1, 1))).sum()
            o = int(O.get(w, 0)); z = (o - e - np.sign(o - e) * .5) / np.sqrt(v) if v > 0 else 0.0
            rows.append(dict(word=w, slot=slot, n=int(vc[w]), obs=o, exp=float(e), ratio=(o + .5) / (e + .5), z=float(z), p=float(2 * stats.norm.sf(abs(z))),
                             reportable=bool(e >= 5 or o >= 5)))
    r = pd.DataFrame(rows); r["p_holm"] = 1.0
    m = r.reportable; r.loc[m, "p_holm"] = L13.H9.holm(r.loc[m, "p"].values)
    return r
