"""h18: out-of-sample test of the h17 keerodal/Apiaceae lead (PREREG.md). No translation claims."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h17_herbal_label_cribs"))
import h17_lib as H17  # noqa: E402

EXCL = {"f41v", "f90v1", "f34v", "f2r", "f3v", "f29v", "f16r"}
KDAL = re.compile(r"^k[a-z]*dal$"); KDY = re.compile(r"^k[a-z]*dy$")


def in_shape(w: str) -> bool:
    w = w.replace("'", "")
    return bool(KDAL.match(w) or KDY.match(w) or (w.startswith("k") and H17.esim(w, "keerodal") >= 0.5))


def regex_shape(x, y):
    r = re.compile(rf"^{re.escape(x)}[a-z]*{re.escape(y)}$")
    return lambda w: bool(r.match(w.replace("'", "")))


def load():
    C = H17.load(); d = C["d"]
    pool = [f for f in C["herb"] if f not in EXCL and f in C["first"]]
    toks = d[d.gtype.isin(["P", "L"])].groupby("folio").w.apply(list).to_dict()
    tgt = pd.read_csv(HERE / "data" / "apiaceae_folios.csv")
    prim = sorted(set(tgt.folio) & set(pool)); novat = sorted(set(tgt[tgt.word_derived == 0].folio) & set(pool))
    return C, pool, toks, prim, novat


def outcomes(C, pool, toks, pred):
    M = np.zeros((len(pool), 3))
    for i, f in enumerate(pool):
        pi = C["para"].get(f) or [C["first"][f]]; t = toks.get(f, [])
        M[i] = (pred(C["first"][f]), np.mean([pred(w) for w in pi]), np.mean([pred(w) for w in t]) if t else 0)
    return M


def perm_test(M, flag, groups, n=10000, seed=0):
    rng = np.random.default_rng(seed); perms = H17.H9.perm_within(groups, rng, n)
    obs = M[flag].mean(0); null = np.array([M[flag[p]].mean(0) for p in perms])
    return obs, null.mean(0), (1 + (null >= obs - 1e-12).sum(0)) / (n + 1)


def strata(C, pool, by_quire=True):
    return [f"{C['quire'][f]}|{C['HL'][f]}" if by_quire else C["HL"][f] for f in pool]


def calib_shapes(C, pool, toks, k=200, seed=0):
    allw = [w.replace("'", "") for f in pool for w in toks.get(f, [])]
    base = np.mean([in_shape(w) for w in allw])
    starts = sorted({w[0] for w in allw if w}); ends = sorted({w[-n:] for w in allw for n in (2, 3) if len(w) > n})
    cands = []
    for x in starts:
        for y in ends:
            if x == "k" and y in ("dal", "dy"): continue
            r = re.compile(rf"^{re.escape(x)}[a-z]*{re.escape(y)}$"); rate = np.mean([bool(r.match(w)) for w in allw])
            if base / 2 <= rate <= base * 2: cands.append((x, y, rate))
    rng = np.random.default_rng(seed)
    if len(cands) > k: cands = [cands[i] for i in rng.choice(len(cands), k, replace=False)]
    return base, cands
