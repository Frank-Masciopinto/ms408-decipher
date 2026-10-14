"""Write STATUS, summary, figure, and README from results/measurements.json."""
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
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import h46_lib as H  # noqa: E402

RES = HERE / "results" / "measurements.json"
FIG = HERE / "figures" / "folio_reset_mechanism.png"
STATUS = HERE / "results" / "STATUS.json"
SUMMARY = HERE / "results" / "summary.json"
README = HERE / "README.md"


def _fmt(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _cell(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _table(rows: list[dict]) -> list[str]:
    header = list(rows[0])
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_cell(row[key]) for key in header) + " |")
    return lines


def _check(data: dict) -> dict:
    pred = H.predictions(data["test1"], data["test2"], data["test3"])
    if pred != data["predictions"]:
        raise SystemExit(f"stored predictions {data['predictions']} != recomputed {pred}")

    for hand in H.HANDS:
        for bname, row in data["test1"][hand]["bins"].items():
            scored, passed = H.is_scored_and_pass(
                row["n_same_eligible"],
                row["n_cross_eligible"],
                row["effect"],
                row["null_p95"],
                min_eligible=data["min_eligible"],
            )
            if scored != row["scored"] or passed != row["pass"]:
                raise SystemExit(f"Test 1 {hand} {bname} scored/pass mismatch")
            effects = np.asarray(row["null_effects"], dtype=np.float64)
            if len(effects) != data["n_rotations"]:
                raise SystemExit(f"Test 1 {hand} {bname} has {len(effects)} nulls")
            p95 = float(np.percentile(effects, 95, method="linear"))
            mean = float(effects.mean())
            if abs(p95 - row["null_p95"]) > 1e-9 or abs(mean - row["null_mean"]) > 1e-9:
                raise SystemExit(f"Test 1 {hand} {bname} null summary mismatch")

        t2 = data["test2"][hand]
        effects2 = np.asarray(t2["null_effects"], dtype=np.float64)
        if len(effects2) != data["n_line_perms"]:
            raise SystemExit(f"Test 2 {hand} has {len(effects2)} nulls")
        p95_2 = float(np.percentile(effects2, 95, method="linear"))
        mean_2 = float(effects2.mean())
        if abs(p95_2 - t2["null_p95"]) > 1e-9 or abs(mean_2 - t2["null_mean"]) > 1e-9:
            raise SystemExit(f"Test 2 {hand} null summary mismatch")
        if bool(t2["effect"] > p95_2) != t2["pass"]:
            raise SystemExit(f"Test 2 {hand} pass flag mismatch")

        for bname, row in data["test3"][hand]["bins"].items():
            scored, passed = H.is_scored_and_pass(
                row["n_v_to_r_eligible"],
                row["n_r_to_v_eligible"],
                row["effect"],
                row["null_p95"],
                min_eligible=data["min_eligible"],
            )
            if scored != row["scored"] or passed != row["pass"]:
                raise SystemExit(f"Test 3 {hand} {bname} scored/pass mismatch")
            effects3 = np.asarray(row["null_effects"], dtype=np.float64)
            if len(effects3) != data["n_trans_swaps"]:
                raise SystemExit(f"Test 3 {hand} {bname} has {len(effects3)} nulls")
            p95_3 = float(np.percentile(effects3, 95, method="linear"))
            mean_3 = float(effects3.mean())
            if abs(p95_3 - row["null_p95"]) > 1e-9 or abs(mean_3 - row["null_mean"]) > 1e-9:
                raise SystemExit(f"Test 3 {hand} {bname} null summary mismatch")

    return pred


def _test1_rows(data: dict) -> list[dict]:
    rows = []
    for hand in H.HANDS:
        for bname in data["test1_bins"]:
            row = data["test1"][hand]["bins"][bname]
            rows.append(
                {
                    "hand": hand,
                    "bin": bname,
                    "same_eligible": row["n_same_eligible"],
                    "same_sampled": row["n_same_sampled"],
                    "same_rate": row["same_rate"],
                    "cross_eligible": row["n_cross_eligible"],
                    "cross_sampled": row["n_cross_sampled"],
                    "cross_rate": row["cross_rate"],
                    "effect": row["effect"],
                    "null_mean": row["null_mean"],
                    "null_p95": row["null_p95"],
                    "scored": row["scored"],
                    "pass": row["pass"],
                }
            )
    return rows


