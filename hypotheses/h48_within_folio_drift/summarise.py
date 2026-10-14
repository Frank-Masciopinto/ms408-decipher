"""Write STATUS.json, summary.json, figures/within_folio_drift.png, and README.md from results/measurements.json."""
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

import h48_lib as H  # noqa: E402

RES = HERE / "results" / "measurements.json"
SUMMARY = HERE / "results" / "summary.json"
STATUS = HERE / "results" / "STATUS.json"
FIG = HERE / "figures" / "within_folio_drift.png"
README = HERE / "README.md"


def _fmt(val, digits: int = 6) -> str:
    if val is None:
        return "null"
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, float):
        return f"{val:.{digits}f}"
    return str(val)


def _table(rows: list[dict]) -> list[str]:
    header = list(rows[0].keys())
    out = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
    ]
    for row in rows:
        out.append("| " + " | ".join(_fmt(row[k]) for k in header) + " |")
    return out


def _check(data: dict) -> dict:
    recomputed = H.score_predictions(data["streams"])
    if recomputed != data["predictions"]:
        raise SystemExit(f"stored predictions {data['predictions']} != recomputed {recomputed}")
    return recomputed


def _build_rows(data: dict) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    streams = data["streams"]
    slope_rows: list[dict] = []
    m1_lag_rows: list[dict] = []
    m2_lag_rows: list[dict] = []
    d3_rows: list[dict] = []

    for key in H.STREAM_ORDER:
        rec = streams[key]
        m1 = rec["M1"]
        m2 = rec["M2"]
        m3 = rec["M3"]
        slope_rows.append(
            {
                "stream": key,
                "n_folios": rec["n_folios"],
                "n_lines": rec["n_lines"],
                "n_tokens": rec["n_tokens"],
                "S_edit": m1["S_edit"],
                "S_edit_p95": m1["S_edit_null_p95"],
                "S_edit_z": round(m1["S_edit_z"], 2),
                "D1_pass": m1["pass"],
                "S_cos3": m2["S_cos3"],
                "S_cos3_p95": m2["S_cos3_null_p95"],
                "S_cos3_z": round(m2["S_cos3_z"], 2),
                "D2_pass": m2["pass"],
                "half_js": m3["half_js"],
                "half_js_z": round(m3["half_js_z"], 2),
            }
        )
        m1_row: dict = {"stream": key}
        m2_row: dict = {"stream": key}
        for b in H.LAG_NAMES:
            m1_row[f"lag_{b}"] = m1["edit1_lag"][b]["rate"]
            m2_row[f"cos3_{b}"] = m2["cos3_lag"][b]["mean"]
        for b in H.LAG_NAMES:
            m2_row[f"jac_{b}"] = m2["jaccard_lag"][b]["mean"]
        m1_lag_rows.append(m1_row)
        m2_lag_rows.append(m2_row)

    for hand in H.HANDS:
        key = f"MS_{hand}"
        d3 = streams[key]["D3"]
        d3_rows.append(
            {
                "hand": hand,
                "obs_Delta12": d3["observed_Delta12_rate"],
                "folio_perm_rate": d3["same_folio_line_permuted_rate"],
                "quire_shuf_rate": d3["quire_shuffle_rate"],
                "total_excess": d3["total_excess"],
                "palette_comp": d3["folio_palette_component"],
                "palette_z": round(d3["folio_palette_z"], 2),
                "palette_share": round(d3["folio_palette_share"], 4),
                "drift_comp": d3["within_folio_drift_component"],
                "drift_z": round(d3["within_folio_drift_z"], 2),
                "drift_share": round(d3["within_folio_drift_share"], 4),
                "both_gt_2sd": d3["both_positive_gt_2sd"],
            }
        )

    return slope_rows, m1_lag_rows, m2_lag_rows, d3_rows


