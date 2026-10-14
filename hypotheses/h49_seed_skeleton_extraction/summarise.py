"""Write summary.json, STATUS.json, figures/seed_skeleton_extraction.png, and README.md for h49."""
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

import h49_lib as H  # noqa: E402

RES = HERE / "results" / "measurements.json"
SUMMARY = HERE / "results" / "summary.json"
STATUS = HERE / "results" / "STATUS.json"
FIG = HERE / "figures" / "seed_skeleton_extraction.png"
README = HERE / "README.md"

SHORT_LABELS = {
    "MS_1A": "MS 1A",
    "page_line_copier_1A": "PLC 1A",
    "MS_2B": "MS 2B",
    "page_line_copier_2B": "PLC 2B",
    "MS_3B": "MS 3B",
    "page_line_copier_3B": "PLC 3B",
    "naibbe_boccaccio_swap": "Naibbe+swap",
    "it_boccaccio": "Boccaccio",
}


def _fmt(val, digits: int = 4) -> str:
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "pass" if val else "fail"
    if isinstance(val, int):
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
    recomputed = H.evaluate_predictions(data["streams"])
    if recomputed != data["predictions"]:
        raise SystemExit(f"stored predictions {data['predictions']} != recomputed {recomputed}")
    return recomputed


def _build_tables(data: dict) -> tuple[list[dict], list[dict], list[dict]]:
    streams = data["streams"]
    mode_rows: list[dict] = []
    continuity_rows: list[dict] = []
    s3_rows: list[dict] = []

    for key in H.STREAM_ORDER:
        rec = streams[key]
        for mode in H.MODES:
            m = rec["modes"][mode]
            mode_rows.append(
                {
                    "stream": key,
                    "mode": mode,
                    "n_tokens": m["n_tokens"],
                    "n_types": m["n_types"],
                    "keep_rate": m["keep_rate"],
                    "D1_seed": m["D1_seed"],
                    "mi_adj_excess": m["mi_adj_excess"],
                    "mi_adj_z": round(m["mi_adj_z"], 2),
                    "morphs_per_type": m["morphs_per_type"],
                    "morphs_affix": m["morphs_per_type_affix"],
                }
            )
            continuity_rows.append(
                {
                    "stream": key,
                    "mode": mode,
                    "adj_folio_cos": m["adj_folio_cos"],
                    "cos_null_mean": m["adj_folio_cos_null_mean"],
                    "cos_z": round(m["adj_folio_cos_z"], 2),
                    "edit1_overlap": m["adj_folio_edit1_overlap"],
                    "edit1_null_mean": m["adj_folio_edit1_null_mean"],
                    "edit1_z": round(m["adj_folio_edit1_z"], 2),
                }
            )

    for hand in H.HANDS:
        bh = data["predictions"]["S3"]["by_hand"][hand]
        s3_rows.append(
            {
                "hand": hand,
                "MS_keep": bh["ms_keep_rate"],
                "PLC_keep": bh["plc_keep_rate"],
                "diff_keep": bh["abs_diff_keep_rate"],
                "MS_D1": bh["ms_D1_seed"],
                "PLC_D1": bh["plc_D1_seed"],
                "diff_D1": bh["abs_diff_D1_seed"],
                "MS_morphs": bh["ms_morphs_per_type"],
                "PLC_morphs": bh["plc_morphs_per_type"],
                "diff_morphs": bh["abs_diff_morphs_per_type"],
                "within_0.08": bh["within_008"],
            }
        )

    return mode_rows, continuity_rows, s3_rows


