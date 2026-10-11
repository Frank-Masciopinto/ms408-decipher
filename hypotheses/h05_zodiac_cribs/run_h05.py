"""Run all h05 analyses; writes results/*.csv and results/summary.json. Usage: python run_h05.py [--quick]"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

import h05_lib as L

QUICK = "--quick" in sys.argv
OUT = L.HERE / "results"
OUT.mkdir(exist_ok=True)
NPERM = 2000 if QUICK else 20000
NCRIB = 60 if QUICK else 400
t0 = time.time()
S: dict = {}


def log(*a):
    print(f"[{time.time() - t0:6.1f}s]", *a, flush=True)


# ------------------------------------------------------------------ 1. folios, loci, labels
df = L.extract_loci()
zt = L.build_ztext(df)
loci = df.copy()
loci["words"] = loci.words.map(lambda w: " ".join(w))
loci.to_csv(OUT / "zodiac_loci.csv", index=False)

fol_rows = []
for f, sign, roman, pdfp, seen in L.PAGES:
    d = df[df.folio == f]
    lab = d[d.ltype == "Lz"]
    fol_rows.append({"folio": f, "sign": sign, "roman_month_word_near_centre": roman, "pdf_page": pdfp, "image_check": seen, "n_ring_loci": int((d.ltype == "Cc").sum()),
                     "n_label_loci": len(lab), "n_label_words": int(lab.n_words.sum()), "n_ring_words": len(zt.rings[f]),
                     "labels_by_band": dict(Counter(lab.band)),
                     "voynichese_text_in_the_centre": " ".join(sum(lab[lab.band == "centre"].words.tolist(), [])) or ""})
pd.DataFrame(fol_rows).to_csv(OUT / "zodiac_folios.csv", index=False)
S["n_pages"] = len(L.PAGES)
S["n_labels"] = int((df.ltype == "Lz").sum())
S["n_label_words"] = int(sum(len(v) for v in zt.labels.values()))
S["n_ring_words"] = int(sum(len(v) for v in zt.rings.values()))
S["missing_signs"] = L.MISSING
log("pages", S["n_pages"], "labels", S["n_labels"], "label words", S["n_label_words"], "ring words", S["n_ring_words"])

# crib table: per sign the label tokens (types, counts) -----------------------------------------
glob_lab = Counter(w for f in L.FOLIOS for w in zt.labels[f])
glob_ring = Counter(w for f in L.FOLIOS for w in zt.rings[f])
rows = []
for s in L.SIGNS:
    lw = zt.sign_words(s, ("labels",))
    rw = zt.sign_words(s, ("rings",))
    c = Counter(lw)
    others = Counter(w for t in L.SIGNS if t != s for w in zt.sign_words(t, ("labels",)))
    n, N = len(lw), sum(glob_lab.values())
    top = []
    for w, k in c.most_common():
        # specificity: log odds of this label word in this sign vs the other signs (add-1)
        lo = np.log((k + 1) / (n + 1)) - np.log((others[w] + 1) / (N - n + 1))
        top.append((w, k, others[w], lo))
    top.sort(key=lambda x: (-x[3], -x[1]))
    pages = [f for f in L.FOLIOS if L.PAGE_SIGN[f] == s]
    month = [p[2] for p in L.PAGES if p[1] == s][0]
    rows.append({"sign": s, "pages": ";".join(pages), "roman_month_word": month, "n_label_words": n, "n_label_types": len(c), "type_token": len(c) / n,
                 "hapax_share": sum(1 for v in c.values() if v == 1) / n, "n_ring_words": len(rw),
                 "most_frequent_labels": " ".join(f"{w}:{k}" for w, k in c.most_common(6)),
                 "most_sign_specific_labels(w:count_here/count_elsewhere)": " ".join(f"{w}:{k}/{o}" for w, k, o, _ in top[:6]),
                 "first_label_word_per_page": " ".join(next((x for x in zt.label_phrases[p][0:1]), [""])[0] for p in pages),
                 "first_ring_word_per_page": " ".join((zt.rings[p][:1] or [""])[0] for p in pages)})
crib = pd.DataFrame(rows)
crib.to_csv(OUT / "crib_table_by_sign.csv", index=False)
# every label token with position, as the full crib table
lab_rows = []
for r in df[df.ltype == "Lz"].itertuples():
    for w in r.words:
        lab_rows.append({"folio": r.folio, "sign": r.sign, "locus": r.locus, "band": r.band, "clock": r.clock, "word": w, "readable": L.readable(w),
                         "units_T1": " ".join(L.units(w)) if L.readable(w) else "", "n_words_in_label": r.n_words})
pd.DataFrame(lab_rows).to_csv(OUT / "label_tokens.csv", index=False)
log("crib table")

# ------------------------------------------------------------------ 2. are the label sets sign-specific?
res = {}
by_page_lab = {f: zt.labels[f] for f in L.FOLIOS}
by_page_all = {f: zt.labels[f] + zt.rings[f] for f in L.FOLIOS}
by_page_ring = {f: zt.rings[f] for f in L.FOLIOS}
S_bi_lab = L.page_similarity(by_page_lab, "bigram")
S_ty_lab = L.page_similarity(by_page_lab, "type")
S_bi_ring = L.page_similarity(by_page_ring, "bigram")
S_bi_lab.to_csv(OUT / "page_similarity_label_unit_bigrams.csv")
S_bi_ring.to_csv(OUT / "page_similarity_ring_unit_bigrams.csv")
res["same_sign_pairs_label_bigram"] = L.same_sign_pair_test(S_bi_lab, NPERM)
res["same_sign_pairs_label_type"] = L.same_sign_pair_test(S_ty_lab, NPERM)
res["same_sign_pairs_ring_bigram"] = L.same_sign_pair_test(S_bi_ring, NPERM)
# the four '-bre' months (Septembre/Octembre/Novembre/Decembre) = f72v2 f72v1 f73r f73v : do they cluster in label space?
bre = ["f72v2", "f72v1", "f73r", "f73v"]
res["bre_months_cohesion_label_bigram"] = L.group_cohesion_test(S_bi_lab, bre)
res["bre_months_cohesion_ring_bigram"] = L.group_cohesion_test(S_bi_ring, bre)
log("similarity tests")
res["classify_page_from_label"] = L.label_classification(by_page_lab, 40 if QUICK else 200)
# sign-level (pool the two pages of Aries / Taurus) classification
pool = {s: zt.sign_words(s, ("labels",)) for s in L.SIGNS}
res["classify_sign_from_label"] = L.label_classification(pool, 40 if QUICK else 200)
log("classification")
feat = {"first_unit": lambda w: L.units(w)[0], "first_two_units": lambda w: "".join(L.units(w)[:2]), "last_unit": lambda w: L.units(w)[-1],
        "last_two_units": lambda w: "".join(L.units(w)[-2:]), "length_units": lambda w: min(len(L.units(w)), 9)}
chi = {}
for k, fn in feat.items():
    r = L.chi2_perm({f: [w for w in v] for f, v in by_page_lab.items()}, fn, 1000 if QUICK else 5000)
    chi[k] = r
res["chi2_label_features_vs_page"] = chi
log("chi2")
# descriptive affix shares per page
aff = []
for f in L.FOLIOS:
    ws = by_page_lab[f]
    u = [L.units(w) for w in ws]
    n = len(ws)
    aff.append({"folio": f, "sign": L.PAGE_SIGN[f], "n": n, "starts_o": sum(x[0] == "o" for x in u) / n,
                "starts_ot": sum("".join(x[:2]) == "ot" for x in u) / n, "starts_ok": sum("".join(x[:2]) == "ok" for x in u) / n,
                "starts_qo": sum(x[0] == "qo" for x in u) / n,
                "ends_y": sum(x[-1] == "y" for x in u) / n, "ends_l": sum(x[-1] == "l" for x in u) / n, "ends_r": sum(x[-1] == "r" for x in u) / n,
                "ends_m": sum(x[-1] == "m" for x in u) / n, "ends_n": sum(x[-1] == "n" for x in u) / n,
                "ends_ar_or": sum("".join(x[-2:]) in ("ar", "or") for x in u) / n, "ends_al": sum("".join(x[-2:]) == "al" for x in u) / n,
                "ends_dy_ly_ry": sum("".join(x[-2:]) in ("dy", "ly", "ry") for x in u) / n,
                "mean_len_units": float(np.mean([len(x) for x in u])), "mean_len_letters": float(np.mean([len(w) for w in ws]))})
aff = pd.DataFrame(aff)
aff.to_csv(OUT / "label_affix_shares_by_page.csv", index=False)
S["affix_share_range"] = {c: [round(float(aff[c].min()), 3), round(float(aff[c].max()), 3)] for c in aff.columns[3:]}
# the 12 pages: is there ONE suffix/prefix shared by all of them? (share of labels carrying it on the weakest page)
best = []
for kind in ("prefix", "suffix"):
    for n in (1, 2, 3):
        cnt = {f: Counter(("".join(L.units(w)[:n]) if kind == "prefix" else "".join(L.units(w)[-n:])) for w in by_page_lab[f]) for f in L.FOLIOS}
        allk = set().union(*[set(c) for c in cnt.values()])
        for k in allk:
            sh = [cnt[f][k] / len(by_page_lab[f]) for f in L.FOLIOS]
            best.append({"kind": kind, "n_units": n, "affix": k, "min_share": min(sh), "median_share": float(np.median(sh)), "max_share": max(sh),
                         "pages_present": sum(s > 0 for s in sh)})
best = pd.DataFrame(best).sort_values("min_share", ascending=False)
best.head(40).to_csv(OUT / "shared_affixes_all_pages.csv", index=False)
# the MS-wide baseline for the same affix (so 'shared' is read against how common it is in running text)
ms_all = [w for _, w in L.ms_words(False)]
msu = [L.units(w) for w in ms_all]
base = {}
for r in best.head(40).itertuples():
    n = r.n_units
    base[(r.kind, r.affix)] = float(np.mean([("".join(u[:n]) if r.kind == "prefix" else "".join(u[-n:])) == r.affix for u in msu]))
bb = best.head(40).copy()
bb["ms_running_text_share"] = [base[(r.kind, r.affix)] for r in bb.itertuples()]
bb.to_csv(OUT / "shared_affixes_all_pages.csv", index=False)
res["top_shared_affixes"] = bb.head(8)[["kind", "affix", "min_share", "median_share", "ms_running_text_share"]].to_dict("records")
# label word types shared between pages vs a token-level shuffle (do pages re-use one pool of label words?)
pages_ = L.FOLIOS
toks = [(f, w) for f in pages_ for w in by_page_lab[f]]
sizes = [len(by_page_lab[f]) for f in pages_]
def mean_pair_jacc(assign):
    sets = [set() for _ in pages_]
    for i, w in assign:
        sets[i].add(w)
    v = [len(a & b) / max(len(a | b), 1) for i, a in enumerate(sets) for b in sets[i + 1:]]
    return float(np.mean(v))
real = mean_pair_jacc([(pages_.index(f), w) for f, w in toks])
rg = np.random.default_rng(5)
words_flat = np.array([w for _, w in toks], dtype=object)
page_of = np.array([pages_.index(f) for f, _ in toks])
nul = np.array([mean_pair_jacc(list(zip(page_of, rg.permutation(words_flat)))) for _ in range(500 if QUICK else 2000)])
res["label_type_overlap"] = {"mean_pairwise_jaccard": real, "null_mean": float(nul.mean()), "null_max": float(nul.max()), "p": (int((nul >= real).sum()) + 1) / (len(nul) + 1),
                             "n_label_word_types": len(set(words_flat)), "types_on_2plus_pages": sum(1 for w in set(words_flat) if len({f for f, x in toks if x == w}) >= 2),
                             "types_on_2plus_signs": sum(1 for w in set(words_flat) if len({L.PAGE_SIGN[f] for f, x in toks if x == w}) >= 2)}
# drift with page order: is 'ot-' / 'ok-' use a smooth function of position in the section (month order) rather than of the sign?
order = np.arange(12)
res["drift_with_page_order"] = {c: {"spearman_rho": L.perm_corr_p(aff[c].values, order, 5000, seed=3)[0], "p": L.perm_corr_p(aff[c].values, order, 5000, seed=3)[1]}
                                 for c in ("starts_ot", "starts_ok", "ends_y", "ends_ar_or", "mean_len_units")}
S["tests_sign_specificity"] = res

# ------------------------------------------------------------------ 3. frequency work: label units vs running text
lab_units = Counter(u for f in L.FOLIOS for w in zt.labels[f] for u in L.units(w))
ring_units = Counter(u for f in L.FOLIOS for w in zt.rings[f] for u in L.units(w))
ms_units = Counter(u for u0 in msu for u in u0)
nl, nm_, nr = sum(lab_units.values()), sum(ms_units.values()), sum(ring_units.values())
rows = []
for u in sorted(set(lab_units) | set(ring_units) | set(ms_units), key=lambda x: -ms_units[x]):
    a, b = lab_units[u], ms_units[u]
    if a + b < 15:
        continue
    tab = [[a, nl - a], [b, nm_ - b]]
    p = sps.fisher_exact(tab)[1]
    rows.append({"unit": u, "label_count": a, "label_share": a / nl, "ring_share": ring_units[u] / nr, "ms_running_share": b / nm_, "ratio_label_vs_ms": (a / nl) / (b / nm_) if b else np.nan, "fisher_p": p})
ue = pd.DataFrame(rows)
hp = L.holm(dict(zip(ue.unit, ue.fisher_p)))
ue["holm_p"] = ue.unit.map(hp)
ue.to_csv(OUT / "label_unit_enrichment.csv", index=False)
S["n_units_enriched_holm05"] = int((ue.holm_p < 0.05).sum())
S["enriched_units_holm05"] = ue[ue.holm_p < 0.05].sort_values("ratio_label_vs_ms", ascending=False)[["unit", "label_share", "ms_running_share"]].round(4).values.tolist()
# positional behaviour: initial / final share of each unit in labels vs running text
def pos_share(words):
    ini, fin, n = Counter(), Counter(), 0
    for w in words:
        u = L.units(w)
        if len(u) >= 2:
            ini[u[0]] += 1
            fin[u[-1]] += 1
            n += 1
    return ini, fin, n
li, lf, ln = pos_share([w for f in L.FOLIOS for w in zt.labels[f]])
ri, rf, rn = pos_share(ms_all)
rows = []
for u in sorted(set(li) | set(lf) | set(ri) | set(rf), key=lambda x: -(li[x] + lf[x] + ri[x] + rf[x])):
    if li[u] + lf[u] < 10:
        continue
    rows.append({"unit": u, "label_initial_share": li[u] / ln, "ms_initial_share": ri[u] / rn, "label_final_share": lf[u] / ln, "ms_final_share": rf[u] / rn})
pd.DataFrame(rows).to_csv(OUT / "label_unit_position_vs_ms.csv", index=False)
S["label_initial_o_share"] = li["o"] / ln
S["ms_initial_o_share"] = ri["o"] / rn
S["label_final_y_share"] = lf["y"] / ln
S["ms_final_y_share"] = rf["y"] / rn
log("unit frequency")

# length / structure profile: labels vs ring text vs running text vs name lists
lists = L.name_lists()
def prof(ws, name):
    u = [L.units(w) for w in ws]
    return {"set": name, "n": len(ws), "mean_letters": float(np.mean([len(w) for w in ws])), "sd_letters": float(np.std([len(w) for w in ws])),
            "mean_units": float(np.mean([len(x) for x in u])), "repeat_share": float(np.mean([len(set(x)) < len(x) for x in u])),
            "distinct_initials": len({x[0] for x in u}), "distinct_finals": len({x[-1] for x in u})}
pr = [prof([w for f in L.FOLIOS for w in zt.labels[f]], "voynich_labels(all pages)"), prof([w for f in L.FOLIOS for w in zt.rings[f]], "voynich_ring_words"),
      prof(ms_all, "voynich_running_text")]
for k, v in lists.items():
    nm = L.names_by_sign(v)
    pr.append({"set": k, "n": len(nm), "mean_letters": float(np.mean([len(x) for x in nm])), "sd_letters": float(np.std([len(x) for x in nm])), "mean_units": float(np.mean([len(x) for x in nm])),
               "repeat_share": float(np.mean([len(set(x)) < len(x) for x in nm])), "distinct_initials": len({x[0] for x in nm}), "distinct_finals": len({x[-1] for x in nm})})
pd.DataFrame(pr).to_csv(OUT / "length_structure_profile.csv", index=False)

# ------------------------------------------------------------------ 4. length test (sign-name length vs page label length)
metr = {}
for kind, key in (("labels", "label"), ("rings", "ring")):
    ws = {s: zt.sign_words(s, (kind,)) for s in L.SIGNS}
    metr[f"{key}_mean_letters"] = [float(np.mean([len(w) for w in ws[s]])) for s in L.SIGNS]
    metr[f"{key}_mean_units"] = [float(np.mean([len(L.units(w)) for w in ws[s]])) for s in L.SIGNS]
pd.DataFrame(metr, index=L.SIGNS).to_csv(OUT / "sign_label_length_metrics.csv")
rows, pv = [], {}
for lname, lst in lists.items():
    nm = L.names_by_sign(lst)
    ln = [len(x) for x in nm]
    for mname, mv in metr.items():
        rho, p = L.perm_corr_p(mv, ln, NPERM, seed=1)
        rows.append({"names": lname, "voynich_metric": mname, "spearman_rho": rho, "p_perm_two_sided": p})
        pv[(lname, mname)] = p
hp = L.holm({f"{a}|{b}": p for (a, b), p in pv.items()})
lt = pd.DataFrame(rows)
lt["holm_p"] = [hp[f"{r.names}|{r.voynich_metric}"] for r in lt.itertuples()]
lt.to_csv(OUT / "length_order_tests.csv", index=False)
S["length_tests"] = {"n_tests": len(lt), "min_p": float(lt.p_perm_two_sided.min()), "min_holm_p": float(lt.holm_p.min()), "n_p_lt_005_uncorrected": int((lt.p_perm_two_sided < .05).sum()),
                     "expected_false_positives_at_005": round(0.05 * len(lt), 1), "best": lt.sort_values("p_perm_two_sided").head(5).round(4).to_dict("records"),
                     "latin_sign_label_letters": lt[(lt.names == "sign:latin") & (lt.voynich_metric == "label_mean_letters")].round(3).to_dict("records")}
log("length tests", S["length_tests"]["min_p"])

# ------------------------------------------------------------------ 5. name-in-page isomorph test
idx = L.IsoIndex(ms_all, zt)
rows, pv = [], {}
isoZ = {}
for lname, lst in lists.items():
    nm = L.names_by_sign(lst)
    for mode in ("exact", "window"):
        Z = L.iso_matrix(idx, nm, mode)
        isoZ[(lname, mode)] = Z
        r = L.perm_diag_sum(Z, NPERM, seed=2)
        obs_hits = [idx.z(s, n, mode)[1] for s, n in zip(L.SIGNS, nm)]
        exp_hits = [idx.z(s, n, mode)[2] for s, n in zip(L.SIGNS, nm)]
        rows.append({"names": lname, "mode": mode, "sum_z_true_pairing": r["obs"], "null_mean": r["null_mean"], "z_vs_null": r["z"], "p_perm": r["p"],
                     "observed_matching_items": float(sum(obs_hits)), "expected_by_ms_rate": float(sum(exp_hits)),
                     "n_names_with_repeat": sum(len(set(n)) < len(n) for n in nm)})
        pv[f"{lname}|{mode}"] = r["p"]
hp = L.holm(pv)
iso = pd.DataFrame(rows)
iso["holm_p"] = [hp[f"{r.names}|{r.mode}"] for r in iso.itertuples()]
iso.to_csv(OUT / "isomorph_name_in_page_tests.csv", index=False)
S["isomorph_tests"] = {"n_tests": len(iso), "min_p": float(iso.p_perm.min()), "min_holm_p": float(iso.holm_p.min()), "n_p_lt_005_uncorrected": int((iso.p_perm < .05).sum()),
                       "best": iso.sort_values("p_perm").head(5).round(4).to_dict("records")}
log("isomorph", S["isomorph_tests"]["min_p"])

# ------------------------------------------------------------------ 6. crib-drag with transfer test
lex = L.lexicons()
rng = np.random.default_rng(7)
import random as _r
pyr = _r.Random(11)
sign_units = {s: [L.units(w) for w in zt.sign_words(s, ("labels", "rings"))] for s in L.SIGNS}
zod_types = Counter(L.units(w) for w in zt.all_words())
glob = Counter(L.units(w) for w in ms_all) + zod_types
rest_types = Counter(L.units(w) for w in ms_all)
crib_rows, null_store, cand_rows = [], {}, []
for lname, lst in lists.items():
    lang = L.lang_of(lname)
    if lang not in lex:
        continue   # no control corpus for French/Spanish/Catalan/Occitan -> no lexicon, names-only tests
    nm = [L.to_lex_alphabet(x, lang) for x in L.names_by_sign(lst)]
    lx = lex[lang]
    by_len: dict = {}
    for w in lx:
        by_len.setdefault(len(w), []).append(w)
    for k in by_len:
        by_len[k].sort()
    names_d = dict(zip(L.SIGNS, nm))
    obs = L.crib_run(names_d, sign_units, glob, zod_types, rest_types, lx)
    # null A: names permuted over signs; null B: random same-length lexicon words
    nullA, nullB = [], []
    for _ in range(NCRIB):
        p = rng.permutation(len(nm))
        nullA.append(L.crib_run({s: nm[i] for s, i in zip(L.SIGNS, p)}, sign_units, glob, zod_types, rest_types, lx))
        nullB.append(L.crib_run(dict(zip(L.SIGNS, L.random_names_like(nm, by_len, pyr))), sign_units, glob, zod_types, rest_types, lx))
    row = {"names": lname, "lexicon_types": len(lx), "n_signs_with_candidate": obs["n_signs_with_candidate"], "n_units_mapped": obs["n_units_mapped"], "conflicts": obs["conflicts"],
           "many_to_one": obs["many_to_one"], "zod_hits": obs["zod_hits"], "zod_hit_types": obs["zod_hit_types"], "zod_fullmapped_tokens": obs["zod_fullmapped"],
           "rest_hits": obs["rest_hits"], "rest_hit_types": obs["rest_hit_types"], "rest_fullmapped_tokens": obs["rest_fullmapped"]}
    for key in ("n_signs_with_candidate", "n_units_mapped", "conflicts", "rest_hit_types", "zod_hit_types"):
        for nn, nul in (("A_perm", nullA), ("B_random", nullB)):
            v = np.array([x[key] for x in nul], float)
            row[f"{key}_null_{nn}_mean"] = float(v.mean())
            row[f"{key}_p_ge_{nn}"] = (int((v >= obs[key]).sum()) + 1) / (len(v) + 1)
    # p among null runs whose mapping covers a comparable number of units (+-1): hits grow with the number of mapped units, so the raw p is biased
    for nn, nul in (("A_perm", nullA), ("B_random", nullB)):
        m = [x for x in nul if abs(x["n_units_mapped"] - obs["n_units_mapped"]) <= 1]
        row[f"n_matched_nulls_{nn}"] = len(m)
        row[f"rest_hit_types_p_matched_{nn}"] = (sum(x["rest_hit_types"] >= obs["rest_hit_types"] for x in m) + 1) / (len(m) + 1) if len(m) >= 10 else np.nan
    row["rest_hit_types_p_joint_A_perm(hits>=obs & conflicts<=obs)"] = (sum(x["rest_hit_types"] >= obs["rest_hit_types"] and x["conflicts"] <= obs["conflicts"] for x in nullA) + 1) / (len(nullA) + 1)
    row["conflicts_null_A_min"] = int(min(x["conflicts"] for x in nullA))
    row["mapping"] = " ".join(f"{k}>{v}" for k, v in sorted(obs["mapping"].items()))
    # transfer significance uses hit-types per fully-mapped type pool; primary statistic: rest_hit_types vs null B (and A)
    crib_rows.append(row)
    null_store[lname] = {"obs": obs["rest_hit_types"], "A": [x["rest_hit_types"] for x in nullA], "B": [x["rest_hit_types"] for x in nullB],
                         "obs_zod": obs["zod_hit_types"], "A_zod": [x["zod_hit_types"] for x in nullA], "B_zod": [x["zod_hit_types"] for x in nullB]}
    for s, (tok, c) in obs["candidates"].items():
        cand_rows.append({"names": lname, "sign": s, "name": names_d[s], "candidate_label_token(EVA)": tok, "count_in_sign_text": c,
                          "n_isomorphic_types_in_whole_ms": sum(1 for u in rest_types if len(u) == len(names_d[s]) and L.pattern(u) == L.pattern(names_d[s]))})
    log("crib", lname)
cr = pd.DataFrame(crib_rows)
pv = {}
for r in cr.itertuples():
    pv[f"{r.names}|A"] = r.rest_hit_types_p_matched_A_perm if not np.isnan(r.rest_hit_types_p_matched_A_perm) else r.rest_hit_types_p_ge_A_perm
    pv[f"{r.names}|B"] = r.rest_hit_types_p_matched_B_random if not np.isnan(r.rest_hit_types_p_matched_B_random) else r.rest_hit_types_p_ge_B_random
hp = L.holm(pv)
cr["holm_p_transfer_vs_A"] = [hp[f"{r.names}|A"] for r in cr.itertuples()]
cr["holm_p_transfer_vs_B"] = [hp[f"{r.names}|B"] for r in cr.itertuples()]
cr.to_csv(OUT / "crib_drag_summary.csv", index=False)
pd.DataFrame(cand_rows).to_csv(OUT / "crib_drag_candidates.csv", index=False)
json.dump(null_store, open(OUT / "crib_null_store.json", "w"))
S["crib_drag"] = {"n_lists": len(cr), "min_p_transfer_vs_A": float(cr.rest_hit_types_p_ge_A_perm.min()), "min_p_transfer_vs_B": float(cr.rest_hit_types_p_ge_B_random.min()),
                  "min_p_matched_A": float(cr.rest_hit_types_p_matched_A_perm.min()), "min_p_matched_B": float(cr.rest_hit_types_p_matched_B_random.min()),
                  "min_holm_p": float(min(cr.holm_p_transfer_vs_A.min(), cr.holm_p_transfer_vs_B.min())), "n_perm": NCRIB,
                  "best_by_B": cr.sort_values("rest_hit_types_p_ge_B_random").head(4)[["names", "n_signs_with_candidate", "n_units_mapped", "conflicts", "rest_hit_types", "rest_hit_types_null_B_random_mean", "rest_hit_types_p_ge_B_random", "rest_hit_types_p_matched_B_random", "rest_hit_types_p_matched_A_perm"]].round(4).to_dict("records"),
                  "signs_with_candidate_range": [int(cr.n_signs_with_candidate.min()), int(cr.n_signs_with_candidate.max())]}
log("crib-drag done", S["crib_drag"]["min_p_transfer_vs_B"])

# Bax (2014) read the label next to the Pleiades on f68r3 (EVA doary / doaro) as a possible 'Taurus'. If that label were a sign name it should be on the Taurus pages.
bax = {}
for w in ("doary", "doaro"):
    bax[w] = {"zodiac_label_or_ring_count_by_sign": {s: zt.sign_words(s).count(w) for s in L.SIGNS if zt.sign_words(s).count(w)},
              "whole_ms_running_text_count": sum(1 for x in ms_all if x == w)}
S["bax_taurus_check"] = bax

# ------------------------------------------------------------------ 7. label pitch table (illustration)
import h02_lib as H2
t2 = H2.build_ms("T2")
st = H2.unit_stats(t2, np.ones(len(t2.L), bool), slot_grammar=True, seed=1)
hz = H2.build_map("a_slotgrammar_ext", st, t2.inv)
hz_c = H2.build_map("c_pos", st, t2.inv)
inv_hz = dict(zip(t2.inv, hz))
inv_hzc = dict(zip(t2.inv, hz_c))
from msdecipher.segment import Segmenter, PRESETS
seg2 = Segmenter(PRESETS["collapsed"] + tuple(H2.SHEET_UNITS), name="T2")
rows = []
typ = Counter(w for f in L.FOLIOS for w in zt.labels[f])
for w, n in typ.most_common():
    u = seg2(w)
    h = [inv_hz.get(x, np.nan) for x in u]
    hc = [inv_hzc.get(x, np.nan) for x in u]
    rows.append({"label_word": w, "count": n, "units_T2": " ".join(u), "n_sheet_units": sum(x in H2.SHEET for x in u), "hz_sequence_slotgrammar_ext": " ".join("?" if np.isnan(x) else f"{x:.0f}" for x in h),
                 "mean_hz": float(np.nanmean(h)) if not np.all(np.isnan(h)) else np.nan, "first_hz": h[0], "last_hz": h[-1], "range_hz": float(np.nanmax(h) - np.nanmin(h)) if not np.all(np.isnan(h)) else np.nan,
                 "contour": "rising" if all(a <= b for a, b in zip(h, h[1:])) else ("falling" if all(a >= b for a, b in zip(h, h[1:])) else "mixed"),
                 "mean_hz_c_pos": float(np.nanmean(hc)) if not np.all(np.isnan(hc)) else np.nan})
lp = pd.DataFrame(rows)
lp.to_csv(OUT / "label_pitch_table.csv", index=False)
inv_tab = pd.DataFrame({"unit": t2.inv, "hz_a_slotgrammar_ext": hz, "hz_c_pos": hz_c, "on_sheet": [u in H2.SHEET for u in t2.inv], "sheet_hz": [H2.SHEET.get(u, np.nan) for u in t2.inv]})
inv_tab.to_csv(OUT / "unit_hz_a_slotgrammar_ext.csv", index=False)
# per sign mean pitch of labels (token-weighted) and test vs permuted page labels
sign_hz = {}
for s in L.SIGNS:
    v = []
    for w in zt.sign_words(s, ("labels",)):
        u = seg2(w)
        h = [inv_hz.get(x, np.nan) for x in u]
        if not np.all(np.isnan(h)):
            v.append(np.nanmean(h))
    sign_hz[s] = v
allv = np.concatenate([sign_hz[s] for s in L.SIGNS])
grp = np.concatenate([[i] * len(sign_hz[s]) for i, s in enumerate(L.SIGNS)])
def eta(x, g):
    m = x.mean(); ss = ((x - m) ** 2).sum()
    return sum(len(x[g == k]) * (x[g == k].mean() - m) ** 2 for k in np.unique(g)) / ss
e_obs = eta(allv, grp)
pr_ = np.random.default_rng(3)
nul = np.array([eta(allv, pr_.permutation(grp)) for _ in range(NPERM // 4)])
S["label_pitch"] = {"mean_hz_by_sign": {s: round(float(np.mean(v)), 1) for s, v in sign_hz.items()}, "eta2_sign": float(e_obs), "p_perm_eta2": (int((nul >= e_obs).sum()) + 1) / (len(nul) + 1),
                    "label_mean_hz_overall": float(allv.mean()), "n_label_types_with_sheet_unit": int((lp.n_sheet_units > 0).sum()), "n_label_types": len(lp),
                    "share_rising_or_falling": float((lp.contour != "mixed").mean())}
log("pitch table")
json.dump(S, open(OUT / "summary.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
log("done")
