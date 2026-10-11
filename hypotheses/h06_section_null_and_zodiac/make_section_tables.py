"""Tables + figure for h06 part 1 from results/section_variants_stats.csv (+ step-2 CSVs of the plaintext-driven hybrids)."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import scipy.stats as sst

import h06_lib as L

CI = L.CI
TOP = L.ROOT / "reports" / "mechanisms" / "hybrid" / "topics"
METRICS = ["nb_bal_acc", "lr_bal_acc", "js", "js_excess", "nb_langA", "nb_langB"]
SEC_METRICS = {"nb_bal_acc": "NB balanced accuracy (5 sections)", "lr_bal_acc": "LR balanced accuracy", "js": "between-section JS (bits)", "js_excess": "JS excess over label-permutation null",
               "nb_langA": "within-Currier-A NB accuracy", "nb_langB": "within-Currier-B NB accuracy"}


def ms_reference() -> tuple[dict, dict]:
    ms = pd.read_csv(TOP / "ms408_section_stats.csv").iloc[0]
    val = {m: float(ms[m]) for m in METRICS}
    se = {"nb_bal_acc": float(ms["unc_nb_bal_acc_se"]), "lr_bal_acc": float(ms["unc_lr_bal_acc_se"]), "js": float(ms["unc_js_se"]), "js_excess": float(ms["unc_js_se"]),
          "nb_langA": float(ms["unc_nb_bal_acc_se"]), "nb_langB": float(ms["unc_nb_bal_acc_se"])}      # no separate bootstrap for the within-language accuracies: overall SE reused
    val.update(nb_shift_null_max=float(ms["nb_shift_null_max"]), nb_shift_null_mean=float(ms["nb_shift_null_mean"]), keyword_overlap=float(ms["keyword_overlap"]))
    return val, se


def shared_k() -> dict:
    d = L.HR.ms_data()
    ctx = L.HR.Ctx(d["words"])
    return {"grammar_params": int(ctx.n_params()), "engine_params": 6}


def tci(x, level=0.95):
    x = np.asarray(x, float)
    n = len(x)
    if n < 2:
        return float("nan"), float("nan")
    h = sst.t.ppf(0.5 + level / 2, n - 1) * x.std(ddof=1) / math.sqrt(n)
    return float(x.mean() - h), float(x.mean() + h)


def build():
    ms, se = ms_reference()
    sk = shared_k()
    runs = pd.read_csv(L.RESULTS / "section_variants_stats.csv")
    kc = pd.read_csv(L.RESULTS / "section_variant_parameter_counts.csv").groupby("variant", sort=False).mean(numeric_only=True)
    tp = pd.read_csv(TOP / "generated_section_stats.csv")
    rows = []
    sets = [(v, g, "section-varying, no plaintext" if not v.startswith("C0g") else "no plaintext, no section dependence", float(kc.loc[v, "k_group_specific"]) if v in kc.index else 0.0, "sv")
            for v, g in runs.groupby("variant", sort=False)]
    # plaintext-driven hybrids and parents from step 2 (parameters: 6 engine params, + grammar for the codebook; Naibbe tables are fixed, not fitted)
    for m, g in tp.groupby("model", sort=False):
        k = {"A1": 6, "A2": 6 + sk["grammar_params"], "B|": 6, "C0": 6 + sk["grammar_params"], "SC": 0}.get(m[:2], 0)
        if m == "SC fitted":
            k = len(json.loads((L.ROOT / "reports" / "mechanisms" / "selfcitation_best_params.json").read_text()))      # fitted Java generator parameters
        grp = "plaintext-driven hybrid" if m[:2] in ("A1", "A2", "B|") else "control / parent"
        sets.append((f"[step 2] {m}", g, grp, float(k), "step2"))
    for name, g, family, k_group, src in sets:
        row = {"variant": name, "family": family, "n_runs": len(g), "k_group_specific": k_group}
        k_shared = sk["grammar_params"] + sk["engine_params"] if src == "sv" else (k_group if src == "step2" else 0)
        row["k_total_fitted_to_ms408"] = k_group + k_shared if src == "sv" else k_group
        chi2 = 0.0
        n_ok = 0
        for m in METRICS:
            x = g[m].to_numpy(float)
            lo, hi = tci(x)
            v = CI.interval_verdict(ms[m], se[m], x.tolist())
            row[f"{m}_mean"], row[f"{m}_ci_lo"], row[f"{m}_ci_hi"], row[f"{m}_z"], row[f"{m}_verdict"] = float(x.mean()), lo, hi, v["z"], v["verdict"]
            chi2 += v["z"] ** 2 if not math.isnan(v["z"]) else 0.0
            n_ok += v["verdict"] == "≈"
        row["chi2_6_section_metrics"] = chi2
        row["n_reproduced_of_6"] = n_ok
        row["aic_like"] = chi2 + 2 * row["k_total_fitted_to_ms408"]
        row["exceeds_ms_shift_null_max"] = float((g["nb_bal_acc"] > ms["nb_shift_null_max"]).mean())
        row["own_shift_null_p_median"] = float(g["nb_shift_p"].median()) if "nb_shift_p" in g else float("nan")
        row["keyword_overlap_mean"] = float(g["keyword_overlap"].mean())
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(L.RESULTS / "section_summary_vs_ms408.csv", index=False)
    # sweep (accuracy vs parameter count), restricted to the section-varying family
    sweep = df[df.family.str.startswith(("section", "no plaintext")) | df.variant.str.startswith("C0g")][["variant", "k_group_specific", "nb_bal_acc_mean", "nb_bal_acc_ci_lo", "nb_bal_acc_ci_hi", "js_mean", "js_excess_mean"]]
    sweep.to_csv(L.RESULTS / "section_param_sweep.csv", index=False)
    # alignment test: aligned vs random-block with the same recipe (paired by seed)
    pairs = [("EUP50 per-section engine+units+pool 50", "RAND EUP50 random folio blocks (null)"), ("EUP200 per-section engine+units+pool 200", "RAND EUP200 random folio blocks (null)"),
             ("U per-section favoured units", "RAND U random folio blocks, all units (null)"), ("P200 per-section pool of 200 types", "RAND P200 random folio blocks (null)")]
    al = []
    for a, b in pairs:
        x = runs[runs.variant == a].sort_values("seed").nb_bal_acc.to_numpy()
        y = runs[runs.variant == b].sort_values("seed").nb_bal_acc.to_numpy()
        t = sst.ttest_ind(x, y, equal_var=False)
        al.append({"aligned": a, "random_blocks": b, "acc_aligned": x.mean(), "acc_random": y.mean(), "diff": x.mean() - y.mean(), "welch_t": t.statistic, "welch_p": t.pvalue})
    pd.DataFrame(al).to_csv(L.RESULTS / "section_alignment_vs_random_blocks.csv", index=False)
    return df, sweep, ms


def figure(df, sweep, ms):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    col = {"section-varying, no plaintext": "tab:blue", "no plaintext, no section dependence": "grey", "plaintext-driven hybrid": "tab:red", "control / parent": "tab:olive"}
    for _, r in df.iterrows():
        rand = r.variant.startswith("RAND") or r.variant.startswith("LANG")
        c = "tab:orange" if rand else col.get(r.family, "k")
        x = max(r.k_group_specific, 0.8)
        for a, (m, lab) in zip(ax, (("nb_bal_acc", "NB balanced accuracy"), ("js", "between-section JS (bits)"))):
            a.errorbar(x, r[f"{m}_mean"], yerr=[[r[f"{m}_mean"] - r[f"{m}_ci_lo"]], [r[f"{m}_ci_hi"] - r[f"{m}_mean"]]], fmt="o", color=c, ms=5, capsize=2)
            if not r.variant.startswith("[step 2]") or r.family == "plaintext-driven hybrid":
                a.annotate(r.variant.split(" ")[0].replace("[step", "").replace("2]", "") if not r.variant.startswith("[step 2]") else r.variant[9:], (x, r[f"{m}_mean"]), fontsize=6, xytext=(3, 3), textcoords="offset points")
            a.set_xscale("log")
            a.set_xlabel("fitted parameters (blue/orange: group-specific only; red/olive: all fitted; log, 1 = none)")
            a.set_ylabel(lab)
    for a, m in zip(ax, ("nb_bal_acc", "js")):
        a.axhline(ms[m], color="k", ls="--", lw=1)
        a.text(1.0, ms[m], " MS 408", fontsize=8, va="bottom")
    ax[0].axhline(ms["nb_shift_null_max"], color="grey", ls=":", lw=1)
    ax[0].set_title("section signal vs parameter cost (blue: section-varying, no plaintext; orange: language-only / random-block nulls;\nred: plaintext-driven hybrids; dotted = MS 408 drift null max)", fontsize=8)
    fig.tight_layout()
    fig.savefig(L.FIG / "fig1_section_signal_vs_parameters.png", dpi=140)


if __name__ == "__main__":
    df, sweep, ms = build()
    figure(df, sweep, ms)
    pd.set_option("display.width", 250)
    print(df[["variant", "family", "k_group_specific", "k_total_fitted_to_ms408", "nb_bal_acc_mean", "nb_bal_acc_verdict", "js_mean", "js_verdict", "js_excess_mean", "nb_langA_mean", "nb_langB_mean",
              "n_reproduced_of_6", "chi2_6_section_metrics", "aic_like"]].round(3).to_string())
    print(pd.read_csv(L.RESULTS / "section_alignment_vs_random_blocks.csv").round(4).to_string())