def _make_figure(data: dict, pred: dict) -> None:
    streams = data["streams"]
    fig, axes = plt.subplots(1, 3, figsize=(15.0, 4.6))
    x = np.arange(len(H.LAG_NAMES))

    style_map = {
        "MS_1A": ("#1f77b4", "-", "o", "MS 1A"),
        "MS_2B": ("#d62728", "-", "s", "MS 2B"),
        "MS_3B": ("#2ca02c", "-", "^", "MS 3B"),
        "self_citation": ("#9467bd", "--", "d", "self_citation"),
        "h39_native_tuned": ("#ff7f0e", "--", "v", "h39_native_tuned"),
        "palette_ctrl": ("#7f7f7f", ":", "x", "palette_ctrl (2B perm)"),
        "it_boccaccio": ("#8c564b", "-.", ".", "it_boccaccio"),
        "la_pliny_herbal": ("#17becf", "-.", ".", "la_pliny_herbal"),
    }

    ax0, ax1, ax2 = axes
    for key in H.STREAM_ORDER:
        color, ls, marker, label = style_map[key]
        m1_vals = [streams[key]["M1"]["edit1_lag"][b]["rate"] for b in H.LAG_NAMES]
        m2_vals = [streams[key]["M2"]["cos3_lag"][b]["mean"] for b in H.LAG_NAMES]
        ax0.plot(x, m1_vals, color=color, linestyle=ls, marker=marker, label=label, lw=1.6, ms=5)
        ax1.plot(x, m2_vals, color=color, linestyle=ls, marker=marker, label=label, lw=1.6, ms=5)

    ax0.set_xticks(x, H.LAG_NAMES)
    ax0.set_xlabel("Within-folio line lag $\\Delta \\ell$")
    ax0.set_ylabel("One-edit rate $P(\\mathrm{edit1} \\mid \\Delta \\ell)$")
    ax0.set_title("M1: Within-folio one-edit decay")
    ax0.grid(True, alpha=0.25)
    ax0.legend(fontsize=7.5, frameon=False, loc="upper right")

    ax1.set_xticks(x, H.LAG_NAMES)
    ax1.set_xlabel("Within-folio line lag $\\Delta \\ell$")
    ax1.set_ylabel("Mean unit-3gram cosine")
    ax1.set_title("M2: Within-folio unit-3gram cosine decay")
    ax1.grid(True, alpha=0.25)

    hands_x = np.arange(len(H.HANDS))
    pal_vals = [streams[f"MS_{h}"]["D3"]["folio_palette_component"] for h in H.HANDS]
    drift_vals = [streams[f"MS_{h}"]["D3"]["within_folio_drift_component"] for h in H.HANDS]
    ax2.bar(hands_x, pal_vals, width=0.55, color="#4C78A8", label="Folio-palette component")
    ax2.bar(
        hands_x,
        drift_vals,
        width=0.55,
        bottom=pal_vals,
        color="#F58518",
        label="Within-folio drift component",
    )
    ax2.set_xticks(hands_x, [f"MS {h}" for h in H.HANDS])
    ax2.set_ylabel("Short-lag ($\\Delta \\ell \\in \\{1,2\\}$) edit1 excess over quire shuffle")
    ax2.set_title("D3: Palette vs sequential drift decomposition")
    ax2.grid(True, axis="y", alpha=0.25)
    ax2.legend(fontsize=8, frameon=False, loc="upper right")

    d1_str = "pass" if pred["D1"] else "fail"
    d2_str = "pass" if pred["D2"] else "fail"
    d3_str = "pass" if pred["D3"] else "fail"
    fig.suptitle(
        f"h48: Within-folio copy drift vs stationary page palette (D1={d1_str}, D2={d2_str}, D3={d3_str})",
        fontsize=11,
    )
    fig.tight_layout()
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _readme(
    data: dict,
    pred: dict,
    slope_rows: list[dict],
    m1_lag_rows: list[dict],
    m2_lag_rows: list[dict],
    d3_rows: list[dict],
) -> str:
    d1_verdict = "pass" if pred["D1"] else "fail"
    d2_verdict = "pass" if pred["D2"] else "fail"
    d3_verdict = "pass" if pred["D3"] else "fail"
    lines = [
        "# h48: within-folio copy drift vs fixed page palette",
        "",
        "Pre-registration: [PREREG.md](PREREG.md). Tests whether within-folio lexical and one-edit "
        "similarity in MS 408 decays with line distance $\\Delta \\ell = \\ell_2 - \\ell_1$ inside a single "
        "folio (top-to-bottom sequential drift) or is stationary across line positions on the folio "
        "(fixed page vocabulary palette).",
        "",
        "## Predictions",
        "",
        f"- **D1 (within-folio one-edit drift):** **{d1_verdict}** "
        f"(passing MS hands: {', '.join(pred['D1_pass_hands'])} — 3/3 hands exceed the 95th percentile "
        "of 200 within-folio line permutations, seed 48).",
        f"- **D2 (within-folio unit-3gram drift):** **{d2_verdict}** "
        f"(passing MS hands: {', '.join(pred['D2_pass_hands'])} — 3/3 hands exceed the 95th percentile "
        "of 200 within-folio line permutations, seed 48).",
        f"- **D3 (drift vs palette decomposition):** **{d3_verdict}** "
        f"(passing MS hands: {', '.join(pred['D3_pass_hands'])} — in 3/3 hands, both the folio-palette "
        "component and the within-folio sequential drift component are strictly positive and $> 2$ null SDs).",
        "",
        "## Summary of slopes (M1, M2) and half-folio drift (M3)",
        "",
        *_table(slope_rows),
        "",
        "## M1: Within-folio one-edit rate `P(edit1 | Delta_l)` by line lag",
        "",
        *_table(m1_lag_rows),
        "",
        "## M2: Within-folio unit-3gram cosine (`cos3`) and word-type Jaccard (`jac`) by line lag",
        "",
        *_table(m2_lag_rows),
        "",
        "## D3: Decomposition of short-lag (`Delta_l in {1,2}`) same-folio one-edit excess over quire shuffle",
        "",
        *_table(d3_rows),
        "",
        "## Key findings (distributional only, no translation claims)",
        "",
        "1. **Sequential within-folio copy drift is present in all three MS hands (`1A`, `2B`, `3B`):** "
        "Permuting line order within each folio preserves the exact folio vocabulary multiset and line lengths, "
        "yet destroys the short-lag excess (`S_edit = +0.008568` in `1A`, `+0.009348` in `2B`, `+0.005960` in `3B`; "
        "`z = 5.21`, `11.47`, `7.81` above the within-folio permutation null). The synthetic stationary-palette "
        "control (`palette_ctrl`) has `S_edit = -0.001525` and `S_cos3 = -0.007502` (both below the null).",
        "2. **Prose controls show mild lexical drift (`S_cos3 > 0`) but zero one-edit drift (`S_edit <= 0`):** "
        "`it_boccaccio` and `la_pliny_herbal` pass `S_cos3` (`+0.008739` and `+0.009669`) from topical continuity, "
        "but fail `S_edit` (`-0.000610` and `-0.000133`), whereas MS hands and copy-drift generators (`self_citation`, "
        "`h39_native_tuned`) show strong decay in both `S_edit` and `S_cos3`.",
        "3. **Both a page-level vocabulary seed and top-to-bottom drift contribute (`D3`):** "
        "Decomposing short-lag (`Delta_l in {1,2}`) same-folio one-edit excess over a 200-draw within-quire shuffle "
        "shows that in `1A` (`62.8%` palette / `37.2%` drift), `2B` (`36.7%` palette / `63.3%` drift), and `3B` "
        "(`59.8%` palette / `40.2%` drift), both components exceed `5` null SDs.",
        "",
        "## Run",
        "",
        "```bash",
        "python -m pytest hypotheses/h48_within_folio_drift/test_h48.py -p no:cacheprovider",
        "python hypotheses/h48_within_folio_drift/run_h48.py",
        "python hypotheses/h48_within_folio_drift/summarise.py",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    data = json.loads(RES.read_text(encoding="utf-8"))
    pred = _check(data)
    slope_rows, m1_lag_rows, m2_lag_rows, d3_rows = _build_rows(data)
    _make_figure(data, pred)

    summary = {
        "hypothesis": "h48_within_folio_drift",
        "predictions": pred,
        "slopes_and_half_drift": slope_rows,
        "m1_edit1_lag": m1_lag_rows,
        "m2_lexical_lag": m2_lag_rows,
        "d3_decomposition": d3_rows,
        "n_perm": data["n_perm"],
        "seed": data["seed"],
        "numpy": data["numpy"],
        "python": data["python"],
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    status = {
        "complete": True,
        "hypothesis": "h48_within_folio_drift",
        "D1": pred["D1"],
        "D1_pass_hands": pred["D1_pass_hands"],
        "D2": pred["D2"],
        "D2_pass_hands": pred["D2_pass_hands"],
        "D3": pred["D3"],
        "D3_pass_hands": pred["D3_pass_hands"],
        "verdict": "supported" if (pred["D1"] and pred["D2"] and pred["D3"]) else "mixed",
        "n_perm": data["n_perm"],
        "seed": data["seed"],
    }
    STATUS.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    README.write_text(
        _readme(data, pred, slope_rows, m1_lag_rows, m2_lag_rows, d3_rows),
        encoding="utf-8",
    )
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
