"""h17: plant identifications and pharmaceutical labels as cribs (PREREG.md). No translation claims."""
from __future__ import annotations

import re
import sys
from functools import lru_cache
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h13_top_word_context")); sys.path.insert(0, str(ROOT / "hypotheses" / "h09_image_context_cribs"))
import h09_lib as H9  # noqa: E402
import h13_lib as H13  # noqa: E402

holm = H9.holm


@lru_cache(maxsize=None)
def lev(a: str, b: str) -> int:
    if len(a) < len(b): a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def esim(a: str, b: str) -> float:
    return 1 - lev(a, b) / max(len(a), len(b), 1)


def maxsim(A, B):
    return max((esim(a, b) for a in A for b in B), default=np.nan)


def resolve(f, pages):
    return [f] if f in pages else sorted(p for p in pages if re.fullmatch(f + r"\d", p))


def load():
    d = H13.token_table(); q = pd.read_csv(ROOT / "data" / "quires.csv", dtype=str, keep_default_na=False).set_index("page")
    pages = set(q.index)
    herb = sorted(p for p in pages if q.section[p] == "herbal" and p in set(d.folio))
    P = d[d.gtype == "P"]
    para = P[P.para_initial].groupby("folio").w.apply(list).to_dict()
    first = P.sort_values(["folio", "line", "pos"]).groupby("folio").w.first().to_dict()
    vocab = d[d.gtype.isin(["P", "L"]) & (d.w.str.len() >= 3)].groupby("folio").w.apply(set).to_dict()
    labels = d[(d.gtype == "L") & (d.w.str.len() >= 3)].groupby("folio").w.apply(list).to_dict()
    HL = (q.lfd_hand + q.currier_language).to_dict(); quire = q.quire.to_dict()
    return dict(d=d, q=q, pages=pages, herb=herb, para=para, first=first, vocab=vocab, labels=labels, HL=HL, quire=quire)


# ------------------------------------------------------------------ pairs
def pharma_pairs(C):
    rows = [dict(herbal=h, pharma=t, source="ZL3b: " + s, uncertain=int(u)) for h, t, s, u in H9.same_plant_pairs()]
    rows += pd.read_csv(HERE / "data" / "pharma_herbal_pairs_extra.csv").to_dict("records")
    out = []
    for r in rows:
        if r["herbal"] not in C["herb"]: continue
        ts = [t for t in resolve(re.sub(r"\[.*", "", r["pharma"]), C["pages"]) if C["q"].section.get(t) == "pharmaceutical"]
        labs = [w for t in ts for w in C["labels"].get(t, [])]
        if labs: out.append({**r, "pharma_pages": " ".join(ts), "labels": labs})
    return out


def pair_stats(labs, h, C):
    pi = C["para"].get(h, []) or [C["first"].get(h, "")]
    s1 = np.mean([maxsim([l], pi) for l in labs])
    s2 = H9.jacc(set(labs), C["vocab"].get(h, set()))
    p3 = {w[:3] for w in pi}; s3 = np.mean([l[:3] in p3 for l in labs])
    return np.array([s1, s2, s3])


def strata_members(h, C, by_quire=True):
    key = lambda f: (C["quire"][f], C["HL"][f]) if by_quire else C["HL"][f]
    m = [f for f in C["herb"] if key(f) == key(h)]
    if by_quire and len(m) < 2:
        m = [f for f in C["herb"] if C["HL"][f] == C["HL"][h]]
    return m


def test_A(C, n=10000, seed=0):
    rng = np.random.default_rng(seed); pairs = pharma_pairs(C)
    obs = np.array([pair_stats(p["labels"], p["herbal"], C) for p in pairs])
    res = {}
    for nm, bq in (("quireHL", True), ("HL", False), ("any", None)):
        pools = [C["herb"] if bq is None else strata_members(p["herbal"], C, bq) for p in pairs]
        cache = [{f: pair_stats(p["labels"], f, C) for f in pool} for p, pool in zip(pairs, pools)]
        null = np.zeros((n, 3))
        for k in range(n):
            null[k] = np.mean([cache[i][pool[rng.integers(len(pool))]] for i, pool in enumerate(pools)], 0)
        res[nm] = dict(null_mean=null.mean(0), p=(1 + (null >= obs.mean(0)).sum(0)) / (n + 1))
    tab = pd.DataFrame([{k: v for k, v in p.items() if k != "labels"} | dict(n_labels=len(p["labels"]), S1=o[0], S2=o[1], S3=o[2],
                        shared=" ".join(sorted(set(p["labels"]) & C["vocab"].get(p["herbal"], set()))))
                        for p, o in zip(pairs, obs)])
    return tab, obs.mean(0), res