def _test2_rows(data: dict) -> list[dict]:
    rows = []
    for hand in H.HANDS:
        row = data["test2"][hand]
        rows.append(
            {
                "hand": hand,
                "folios": f"{row['n_folios_eligible']}/{row['n_folios_total']}",
                "seed_eligible": row["n_seed_eligible"],
                "seed_edit1": row["n_seed_edit1"],
                "seed_rate": row["seed_rate"],
                "interior_eligible": row["n_interior_eligible"],
                "interior_edit1": row["n_interior_edit1"],
                "interior_rate": row["interior_rate"],
                "effect": row["effect"],
                "null_mean": row["null_mean"],
                "null_p95": row["null_p95"],
                "pass": row["pass"],
            }
        )
    return rows


def _test3_rows(data: dict) -> list[dict]:
    rows = []
    for hand in H.HANDS:
        for bname in data["test3_bins"]:
            row = data["test3"][hand]["bins"][bname]
            rows.append(
                {
                    "hand": hand,
                    "bin": bname,
                    "transitions": f"{row['n_v_to_r_transitions']} v->r / {row['n_r_to_v_transitions']} r->v",
                    "v_to_r_eligible": row["n_v_to_r_eligible"],
                    "v_to_r_rate": row["v_to_r_rate"],
                    "r_to_v_eligible": row["n_r_to_v_eligible"],
                    "r_to_v_rate": row["r_to_v_rate"],
                    "effect": row["effect"],
                    "null_mean": row["null_mean"],
                    "null_p95": row["null_p95"],
                    "scored": row["scored"],
                    "pass": row["pass"],
                }
            )
    return rows


