"""Run every test for hypothesis h01 (tone / glyph / meaning translation sheet). Usage: python hypotheses/h01_tone_sheet/run_h01.py [--quick]
Writes results/*.csv, results/results.json and figures/*.png next to this file. Deterministic (fixed seeds)."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h01_lib as L  # noqa: E402

RES = L.HERE / "results"
FIG = L.HERE / "figures"
TR = L.ROOT / "data" / "transcriptions"


def save(df: pd.DataFrame, name: str):
    df.to_csv(RES / name, index=False)


def main(quick: bool = False):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    RES.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    nperm = 1000 if quick else 5000
    out: dict = {}
    table = L.load_table()
    units = list(table["glyph"])
    tones = list(table["tone_hz"])
    pred = L.load_predictions()

    # =================================================================== (A) tones
    t = np.array(tones, float)
    srt = np.sort(t)
    rows = []
    for i, f in enumerate(srt):
        nm, dev = L.nearest_12tet(f)
        nm432, dev432 = L.nearest_12tet(f, 432.0)
        rows.append({"glyph": table.loc[table.tone_hz == f, "glyph"].iloc[0], "tone_hz": f, "ratio_to_lowest": f / srt[0],
                     "step_from_previous_semitones": (12 * math.log2(f / srt[i - 1]) if i else float("nan")),
                     "step_from_previous_hz": (f - srt[i - 1]) if i else float("nan"),
                     "nearest_12tet_A440": nm, "dev_cents_A440": dev, "nearest_12tet_A432": nm432, "dev_cents_A432": dev432})
    tone_df = pd.DataFrame(rows)
    save(tone_df, "tones_sorted.csv")
    best = L.best_grid_fit(t, 100.0, 0.5)
    inv, pinv = L.kendall_inversions_p([int(np.where(srt == x)[0][0]) for x in t])
    ntest = 3000 if quick else 20000
    null_log, summ_log = L.tone_null(t, ntest, mode="log")
    null_lin, summ_lin = L.tone_null(t, ntest, mode="linear")
    summ = pd.concat([summ_log, summ_lin])
    save(summ, "tone_scale_fit_vs_null.csv")
    lin = L.linear_rank_fit(t)
    out["tones"] = {"sorted_hz": srt.tolist(), "best_12tet_rms_cents": best[0], "best_12tet_ref_hz": best[1], "best_12tet_max_dev_cents": best[2],
                    "fixed_ref_rms": L.fixed_reference_rms(t), "printed_order_inversions": inv, "printed_order_p_under_random": pinv,
                    "linear_rank_fit": lin, "adjacent_steps_semitones": [float(12 * math.log2(srt[i + 1] / srt[i])) for i in range(7)],
                    "adjacent_steps_hz": [float(srt[i + 1] - srt[i]) for i in range(7)]}
    # figure
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    cc = L.cents(srt, srt[0])
    ax[0].vlines(np.arange(0, cc.max() + 100, 100), 0, 1, color="0.85")
    ax[0].plot(cc, np.full_like(cc, .5), "o")
    for f, c, g in zip(srt, cc, tone_df.glyph):
        ax[0].annotate(f"{g}\n{int(f)}", (c, .5), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
    ax[0].set_title("Sheet tones vs 12-TET grid anchored at 174 Hz", fontsize=9)
    ax[0].set_yticks([])
    ax[0].set_xlabel("cents")
    ax[1].hist(null_log["12-TET chromatic (free ref)"], bins=50, color="0.7")
    ax[1].axvline(best[0] if False else summ_log.set_index("model").loc["12-TET chromatic (free ref)", "sheet_value"], color="r")
    ax[1].set_title("RMS fit to 12-TET: sheet (red) vs random 8-tone sets")
    ax[1].set_xlabel("RMS deviation, cents (free reference pitch)")
    fig.tight_layout()
    fig.savefig(FIG / "tones_vs_12tet.png", dpi=130)
    plt.close(fig)

    # =================================================================== load the manuscript
    folios = L.load_folios(TR / "ZL3b-n.txt", "P")
    tokens = L.all_tokens(folios)
    out["corpus"] = {"file": "ZL3b-n.txt", "folios": len(folios), "tokens": len(tokens), "types": len(set(tokens)),
                     "glyph_tokens": sum(len(w) for w in tokens), "hapax_types": sum(1 for c in Counter(tokens).values() if c == 1)}
    sections = sorted({f.section for f in folios})

    # =================================================================== (B) existence, coverage
    ut = L.unit_table(tokens, units, folios, n_boot=200 if quick else 500)
    save(ut, "unit_table.csv")
    xb = L.cross_boundary_counts(folios, units)
    save(xb, "unit_cross_boundary.csv")
    cov = L.coverage_stats(tokens, units)
    cov.update(L.line_coverage(folios, units))
    sheet_letters = sorted(set("".join(units)))
    allowed11 = [c for c in sheet_letters]
    letters_only = L.coverage_stats(tokens, allowed11)       # if every single sheet *letter* could be read
    cov["sheet_letters"] = "".join(sheet_letters)
    cov["tokens_made_only_of_sheet_letters"] = letters_only["tokens_fully_tileable"]
    cov["types_made_only_of_sheet_letters"] = letters_only["types_fully_tileable"]
    # EVA letters never mentioned by the sheet, share of glyph tokens
    cnt_letters = Counter(c for w in tokens for c in w)
    tot_letters = sum(cnt_letters.values())
    cov["glyph_share_outside_sheet_letters"] = sum(c for k, c in cnt_letters.items() if k not in sheet_letters) / tot_letters
    cov["top_units_reference"] = L.top_k_units_word_coverage(tokens, 8)
    cum = L.unit_cum_coverage(tokens)
    save(cum, "unit_cumulative_coverage.csv")
    cov["units_for_90pct"] = int((cum.cum_share < 0.90).sum() + 1)
    cov["units_for_95pct"] = int((cum.cum_share < 0.95).sum() + 1)
    cov["units_for_99pct"] = int((cum.cum_share < 0.99).sum() + 1)
    cov["n_collapsed_units"] = int(len(cum))
    cat = pd.read_csv(L.ROOT / "glyphs" / "catalog.csv")
    p = cat[cat.group == "P"]
    cov["catalog_eva_symbols_P"] = int((p.kind == "eva").sum())
    cov["catalog_rare_codes_P"] = int((p.kind != "eva").sum())
    cov["catalog_symbols_ge_1pct"] = int((p.share >= 0.01).sum())
    cov["catalog_has_standalone_unit"] = {u: bool((p.glyph == u).any()) for u in units}
    cov["catalog_letters_present"] = {c: bool((p.glyph == c).any()) for c in sheet_letters}
    ft = L.fully_tileable_words(tokens, units)
    save(ft, "fully_tileable_words.csv")
    cov["tileable_word_examples"] = ft.head(15).to_dict("records")
    ord_df = L.order_asymmetry(tokens, units)
    save(ord_df, "unit_order_in_words.csv")
    # top 30 words
    rows = []
    for w, c in Counter(tokens).most_common(30):
        cvr, ways = L.tilings(w, units)
        rows.append({"word": w, "count": c, "chars": len(w), "chars_covered_by_sheet_units": cvr, "fully_readable": cvr == len(w)})
    save(pd.DataFrame(rows), "top30_words_readability.csv")
    out["coverage"] = cov
    # digraph candidates from earlier stages
    dc = pd.read_csv(L.ROOT / "glyphs" / "digraph_candidates.csv")
    pm = pd.read_csv(L.ROOT / "glyphs" / "top_pmi_bigrams.csv")
    out["earlier_stage_flags"] = {"in_digraph_candidates": [u for u in units if u in set(dc.candidate)],
                                 "in_top_pmi_bigrams": [u for u in units if u in set(pm.iloc[:, 0].astype(str))],
                                 "top_pmi_columns": list(pm.columns)}
    # figure: unit counts
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.bar(ut.unit, ut.occurrences, color="C0", label="observed")
    ax.plot(ut.unit, ut.expected_if_letters_shuffled_in_word, "r_", markersize=24, mew=3, label="expected if letters shuffled within each word")
    ax.set_yscale("log")
    ax.set_ylabel("occurrences (log)")
    ax.set_title("The sheet's eight 'glyphs' in the ZL3b running text")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "unit_counts.png", dpi=130)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(cum["rank"], cum.cum_share, "o-", ms=3)
    ax.axvline(8, color="r", ls="--")
    ax.axhline(cov["char_cov"], color="g", ls=":")
    ax.set_xlabel("number of units (collapsed EVA units, frequency order)")
    ax.set_ylabel("cumulative share of glyph tokens")
    ax.set_title("8 symbols cover well under the ~100% a translation sheet needs\n(red: 8 units; green: the sheet's 8 units, character coverage)")
    fig.tight_layout()
    fig.savefig(FIG / "coverage_cumulative.png", dpi=130)
    plt.close(fig)

    # replication on other transcriptions
    rep = []
    for fn in ["ZL3b-n.txt", "IT2a-n.txt", "RF1b-e.txt", "GC2a-n.txt"]:
        pth = TR / fn
        if not pth.exists():
            continue
        if "v101" in pth.read_text(errors="replace")[:200]:
            continue          # GC2a uses a different (non-EVA) alphabet: the 8 strings are meaningless there
        try:
            fo = L.load_folios(pth, "P")
        except Exception as e:  # noqa: BLE001
            print("skip", fn, e)
            continue
        tk = L.all_tokens(fo)
        c2 = L.coverage_stats(tk, units)
        row = {"file": fn, "tokens": len(tk), "types": len(set(tk)), "tokens_fully_tileable": c2["tokens_fully_tileable"],
               "types_fully_tileable": c2["types_fully_tileable"], "char_cov": c2["char_cov"], "tokens_containing_a_unit": c2["tokens_containing_a_unit"]}
        for u in units:
            row[f"n_{u}"] = sum(w.count(u) for w in tk)
        rep.append(row)
    save(pd.DataFrame(rep), "replication_other_transcriptions.csv")

    # controls: same 8 strings in other texts
    crow = []
    try:
        from msdecipher.controls_text import load_tokens, SOURCES  # type: ignore
    except Exception:
        sys.path.insert(0, str(L.ROOT / "src"))
        from msdecipher.controls_text import load_tokens  # type: ignore
        from msdecipher.controls_fetch import SOURCES  # type: ignore
    for s in SOURCES:
        if s.get("script"):
            continue
        try:
            tk = load_tokens(s["id"], 35000)
        except Exception as e:  # noqa: BLE001
            print("skip control", s["id"], e)
            continue
        c3 = L.coverage_stats(tk, units)
        row = {"control": s["id"], "lang": s["lang"], "tokens": len(tk), "tokens_fully_tileable": c3["tokens_fully_tileable"],
               "char_cov": c3["char_cov"], "tokens_containing_a_unit": c3["tokens_containing_a_unit"]}
        for u in units:
            r = L.pair_obs_exp(tk, u[0], u[1])
            o, e = r["obs"].get("all", 0), r["exp"].get("all", 0)
            row[f"oe_{u}"] = o / e if e else float("nan")
            row[f"n_{u}"] = o
        crow.append(row)
    ctl = pd.DataFrame(crow)
    save(ctl, "controls_unit_coverage.csv")
    out["controls"] = {"median_tokens_fully_tileable": float(ctl.tokens_fully_tileable.median()),
                       "max_tokens_fully_tileable": float(ctl.tokens_fully_tileable.max()),
                       "median_char_cov": float(ctl.char_cov.median()),
                       "median_tokens_containing_a_unit": float(ctl.tokens_containing_a_unit.median()),
                       "median_oe": {u: float(ctl[f"oe_{u}"].median()) for u in units}, "n_controls": int(len(ctl))}

    # =================================================================== (C) statistical tests
    rng = np.random.default_rng(1)
    # neighbour MI, compared with frequency-matched random bigrams
    base_counts = {u: sum(w.count(u) for w in tokens) for u in units}
    freq_bi = Counter(w[i:i + 2] for w in tokens for i in range(len(w) - 1))
    rows = []
    n_ctrl = 20 if quick else 60
    for u in units:
        r = L.neighbour_mi(folios, u, n_perm=100 if quick else 300, rng=np.random.default_rng(2))
        c = base_counts[u]
        cand = [b for b, k in freq_bi.items() if b not in units and 0.6 * c <= k <= 1.67 * c]
        z_ctrl = []
        mi_ctrl = []
        if len(cand) >= 5 and c >= 20:
            pick = np.random.default_rng(4).choice(cand, size=min(n_ctrl, len(cand)), replace=False)
            for b in pick:
                rr = L.neighbour_mi(folios, str(b), n_perm=60, rng=np.random.default_rng(5))
                z_ctrl.append(rr["z"])
                mi_ctrl.append(rr["mi_bits"])
        rows.append({"unit": u, "occurrences": c, **r, "n_matched_controls": len(z_ctrl),
                     "control_median_z": float(np.median(z_ctrl)) if z_ctrl else float("nan"),
                     "control_median_mi_bits": float(np.median(mi_ctrl)) if mi_ctrl else float("nan"),
                     "frac_controls_with_mi_ge_unit": float(np.mean(np.array(mi_ctrl) >= r["mi_bits"])) if mi_ctrl else float("nan")})
    nm = pd.DataFrame(rows)
    save(nm, "neighbour_mi.csv")

    # =================================================================== (D) sections
    main_secs = ["herbal", "biological", "pharmaceutical", "stars", "cosmological", "astronomical", "text-only"]
    enr = L.enrichment_matrix(folios, units, main_secs, n_perm=nperm)
    enr_s = L.enrichment_matrix(folios, units, main_secs, n_perm=nperm, strata=True)
    save(enr, "section_enrichment.csv")
    save(enr_s, "section_enrichment_language_stratified.csv")
    # pre-specified pairs
    strict = {r.glyph: [x for x in r.strict_sections.split(";") if x] for r in pred.itertuples()}
    liberal = {r.glyph: [x for x in r.liberal_sections.split(";") if x] for r in pred.itertuples()}
    pr_rows = []
    for r in pred.itertuples():
        for s in strict[r.glyph]:
            e1 = enr[(enr.unit == r.glyph) & (enr.section == s)].iloc[0]
            e2 = enr_s[(enr_s.unit == r.glyph) & (enr_s.section == s)].iloc[0]
            pr_rows.append({"unit": r.glyph, "meaning": r.meaning, "predicted_section": s, "priority": r.priority,
                            "occurrences_in_section": int(e1.occurrences_in_section), "rate_per_1000_in": e1.rate_per_1000_in,
                            "rate_per_1000_out": e1.rate_per_1000_out, "log2_ratio": e1.log2_ratio, "p_enriched": e1.p_enriched,
                            "p_enriched_language_stratified": e2.p_enriched, "p_depleted": e1.p_depleted})
    prd = pd.DataFrame(pr_rows)
    prd["holm_p_all"] = L.holm(list(prd.p_enriched))
    prd["holm_p_stratified"] = L.holm(list(prd.p_enriched_language_stratified))
    save(prd, "section_predictions_test.csv")
    # all-loci sensitivity (labels, circular, radial text -> zodiac included)
    folios_all = L.load_folios(TR / "ZL3b-n.txt", "PCRL")
    secs_all = sorted({f.section for f in folios_all})
    enr_all = L.enrichment_matrix(folios_all, units, [s for s in secs_all if s in main_secs + ["zodiac"]], n_perm=max(nperm // 2, 500))
    save(enr_all, "section_enrichment_all_loci.csv")
    mp_strict = L.mapping_permutation_test(folios, units, strict, n_label_perm=500 if quick else 3000)
    mp_lib = L.mapping_permutation_test(folios, units, liberal, n_label_perm=500 if quick else 3000)
    pd.DataFrame({"strict": mp_strict.pop("all_scores")}).to_csv(RES / "mapping_permutation_scores_strict.csv", index=False)
    pd.DataFrame({"liberal": mp_lib.pop("all_scores")}).to_csv(RES / "mapping_permutation_scores_liberal.csv", index=False)
    out["sections"] = {"n_folios_by_section": dict(Counter(f.section for f in folios)),
                       "tokens_by_section": {s: sum(len(f.tokens) for f in folios if f.section == s) for s in sections},
                       "mapping_strict": mp_strict, "mapping_liberal": mp_lib,
                       "avg_sections_accepted_strict": float(np.mean([len(v) for v in strict.values() if v])),
                       "avg_sections_accepted_liberal": float(np.mean([len(v) for v in liberal.values()])),
                       "language_by_section": {s: dict(Counter(f.language for f in folios if f.section == s)) for s in sections}}
    # figure heatmap
    piv = enr.pivot(index="unit", columns="section", values="log2_ratio").loc[units, main_secs]
    pv = enr.pivot(index="unit", columns="section", values="p_enriched").loc[units, main_secs]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    im = ax.imshow(piv.values, cmap="RdBu_r", vmin=-3, vmax=3)
    ax.set_xticks(range(len(main_secs)), main_secs, rotation=30, ha="right")
    ax.set_yticks(range(len(units)), [f"{u} ({d})" for u, d in zip(units, table.meaning.str.split(",").str[0])], fontsize=7)
    for i, u in enumerate(units):
        for j, s in enumerate(main_secs):
            ptxt = pv.values[i, j]
            ax.text(j, i, f"{piv.values[i, j]:.1f}" + ("*" if ptxt < 0.01 else ""), ha="center", va="center", fontsize=7)
            if s in strict[u]:
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, ec="k", lw=2))
    ax.set_title("log2 rate ratio (section vs rest); black box = section predicted by the sheet's meaning;\n* = permutation p<0.01 (enriched)", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=.7)
    fig.tight_layout()
    fig.savefig(FIG / "section_enrichment_heatmap.png", dpi=130)
    plt.close(fig)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    for a, (nm_, mp, col) in zip(ax, [("strict", "mapping_permutation_scores_strict.csv", "C0"), ("liberal", "mapping_permutation_scores_liberal.csv", "C1")]):
        sc = pd.read_csv(RES / mp).iloc[:, 0].dropna()
        a.hist(sc, bins=60, color=col, alpha=.7)
        a.axvline(out["sections"][f"mapping_{nm_}"]["sheet_score"], color="r")
        a.set_title(f"{nm_} table: score of all 8! unit-meaning pairings; sheet = red", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "mapping_permutation.png", dpi=130)
    plt.close(fig)

    # mapping test restricted to units that actually occur (>= 30 occurrences)
    common = [u for u in units if base_counts[u] >= 30]
    mp_common = L.mapping_permutation_test(folios, common, strict, n_label_perm=300 if quick else 2000)
    mp_common.pop("all_scores")
    out["sections"]["mapping_strict_units_ge30"] = {"units": common, **mp_common}
    # Holm over the whole 8 x 7 matrix
    enr["holm_p_enriched_all_cells"] = L.holm(list(enr.p_enriched))
    enr["holm_p_depleted_all_cells"] = L.holm(list(enr.p_depleted))
    save(enr, "section_enrichment.csv")
    out["sections"]["cells_enriched_holm05"] = enr[enr.holm_p_enriched_all_cells < .05][["unit", "section", "occurrences_in_section", "log2_ratio", "p_enriched", "holm_p_enriched_all_cells"]].to_dict("records")
    out["sections"]["cells_depleted_holm05"] = enr[enr.holm_p_depleted_all_cells < .05][["unit", "section", "occurrences_in_section", "log2_ratio", "p_depleted", "holm_p_depleted_all_cells"]].to_dict("records")
    # how special is dy -> biological? same test for ordinary frequent letter pairs
    pool = [b for b in L.frequent_bigrams(tokens, 60) if b not in units][:50]
    spec = L.specificity_pool(folios, "biological", pool + ["dy", "qo", "ka", "ly"], n_perm=300 if quick else 2000)
    spec = spec.sort_values("log2_ratio", ascending=False)
    save(spec, "specificity_biological_pool.csv")
    ord_pool = spec[spec.unit.isin(pool)]
    dyrow = spec[spec.unit == "dy"].iloc[0]
    out["specificity_biological"] = {"n_pool": len(pool), "pool_with_p_enriched_lt_0.01": int((ord_pool.p_enriched < 0.01).sum()),
                                     "pool_with_log2_ratio_ge_dy": int((ord_pool.log2_ratio >= dyrow.log2_ratio).sum()),
                                     "dy_log2_ratio": float(dyrow.log2_ratio), "pool_median_abs_log2_ratio": float(ord_pool.log2_ratio.abs().median()),
                                     "sheet_units_enriched_p_lt_0.01": [u for u in ["dy", "qo", "ka", "ly"] if float(spec[spec.unit == u].iloc[0].p_enriched) < .01]}

    # predictive information: classify folio section / Currier language from unit counts
    ysec = np.array([f.section for f in folios])
    ylang = np.array([f.language for f in folios])
    keep = np.array([len(f.tokens) >= 50 for f in folios])
    Xs = L.unit_count_features(folios, units)
    out_pred = {"n_folios_used": int(keep.sum()), "majority_section_acc": float(Counter(ysec[keep]).most_common(1)[0][1] / keep.sum()),
                "majority_lang_acc": float(Counter(ylang[keep]).most_common(1)[0][1] / keep.sum())}
    rs = np.random.default_rng(9)
    bi_pool = [b for b in L.frequent_bigrams(tokens, 60) if b not in units]
    for tgt_name, y in (("section", ysec), ("language", ylang)):
        res = L.nb_loo(Xs[keep], y[keep])
        rnd_acc, rnd_bal = [], []
        for _ in range(60 if quick else 200):
            pick = list(rs.choice(bi_pool, size=8, replace=False))
            r = L.nb_loo(L.unit_count_features(folios, pick)[keep], y[keep])
            rnd_acc.append(r["accuracy"])
            rnd_bal.append(r["balanced_accuracy"])
        sh_acc, sh_bal = [], []
        for _ in range(60 if quick else 200):
            r = L.nb_loo(Xs[keep], rs.permutation(y[keep]))
            sh_acc.append(r["accuracy"])
            sh_bal.append(r["balanced_accuracy"])
        top8 = L.nb_loo(L.unit_count_features(folios, bi_pool[:8])[keep], y[keep])
        out_pred[tgt_name] = {"sheet_units": res, "random_frequent_bigram_sets": {"acc_median": float(np.median(rnd_acc)), "acc_p05": float(np.percentile(rnd_acc, 5)),
                              "acc_p95": float(np.percentile(rnd_acc, 95)), "bal_median": float(np.median(rnd_bal)),
                              "frac_sets_ge_sheet_acc": float(np.mean(np.array(rnd_acc) >= res["accuracy"])),
                              "frac_sets_ge_sheet_bal": float(np.mean(np.array(rnd_bal) >= res["balanced_accuracy"]))},
                              "label_shuffled_sheet_units": {"acc_median": float(np.median(sh_acc)), "acc_p95": float(np.percentile(sh_acc, 95)),
                                                              "bal_median": float(np.median(sh_bal)), "bal_p95": float(np.percentile(sh_bal, 95))},
                              "top8_frequent_bigrams": top8}
    # drop the 4 near-absent units: how much of the prediction survives with only qo, ka, dy, ly
    four = ["qo", "ka", "dy", "ly"]
    out_pred["section"]["only_qo_ka_dy_ly"] = L.nb_loo(L.unit_count_features(folios, four)[keep], ysec[keep])
    out_pred["section"]["only_ri_ae_ya_ny"] = L.nb_loo(L.unit_count_features(folios, ["ri", "ae", "ya", "ny"])[keep], ysec[keep])
    out["predictive"] = out_pred
    out["neighbour_mi"] = nm.to_dict("records")

    # =================================================================== write
    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return None if (isinstance(o, float) and (math.isnan(o) or math.isinf(o))) else float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        return o
    (RES / "results.json").write_text(json.dumps(clean(out), indent=1))
    print("done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    main(ap.parse_args().quick)