# ------------------------------------------------------------------ B
def taxa(C, merge_elv=False, exclude=()):
    t = pd.read_csv(HERE / "data" / "plant_ids.csv"); t = t[~t.source.isin(exclude)]
    if merge_elv: t["source"] = t.source.replace({"ELV_Grolier": "ELV", "ELV_Beinecke": "ELV"})
    t = t[t.folio.isin(C["herb"])]
    out = {}
    for lvl in ("genus", "family"):
        g = t.groupby(["folio", lvl]).source.nunique()
        out[lvl] = {f: g.loc[f].to_dict() for f in g.index.get_level_values(0).unique()}
    return out


def folio_sims(C, folios):
    S = {}
    for a, b in combinations(folios, 2):
        pa, pb = C["para"].get(a) or [C["first"][a]], C["para"].get(b) or [C["first"][b]]
        S[a, b] = (esim(C["first"][a], C["first"][b]), maxsim(pa, pb), H9.jacc(C["vocab"].get(a, set()), C["vocab"].get(b, set())))
    return S


def b_stat(assign, S, folios, min_cons=1):
    num = np.zeros(3); den = 0.0; npair = 0
    for a, b in combinations(folios, 2):
        A, B = assign[a], assign[b]
        w = max((min(A[x], B[x]) for x in A.keys() & B.keys() if min(A[x], B[x]) >= min_cons), default=0)
        if w:
            num += w * np.array(S[a, b]); den += w; npair += 1
    return (num / den if den else np.full(3, np.nan)), npair


def test_B(C, lvl="genus", min_cons=1, n=10000, seed=0, merge_elv=False, by_quire=False):
    rng = np.random.default_rng(seed); T = taxa(C, merge_elv)[lvl]
    folios = [f for f in C["herb"] if f in T and f in C["first"]]
    S = folio_sims(C, folios)
    obs, npair = b_stat(T, S, folios, min_cons)
    allm = np.nanmean(np.array(list(S.values())), 0)
    key = (lambda f: (C["quire"][f], C["HL"][f])) if by_quire else (lambda f: C["HL"][f])
    groups = [key(f) for f in folios]; perms = H9.perm_within(groups, rng, n)
    null = np.array([b_stat({folios[i]: T[folios[j]] for i, j in enumerate(p)}, S, folios, min_cons)[0] for p in perms])
    p = (1 + (null >= obs).sum(0)) / (n + 1)
    return dict(level=lvl, min_cons=min_cons, n_folios=len(folios), n_pairs=npair, obs=obs, all_pairs_mean=allm, null_mean=np.nanmean(null, 0), p=p)


# ------------------------------------------------------------------ C
def test_C(C, n=10000, seed=0, exclude=()):
    rng = np.random.default_rng(seed); T = taxa(C, exclude=exclude); cr = pd.read_csv(HERE / "data" / "bax_cribs.csv")
    rows, nulls = [], []
    for r in cr.itertuples():
        for lvl in ("genus", "family"):
            key = getattr(r, lvl)
            tgt = [f for f in C["herb"] if f != r.folio and key in T[lvl].get(f, {})]
            if not tgt: continue
            sim = lambda f: maxsim([r.crib_word], C["para"].get(f) or [C["first"][f]])
            obs = np.mean([sim(f) for f in tgt])
            pools = [[g for g in C["herb"] if C["HL"][g] == C["HL"][f] and g != r.folio and g in C["first"]] for f in tgt]
            cache = {g: sim(g) for pool in pools for g in pool}
            null = np.array([np.mean([cache[pool[rng.integers(len(pool))]] for pool in pools]) for _ in range(n)])
            rows.append(dict(crib=r.crib_word, folio=r.folio, level=lvl, taxon=key, targets=" ".join(tgt), obs=obs, null_mean=null.mean(),
                             p=(1 + (null >= obs).sum()) / (n + 1), best=" ".join(f"{f}:{max(C['para'].get(f) or [C['first'][f]], key=lambda w: esim(r.crib_word, w))}" for f in tgt)))
            nulls.append((lvl, obs, null))
    comb = {}
    for lvl in ("genus", "family"):
        z = [(o, nl) for l, o, nl in nulls if l == lvl]
        if z:
            o = np.mean([a for a, _ in z]); nl = np.mean([b for _, b in z], 0)
            comb[lvl] = dict(obs=o, null_mean=nl.mean(), p=(1 + (nl >= o).sum()) / (n + 1), k=len(z))
    return pd.DataFrame(rows), comb


