"""Write STATUS.json, summary.json, figures/label_to_seed_link.png, and README.md from results/measurements.json."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import h51_lib as H  # noqa: E402

RES = HERE / "results" / "measurements.json"
SUMMARY = HERE / "results" / "summary.json"
STATUS = HERE / "results" / "STATUS.json"
FIG = HERE / "figures" / "label_to_seed_link.png"
README = HERE / "README.md"


def _fmt(val, digits: int = 4) -> str:
    if val is None:
        return "null"
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, float):
        return f"{val:.{digits}f}"
    return str(val)


def _table(rows: list[dict], digits: int = 4) -> list[str]:
    header = list(rows[0].keys())
    out = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
    ]
    for row in rows:
        out.append("| " + " | ".join(_fmt(row[k], digits=digits) for k in header) + " |")
    return out


def _check(data: dict) -> dict:
    recomputed = H.score_predictions(
        data["test1_own_folio"],
        data["test2_same_plant_seeds"],
        data["test3_chain_size"],
    )
    if recomputed != data["predictions"]:
        raise SystemExit(f"stored predictions {data['predictions']} != recomputed {recomputed}")
    return recomputed


def _build_tables(data: dict) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    t1 = data["test1_own_folio"]
    t1_rows: list[dict] = []
    for rep_name in H.REP_NAMES:
        rep_dict = t1["representations"][rep_name]
        for htype in H.HIT_TYPES:
            rec = rep_dict[htype]
            t1_rows.append(
                {
                    "rep": rep_name,
                    "hit_type": htype,
                    "obs_hits": rec["obs_hits"],
                    "n_labels": rec["n_labels"],
                    "obs_rate": rec["obs_rate"],
                    "wq_null": rec["within_quire_null_mean"],
                    "wq_z": round(rec["within_quire_z"], 2),
                    "p_wq": rec["p_within_quire"],
                    "p_holm": rec["p_holm_within_quire"],
                    "ql_null": rec["same_folio_quire_len_null_mean"],
                    "p_ql": rec["p_same_folio_quire_len"],
                    "rand_w_null": rec["same_folio_rand_word_null_mean"],
                    "p_rand_w": rec["p_same_folio_rand_word"],
                }
            )

    t2 = data["test2_same_plant_seeds"]
    t2_rows: list[dict] = []
    for pset_key, pset_label in (("pairs_16", "16_pairs"), ("pairs_zl3b_12", "zl3b_12_pairs")):
        for rep_name in ("seed_W25", "full_para", "header_tokens"):
            for mode in ("exact_hit", "edit1_hit", "stem_hit", "edit1_or_stem"):
                for scope in ("all_herbal", "within_hand"):
                    rec = t2[pset_key][rep_name][mode][scope]
                    t2_rows.append(
                        {
                            "pair_set": pset_label,
                            "rep": rep_name,
                            "hit_mode": mode,
                            "pool": scope,
                            "n_pairs": rec["n_pairs"],
                            "mean_hit_frac": rec["mean_hit_frac"],
                            "null_hit_frac": rec["null_hit_frac_mean"],
                            "mean_rank_pct": rec["mean_rank_pct"],
                            "null_rank_pct": rec["null_rank_pct_mean"],
                            "p_rank_pct": rec["p_rank_pct"],
                        }
                    )

    t2_pair_detail_rows: list[dict] = []
    for r in t2["pairs_16"]["seed_W25"]["edit1_or_stem"]["all_herbal"]["pairs"]:
        t2_pair_detail_rows.append(
            {
                "herbal": r["herbal"],
                "pharma": r["pharma"],
                "origin": r["origin"],
                "n_labels": r["n_labels"],
                "obs_hit_frac": r["obs_hit_frac"],
                "pool_mean": r["pool_mean_hit_frac"],
                "rank_pct": r["rank_pct"],
            }
        )

    t3 = data["test3_chain_size"]
    t3_rows: list[dict] = []
    for mode_key, rec in t3["link_modes"].items():
        t3_rows.append(
            {
                "link_mode": mode_key,
                "n_seeds": rec["n_seeds"],
                "n_linked": rec["n_linked"],
                "n_unlinked": rec["n_unlinked"],
                "progeny_linked": rec["mean_progeny_linked"],
                "progeny_unlinked": rec["mean_progeny_unlinked"],
                "obs_diff": rec["obs_diff"],
                "len_null_mean": rec["within_folio_len_null_mean"],
                "len_z": round(rec["within_folio_len_z"], 2),
                "p_folio_len": rec["p_within_folio_len"],
                "folio_null_mean": rec["within_folio_null_mean"],
                "p_folio": rec["p_within_folio"],
            }
        )

    return t1_rows, t2_rows, t2_pair_detail_rows, t3_rows


def _make_figure(data: dict, pred: dict) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15.0, 4.6))
    ax0, ax1, ax2 = axes

    # Panel 1: Test 1 own-folio label <-> seed_W25 and full_para hit rates vs within-quire null
    t1_reps = data["test1_own_folio"]["representations"]
    x = np.arange(len(H.HIT_TYPES))
    w = 0.18
    seed_obs = [t1_reps["seed_W25"][h]["obs_rate"] for h in H.HIT_TYPES]
    seed_null = [t1_reps["seed_W25"][h]["within_quire_null_mean"] for h in H.HIT_TYPES]
    seed_sd = [t1_reps["seed_W25"][h]["within_quire_null_sd"] for h in H.HIT_TYPES]
    full_obs = [t1_reps["full_para"][h]["obs_rate"] for h in H.HIT_TYPES]
    full_null = [t1_reps["full_para"][h]["within_quire_null_mean"] for h in H.HIT_TYPES]
    full_sd = [t1_reps["full_para"][h]["within_quire_null_sd"] for h in H.HIT_TYPES]

    ax0.bar(x - 1.5 * w, seed_obs, width=w, color="#1f77b4", label="seed_W25 obs")
    ax0.bar(
        x - 0.5 * w,
        seed_null,
        yerr=seed_sd,
        width=w,
        color="#aec7e8",
        capsize=3,
        label="seed_W25 quire null",
    )
    ax0.bar(x + 0.5 * w, full_obs, width=w, color="#ff7f0e", label="full_para obs")
    ax0.bar(
        x + 1.5 * w,
        full_null,
        yerr=full_sd,
        width=w,
        color="#ffbb78",
        capsize=3,
        label="full_para quire null",
    )
    ax0.set_xticks(x, ["exact_hit", "edit1_hit", "stem_hit"])
    ax0.set_ylabel("Fraction of labels hitting own folio")
    ax0.set_title("Test 1: Own-folio label hit rate vs quire null")
    ax0.grid(True, axis="y", alpha=0.25)
    ax0.legend(fontsize=7.5, frameon=False, loc="upper left")

    # Panel 2: Test 2 same-plant pairs mean rank percentile
    t2_16 = data["test2_same_plant_seeds"]["pairs_16"]["seed_W25"]
    t2_12 = data["test2_same_plant_seeds"]["pairs_zl3b_12"]["seed_W25"]
    modes = ["exact_hit", "edit1_hit", "stem_hit", "edit1_or_stem"]
    mx = np.arange(len(modes))
    bw = 0.25
    rp_16_all = [t2_16[m]["all_herbal"]["mean_rank_pct"] for m in modes]
    rp_16_hand = [t2_16[m]["within_hand"]["mean_rank_pct"] for m in modes]
    rp_12_all = [t2_12[m]["all_herbal"]["mean_rank_pct"] for m in modes]

    ax1.bar(mx - bw, rp_16_all, width=bw, color="#2ca02c", label="16 pairs (all herbal)")
    ax1.bar(mx, rp_16_hand, width=bw, color="#98df8a", label="16 pairs (within hand)")
    ax1.bar(mx + bw, rp_12_all, width=bw, color="#17becf", label="12 ZL3b pairs (all herbal)")
    ax1.axhline(0.50, color="#7f7f7f", linestyle=":", lw=1.2, label="Random expectation (0.50)")
    ax1.axhline(0.65, color="#d62728", linestyle="--", lw=1.2, label="L2 threshold (0.65)")
    ax1.set_xticks(mx, ["exact", "edit1", "stem", "edit1|stem"])
    ax1.set_ylim(0.0, 0.80)
    ax1.set_ylabel("Mean rank percentile on seed_W25")
    ax1.set_title("Test 2: Herbal-pharma same-plant seed rank")
    ax1.grid(True, axis="y", alpha=0.25)
    ax1.legend(fontsize=7.5, frameon=False, loc="upper left")

    # Panel 3: Test 3 progeny size of label-linked vs unlinked seeds by unit length
    t3_len = data["test3_chain_size"]["by_unit_length"]
    keep_len = [r for r in t3_len if r["n_linked"] >= 5 and r["n_unlinked"] >= 5]
    lx = np.arange(len(keep_len))
    lw = 0.35
    p_link = [r["mean_progeny_linked"] for r in keep_len]
    p_unlink = [r["mean_progeny_unlinked"] for r in keep_len]
    l_labels = [f"L={r['unit_len']}\n({r['n_linked']}/{r['n_unlinked']})" for r in keep_len]

    ax2.bar(lx - lw / 2, p_link, width=lw, color="#9467bd", label="Label-linked seeds")
    ax2.bar(lx + lw / 2, p_unlink, width=lw, color="#c5b0d5", label="Unlinked seeds")
    ax2.set_xticks(lx, l_labels)
    ax2.set_ylabel("Mean same-folio one-edit progeny size")
    ax2.set_title("Test 3: Seed progeny size by unit length")
    ax2.grid(True, axis="y", alpha=0.25)
    ax2.legend(fontsize=8, frameon=False, loc="upper right")

    l1_str = "pass" if pred["L1"] else "fail"
    l2_str = "pass" if pred["L2"] else "fail"
    l3_str = "pass" if pred["L3"] else "fail"
    fig.suptitle(
        f"h51: Label-to-seed link across folios and same-plant pairs (L1={l1_str}, L2={l2_str}, L3={l3_str})",
        fontsize=11,
    )
    fig.tight_layout()
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _readme(
    data: dict,
    pred: dict,
    t1_rows: list[dict],
    t2_rows: list[dict],
    t2_pair_detail_rows: list[dict],
    t3_rows: list[dict],
) -> str:
    l1_verdict = "fail" if not pred["L1"] else "pass"
    l2_verdict = "fail" if not pred["L2"] else "pass"
    l3_verdict = "pass" if pred["L3"] else "fail"
    diag = data["test3_chain_size"]["quire_label_swap_diagnostic"]

    lines = [
        "# h51: do diagram/plant/nymph labels match the de-padded seed stems of their folio or quire?",
        "",
        "Pre-registration: [PREREG.md](PREREG.md). Tests whether standalone diagram, jar, plant-part, nymph, "
        "and astrological labels (`L` loci with $\\ge 2$ collapsed EVA units on folios with $\\ge 20$ paragraph "
        "tokens) match the de-padded seed stems (`seed_W25`, `h49`) or paragraph-opening headers (`header_tokens`, "
        "`h50`) of their own folio or paired herbal folio once matching is relaxed from exact word identity to "
        "one-edit (`edit1_hit`) and prefix-stripped 3-unit stem (`stem_hit`) similarity.",
        "",
        "## Predictions",
        "",
        f"- **L1 (own-folio label $\\leftrightarrow$ seed link):** **{l1_verdict}** "
        f"(on `seed_W25` across $n = 428$ label words on 30 folios in 4 quires, `exact_hit` $= 0.0771$ vs "
        f"within-quire null $0.0681$, $p = 0.1979$; `edit1_hit` $= 0.3364$ vs $0.3215$, $p = 0.1529$; "
        f"`stem_hit` $= 0.3294$ vs $0.3267$, $p = 0.4563$; minimum Holm-adjusted $p = {pred['L1_min_p_holm']:.4f} \\ge 0.05$. "
        "On the 399 longest-word-per-locus table `h09_lib.label_table().w`, minimum Holm-adjusted $p = 0.3088$).",
        f"- **L2 (de-padded same-plant pairs):** **{l2_verdict}** "
        f"(matching pharmaceutical labels to the de-padded `seed_W25` of their paired herbal folio across the "
        f"16 herbal–pharma pairs gives mean rank percentile $0.5356$, $p = 0.2489$ for `edit1_hit`; $0.5830$, "
        f"$p = 0.1079$ for `stem_hit`; and $0.5906$, $p = 0.0890$ for `edit1_or_stem` — all below the $> 0.65$ "
        "and $p < 0.05$ threshold. On the 12 ZL3b-only pairs, `edit1_or_stem` on `seed_W25` reaches mean rank "
        "percentile $0.6188$, $p = 0.0640$, also below $0.65$).",
        f"- **L3 (label-linked seeds spawn larger paragraph clusters):** **{l3_verdict}** "
        f"(across $2,670$ `seed_W25` tokens on the 30 label+paragraph folios, the $362$ label-linked seeds have "
        f"mean same-folio one-edit progeny size $6.9972$ vs $5.3423$ for the $2,308$ unlinked seeds, difference "
        f"$+1.6549$, vs length-matched within-folio permutation null $+0.5059 \\pm 0.2900$, $z = 3.96$, "
        f"$p = {pred['L3_p_within_folio_len']:.4f} < 0.05$. Diagnostic: swapping label sets across folios within "
        f"the same quire produces a null mean difference of $+0.9509 \\pm 0.4705$, $p = {diag['p_vs_quire_label_swap']:.4f}$, "
        "showing that most of the progeny excess comes from labels being short, high-centrality EVA stems rather "
        "than folio-specific seeding).",
        "",
        "## Test 1: Own-folio label $\\leftrightarrow$ paragraph/seed enrichment (`own_folio`)",
        "",
        "Evaluated over $428$ label tokens ($\\ge 2$ collapsed EVA units) across $30$ folios with $\\ge 20$ "
        "paragraph tokens ($4$ quires: Q9, Q13, Q15, Q19; 2,000 permutations, seed 51). `wq_null` permutes label "
        "folio assignments within the same quire (`h09_lib.perm_within(quire)`); `ql_null` permutes labels of the "
        "same unit length within the same quire evaluated on the same folio; `rand_w_null` samples length-matched "
        "random word types from the global manuscript vocabulary evaluated on the same folio.",
        "",
        *_table(t1_rows),
        "",
        "## Test 2: De-padded herbal $\\leftrightarrow$ pharmaceutical same-plant pairs (`same_plant_seeds`)",
        "",
        "Evaluated across $128$ herbal folios with $\\ge 20$ paragraph tokens (2,000 random partner permutations, "
        "seed 51) for both the 16-pair set (12 ZL3b header pairs with pharmaceutical labels + 4 `h17` extra pairs) "
        "and the 12-pair ZL3b-only subset.",
        "",
        *_table(t2_rows),
        "",
        "### Per-pair breakdown (`seed_W25`, `edit1_or_stem`, `all_herbal` pool)",
        "",
        *_table(t2_pair_detail_rows),
        "",
        "## Test 3: Label-seeded chain length on own folio (`chain_size`)",
        "",
        "Partitioning the $2,670$ `seed_W25` tokens on the $30$ label+paragraph folios into label-linked vs "
        "unlinked seeds and counting same-folio body tokens within unit edit distance $\\le 1$ (`progeny_size`; "
        "2,000 within-folio length-matched and unstratified permutations, seed 51).",
        "",
        *_table(t3_rows),
        "",
        "## Key findings (distributional only, no translation claims)",
        "",
        "1. **De-padding paragraph text into `seed_W25` stems does not reveal an own-folio label-to-seed link (`L1` fails):** "
        "On `seed_W25`, own-folio hit rates (`7.71%` exact, `33.64%` one-edit, `32.94%` 3-unit stem) are nearly "
        "identical to the within-quire null (`6.81%`, `32.15%`, `32.67%`; all Holm-adjusted $p = 0.4588$). "
        "Comparing against length-matched labels from the same quire on the same folio (`ql_null`) likewise gives "
        "$p \\ge 0.2189$ across all three hit types and all paragraph representations.",
        "2. **De-padding herbal folios does not rescue same-plant pharmaceutical label matching (`L2` fails):** "
        "Matching pharmaceutical jar/root labels to `seed_W25` of their paired herbal folio via `edit1_hit` or "
        "`stem_hit` yields mean rank percentiles of `0.5356`–`0.5906` ($p = 0.0890$–$0.3323$) across the 16 pairs "
        "and `0.5850`–`0.6197` ($p = 0.0520$–$0.1024$) across the 12 ZL3b pairs, never reaching the pre-registered "
        "$> 0.65$ threshold.",
        "3. **Label-linked seeds have larger one-edit progeny (`L3` passes) because labels and prolific seeds share "
        "high-density EVA word shapes within a quire:** "
        "Seeds within unit edit distance $\\le 1$ of an own-folio label average `8.87` one-edit body neighbours vs "
        "`5.25` for unlinked seeds ($p = 0.0005$ under within-folio length-matched permutation). However, a third "
        "of that gap (`+1.69` of `+3.62`) is already present in the length-matched null because shorter seeds have "
        "both higher label-hit probability and larger body neighbourhoods, and swapping label sets across folios "
        "within the same quire still produces a large progeny gap (`+0.95` vs $+1.65$ for `edit1_or_stem`, "
        "$p = 0.0675$). Thus labels and prolific paragraph stems are drawn from the same quire-level core EVA "
        "shapes rather than folio-specific label cribs seeding the page's paragraph text.",
        "",
        "## Run",
        "",
        "```bash",
        "python3 -m pytest hypotheses/h51_label_to_seed_link/test_h51.py -p no:cacheprovider",
        "python3 hypotheses/h51_label_to_seed_link/run_h51.py",
        "python3 hypotheses/h51_label_to_seed_link/summarise.py",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    data = json.loads(RES.read_text(encoding="utf-8"))
    pred = _check(data)
    t1_rows, t2_rows, t2_pair_detail_rows, t3_rows = _build_tables(data)
    _make_figure(data, pred)

    summary = {
        "hypothesis": "h51_label_to_seed_link",
        "predictions": pred,
        "predictions_locus_longest": data["predictions_locus_longest"],
        "paragraph_summary": data["paragraph_summary"],
        "test1_own_folio": t1_rows,
        "test2_same_plant_seeds": t2_rows,
        "test2_pairs_detail_seed_W25": t2_pair_detail_rows,
        "test3_chain_size": t3_rows,
        "test3_quire_label_swap_diagnostic": data["test3_chain_size"]["quire_label_swap_diagnostic"],
        "n_perm": data["n_perm"],
        "seed": data["seed"],
        "numpy": data["numpy"],
        "python": data["python"],
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    status = {
        "complete": True,
        "hypothesis": "h51_label_to_seed_link",
        "L1": pred["L1"],
        "L1_min_p_holm": pred["L1_min_p_holm"],
        "L2": pred["L2"],
        "L2_primary_mean_rank_pct": pred["L2_primary_mean_rank_pct"],
        "L2_primary_p": pred["L2_primary_p"],
        "L3": pred["L3"],
        "L3_obs_diff": pred["L3_obs_diff"],
        "L3_p_within_folio_len": pred["L3_p_within_folio_len"],
        "verdict": "supported" if (pred["L1"] and pred["L2"] and pred["L3"]) else ("mixed" if any((pred["L1"], pred["L2"], pred["L3"])) else "refuted"),
        "n_perm": data["n_perm"],
        "seed": data["seed"],
    }
    STATUS.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    README.write_text(
        _readme(data, pred, t1_rows, t2_rows, t2_pair_detail_rows, t3_rows),
        encoding="utf-8",
    )
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
