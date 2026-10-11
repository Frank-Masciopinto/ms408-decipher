"""h06 part 2: zodiac pages vs generators fitted on non-zodiac folios; copy scope (zodiac-local vs global pool); calendar structure.

Run: python run_h06_zodiac.py [--seeds 10] [--quick]    (~10 min)
"""
from __future__ import annotations

import argparse
import json
import random
import time

import numpy as np
import pandas as pd

import h06_lib as L
import h06_zodiac as Z

CI = L.CI


def _gen_job(job):
    L.WSR._one_thread()
    name, seed = job
    zm, ring, lab = Z._Z["zm"], Z._Z["ring_real"], Z._Z["lab_real"]
    r, l = Z.gen_zodiac(name, seed, ring, lab, zm)
    st = Z.zodiac_stats(r, l, zm.rest.words, zm.rest.types, zm.rest.units, zm.rest.counter)
    from scipy.stats import ks_2samp
    real_len = [len(Z.SEG(w)) for p in Z.PAGES for w in lab[p]]
    gen_len = [len(Z.SEG(w)) for p in Z.PAGES for w in l[p]]
    st["label_len_ks_vs_real"] = float(ks_2samp(real_len, gen_len).statistic)
    return {"generator": name, "seed": seed, **st}


def main(n_seeds: int = 10, quick: bool = False, workers=None):
    t0 = time.time()
    out = L.RESULTS
    ring, lab = Z.zodiac_data()
    print("zodiac tokens: ring", sum(map(len, ring.values())), "labels", sum(map(len, lab.values())), flush=True)
    zm = Z.ZodiacModels(seed=0)
    Z._Z.update(zm=zm, ring_real=ring, lab_real=lab)
    print(f"models fitted on non-zodiac folios ({time.time() - t0:.0f}s)", flush=True)

    # ---------------------------------------------------------------- A. real statistics (+ page-jackknife SE, + non-zodiac window null)
    jk = Z.jackknife_pages(ring, lab, zm.rest)
    sizes = [len(ring[p]) + len(lab[p]) for p in Z.PAGES]
    nw = Z.null_windows(zm.rest, sizes)
    real = pd.DataFrame([{"stat": k, "label": Z.STAT_LABELS[k], "zodiac": jk["stats"][k], "se_page_jackknife": jk["se"][k],
                          "nonzodiac_window_null_mean": nw.get(k, (np.nan, np.nan))[0], "nonzodiac_window_null_sd": nw.get(k, (np.nan, np.nan))[1]} for k in Z.STAT_LABELS])
    real.to_csv(out / "zodiac_real_stats.csv", index=False)
    nonz_lab = zm.label_words
    ref = {"nonzodiac_labels_n": len(nonz_lab), "nonzodiac_labels_o_initial": float(np.mean([w[0] == "o" for w in nonz_lab])),
           "rest_o_initial": float(np.mean([w[0] == "o" for w in zm.rest.words])), "rest_q_share": float(np.mean(["q" in w for w in zm.rest.words])),
           "nonzodiac_label_hapax": float(np.mean([v == 1 for v in __import__("collections").Counter(nonz_lab).values()])),
           "rest_label_mean_len": float(np.mean([len(Z.SEG(w)) for w in nonz_lab])), "rest_mean_len": float(np.mean([len(Z.SEG(w)) for w in zm.rest.words]))}
    json.dump(ref, open(out / "zodiac_reference_values.json", "w"), indent=1)
    print(real.round(3).to_string(), flush=True)

    # ---------------------------------------------------------------- B. generators
    names = Z.GENERATORS if not quick else Z.GENERATORS[3:6]
    jobs = [(n, s) for n in names for s in range(1, n_seeds + 1)]
    rows = CI.pmap(lambda i: _gen_job(jobs[i]), range(len(jobs)), workers)
    runs = pd.DataFrame(rows)
    runs.to_csv(out / "zodiac_generator_runs.csv", index=False)
    ver = []
    for n in names:
        g = runs[runs.generator == n]
        for k in Z.STAT_LABELS:
            v = CI.interval_verdict(jk["stats"][k], jk["se"][k], g[k].tolist())
            ver.append({"generator": n, "stat": k, "label": Z.STAT_LABELS[k], "zodiac": jk["stats"][k], "se": jk["se"][k], **v})
    ver = pd.DataFrame(ver)
    ver.to_csv(out / "zodiac_generator_verdicts.csv", index=False)
    print(f"generators done ({time.time() - t0:.0f}s)", flush=True)

    # ---------------------------------------------------------------- C. copy locality (real data)
    all_ring_types = [w for p in Z.PAGES for w in ring[p]]
    all_lab_types = [w for p in Z.PAGES for w in lab[p]]
    rest_pool = zm.rest.words
    rest_types = set(rest_pool)
    near_z = Z.near_sets(all_ring_types + all_lab_types, set(all_ring_types + all_lab_types))
    near_r = Z.near_sets(all_ring_types + all_lab_types, rest_types)
    loc = []
    for nm, seqs in (("ring text", ring), ("labels (locus order)", lab)):
        for W in (10, 30):
            r = Z.locality(seqs, near_z, rest_pool, near_r, W=W, perm=300 if nm == "ring text" else 300, seed=1)
            loc.append({"text": nm, "window": W, **r})
    # ordinary MS folios for comparison: 12 random folios of >= 60 tokens, same procedure, repeated
    rng = random.Random(5)
    folios = [e for e in zm.entries if len(e["words"]) >= 60]
    base = []
    for rep in range(10):
        pick = rng.sample(folios, 12)
        seqs = {f"x{i}": e["words"][:90] for i, e in enumerate(pick)}
        ty = [w for s in seqs.values() for w in s]
        nz = Z.near_sets(ty, set(ty))
        nr = Z.near_sets(ty, rest_types)
        base.append(Z.locality(seqs, nz, rest_pool, nr, W=30, perm=0, seed=rep))
    loc.append({"text": "12 random ordinary MS folios (first 90 tokens), mean of 10 draws", "window": 30,
                **{k: float(np.mean([b[k] for b in base])) for k in ("local", "other_pages", "nonzodiac", "diff_local_minus_other", "n_tokens")},
                "diff_se_jackknife": float(np.std([b["diff_local_minus_other"] for b in base], ddof=1))})
    pd.DataFrame(loc).to_csv(out / "zodiac_copy_locality.csv", index=False)
    print(pd.DataFrame(loc).round(4).to_string(), flush=True)

    # ---------------------------------------------------------------- D. scope fits: copy-and-modify from a page-local vs window vs global zodiac vs global (+P) pool
    pages = Z.PAGES
    odd, even = pages[0::2], pages[1::2]
    sc_rows = []
    for scope in ("page", "window", "global", "global+P"):
        for rep in range(4):                                   # 4 independent searches per scope (search noise)
            ins = Z.scope_fit(zm, ring, scope, pages, [], seed=3 + 10 * rep, workers=workers)
            cv1 = Z.scope_fit(zm, ring, scope, odd, even, seed=4 + 10 * rep, workers=workers)
            cv2 = Z.scope_fit(zm, ring, scope, even, odd, seed=5 + 10 * rep, workers=workers)
            sc_rows.append({"scope": scope, "search_rep": rep, "in_sample_dist_12_pages": ins["fit_dist"], "heldout_dist_fit_odd_eval_even": cv1["heldout_dist"],
                            "heldout_dist_fit_even_eval_odd": cv2["heldout_dist"], "heldout_dist_mean": float(np.mean([cv1["heldout_dist"], cv2["heldout_dist"]])),
                            **{f"p:{k}": v for k, v in ins["params"].items() if k != "p_pool"}})
            print(sc_rows[-1], flush=True)
    # the P-fitted (non-zodiac) engine for reference: no refit
    pd.DataFrame(sc_rows).to_csv(out / "zodiac_copy_scope_fits.csv", index=False)

    # ---------------------------------------------------------------- D2. zodiac as one more section: fit on half the zodiac pages, test on the other half
    cv = Z.zodiac_cv(zm, ring, lab, n_seeds=n_seeds)
    cv.to_csv(out / "zodiac_cv_verdicts.csv", index=False)
    print(cv.groupby(["fold", "generator"]).apply(lambda g: (g.verdict == "≈").sum()), flush=True)

    # ---------------------------------------------------------------- E. calendar structure
    cal = []
    allp = {p: ring[p] + lab[p] for p in pages}
    for nm, toks, kind in (("ring text, type Jaccard", ring, "jaccard"), ("labels, type Jaccard", lab, "jaccard"), ("ring text, unit-bigram cosine", ring, "cosine"),
                           ("labels, unit-bigram cosine", lab, "cosine"), ("ring+labels, unit-bigram cosine", allp, "cosine")):
        M = Z.page_similarity(toks, kind)
        cal.append({"similarity": nm, **Z.calendar_tests(M, n_perm=20000, seed=7)})
        np.savetxt(out / f"zodiac_page_similarity_{nm.split(',')[0].replace(' ', '_').replace('+', '_')}_{kind}.csv", M, delimiter=",", fmt="%.4f")
    pd.DataFrame(cal).to_csv(out / "zodiac_calendar_tests.csv", index=False)
    print(pd.DataFrame(cal).round(4).to_string(), flush=True)
    print("done", time.time() - t0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    main(a.seeds, a.quick, a.workers)
