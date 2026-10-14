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
sys.path.insert(0, str(HERE))

import h43_lib as H  # noqa: E402

RES = HERE / "results" / "measurements.json"
FIG = HERE / "figures" / "page_edge.png"
STATUS = HERE / "results" / "STATUS.json"
SUMMARY = HERE / "results" / "summary.json"
README = HERE / "README.md"

SERIES = (
    ("hands", "1A", "1A"),
    ("hands", "2B", "2B"),
    ("hands", "3B", "3B"),
    ("controls", "it_boccaccio", "Boccaccio"),
    ("controls", "it_cucina", "Cucina"),
    ("controls", "la_pliny_herbal", "Pliny"),
)


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
    pred = H.predictions(data["hands"], data["controls"])
    if pred != data["predictions"]:
        raise SystemExit(f"stored predictions {data['predictions']} != recomputed {pred}")
    for group in ("hands", "controls"):
        for name, rec in data[group].items():
            for distance, row in rec["distances"].items():
                again = H.is_pass(row["n_same"], row["n_cross"], row["effect"], row["null_p95"])
                if again != row["pass"]:
                    raise SystemExit(f"{name} d={distance} pass flag does not match the rule")
                if row["effect"] is None:
                    continue
                effects = np.asarray(row["null_effects"], dtype=np.float64)
                if len(effects) != H.N_NULL:
                    raise SystemExit(f"{name} d={distance} has {len(effects)} nulls")
                p95 = float(np.percentile(effects, 95, method="linear"))
                mean = float(effects.mean())
                if abs(p95 - row["null_p95"]) > 1e-9 or abs(mean - row["null_mean"]) > 1e-9:
                    raise SystemExit(f"{name} d={distance} null summary does not match the stored draws")
                scored = row["n_same"] >= H.MIN_PAIRS and row["n_cross"] >= H.MIN_PAIRS
                if scored != row["scored"]:
                    raise SystemExit(f"{name} d={distance} scored flag does not match pair counts")
    return pred


def _rows(data: dict) -> list[dict]:
    rows = []
    for group, key, label in SERIES:
        rec = data[group][key]
        for distance in ("80", "160"):
            row = rec["distances"][distance]
            rows.append(
                {
                    "series": label,
                    "distance": int(distance),
                    "n_same": row["n_same"],
                    "n_cross": row["n_cross"],
                    "effect": row["effect"],
                    "null_p95": row["null_p95"],
                    "scored": row["scored"],
                    "pass": row["pass"],
                }
            )
    return rows