def _figure(data: dict, pred: dict) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.6))

    # Panel 1: Test 1 cross-folio drop
    ax1 = axes[0]
    t1_labels = []
    t1_eff = []
    t1_p95 = []
    t1_colors = []
    for hand in H.HANDS:
        for bname in data["test1_bins"]:
            row = data["test1"][hand]["bins"][bname]
            t1_labels.append(f"{hand}\n{bname}")
            t1_eff.append(np.nan if row["effect"] is None else row["effect"])
            t1_p95.append(np.nan if row["null_p95"] is None else row["null_p95"])
            if not row["scored"]:
                t1_colors.append("#b0b0b0")
            elif row["pass"]:
                t1_colors.append("#4C78A8")
            else:
                t1_colors.append("#E45756")
    x1 = np.arange(len(t1_labels))
    ax1.bar(x1, t1_eff, color=t1_colors, width=0.68, zorder=2)
    ax1.scatter(x1, t1_p95, marker="_", s=180, c="black", zorder=3)
    ax1.axhline(0.0, color="0.35", lw=0.8, zorder=1)
    ax1.set_xticks(x1, t1_labels, fontsize=7.5)
    ax1.set_ylabel("rate(same) − rate(cross)")
    ax1.set_title(f"Test 1: Cross-folio drop (F1 {'pass' if pred['F1'] else 'fail'})")

    # Panel 2: Test 2 first-line seed test
    ax2 = axes[1]
    t2_labels = list(H.HANDS)
    t2_eff = []
    t2_p95 = []
    t2_colors = []
    for hand in H.HANDS:
        row = data["test2"][hand]
        t2_eff.append(np.nan if row["effect"] is None else row["effect"])
        t2_p95.append(np.nan if row["null_p95"] is None else row["null_p95"])
        t2_colors.append("#4C78A8" if row["pass"] else "#E45756")
    x2 = np.arange(len(t2_labels))
    ax2.bar(x2, t2_eff, color=t2_colors, width=0.55, zorder=2)
    ax2.scatter(x2, t2_p95, marker="_", s=260, c="black", zorder=3)
    ax2.axhline(0.0, color="0.35", lw=0.8, zorder=1)
    ax2.set_xticks(x2, t2_labels)
    ax2.set_ylabel("seed_rate − interior_rate")
    ax2.set_title(f"Test 2: Line-1 seed rate (F2 {'pass' if pred['F2'] else 'fail'})")

    # Panel 3: Test 3 v->r vs r->v
    ax3 = axes[2]
    t3_labels = []
    t3_eff = []
    t3_p95 = []
    t3_colors = []
    for hand in H.HANDS:
        for bname in data["test3_bins"]:
            row = data["test3"][hand]["bins"][bname]
            t3_labels.append(f"{hand}\n{bname}")
            t3_eff.append(np.nan if row["effect"] is None else row["effect"])
            t3_p95.append(np.nan if row["null_p95"] is None else row["null_p95"])
            if not row["scored"]:
                t3_colors.append("#b0b0b0")
            elif row["pass"]:
                t3_colors.append("#4C78A8")
            else:
                t3_colors.append("#E45756")
    x3 = np.arange(len(t3_labels))
    ax3.bar(x3, t3_eff, color=t3_colors, width=0.62, zorder=2)
    ax3.scatter(x3, t3_p95, marker="_", s=220, c="black", zorder=3)
    ax3.axhline(0.0, color="0.35", lw=0.8, zorder=1)
    ax3.set_xticks(x3, t3_labels, fontsize=8.5)
    ax3.set_ylabel("rate(v_to_r) − rate(r_to_v)")
    ax3.set_title(f"Test 3: Spread vs page turn (F3 {'pass' if pred['F3'] else 'fail'})")

    handles = [
        Patch(facecolor="#4C78A8", edgecolor="none", label="pass"),
        Patch(facecolor="#E45756", edgecolor="none", label="scored, below null 95th"),
        Patch(facecolor="#b0b0b0", edgecolor="none", label="not scored"),
        Line2D([0], [0], color="black", marker="_", linestyle="None", markersize=14, label="null 95th percentile"),
    ]
    fig.legend(handles=handles, ncol=4, frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.03))
    fig.suptitle(
        f"h46: Folio reset mechanism checks    "
        f"F1 {'pass' if pred['F1'] else 'fail'}    "
        f"F2 {'pass' if pred['F2'] else 'fail'}    "
        f"F3 {'pass' if pred['F3'] else 'fail'}"
    )
    fig.tight_layout()
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _readme(data: dict, pred: dict, t1_rows: list[dict], t2_rows: list[dict], t3_rows: list[dict]) -> str:
    f1_str = "pass" if pred["F1"] else "fail"
    f2_str = "pass" if pred["F2"] else "fail"
    f3_str = "pass" if pred["F3"] else "fail"

    lines = [
        "# h46: how does the folio reset work?",
        "",
        "Pre-registration: [PREREG.md](PREREG.md). Distributional and structural checks only; no translation claims.",
        "",
        "## Data and units",
        "",
        f"Paragraph words in reading order from `h14_lib.table()`, `{data['transcription']}`, comma as a word space, "
        "hands `1A`, `2B`, `3B`. Each word is segmented into collapsed EVA units via `h13_lib.SEG(w)`. "
        "Two words form a one-edit pair when `edit1(u_i, u_j)` is true (`Levenshtein.distance(u_i, u_j) == 1` on unit tuples, "
        "`u_i != u_j`, `|len(u_i) - len(u_j)| <= 1`). Eligible pairs have `|len(u_i) - len(u_j)| <= 1` in the specified lag bin.",
        "",
        "## Predictions",
        "",
        f"- **F1 (folio boundary breaks one-edit chains):** **{f1_str}**. "
        f"In Test 1 (`21-100` or `101-500`), passing bins in Hand 1A: `{pred['F1_1A_passing_bins']}`; "
        f"passing bins in Hand 2B: `{pred['F1_2B_passing_bins']}`. "
        "(All three hands pass at `6-20`, and Hands `1A` and `3B` pass at `21-100`, with `3B` also passing at `101-500`; "
        "in Hand `2B`, the observed `rate(same) - rate(cross)` is positive at `21-100` (`+0.006200`) and `101-500` (`+0.003300`), "
        "but within-quire rotation preserves the same within-folio burst structure (`null_mean = +0.006339` and `+0.004204`, "
        "`null_p95 = +0.011412` and `+0.008700`), so `2B` does not exceed the rotation null beyond `6-20`.)",
        f"- **F2 (first-line seeding):** **{f2_str}**. "
        f"Passing hands in Test 2: `{pred['F2_passing_hands']}`. "
        "Across all three hands (`1A`, `2B`, `3B`), the folio-opening line-1 seed rate is *lower* than the interior baseline rate "
        "(`effect = -0.016680`, `-0.023632`, `-0.019057`), opposite to first-line seeding and consistent with line-1 vocabulary/register specialization.",
        f"- **F3 (open-spread copying in Hand 2B):** **{f3_str}**. "
        f"Passing bins in Hand 2B Test 3 (`21-100` or `101-500`): `{pred['F3_2B_passing_bins']}`. "
        f"In Hand `2B`, `rate(v_to_r) - rate(r_to_v)` is `{_fmt(data['test3']['2B']['bins']['21-100']['effect'])}` at `21-100` "
        f"(`null_p95 = {_fmt(data['test3']['2B']['bins']['21-100']['null_p95'])}`) and "
        f"`{_fmt(data['test3']['2B']['bins']['101-500']['effect'])}` at `101-500` "
        f"(`null_p95 = {_fmt(data['test3']['2B']['bins']['101-500']['null_p95'])}`).",
        "",
        "## Test 1 — Cross-folio drop in one-edit pairs at matched lag",
        "",
        "Up to 20,000 eligible pairs per side (`h42_lib.systematic_ranks`), scored when both `same` and `cross` have at least 200 eligible pairs, "
        "compared against 100 circular rotations of the token stream inside each quire against fixed folio lengths (seed 46).",
        "",
        *_table(t1_rows),
        "",
        "## Test 2 — Folio-opening line seed test",
        "",
        "Same-folio eligible pairs `(i, j)` (`i < j` on different lines) on folios with at least 6 paragraph lines: "
        "`seed_rate` (token `i` on line 1, token `j` on a later line) minus `interior_rate` (neither token on line 1), "
        "compared against 200 within-folio line-order permutations (seed 46).",
        "",
        *_table(t2_rows),
        "",
        "## Test 3 — Visible spread (`v -> r`) vs page turn (`r -> v`)",
        "",
        "Cross-folio eligible pairs `(i, j)` across consecutive manuscript folios (`folio_index[j] == folio_index[i] + 1`) "
        "in `21-100` and `101-500`: `rate(v_to_r) - rate(r_to_v)` against 200 random permutations of the `r_to_v` / `v_to_r` "
        "labels across consecutive folio transitions within each hand (seed 46).",
        "",
        *_table(t3_rows),
        "",
        "## Run",
        "",
        "```bash",
        "export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1",
        "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1",
        "python -m pytest hypotheses/h46_folio_reset_mechanism/test_h46.py",
        "python hypotheses/h46_folio_reset_mechanism/run_h46.py",
        "python hypotheses/h46_folio_reset_mechanism/summarise.py",
        "```",
        "",
        f"numpy {data['numpy']}, rapidfuzz {data['rapidfuzz']}, python {data['python']}, runtime {data['runtime_sec']:.1f}s.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    data = json.loads(RES.read_text(encoding="utf-8"))
    pred = _check(data)
    t1_rows = _test1_rows(data)
    t2_rows = _test2_rows(data)
    t3_rows = _test3_rows(data)
    _figure(data, pred)
    summary = {
        "predictions": pred,
        "test1_rows": t1_rows,
        "test2_rows": t2_rows,
        "test3_rows": t3_rows,
        "numpy": data["numpy"],
        "rapidfuzz": data["rapidfuzz"],
        "python": data["python"],
        "runtime_sec": data["runtime_sec"],
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    README.write_text(_readme(data, pred, t1_rows, t2_rows, t3_rows), encoding="utf-8")
    status = {
        "complete": True,
        "F1": pred["F1"],
        "F2": pred["F2"],
        "F3": pred["F3"],
        "predictions": pred,
        "null_seed": data["null_seed"],
        "n_rotations": data["n_rotations"],
        "n_line_perms": data["n_line_perms"],
        "n_trans_swaps": data["n_trans_swaps"],
    }
    STATUS.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
