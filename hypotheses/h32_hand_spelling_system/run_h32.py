"""h32 runner. python run_h32.py [part1|part2|all]  (results/ ; part 1 ~15 min on 5 cores, part 2 ~15 min)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

import h32_lib as L

OUT = L.HERE / "results"; OUT.mkdir(exist_ok=True)
SEEDS = range(5); N_PERM_HAND = 20; NPROC = 5
q, bags, seqs = L.load()
P = lambda hl, sec: L.pages(q, hl, sec)


def halves(pg, seed=99):
    r = np.random.default_rng(seed); pg = list(r.permutation(pg)); return pg[: len(pg) // 2], pg[len(pg) // 2:]


def configs():
    h1a, h2b, h3b = P("1A", "herbal"), P("2B", "herbal"), P("3B", "herbal")
    a1, a2 = halves(h1a); b1, b2 = halves(h2b)
    return {  # name: (target pages A, source pages B, kind)
        "1A herbal <- 2B herbal": (h1a, h2b, "hand, section-matched"),
        "2B herbal <- 1A herbal": (h2b, h1a, "hand, section-matched"),
        "1A herbal <- 3B herbal": (h1a, h3b, "hand, section-matched"),
        "1A herbal <- 2B biological": (h1a, P("2B", "biological"), "hand + section"),
        "1A herbal <- 1A pharmaceutical": (h1a, P("1A", "pharmaceutical"), "same hand, cross-section"),
        "2B herbal <- 2B biological": (h2b, P("2B", "biological"), "same hand, cross-section"),
        "3B herbal <- 3B stars": (h3b, P("3B", "stars"), "same hand, cross-section"),
        "1A herbal half <- 1A herbal half": (a1, a2, "noise floor"),
        "2B herbal half <- 2B herbal half": (b1, b2, "noise floor"),
    }


def job(args):
    name, A, B, kind, seed, context, method = args
    if method == "h11":
        o = L.H11.gap_closure(bags, A, B, seed=seed); o = dict(js_before=o["js_before"], closed_10=o["closed"], rules=o["rules"])
    else:
        o, _ = L.transducer_closure(bags, A, B, seed=seed, context=context)
    return dict(pair=name, kind=kind, seed=seed, method=method if method == "h11" else ("transducer" if context else "context-free"), **o)


def part1():
    C = configs(); jobs = []
    for name, (A, B, kind) in C.items():
        for s in SEEDS:
            jobs.append((name, A, B, kind, s, True, "td"))
            if name in ("1A herbal <- 2B herbal", "1A herbal <- 3B herbal"):
                jobs += [(name, A, B, kind, s, False, "td"), (name, A, B, kind, s, True, "h11")]
    h1a, h2b = P("1A", "herbal"), P("2B", "herbal"); pool = h1a + h2b; rng = np.random.default_rng(7)
    for i in range(N_PERM_HAND):
        pp = list(rng.permutation(pool)); jobs.append((f"permuted hands #{i}", pp[: len(h1a)], pp[len(h1a):], "permuted-hand control", 0, True, "td"))
    with ProcessPoolExecutor(NPROC) as ex: rows = list(ex.map(job, jobs))
    df = pd.DataFrame(rows); df.to_csv(OUT / "closure.csv", index=False); return df


# ------------------------------------------------------------------ part 2: same content
def full_rules():
    A, B = P("1A", "herbal"), P("2B", "herbal"); cA, cB = L.bag(bags, A), L.bag(bags, B)
    rules, _ = L.greedy(cB, cA, L.full_candidates(cB, cA), 30); return rules


def sw_job(args):
    qname, x, pname, y, seed = args
    obs, p, null = L.sw_test(x, y, n_shuf=200, seed=seed)
    return dict(query=qname, page=pname, obs=obs, p=p, null_mean=null, nx=len(x), ny=len(y))


def ngram_share(X, Y, n, rng=None):
    g = lambda pages: set(tuple(s[i:i + n]) for s in pages for i in range(len(s) - n + 1))
    if rng is not None: X = [list(rng.permutation(s)) for s in X]
    return len(g(X) & g(Y))


def family_test(prof_q, prof_t, fam, n_perm=2000, seed=0):
    """mean cosine same-family minus different-family over query x target pairs with known family."""
    Q = [p for p in prof_q if p in fam]; T = [p for p in prof_t if p in fam]
    keys = sorted(set().union(*[prof_q[p] for p in Q], *[prof_t[p] for p in T]))
    vec = lambda c: (lambda v: v / np.linalg.norm(v))(np.array([c[k] for k in keys], float))
    S = np.array([[vec(prof_q[a]) @ vec(prof_t[b]) for b in T] for a in Q]); same_mask = lambda fq, ft: np.equal.outer(fq, ft)
    fq, ft = np.array([fam[p] for p in Q]), np.array([fam[p] for p in T])
    excl = np.array([[a == b for b in T] for a in Q])
    def stat(fq, ft):
        m = same_mask(fq, ft) & ~excl; d = ~same_mask(fq, ft) & ~excl
        return S[m].mean() - S[d].mean() if m.any() else np.nan
    obs = stat(fq, ft); rng = np.random.default_rng(seed)
    null = np.array([stat(rng.permutation(fq), rng.permutation(ft)) for _ in range(n_perm)])
    return dict(n_query=len(Q), n_target=len(T), n_same_pairs=int((same_mask(fq, ft) & ~excl).sum()), obs=obs,
                null_mean=float(np.nanmean(null)), p=float((1 + np.sum(null >= obs)) / (1 + n_perm)))


def part2():
    rules = full_rules(); (OUT / "full_rules.txt").write_text("\n".join(map(repr, rules)) + "\n")
    h1a, h2b = P("1A", "herbal"), P("2B", "herbal"); rng = np.random.default_rng(3)
    ref_q = list(rng.choice(h1a, size=len(h2b), replace=False))
    tgt = {p: [L.enc(w) for w in seqs[p]] for p in h1a}
    queries = {"2B mapped": {p: L.map_tokens(seqs[p], rules) for p in h2b},
               "2B raw": {p: [L.enc(w) for w in seqs[p]] for p in h2b},
               "1A reference": {p: tgt[p] for p in ref_q}}
    jobs = [(qn, x, pn, y, 11) for qn, Qd in queries.items() for qp, x in Qd.items() for pn, y in tgt.items()
            if pn != qp and len(x) and len(y)]
    # keep query page id
    jobs = [(f"{qn}|{qp}", x, pn, y, s) for (qn, x, pn, y, s), qp in
            zip(jobs, [qp for qn, Qd in queries.items() for qp, x in Qd.items() for pn, y in tgt.items() if pn != qp and len(x) and len(y)])]
    with ProcessPoolExecutor(NPROC) as ex: rows = list(ex.map(sw_job, jobs, chunksize=8))
    sw = pd.DataFrame(rows); sw[["set", "qpage"]] = sw["query"].str.split("|", expand=True)
    sw["q_bh"] = np.nan
    for s in sw.set.unique():
        m = sw.set == s; sw.loc[m, "q_bh"] = L.bh(sw.loc[m, "p"].values)
    sw.to_csv(OUT / "sw_pairs.csv", index=False)
    summ = sw.groupby("set").agg(pairs=("p", "size"), frac_p01=("p", lambda v: float(np.mean(v <= 0.01))),
                                 frac_p05=("p", lambda v: float(np.mean(v <= 0.05))), n_bh05=("q_bh", lambda v: int(np.sum(v < 0.05))),
                                 mean_obs=("obs", "mean"), mean_null=("null_mean", "mean"), max_obs=("obs", "max")).reset_index()
    summ.to_csv(OUT / "sw_summary.csv", index=False)
    # shared n-grams
    T = list(tgt.values()); rows = []
    for qn, Qd in queries.items():
        X = list(Qd.values()); Tq = [tgt[p] for p in h1a if p not in Qd]
        for n in (2, 3):
            obs = ngram_share(X, Tq, n); r = np.random.default_rng(5)
            null = [ngram_share(X, Tq, n, r) for _ in range(100)]
            rows.append(dict(set=qn, n=n, shared=obs, null_mean=float(np.mean(null)), ratio=obs / np.mean(null),
                             p=float((1 + np.sum(np.array(null) >= obs)) / 101)))
    pd.DataFrame(rows).to_csv(OUT / "ngram_share.csv", index=False)
    # plant family
    ids = pd.read_csv(L.ROOT / "hypotheses/h17_herbal_label_cribs/data/plant_ids.csv").dropna(subset=["family"])
    fam = {}
    for f, g in ids.groupby("folio"):
        vc = g.family.value_counts()
        if len(vc) == 1 or vc.iloc[0] > vc.iloc[1]: fam[f] = vc.index[0]
    prof = {qn: {p: Counter(x) for p, x in Qd.items()} for qn, Qd in queries.items()}
    ptgt = {p: Counter(x) for p, x in tgt.items()}
    fr = [dict(set=qn, **family_test(prof[qn], {p: c for p, c in ptgt.items() if p not in prof[qn]} if qn == "1A reference" else ptgt, fam))
          for qn in queries]
    pd.DataFrame(fr).to_csv(OUT / "family_test.csv", index=False)
    return summ


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("part1", "all"): print(part1().groupby(["pair", "method"])[["closed_10", "closed_30"]].mean())
    if what in ("part2", "all"): print(part2())
