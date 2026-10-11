"""Build summary tables and figures from results/*.csv (run after run_h02.py). Writes results/*.csv summaries and figures/*.png."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h02_lib as L  # noqa: E402

RES, FIG = L.HERE / "results", L.HERE / "figures"
POSITIONAL_ORDERS = ("slot", "slotgrammar", "seriation", "final", "pos", "cluster", "smooth", "slotmono")
REG_STATS = ["mono_frac", "arch_frac", "mean_abs_int_st", "contour_H5", "motif_top5", "zlib_ratio"]


def is_positional(m: str) -> bool:
    parts = m.split("_")
    return any(p in POSITIONAL_ORDERS or p.startswith("cluster") for p in parts[1:])


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ms = pd.read_csv(RES / "map_stats.csv")
    long = pd.read_csv(RES / "map_table_long.csv")
    sec = pd.read_csv(RES / "section_tests.csv")
    desc = pd.read_csv(RES / "maps_description.csv").set_index("map")
    out = {}

    # ---------------------------------------------------------------- wide tables (the deliverable: every candidate map)
    for tok in ("T1", "T2"):
        w = long[long.tok == tok].pivot(index="unit", columns="map", values="hz").round(1)
        cnt = long[(long.tok == tok) & (long["map"] == "c_pos")].set_index("unit")["count_in_text"]
        w.insert(0, "count_in_text", cnt)
        w = w.sort_values("count_in_text", ascending=False)
        for u, hz_ in L.SHEET.items():
            if u in w.index:
                w.loc[u, "sheet_hz_printed"] = hz_
        cols = ["count_in_text"] + (["sheet_hz_printed"] if "sheet_hz_printed" in w else []) + [c for c in desc.index if c in w.columns]
        w[cols].to_csv(RES / f"map_table_wide_{tok}.csv")

    # ---------------------------------------------------------------- MS summary per map
    ms["group"] = ms["map"].str[0]
    ms["positional_fit"] = ms["map"].map(is_positional)
    ms["score_vs_shuf"] = ms.apply(lambda r: L.STAT_DIR[r["stat"]] * (r["obs"] - r["shuf_mean"]), axis=1)
    ms["score_vs_rand"] = ms.apply(lambda r: L.STAT_DIR[r["stat"]] * (r["obs"] - r["rand_mean"]), axis=1)
    ms["z_rand_dir"] = ms.apply(lambda r: L.STAT_DIR[r["stat"]] * r["z_rand"], axis=1)
    ms["z_shuf_dir"] = ms.apply(lambda r: L.STAT_DIR[r["stat"]] * r["z_shuf"], axis=1)
    R_ms = None
    rows = []
    for tok in ("T1", "T2"):
        sub = ms[(ms.text == "MS408") & (ms.tok == tok)]
        for m, g in sub.groupby("map"):
            gi = g.set_index("stat")
            row = {"tok": tok, "map": m, "group": m[0], "positional_fit": is_positional(m), "n_pitches": int(g.n_pitches.iloc[0])}
            n_both = 0
            for s in REG_STATS:
                r = gi.loc[s]
                row[f"{s}_obs"] = r["obs"]
                row[f"{s}_shuf_mean"] = r["shuf_mean"]
                row[f"{s}_rand_mean"] = r["rand_mean"]
                both = (r["p_shuf_regular"] <= 0.01) and (r["p_rand_regular"] <= 0.01)
                row[f"{s}_beats_both_nulls"] = bool(both)
                n_both += both
            row["n_regularity_stats_beating_both_nulls"] = n_both
            rows.append(row)
    msum = pd.DataFrame(rows)
    # ---------------------------------------------------------------- MS vs controls under the same map
    nat = ms[(ms.family == "natural") & (ms.tok == "C")]
    cip = ms[(ms.family == "cipher") & (ms.tok == "C")]
    gen = ms[(ms.family == "generator") & (ms.tok == "C")]
    rows = []
    for tok in ("T1", "T2"):
        sub = ms[(ms.text == "MS408") & (ms.tok == tok)]
        for (m, s), g in sub.groupby(["map", "stat"]):
            if s not in REG_STATS:
                continue
            sc = float(g.score_vs_shuf.iloc[0])
            def rng_(df):
                d = df[(df["map"] == m) & (df["stat"] == s)].score_vs_shuf.dropna()
                return (float(d.min()), float(d.max()), len(d)) if len(d) else (np.nan, np.nan, 0)
            a, b, n = rng_(nat)
            c, d_, n2 = rng_(cip)
            e, f, n3 = rng_(gen)
            rows.append({"tok": tok, "map": m, "stat": s, "ms_score": sc, "natural_min": a, "natural_max": b, "n_natural": n,
                         "cipher_min": c, "cipher_max": d_, "generator_min": e, "generator_max": f,
                         "ms_above_all_natural": bool(sc > b), "ms_above_all_controls": bool(sc > max(b, d_, f)),
                         "ms_over_natural_max_ratio": (sc / b) if b and b > 0 else np.nan, "positional_fit": is_positional(m)})
    vs = pd.DataFrame(rows)
    vs.to_csv(RES / "ms_vs_controls_scores.csv", index=False)
    cnt = vs.groupby(["tok", "map"]).agg(n_stats_ms_above_all_natural=("ms_above_all_natural", "sum"), n_stats_ms_above_all_controls=("ms_above_all_controls", "sum")).reset_index()
    msum = msum.merge(cnt, on=["tok", "map"])
    msum["description"] = msum["map"].map(desc["description"])
    msum.to_csv(RES / "ms_map_summary.csv", index=False)

    # ---------------------------------------------------------------- sections / Currier A-B
    sec["group"] = sec["map"].str[0]
    sec["positional_fit"] = sec["map"].map(is_positional)
    sec["section_beats_random_p95"] = (sec.eta2_section > sec.eta2_rand_p95) & (sec.p_section_perm <= 0.01)
    sec["ab_beats_random_p95"] = (sec.ab_d.abs() > sec.abs_d_rand_p95) & (sec.p_ab_perm <= 0.01)
    secs = []
    for (tok, st_), g in sec.groupby(["tok", "folio_stat"]):
        secs.append({"tok": tok, "folio_stat": st_, "n_maps": len(g), "n_section_p_le_0.01": int((g.p_section_perm <= .01).sum()),
                     "n_section_beats_random_p95": int(g.section_beats_random_p95.sum()), "n_ab_p_le_0.01": int((g.p_ab_perm <= .01).sum()),
                     "n_ab_beats_random_p95": int(g.ab_beats_random_p95.sum()), "median_eta2": float(g.eta2_section.median()),
                     "median_eta2_rand": float(g.eta2_rand_median.median()), "max_eta2": float(g.eta2_section.max()),
                     "best_map_section": g.sort_values("eta2_section", ascending=False)["map"].iloc[0]})
    pd.DataFrame(secs).to_csv(RES / "section_summary.csv", index=False)
    sec.to_csv(RES / "section_tests_flagged.csv", index=False)

    # ---------------------------------------------------------------- T1 vs T2 consistency
    p1 = msum[msum.tok == "T1"].set_index("map")
    p2 = msum[msum.tok == "T2"].set_index("map")
    common = p1.index.intersection(p2.index)
    out["t1_t2_corr_mono"] = float(np.corrcoef(p1.loc[common, "mono_frac_obs"], p2.loc[common, "mono_frac_obs"])[0, 1])

    # ---------------------------------------------------------------- figures
    t1 = ms[(ms.text == "MS408") & (ms.tok == "T1") & ms["stat"].isin(REG_STATS)]
    z = t1.pivot(index="map", columns="stat", values="z_rand_dir")[REG_STATS]
    order = sorted(z.index, key=lambda m: (m[0], m))
    fig, ax = plt.subplots(figsize=(7.5, 11))
    im = ax.imshow(np.clip(z.loc[order].values, -15, 15), cmap="RdBu_r", vmin=-15, vmax=15, aspect="auto")
    ax.set_xticks(range(len(REG_STATS)), REG_STATS, rotation=35, ha="right")
    ax.set_yticks(range(len(order)), [("* " if is_positional(m) else "  ") + m for m in order], fontsize=7)
    ax.set_title("MS 408: how much more melodically regular than random re-assignments\n(z vs 120 random permutations of the same pitches; + = more regular;\n* = map fitted to positional behaviour, circular)", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=.5)
    fig.tight_layout()
    fig.savefig(FIG / "ms_z_vs_random_map.png", dpi=120)
    plt.close(fig)

    reps = ["c_pos", "b_major12_slot", "d_smooth", "a_slot_ext", "b_major12_freq", "c_entropy"]
    fig, axes = plt.subplots(2, 3, figsize=(13, 6.5))
    for ax, m in zip(axes.ravel(), reps):
        sub = ms[(ms["map"] == m) & (ms["stat"] == "mono_frac") & (ms.tok.isin(["C", "T1"]))].copy()
        sub = sub.sort_values(["family", "text"])
        cols = {"ms408": "red", "natural": "C0", "cipher": "C2", "generator": "C1"}
        xs = np.arange(len(sub))
        ax.bar(xs, sub.obs, color=[cols[f] for f in sub.family])
        ax.plot(xs, sub.shuf_mean, "k_", markersize=12, mew=2)
        ax.plot(xs, sub.rand_mean, "m_", markersize=12, mew=2)
        ax.set_xticks(xs, sub.text, rotation=75, fontsize=6)
        ax.set_title(f"{m}: share of monotone words (len>=3)\nblack = within-word shuffle null, magenta = random-map null", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "mono_frac_ms_vs_controls.png", dpi=120)
    plt.close(fig)

    osup = pd.read_csv(RES / "ordering_support_of_the_8_values.csv")
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar(osup.ordering, osup.spearman_rho, color=["C3" if o == "printed_row_order" else "C0" for o in osup.ordering])
    for i, (r_, p_) in enumerate(zip(osup.spearman_rho, osup.holm_p_two_sided)):
        ax.text(i, r_ + (0.03 if r_ >= 0 else -0.08), f"Holm p={p_:.2f}", ha="center", fontsize=7)
    ax.set_ylabel("Spearman rho (Hz vs rank of the 8 units)")
    ax.set_title("Which ordering of the manuscript's units do the sheet's 8 Hz values follow?")
    plt.xticks(rotation=30)
    fig.tight_layout()
    fig.savefig(FIG / "ordering_support.png", dpi=120)
    plt.close(fig)

    # piano-roll examples
    t = L.build_ms("T1")
    st = L.unit_stats(t, np.ones(len(t.L), bool), slot_grammar=True, seed=1)
    from msdecipher.segment import Segmenter, PRESETS
    seg = Segmenter(PRESETS["collapsed"])
    words = ["qokeedy", "chedy", "daiin", "shedy", "qokaiin", "okeol", "otaiin"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=False)
    for ax, m in zip(axes, ["c_pos", "b_major12_freq", "d_smooth"]):
        pv = L.build_map(m, st, t.inv)
        idx = {u: i for i, u in enumerate(t.inv)}
        for k, w in enumerate(words):
            us = seg(w)
            y = [12 * math.log2(pv[idx[u]] / L.F0) for u in us]
            ax.plot(range(len(y)), y, "o-", label=w, ms=4)
        ax.set_title(f"{m}: pitch (semitones above 174 Hz) along a word", fontsize=8)
        ax.set_xlabel("unit position in word")
    axes[0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(FIG / "word_contours_examples.png", dpi=120)
    plt.close(fig)

    s1 = sec[(sec.tok == "T1") & (sec.folio_stat == "meanP")]
    fig, ax = plt.subplots(figsize=(6, 4.2))
    ax.scatter(s1.eta2_rand_p95, s1.eta2_section, c=["red" if p else "C0" for p in s1.positional_fit], s=14)
    lim = max(s1.eta2_section.max(), s1.eta2_rand_p95.max()) * 1.05
    ax.plot([0, lim], [0, lim], "k--", lw=.8)
    ax.set_xlabel("eta^2 of section, 95th pct over random maps")
    ax.set_ylabel("eta^2 of section, the map")
    ax.set_title("Per-folio mean pitch vs illustration section (T1)\nred = positional-fitted maps; above diagonal = beats random maps", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "section_eta2_vs_random.png", dpi=120)
    plt.close(fig)

    json.dump(out, open(RES / "report_extras.json", "w"), indent=1)
    print("report built")


if __name__ == "__main__":
    main()
