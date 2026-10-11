"""Tables + figures for h06 part 2 from results/zodiac_*.csv."""
from __future__ import annotations

import numpy as np
import pandas as pd

import h06_lib as L
import h06_zodiac as Z

R = L.RESULTS
KEY = ["zod_js_vs_rest", "zod_oov_share", "label_o_initial", "ring_o_initial", "label_q_share", "ring_q_share", "rep_ring", "rep_label", "label_hapax_types", "label_len_mean",
       "jaccard_ring", "jaccard_label", "ring_label_unit_js"]


def short(g: str) -> str:
    return g.split(" (")[0].split(",")[0][:34]


def build():
    ver = pd.read_csv(R / "zodiac_generator_verdicts.csv")
    summ = []
    for g, d in ver.groupby("generator", sort=False):
        z = d.z.replace([np.inf, -np.inf], np.nan).clip(-20, 20)
        summ.append({"generator": g, "n_reproduced_of_22": int((d.verdict == "≈").sum()), "n_above": int((d.verdict == "↑").sum()), "n_below": int((d.verdict == "↓").sum()),
                     "rms_z_clipped20": float(np.sqrt(np.nanmean(z ** 2))), "median_abs_z": float(np.nanmedian(np.abs(z)))})
    summ = pd.DataFrame(summ)
    summ.to_csv(R / "zodiac_generator_summary.csv", index=False)
    wide = ver.assign(cell=lambda d: d.family_mean.map("{:.3f}".format) + " " + d.verdict).pivot(index="label", columns="generator", values="cell")
    wide.insert(0, "zodiac (± page-jackknife SE)", ver.drop_duplicates("stat").set_index("label").apply(lambda r: f"{r.zodiac:.3f} ± {r.se:.3f}", axis=1))
    wide.to_csv(R / "zodiac_generator_table.csv")
    cal = pd.read_csv(R / "zodiac_calendar_tests.csv")                # Holm over all 15 calendar p-values (5 similarity matrices x 3 statistics)
    cal = cal.drop(columns=[c for c in cal if c.startswith("holm_")])
    pcols = ["p_circular", "p_partial", "p_adjacent_minus_distant"]
    allp = np.concatenate([cal[c].to_numpy() for c in pcols])
    o = np.argsort(allp)
    adj = np.empty(len(allp))
    run = 0.0
    for r, i in enumerate(o):
        run = max(run, (len(allp) - r) * allp[i])
        adj[i] = min(1.0, run)
    for j, c in enumerate(pcols):
        cal["holm_" + c] = adj[j * len(cal):(j + 1) * len(cal)]
    cal.to_csv(R / "zodiac_calendar_tests.csv", index=False)
    cv = pd.read_csv(R / "zodiac_cv_verdicts.csv")
    cs = cv.groupby(["generator", "k_zodiac_params"]).apply(lambda g: pd.Series({"n_reproduced_mean_of_22_per_half": (g.verdict == "≈").sum() / g.fold.nunique(),
                                                                                  "rms_z_clipped20": float(np.sqrt(np.nanmean(g.z.replace([np.inf, -np.inf], np.nan).clip(-20, 20) ** 2)))})).reset_index()
    cs.to_csv(R / "zodiac_cv_summary.csv", index=False)
    sc = pd.read_csv(R / "zodiac_copy_scope_fits.csv").groupby("scope", sort=False).agg(
        in_sample_mean=("in_sample_dist_12_pages", "mean"), in_sample_sd=("in_sample_dist_12_pages", "std"), heldout_mean=("heldout_dist_mean", "mean"), heldout_sd=("heldout_dist_mean", "std"),
        best_heldout=("heldout_dist_mean", "min"), p_copy_median=("p:p_copy", "median")).reset_index()
    sc.to_csv(R / "zodiac_copy_scope_summary.csv", index=False)
    return ver, summ, cs, sc