def _make_figure(data: dict, pred: dict) -> None:
    streams = data["streams"]
    fig, axes = plt.subplots(2, 2, figsize=(14.0, 9.2))
    ax_keep, ax_d1, ax_mi, ax_morph = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]

    xs = np.arange(len(H.STREAM_ORDER))
    labels = [SHORT_LABELS[s] for s in H.STREAM_ORDER]
    w = 0.26

    # Panel A: Retention rate (keep_rate) across modes
    keep_w25 = [streams[s]["modes"]["local_W25"]["keep_rate"] for s in H.STREAM_ORDER]
    keep_fc = [streams[s]["modes"]["folio_comp"]["keep_rate"] for s in H.STREAM_ORDER]
    ax_keep.bar(xs - w / 2, keep_w25, width=w, color="#4C78A8", label="local_W25 (W=25)")
    ax_keep.bar(xs + w / 2, keep_fc, width=w, color="#F58518", label="folio_comp (whole folio)")
    ax_keep.set_xticks(xs, labels, rotation=22, ha="right")
    ax_keep.set_ylabel("Fraction of tokens retained (`keep_rate`)")
    ax_keep.set_ylim(0.0, 0.85)
    ax_keep.set_title("A. Seed Retention Rate (`keep_rate`)")
    ax_keep.grid(True, axis="y", alpha=0.25)
    ax_keep.legend(fontsize=8.5, frameon=False)

    # Panel B: Held-out word-order gain D1_seed across modes
    d1_raw = [streams[s]["modes"]["raw"]["D1_seed"] for s in H.STREAM_ORDER]
    d1_w25 = [streams[s]["modes"]["local_W25"]["D1_seed"] for s in H.STREAM_ORDER]
    d1_fc = [streams[s]["modes"]["folio_comp"]["D1_seed"] for s in H.STREAM_ORDER]
    ax_d1.bar(xs - w, d1_raw, width=w, color="#7F7F7F", label="raw")
    ax_d1.bar(xs, d1_w25, width=w, color="#4C78A8", label="local_W25")
    ax_d1.bar(xs + w, d1_fc, width=w, color="#F58518", label="folio_comp")
    ax_d1.axhline(0.0, color="black", lw=0.9)
    ax_d1.axhline(H.S1_MIN_D1, color="#D62728", ls="--", lw=1.1, label="S1 threshold (+0.05)")
    ax_d1.set_xticks(xs, labels, rotation=22, ha="right")
    ax_d1.set_ylabel("$D_1 = \\mathrm{KN1} - \\min(\\mathrm{KN2}, \\mathrm{KN3})$ (bits/word)")
    ax_d1.set_title("B. Held-Out Word-Order Gain ($D_1$) After De-Padding (S1)")
    ax_d1.grid(True, axis="y", alpha=0.25)
    ax_d1.legend(fontsize=8, frameon=False)

    # Panel C: Within-folio adjacent stem MI z-score (mi_adj_z) on local_W25 and folio_comp
    mi_w25 = [streams[s]["modes"]["local_W25"]["mi_adj_z"] for s in H.STREAM_ORDER]
    mi_fc = [streams[s]["modes"]["folio_comp"]["mi_adj_z"] for s in H.STREAM_ORDER]
    ax_mi.bar(xs - w / 2, mi_w25, width=w, color="#4C78A8", label="local_W25")
    ax_mi.bar(xs + w / 2, mi_fc, width=w, color="#F58518", label="folio_comp")
    ax_mi.axhline(H.S2_MIN_Z, color="#D62728", ls="--", lw=1.1, label="S2 95% threshold (z = 1.96)")
    ax_mi.axhline(0.0, color="black", lw=0.8)
    ax_mi.set_xticks(xs, labels, rotation=22, ha="right")
    ax_mi.set_ylabel("Adjacent stem bigram MI $z$-score (`mi_adj_z`)")
    ax_mi.set_title("C. Within-Folio Seed-Order MI $z$-Score (S2)")
    ax_mi.grid(True, axis="y", alpha=0.25)
    ax_mi.legend(fontsize=8, frameon=False)

    # Panel D: Morpheme inventory (morphs_per_type) & cross-folio continuity (adj_folio_cos) on local_W25
    mpt_w25 = [streams[s]["modes"]["local_W25"]["morphs_per_type"] for s in H.STREAM_ORDER]
    cos_w25 = [streams[s]["modes"]["local_W25"]["adj_folio_cos"] for s in H.STREAM_ORDER]
    e1_w25 = [streams[s]["modes"]["local_W25"]["adj_folio_edit1_overlap"] for s in H.STREAM_ORDER]
    ax_morph.bar(xs - w, mpt_w25, width=w, color="#54A24B", label="morphs_per_type (Bayes M2)")
    ax_morph.bar(xs, cos_w25, width=w, color="#E45756", label="adj_folio_cos (word cosine)")
    ax_morph.bar(xs + w, e1_w25, width=w, color="#B279A2", label="adj_folio_edit1_overlap")
    ax_morph.axhline(
        H.NAT_MORPH_THRESHOLD,
        color="#54A24B",
        ls="--",
        lw=1.0,
        label="h31 language-like morphs (0.18)",
    )
    ax_morph.set_xticks(xs, labels, rotation=22, ha="right")
    ax_morph.set_ylabel("Ratio / Cosine / Overlap (`local_W25`)")
    ax_morph.set_title("D. Piece Inventory & Cross-Folio Continuity on `local_W25` (S3)")
    ax_morph.grid(True, axis="y", alpha=0.25)
    ax_morph.legend(fontsize=7.8, frameon=False)

    s1_str = "pass" if pred["S1"]["passed"] else "fail"
    s2_str = "pass" if pred["S2"]["passed"] else "fail"
    s3_str = "pass" if pred["S3"]["passed"] else "fail"
    fig.suptitle(
        f"h49: De-Padding / Seed-Skeleton Extraction (S1={s1_str}, S2={s2_str}, S3={s3_str}; verdict={pred['verdict']})",
        fontsize=11.5,
    )
    fig.tight_layout()
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _readme(
    data: dict,
    pred: dict,
    mode_rows: list[dict],
    continuity_rows: list[dict],
    s3_rows: list[dict],
) -> str:
    st = data["streams"]
    s1_v = "fail" if not pred["S1"]["passed"] else "pass"
    s2_v = "fail" if not pred["S2"]["passed"] else "pass"
    s3_v = "pass" if pred["S3"]["passed"] else "fail"

    z_raw_1a = st["MS_1A"]["modes"]["raw"]["mi_adj_z"]
    z_raw_2b = st["MS_2B"]["modes"]["raw"]["mi_adj_z"]
    z_raw_3b = st["MS_3B"]["modes"]["raw"]["mi_adj_z"]
    z_w25_1a = st["MS_1A"]["modes"]["local_W25"]["mi_adj_z"]
    z_w25_2b = st["MS_2B"]["modes"]["local_W25"]["mi_adj_z"]
    z_w25_3b = st["MS_3B"]["modes"]["local_W25"]["mi_adj_z"]
    z_fc_1a = st["MS_1A"]["modes"]["folio_comp"]["mi_adj_z"]
    z_fc_2b = st["MS_2B"]["modes"]["folio_comp"]["mi_adj_z"]
    z_fc_3b = st["MS_3B"]["modes"]["folio_comp"]["mi_adj_z"]
    z_fc_plc2b = st["page_line_copier_2B"]["modes"]["folio_comp"]["mi_adj_z"]
    z_w25_it = st["it_boccaccio"]["modes"]["local_W25"]["mi_adj_z"]
    z_fc_it = st["it_boccaccio"]["modes"]["folio_comp"]["mi_adj_z"]

    lines = [
        "# h49: Does Stripping Same-Folio One-Edit Echoes Uncover a Language-Like Seed Skeleton?",
        "",
        "Pre-registration: [PREREG.md](PREREG.md). Tests whether stripping same-folio exact repeats "
        "and unit-edit-distance-1 echoes (`local_W25` with lookback window $W = 25$, and `folio_comp` "
        "across the entire folio) uncovers a language-like seed skeleton in MS 408 (`1A`, `2B`, `3B`) "
        "with positive held-out word-order gain ($D_1 > 0$) or sequential within-folio seed syntax, "
        "or whether the stripped MS 408 skeleton matches the no-plaintext `h47` `page_line_copier` generator.",
        "",
        "## Predictions and Verdicts (`S1`–`S3`)",
        "",
        f"- Overall verdict: **`{pred['verdict']}`**",
        f"- **S1 (de-padding uncovers positive word-order syntax):** **{s1_v}** "
        f"(passing MS hands: `{len(pred['S1']['passing_hands'])}/3` {pred['S1']['passing_hands']}). "
        "Stripping one-edit echoes does not flip $D_1$ positive in any MS hand: on `local_W25`, "
        "`D1_seed` is `-0.2249` (`1A`), `-0.2325` (`2B`), and `-0.2402` (`3B`); on `folio_comp`, "
        "`D1_seed` is `-0.2133` (`1A`), `-0.1534` (`2B`), and `-0.1243` (`3B`).",
        f"- **S2 (sequential order among seeds inside a folio):** **{s2_v}** "
        f"(passing MS hands: `{len(pred['S2']['passing_hands'])}/3` {pred['S2']['passing_hands']}). "
        "On `folio_comp`, adjacent top-50 stem bigram MI exceeds the 95th percentile (`mi_adj_z > 1.96`) "
        f"of 100 within-folio seed permutations in `2/3` hands (`1A`: `z = {z_fc_1a:+.2f}`, "
        f"`2B`: `z = {z_fc_2b:+.2f}`, `3B`: `z = {z_fc_3b:+.2f}`; on `local_W25`: `z = {z_w25_1a:+.2f}`, "
        f"`{z_w25_2b:+.2f}`, `{z_w25_3b:+.2f}`). However, the no-plaintext `page_line_copier_2B` "
        f"also reaches `z = {z_fc_plc2b:+.2f}` on `folio_comp` from line-initial/final character-state "
        f"bias, whereas plain Italian prose (`it_boccaccio`) reaches `z = {z_w25_it:+.2f}` on `local_W25` "
        f"and `z = {z_fc_it:+.2f}` on `folio_comp`.",
        f"- **S3 (MS seed skeleton vs `h47` no-plaintext skeleton):** **{s3_v}** "
        f"(passing MS hands: `{len(pred['S3']['passing_hands'])}/3` {pred['S3']['passing_hands']}). "
        "Across all three hands (`1A`, `2B`, `3B`), the `local_W25` retention rate (`keep_rate`), "
        "word-order gain (`D1_seed`), and Bayesian piece inventory (`morphs_per_type`) of MS 408 lie "
        "within $\\pm 0.08$ of the no-plaintext `page_line_copier` generator.",
        "",
        "## S3 Comparison: MS 408 vs `page_line_copier` on `local_W25` ($\\pm 0.08$ equivalence band)",
        "",
        *_table(s3_rows, digits=4),
        "",
        "## Measures 1–3: Retention Rate (`keep_rate`), Word-Order Gain (`D1_seed`, `mi_adj_z`), and Piece Inventory (`morphs_per_type`)",
        "",
        *_table(mode_rows, digits=4),
        "",
        "## Measure 4: Cross-Folio Seed Continuity (`adj_folio_cos` and 1-Edit Overlap vs 200 Within-Quire Permutations)",
        "",
        *_table(continuity_rows, digits=4),
        "",
        "## Key Findings (Distributional Only, No Translation Claims)",
        "",
        "1. **De-padding same-folio one-edit echoes removes 45%–55% of MS tokens locally (`local_W25`) and 58%–76% whole-folio (`folio_comp`), but leaves $D_1$ strictly negative (`S1` falsified):** "
        "If negative raw $D_1$ in MS 408 (`-0.1775`, `-0.1351`, `-0.1712`) were caused by local one-edit padding echoes interrupting an ordered seed text, removing those echoes would move $D_1$ positive. Instead, `local_W25` pushes $D_1$ slightly more negative (`-0.2249`, `-0.2325`, `-0.2402`), matching `page_line_copier` (`-0.2439`, `-0.2523`, `-0.2407` within $0.020$ bits/word).",
        "2. **Within-folio adjacent stem MI drops by ~90% once local echoes are stripped (`S2` marginally passes in 2/3 hands):** "
        f"In raw MS 408, adjacent stem MI is strongly elevated (`mi_adj_z = {z_raw_1a:+.2f}`, `{z_raw_2b:+.2f}`, `{z_raw_3b:+.2f}`) because of within-line character-junction rules and short-lag near-repeats. Stripping same-folio one-edit components (`folio_comp`) reduces `mi_adj_z` to `{z_fc_1a:+.2f}` (`1A`), `{z_fc_2b:+.2f}` (`2B`), and `{z_fc_3b:+.2f}` (`3B`), comparable to `page_line_copier_2B` (`{z_fc_plc2b:+.2f}`), whereas natural prose (`it_boccaccio`) retains strong sequential order (`mi_adj_z = {z_w25_it:+.2f}` on `local_W25` and `{z_fc_it:+.2f}` on `folio_comp`).",
        "3. **The stripped MS seed skeleton is quantitatively indistinguishable from the no-plaintext `h47` generator (`S3` supported):** "
        "Across all three hands on `local_W25`, maximum absolute differences between MS and `page_line_copier` are `0.0727` on `keep_rate`, `0.0198` on `D1_seed`, and `0.0113` on `morphs_per_type` — all inside the preregistered $\\pm 0.08$ tolerance.",
        "",
        "## Reproduction",
        "",
        "```bash",
        "python3 -m pytest hypotheses/h49_seed_skeleton_extraction/test_h49.py -p no:cacheprovider",
        "python3 hypotheses/h49_seed_skeleton_extraction/run_h49.py",
        "python3 hypotheses/h49_seed_skeleton_extraction/summarise.py",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    if not RES.is_file():
        raise SystemExit(f"Missing {RES}; run run_h49.py first.")
    data = json.loads(RES.read_text(encoding="utf-8"))
    pred = _check(data)
    mode_rows, continuity_rows, s3_rows = _build_tables(data)
    _make_figure(data, pred)

    summary = {
        "hypothesis": "h49_seed_skeleton_extraction",
        "verdict": pred["verdict"],
        "predictions": pred,
        "s3_comparison_local_W25": s3_rows,
        "measures_table": mode_rows,
        "continuity_table": continuity_rows,
        "seed": data["seed"],
        "w_local": data["w_local"],
        "n_perm_mi": data["n_perm_mi"],
        "n_perm_folio": data["n_perm_folio"],
        "numpy": data["numpy"],
        "python": data["python"],
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    status = {
        "complete": True,
        "hypothesis": "h49_seed_skeleton_extraction",
        "verdict": pred["verdict"],
        "S1": pred["S1"]["passed"],
        "S1_passing_hands": pred["S1"]["passing_hands"],
        "S2": pred["S2"]["passed"],
        "S2_passing_hands": pred["S2"]["passing_hands"],
        "S3": pred["S3"]["passed"],
        "S3_passing_hands": pred["S3"]["passing_hands"],
        "seed": data["seed"],
        "runtime_sec": data["runtime_sec"],
    }
    STATUS.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    README.write_text(
        _readme(data, pred, mode_rows, continuity_rows, s3_rows),
        encoding="utf-8",
    )
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
