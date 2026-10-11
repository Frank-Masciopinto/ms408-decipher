"""Figures and summary tables from results/*.csv (run after run_h03.py)."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import h03_lib as L

RES, FIG = L.HERE / "results", L.HERE / "figures"
FIG.mkdir(exist_ok=True)


def mechanism_table(p):
    """Compare MS 408 with the mechanism controls: Naibbe cipher outputs, self-citation outputs (authors' defaults and fitted) and the slot-grammar generator."""
    rows = []
    groups = {"naibbe": lambda c: c.startswith("naibbe"), "selfcite_default": lambda c: c.startswith("selfcite_default"), "selfcite_fitted": lambda c: c.startswith("selfcite_fitted"),
              "slot_generator": lambda c: c == "gen_slot_grammar", "natural_text": lambda c: c in ("la_vulgate", "la_pliny_herbal", "it_dante", "de_faust", "he_tanakh", "ar_quran"),
              "MS_word_order_shuffled": lambda c: c == "MS408_wordorder_shuffled", "MS_letters_shuffled": lambda c: c == "MS408_letters_shuffled"}
    quantities = [("next_word_first_unit", "DIFF last_unit+slot - last_unit"), ("next_word_slot_pattern", "slot_pattern"), ("next_word_slot_pattern", "DIFF slot_pattern - best_letter_feature(max of 4)"),
                  ("line_position", "slot_pattern"), ("line_position", "DIFF slot_pattern - best_letter_feature(max of 4)"),
                  ("currier_language_AB", "DIFF slot_pattern - best_letter_feature(max of 4)"), ("illustration_section", "DIFF slot_pattern - best_letter_feature(max of 4)")]
    for grammar in ("learned", "zattera"):
        for task, feat in quantities:
            q = p[(p.grammar == grammar) & (p.task == task) & (p.feature == feat)]
            m = q[q.corpus == "MS408"]
            if m.empty:
                continue
            m = m.iloc[0]
            row = {"grammar": grammar, "task": task, "quantity": feat, "MS408": m.gain_bits_per_word, "MS408_ci_lo": m.ci_lo, "MS408_ci_hi": m.ci_hi}
            for g, f in groups.items():
                v = q[q.corpus.map(f)].gain_bits_per_word
                row[f"{g}_min"], row[f"{g}_max"] = (v.min(), v.max()) if len(v) else (np.nan, np.nan)
            mech = q[q.corpus.map(lambda c: groups["naibbe"](c) or groups["selfcite_default"](c) or groups["selfcite_fitted"](c) or groups["slot_generator"](c))].gain_bits_per_word
            row["mechanism_controls_max"] = mech.max() if len(mech) else np.nan
            row["MS_ci_lo_exceeds_all_mechanism_controls"] = bool(len(mech) and m.ci_lo > mech.max())
            rows.append(row)
    pd.DataFrame(rows).to_csv(RES / "mechanism_comparison.csv", index=False)


def main():
    # 1. slot x unit emission heat map of the learned grammar, with the Hz of each slot
    P = pd.read_csv(RES / "slot_emission_matrix_learned.csv")
    tab = pd.read_csv(RES / "slot_unit_hz_table_learned.csv")
    units = [u for u in tab[tab.unit_type == "unit"].sort_values("modal_slot").unit if u in P.columns and tab.set_index("unit").loc[u, "count"] > 300][:30]
    units = sorted(units, key=lambda u: (tab.set_index("unit").loc[u, "modal_slot"], -tab.set_index("unit").loc[u, "count"]))
    M = P[[str(u) for u in units]].values
    fig, ax = plt.subplots(figsize=(10, 4.6))
    im = ax.imshow(M, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(units)), units, fontsize=8)
    ax.set_yticks(range(12), [f"slot {k + 1}  {float(L.slot_hz_log(k)):.0f} Hz  (p_emit {e:.2f})" for k, e in enumerate(P.p_emit)], fontsize=7)
    ax.set_title("Learned 12-slot grammar on MS 408: P(unit | slot); rows carry the slot-index pitch (174 -> 433 Hz)", fontsize=9)
    fig.colorbar(im, shrink=.7)
    fig.tight_layout()
    fig.savefig(FIG / "slot_unit_heatmap.png", dpi=120)
    plt.close(fig)

    # 2. the sheet's Hz against slot position
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, kind in zip(axes, ("learned", "zattera")):
        t = pd.read_csv(RES / f"slot_unit_hz_table_{kind}.csv")
        s = t[t.unit_type == "sheet digraph"].dropna(subset=["mean_slot"])
        sp = pd.read_csv(RES / f"sheet_slot_order_spearman_{kind}.csv").set_index("variant").loc["mean_slot"]
        ax.scatter(s.mean_slot, s.sheet_hz, c="C3")
        for _, r in s.iterrows():
            ax.annotate(r.unit, (r.mean_slot, r.sheet_hz), xytext=(4, 3), textcoords="offset points")
        xs = np.linspace(1, 12, 20)
        ax.plot(xs, sp.intercept_hz + sp.slope_hz_per_slot * xs, "k--", lw=.8)
        ax.set_xlabel("mean slot of the digraph's two letters (1-12)")
        ax.set_ylabel("Hz printed on the sheet")
        ax.set_title(f"{kind} slots: rho = {sp.spearman_rho:.2f} (n={int(sp.n_units)}), Fisher 95% CI [{sp.fisher_ci_lo:.2f}, {sp.fisher_ci_hi:.2f}],\nexact permutation p (two-sided) = {sp.p_two_sided_perm:.3f}; R2 = {sp.r2_linear:.2f}", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "sheet_hz_vs_slot.png", dpi=120)
    plt.close(fig)

    # 3. pattern rank-frequency
    rf = pd.read_csv(RES / "pattern_rank_frequency.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, kind in zip(axes, ("learned", "zattera")):
        for name, g in rf[rf.grammar == kind].groupby("corpus"):
            if name.startswith("naibbe__la_vulgate_2") or name.startswith("naibbe__la_vulgate_3") or "_s2" in name or "_s3" in name or name == "MS408_wordorder_shuffled" or name == "naibbe__it_dante_1":
                continue
            lw, col = (2.5, "red") if name == "MS408" else (1, None)
            ax.loglog(g["rank"], g["count"] / g["count"].sum(), label=name, lw=lw, color=col)
        ax.set_xlabel("pattern rank")
        ax.set_ylabel("share of covered tokens (top 400 patterns, normalised on those)")
        ax.set_title(f"slot-occupancy pattern vocabulary, {kind} slots (held-out words)", fontsize=9)
    axes[0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(FIG / "pattern_zipf.png", dpi=120)
    plt.close(fig)

    # 4. predictive gains: slot pattern vs same-capacity letter feature
    p = pd.read_csv(RES / "predictive_gains.csv")
    BL = "DIFF slot_pattern - best_letter_feature(max of 4)"
    d = p[p.feature.isin([BL, "DIFF last_unit+slot - last_unit+second_penult"])]
    tasks = [("next_word_first_unit", "DIFF last_unit+slot - last_unit+second_penult"), ("next_word_slot_pattern", BL),
             ("line_position", BL), ("currier_language_AB", BL),
             ("illustration_section", BL)]
    fig, axes = plt.subplots(1, 5, figsize=(17, 6), sharey=False)
    for ax, (task, feat) in zip(axes, tasks):
        g = d[(d.task == task) & (d.feature == feat) & (d.grammar == "learned")].copy()
        gz = d[(d.task == task) & (d.feature == feat) & (d.grammar == "zattera")].copy()
        order = ["MS408"] + sorted(set(g.corpus) - {"MS408"})
        ys = []
        for i, name in enumerate(order[::-1]):
            for dx, df, col in ((0.15, g, "C0"), (-0.15, gz, "C1")):
                r = df[df.corpus == name]
                if len(r):
                    r = r.iloc[0]
                    ax.errorbar(r.gain_bits_per_word, i + dx, xerr=[[r.gain_bits_per_word - r.ci_lo], [r.ci_hi - r.gain_bits_per_word]], fmt="o", color=col, ms=3, lw=1)
        ax.set_yticks(range(len(order)), order[::-1], fontsize=6)
        ax.axvline(0, color="k", lw=.6)
        ax.set_title(f"{task}\n{feat.replace('DIFF ', '')}", fontsize=7)
        ax.set_xlabel("held-out gain difference, bits/word (95% CI)", fontsize=7)
    axes[0].plot([], [], "o", color="C0", label="learned 12 slots")
    axes[0].plot([], [], "o", color="C1", label="Zattera slots")
    axes[0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(FIG / "predictive_gain_slot_vs_letters.png", dpi=110)
    plt.close(fig)

    # 5. CV profile per slot and syllable-like statistics
    prof = pd.read_csv(RES / "slot_cv_profiles.csv")
    pv = prof.pivot_table(index=["corpus", "grammar"], columns="slot", values="vowel_like_share")
    rows = [("MS408", "learned"), ("MS408", "zattera"), ("la_vulgate", "learned"), ("it_dante", "learned"), ("de_faust", "learned"), ("he_tanakh", "learned"), ("ar_quran", "learned"),
            ("gen_slot_grammar", "learned"), ("naibbe__la_vulgate_1", "learned"), ("selfcite_default_s1", "learned"), ("MS408_letters_shuffled", "learned")]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    im = ax.imshow(pv.loc[rows].values, aspect="auto", cmap="coolwarm", vmin=0, vmax=1)
    ax.set_yticks(range(len(rows)), [f"{a} [{b}]" for a, b in rows], fontsize=7)
    ax.set_xticks(range(12), range(1, 13))
    ax.set_xlabel("slot")
    ax.set_title("share of vowel-like units (Sukhotin) in each slot; blue = consonant-like, red = vowel-like", fontsize=9)
    fig.colorbar(im, shrink=.7)
    fig.tight_layout()
    fig.savefig(FIG / "slot_vowel_profile.png", dpi=120)
    plt.close(fig)

    s = pd.read_csv(RES / "syllable_overview.csv")
    s = s[s.grammar == "learned"]
    s = s[~s.corpus.str.contains("wordorder")]
    s["slot_excess_norm"] = (s.slot_segregation_index - s.slot_null_mean) / (1 - s.slot_null_mean)
    s.to_csv(RES / "syllable_overview_normalised.csv", index=False)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    for ax, col, ttl in zip(axes, ["cv_switch_excess", "nuclei_per_extra_unit_slope", "slot_excess_norm"],
                            ["C/V switch rate minus shuffled-in-word", "vowel-like runs (nuclei) per extra unit", "slot C/V segregation, normalised excess over label-permutation null"]):
        ss = s.sort_values(col)
        ax.barh(ss.corpus, ss[col], color=["red" if c == "MS408" else "C0" for c in ss.corpus])
        ax.tick_params(axis="y", labelsize=6)
        ax.set_title(ttl, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "syllable_like_statistics.png", dpi=120)
    plt.close(fig)

    # 6. held-out bits per word, slot vs bigram
    o = pd.read_csv(RES / "heldout_overview.csv")
    o = o[(o.grammar == "learned") & ~o.corpus.str.contains("wordorder")].dropna(subset=["bits_per_word_slot12"])
    o["gap_bits"] = o.bits_per_word_slot12 - o.bits_per_word_unit_bigram
    o["ratio"] = o.bits_per_word_slot12 / o.bits_per_word_unit_bigram
    o[["corpus", "family", "hard_coverage_heldout", "bits_per_word_slot12", "bits_per_word_unit_bigram", "gap_bits", "ratio"]].to_csv(RES / "slot_vs_bigram_bits.csv", index=False)
    fig, ax = plt.subplots(figsize=(7, 5))
    oo = o.sort_values("ratio")
    ax.barh(oo.corpus, oo.ratio, color=["red" if c == "MS408" else "C0" for c in oo.corpus])
    ax.axvline(1, color="k", lw=.6)
    ax.set_xlabel("held-out bits per word: 12-slot grammar / unit-bigram model")
    ax.tick_params(axis="y", labelsize=6)
    fig.tight_layout()
    fig.savefig(FIG / "slot_vs_bigram_bits.png", dpi=120)
    plt.close(fig)
    mechanism_table(p)
    print("figures built")


if __name__ == "__main__":
    main()