def figures(ver, summ):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # fig 2: key zodiac statistics, real vs generators
    fig, axs = plt.subplots(3, 5, figsize=(17, 8))
    gens = list(dict.fromkeys(ver.generator))
    for ax, k in zip(axs.flat, KEY):
        d = ver[ver.stat == k]
        real, se = d.zodiac.iloc[0], d.se.iloc[0]
        ax.axhspan(real - 1.96 * se, real + 1.96 * se, color="tab:red", alpha=0.2)
        ax.axhline(real, color="tab:red", lw=1)
        ax.errorbar(range(len(d)), d.family_mean, yerr=d.family_sd, fmt="o", color="k", ms=4, capsize=2)
        ax.set_title(Z.STAT_LABELS[k], fontsize=8)
        ax.set_xticks(range(len(d)))
        ax.set_xticklabels([f"G{gens.index(g) + 1}" for g in d.generator], fontsize=7)
    for ax in axs.flat[len(KEY):]:
        ax.axis("off")
    axs.flat[len(KEY)].text(0, 1, "\n".join(f"G{i + 1}: {g[:60]}" for i, g in enumerate(gens)), fontsize=6.5, va="top")
    fig.suptitle("Zodiac pages: real value (red, ±1.96 SE page-jackknife) vs generators fitted on non-zodiac text (mean ± SD over 10 seeds)", fontsize=10)
    fig.tight_layout()
    fig.savefig(L.FIG / "fig2_zodiac_stats_vs_generators.png", dpi=140)
    # fig 3: page similarity vs month, heatmaps and similarity vs circular distance
    fig, axs = plt.subplots(2, 3, figsize=(15, 8))
    mats = {"ring text, type Jaccard": "ring_text_jaccard", "labels, unit-bigram cosine": "labels_cosine", "ring text, unit-bigram cosine": "ring_text_cosine"}
    labels = [f"{Z.SIGN[p][:3]} {p}" for p in Z.PAGES]
    months = [Z.MONTH[p] for p in Z.PAGES]
    for j, (title, f) in enumerate(mats.items()):
        M = np.loadtxt(R / f"zodiac_page_similarity_{f}.csv", delimiter=",")
        ax = axs[0, j]
        ax.imshow(M, cmap="viridis")
        ax.set_xticks(range(12))
        ax.set_xticklabels(labels, rotation=90, fontsize=6)
        ax.set_yticks(range(12))
        ax.set_yticklabels(labels, fontsize=6)
        ax.set_title(title + " (pages in month order)", fontsize=8)
        ax = axs[1, j]
        xs, ys = [], []
        for a in range(12):
            for b in range(a + 1, 12):
                xs.append(Z.circ_dist(months[a], months[b]) + np.random.default_rng(a * 12 + b).uniform(-0.12, 0.12))
                ys.append(M[a, b])
        ax.scatter(xs, ys, s=10)
        ax.set_xlabel("circular month distance (Aquarius/Capricorn missing)")
        ax.set_ylabel("similarity")
        ax.set_title(title, fontsize=8)
    fig.tight_layout()
    fig.savefig(L.FIG / "fig3_zodiac_calendar_similarity.png", dpi=140)
    # fig 4: copy scope
    sc = pd.read_csv(R / "zodiac_copy_scope_fits.csv")
    fig, ax = plt.subplots(figsize=(6, 4))
    for i, (s, g) in enumerate(sc.groupby("scope", sort=False)):
        ax.scatter([i - 0.15] * len(g), g.in_sample_dist_12_pages, color="tab:blue", s=14, label="in-sample (12 pages)" if i == 0 else None)
        ax.scatter([i + 0.15] * len(g), g.heldout_dist_mean, color="tab:red", s=14, label="held-out pages (2-fold)" if i == 0 else None)
    ax.set_xticks(range(4))
    ax.set_xticklabels(["page-local", "recent window", "global zodiac", "global + non-zodiac"], fontsize=8)
    ax.set_ylabel("RMS z over 8 ring statistics (lower = better)")
    ax.legend(fontsize=8)
    ax.set_title("Copy-and-modify scope fits (6 free parameters each, 4 searches)", fontsize=9)
    fig.tight_layout()
    fig.savefig(L.FIG / "fig4_zodiac_copy_scope.png", dpi=140)


if __name__ == "__main__":
    ver, summ, cs, sc = build()
    figures(ver, summ)
    pd.set_option("display.width", 250)
    print(summ.round(2).to_string())
    print(cs.round(2).to_string())
    print(sc.round(3).to_string())