def _figure(data: dict, pred: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.8), sharey=False)
    labels = [label for _g, _k, label in SERIES]
    x = np.arange(len(labels))
    for ax, distance in zip(axes, ("80", "160")):
        effects = []
        p95 = []
        colors = []
        for group, key, _label in SERIES:
            row = data[group][key]["distances"][distance]
            effects.append(np.nan if row["effect"] is None else row["effect"])
            p95.append(np.nan if row["null_p95"] is None else row["null_p95"])
            if not row["scored"]:
                colors.append("#b0b0b0")
            elif row["pass"]:
                colors.append("#4C78A8")
            else:
                colors.append("#E45756")
        ax.bar(x, effects, color=colors, width=0.72, zorder=2, edgecolor="none")
        ax.scatter(x, p95, marker="_", s=280, c="black", zorder=3)
        ax.axhline(0.0, color="0.35", lw=0.8, zorder=1)
        ax.set_xticks(x, labels, rotation=25, ha="right")
        ax.set_title(f"start distance {distance}")
        ax.set_ylabel("mean same cosine − mean cross cosine")
    e2 = "not scored" if pred["E2"] is None else ("pass" if pred["E2"] else "fail")
    e1 = "pass" if pred["E1"] else "fail"
    fig.suptitle(f"Page-edge vocabulary effect    E1 {e1}    E2 {e2}")
    handles = [
        Patch(facecolor="#4C78A8", edgecolor="none", label="pass"),
        Patch(facecolor="#E45756", edgecolor="none", label="scored, below the null"),
        Patch(facecolor="#b0b0b0", edgecolor="none", label="not scored"),
        Line2D([0], [0], color="black", marker="_", linestyle="None", markersize=14, label="null 95th percentile"),
    ]
    fig.legend(handles=handles, ncol=4, frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout()
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _readme(data: dict, pred: dict, rows: list[dict]) -> str:
    e1 = "pass" if pred["E1"] else "fail"
    if pred["E2"] is None:
        e2_line = (
            f"E2 is not scored. Available controls: {pred['n_controls_available']}. "
            "The manuscript result is uncalibrated."
        )
    else:
        e2 = "pass" if pred["E2"] else "fail"
        passed = ", ".join(pred["E2_pass_controls"]) if pred["E2_pass_controls"] else "none"
        e2_line = (
            f"**{e2}**. Passing controls: {passed}. "
            f"Available controls: {pred['n_controls_available']}."
        )
    hand_bits = []
    for hand in H.HANDS:
        row = data["hands"][hand]["distances"]["80"]
        hand_bits.append(
            f"{hand}: effect {_fmt(row['effect'])}, null 95th {_fmt(row['null_p95'])}, "
            f"same {row['n_same']}, cross {row['n_cross']}, scored {row['scored']}, pass {row['pass']}"
        )
    lines = [
        "# h43: vocabulary at the page edge",
        "",
        "Pre-registration: [PREREG.md](PREREG.md). Paragraph words in reading order. "
        "A window is 80 tokens lying on one folio. Pairs have start-distance 80 or 160. "
        "Same means both windows are on one folio. Cross means a folio boundary falls between them. "
        "Similarity is the cosine of the two word-count vectors. "
        "The effect is the mean same cosine minus the mean cross cosine. "
        "A distance is scored only when both sides have at least 30 pairs. "
        "Inside each quire the token stream is rotated circularly against that quire's folio lengths, "
        "100 times, one numpy Generator seeded with 43, consumed in the order 1A, 2B, 3B, "
        "Boccaccio, cucina, Pliny. Each quire draws an independent shift on 0..n-1. "
        "Folio sizes stay fixed and local order stays fixed. A scored distance passes when the "
        "observed effect is above the null 95th percentile (`numpy.percentile`, linear).",
        "",
        "Manuscript words are the h14 paragraph table for hands 1A, 2B and 3B, transcription "
        f"{data['transcription']}, comma treated as a word space. Folios and quires are the real ones.",
        "",
        "Control boundaries are read from the raw files before tokenisation. "
        "Each stretch is tokenised on its own with the same normaliser as the existing loader, "
        "so a token cannot cross a boundary. "
        "Boccaccio: a boundary at each Novella heading (Introduzione is not a boundary). "
        "Cucina: a Zambrini recipe heading, a line that is entirely `=...=` or `_..._`, "
        "inside the loader's span from INCOMINCIASI to the line before TAVOLA. "
        "Pliny: a TEI `div` with `subtype=\"chapter\"` in books 20-27. "
        "Blank lines are not boundaries. "
        "Each control is one fake quire, one rotation group, because the source has no quires. "
        "A control is available only with at least 20 boundaries.",
        "",
        "## Predictions",
        "",
        f"- E1. At distance 80, at least two of the three hands pass: **{e1}**.",
        *[f"  - {bit}." for bit in hand_bits],
        f"- E2. At distance 80, at least two available controls pass. {e2_line}",
        "",
        "## Pair effects",
        "",
        *_table(rows),
        "",
        "## Sizes",
        "",
    ]
    size_rows = []
    for group, key, label in SERIES:
        rec = data[group][key]
        size_rows.append(
            {
                "series": label,
                "tokens": rec["n_tokens"],
                "folios": rec["n_folios"],
                "quires": rec["n_quires"],
                "boundaries": rec.get("n_boundaries", ""),
                "available": rec.get("available", ""),
            }
        )
    lines.extend(_table(size_rows))
    lines.extend(
        [
            "",
            "## Run",
            "",
            "```",
            "export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1",
            "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1",
            "python -m pytest hypotheses/h43_page_edge/test_h43.py -p no:cacheprovider",
            "python hypotheses/h43_page_edge/run_h43.py",
            "python hypotheses/h43_page_edge/summarise.py",
            "```",
            "",
            f"numpy {data['numpy']}, python {data['python']}, runtime {data['runtime_sec']:.1f}s.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    data = json.loads(RES.read_text(encoding="utf-8"))
    pred = _check(data)
    rows = _rows(data)
    _figure(data, pred)
    summary = {"predictions": pred, "rows": rows, "numpy": data["numpy"], "python": data["python"]}
    SUMMARY.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    README.write_text(_readme(data, pred, rows), encoding="utf-8")
    status = {
        "complete": True,
        "E1": pred["E1"],
        "E2": pred["E2"],
        "E2_scored": pred["E2_scored"],
        "uncalibrated": pred["uncalibrated"],
        "hands_pass_distance_80": pred["E1_pass_hands"],
        "controls_available": pred["available_controls"],
        "controls_pass_distance_80": pred["E2_pass_controls"],
        "window": data["window"],
        "min_pairs": data["min_pairs"],
        "n_null": data["n_null"],
        "null_seed": data["null_seed"],
    }
    STATUS.write_text(json.dumps(status, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=1), flush=True)


if __name__ == "__main__":
    main()
