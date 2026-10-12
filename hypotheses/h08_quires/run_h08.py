"""h08: quire map + quire-level resampling of the key MS 408 confidence intervals.

python hypotheses/h08_quires/run_h08.py [--boot 100] [--workers N]
Writes data/quires.csv and hypotheses/h08_quires/*.csv / results.json.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sst

from msdecipher import controls_ci as CI
from msdecipher import controls_run as CR
from msdecipher import mech_hybrid_run as HR
from msdecipher import mech_hybrid_topics as MT
from msdecipher import quires as Q
from msdecipher.paths import reports_dir

OUT = Path(__file__).resolve().parent
KEY = ["unit_h2", "shuffle_gap_h2", "zipf_mle_s_r10_1000", "heaps_beta_in_order", "heaps_beta_shuffled", "unit_h3",
       "type_token_ratio", "word_entropy_H1"]
# earlier section-signal thresholds (FINDINGS row 8-9)
DRIFT_MAX, NB_BEST_NOPLAIN_LO = 0.611, 0.676
JS_NULL, JS_BEST_GEN = 0.246, 0.357


def verdict(ms, se, mean, sd, n):
    if n < 2 or any(math.isnan(x) for x in (ms, mean, sd)):
        return "?"
    scale = math.sqrt(sd ** 2 * (1 + 1 / n) + se ** 2)
    if scale == 0:
        z = 0.0 if ms == mean else math.copysign(math.inf, ms - mean)
    else:
        z = (ms - mean) / scale
    return "≈" if abs(z) <= sst.t.ppf(.975, n - 1) else ("↑" if z > 0 else "↓")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=100)
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args(argv)
    df, summ = Q.write_quire_map(out_dir=OUT)
    print(f"quire map: {len(df)} pages, {df.quire.nunique()} quires present")

    # ------------------------------------------------ token-level metrics (controls machinery)
    rows, _ = CR.ms_variants()
    named = CR.ms_pages_named()
    pages = [w for _, w in named]
    names = [p for p, _ in named]
    segs = {"collapsed": rows[CR.MS_MAIN][1], "raw": rows[CR.MS_RAW][1]}
    old = pd.read_csv(reports_dir() / "controls" / "ms408_ci.csv")
    comp = pd.read_csv(reports_dir() / "controls" / "comparison.csv").set_index("name")
    point = {"collapsed": comp.loc[CR.MS_MAIN], "raw": comp.loc[CR.MS_RAW]}
    tabs = []
    for level in ("quire", "bifolium"):
        keys = Q.group_units(names, df, level)
        reps = CR.resample_ms_groups(pages, keys, segs, a.boot, a.workers, print, name=level)
        tabs.append(CR.group_ci_table(point, reps, level).set_index(["metric", "units"]))
    new = pd.concat(tabs, axis=1)
    new = new.loc[:, ~new.columns.duplicated()].reset_index()
    m = old.merge(new.drop(columns="estimate"), on=["metric", "units"])
    m["se_quire_used"] = m[["se_used", "se_jack_quire"]].max(axis=1)
    m["ratio_quire_vs_block8"] = m["se_jack_quire"] / m["se_jack_block8"]
    m["ratio_quire_vs_used"] = m["se_jack_quire"] / m["se_used"]
    m["ratio_bifolium_vs_block8"] = m["se_jack_bifolium"] / m["se_jack_block8"]
    m.to_csv(OUT / "ms408_ci_quire.csv", index=False)

    # earlier verdicts recomputed with quire SE (family prediction intervals, verdicts.csv)
    vd = pd.read_csv(reports_dir() / "controls" / "verdicts.csv")
    se_q = {(r.metric, r.units): r.se_quire_used for r in m.itertuples()}
    flips = []
    for r in vd.itertuples():
        for tag in ("collapsed", "raw"):
            se = se_q.get((r.metric, tag), float("nan"))
            v = verdict(getattr(r, f"ms_{tag}"), se, r.family_mean, r.family_sd, r.n_members)
            old_v = getattr(r, f"verdict_{tag}")
            # same formula with the stored (page / 8-page-block) SE, so only the SE change can flip a verdict
            old_re = verdict(getattr(r, f"ms_{tag}"), getattr(r, f"se_{tag}"), r.family_mean, r.family_sd, r.n_members)
            if v != old_re and old_v in ("≈", "↑", "↓"):
                flips.append({"family": r.family, "metric": r.metric, "units": tag, "old": old_v, "new": v,
                              "se_old": getattr(r, f"se_{tag}"), "se_quire": se})
    pd.DataFrame(flips, columns=["family", "metric", "units", "old", "new", "se_old", "se_quire"]).to_csv(
        OUT / "verdict_flips.csv", index=False)

    # ------------------------------------------------ section signal (folio documents)
    d = HR.ms_data()
    layout = MT.folio_layout(d)
    docs = [{**{k: e[k] for k in ("folio", "section", "cls", "lang")}, "words": e["words"]} for e in layout]
    sec = {}
    sec["folio"] = MT.ms_uncertainty(docs, 300)
    for level in ("quire", "bifolium"):
        g = dict(zip(df["page"], Q.group_units(list(df["page"]), df, level)))
        sec[level] = MT.ms_uncertainty(docs, 300, group_of=g)
    X, y, folios, _ = MT.design(docs)
    js = MT.mean_pairwise_js(X, y)
    nb = MT.class_scores(y, MT.cv_predict(X, y, "nb", 0))[0]
    # leak-free held-out NB: quire / bifolium folds
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.naive_bayes import MultinomialNB
    held = {}
    for level in ("quire", "bifolium"):
        accs = []
        for seed in range(5):
            folds = Q.group_folds(folios, df, 5, level, seed, labels=list(y))
            assert Q.leakage(folios, folds, df, level) == 0
            pr = np.empty(len(y), dtype=object)
            for tr, te in folds:
                pr[te] = MultinomialNB(alpha=0.2).fit(X[tr], y[tr]).predict(X[te])
            accs.append(balanced_accuracy_score(y, pr))
        held[level] = (float(np.mean(accs)), float(np.std(accs)))
    secrows = []
    for scheme, u in sec.items():
        for stat, est, key in (("nb_bal_acc", nb, "nb_bal_acc"), ("js", js, "js")):
            se_b = u[f"{key}_se"]
            lo, hi = u[f"{key}_ci"]
            se_j = u.get(f"{key}_jack_se", float("nan"))
            se = se_b if math.isnan(se_j) else max(se_b, se_j)   # repo convention: larger SE, est ± 1.96 SE
            secrows.append({"stat": stat, "scheme": scheme, "estimate": est, "boot_se": se_b, "boot_lo": lo, "boot_hi": hi,
                            "jack_se": se_j, "se_used": se, "ci_lo": est - 1.96 * se, "ci_hi": est + 1.96 * se})
    secdf = pd.DataFrame(secrows)
    secdf.to_csv(OUT / "section_ci_quire.csv", index=False)
    res = {"key_metrics": m[m.metric.isin(KEY)][["metric", "units", "estimate", "se_jack_page", "se_jack_block8",
                                                  "se_used", "se_jack_quire", "boot_se_quire", "se_jack_bifolium",
                                                  "ratio_quire_vs_block8", "ci_lo", "ci_hi", "ci_lo_quire",
                                                  "ci_hi_quire"]].to_dict("records"),
           "n_verdict_flips": len(flips), "flips": flips, "section": secrows,
           "heldout_nb_group_folds": held, "nb_stratified_cv": nb, "js": js,
           "thresholds": {"drift_max": DRIFT_MAX, "nb_best_noplain": NB_BEST_NOPLAIN_LO, "js_null": JS_NULL,
                          "js_best_gen": JS_BEST_GEN}}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float, ensure_ascii=False))
    print(json.dumps(res, indent=1, default=float, ensure_ascii=False)[:6000])


if __name__ == "__main__":
    sys.exit(main())