def id_summary(C):
    t = pd.read_csv(HERE / "data" / "plant_ids.csv")
    g = t.groupby(["folio", "genus"]).source.nunique().reset_index()
    top = g.sort_values("source", ascending=False).groupby("folio").head(1).rename(columns={"source": "consensus"})
    n_src = t.groupby("folio").source.nunique().rename("n_sources"); n_gen = t.groupby("folio").genus.nunique().rename("n_genera")
    top = top.set_index("folio").join(n_src).join(n_gen).reset_index()
    top["first_word"] = top.folio.map(C["first"]); top["HL"] = top.folio.map(C["HL"]); top["quire"] = top.folio.map(C["quire"])
    return top.sort_values(["consensus", "folio"], ascending=[False, True])


def control_C(C, n=2000, seed=1):
    """Calibration for C: treat the paragraph-initial word of EVERY family-ID'd herbal folio as a pseudo-crib and
    compute the same family statistic; reports the share of pseudo-cribs whose per-crib p < 0.05 and the median
    obs - null gap, for all words and for k-initial ones (Bax's cribs all start with k)."""
    rng = np.random.default_rng(seed); T = taxa(C)["family"]; rows = []
    for f in C["herb"]:
        if f not in T or f not in C["first"]: continue
        w = (C["para"].get(f) or [C["first"][f]])[0]
        for fam in T[f]:
            tgt = [g for g in C["herb"] if g != f and fam in T.get(g, {}) and g in C["first"]]
            if not tgt: continue
            sim = lambda g: maxsim([w], C["para"].get(g) or [C["first"][g]])
            obs = np.mean([sim(g) for g in tgt])
            pools = [[g for g in C["herb"] if C["HL"][g] == C["HL"][t] and g != f and g in C["first"]] for t in tgt]
            cache = {g: sim(g) for pool in pools for g in pool}
            null = np.array([np.mean([cache[pool[rng.integers(len(pool))]] for pool in pools]) for _ in range(n)])
            rows.append(dict(folio=f, word=w, family=fam, obs=obs, gap=obs - null.mean(), p=(1 + (null >= obs).sum()) / (n + 1)))
    d = pd.DataFrame(rows); k = d[d.word.str.startswith("k")]
    return dict(n=len(d), frac_p05=float((d.p < 0.05).mean()), median_gap=float(d.gap.median()),
                n_k=len(k), frac_p05_k=float((k.p < 0.05).mean()) if len(k) else None, median_gap_k=float(k.gap.median()) if len(k) else None,
                k_rows=k[["folio", "word", "family", "gap", "p"]].round(3).to_dict("records"))


def test_C_drop_mutual(C, n=10000, seed=2):
    """Sensitivity: family-level C with all four crib folios removed from targets and null pools."""
    rng = np.random.default_rng(seed); T = taxa(C)["family"]; cr = pd.read_csv(HERE / "data" / "bax_cribs.csv")
    excl = set(cr.folio); obs, nulls, rows = [], [], []
    for r in cr.itertuples():
        tgt = [g for g in C["herb"] if g not in excl and r.family in T.get(g, {}) and g in C["first"]]
        sim = lambda g: maxsim([r.crib_word], C["para"].get(g) or [C["first"][g]])
        pools = [[g for g in C["herb"] if C["HL"][g] == C["HL"][t] and g not in excl and g in C["first"]] for t in tgt]
        cache = {g: sim(g) for p in pools for g in p}
        o = np.mean([sim(g) for g in tgt]); nl = np.array([np.mean([cache[p[rng.integers(len(p))]] for p in pools]) for _ in range(n)])
        obs.append(o); nulls.append(nl); rows.append(dict(crib=r.crib_word, obs=o, null_mean=nl.mean(), p=(1 + (nl >= o).sum()) / (n + 1)))
    o = np.mean(obs); nl = np.mean(nulls, 0)
    return dict(per_crib=rows, obs=o, null_mean=nl.mean(), p=(1 + (nl >= o).sum()) / (n + 1),
                p_without_keerodal=float((1 + (np.mean(nulls[:3], 0) >= np.mean(obs[:3])).sum()) / (n + 1)))
