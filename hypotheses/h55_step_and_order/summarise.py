"""Write the h55 summary, status, figure, and README from measurements.json."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
HANDS = ("1A", "2B", "3B")


def main() -> None:
    payload = json.loads((HERE / "results" / "measurements.json").read_text(encoding="utf-8"))
    summary = {
        "slots": payload["slots"],
        "S1_valid": payload["S1_valid"],
        "S1_hands": payload["S1_hands"],
        "S1_copier_hits": payload["S1_copier_hits"],
        "S1_plant_hits": payload["S1_plant_hits"],
        "bits": payload["bits"],
        "S2_valid": payload["S2_valid"],
        "S2_hands": payload["S2_hands"],
        "S2_copier_hits": payload["S2_copier_hits"],
        "S2_plant_hits": payload["S2_plant_hits"],
        "paragraphs": payload["paragraphs"],
        "opening": payload["sides"]["opening"]["label"],
        "opening_hands": payload["sides"]["opening"]["hands"],
        "closing": payload["sides"]["closing"]["label"],
        "closing_hands": payload["sides"]["closing"]["hands"],
        "X": payload["X"]["label"],
    }
    (HERE / "results" / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (HERE / "results" / "STATUS.json").write_text(
        json.dumps({"hypothesis": "h55_step_and_order", **summary}, indent=2),
        encoding="utf-8",
    )
    _figure(payload)
    _readme(payload, summary)


def _cell(cell: dict) -> str:
    return f"{cell['excess']:+.4f} (z {cell['z']:+.2f}, n {cell['n_pairs']})"


def _step(cell: dict) -> str:
    flag = "above p95" if cell.get("null_p95") is not None and cell["observed"] > cell["null_p95"] else "inside null"
    return f"{cell['excess']:+.4f} (z {cell['z']:+.2f}, {flag}, n {cell['n_left']}/{cell['n_right']})"


def _figure(payload: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.2))
    xs = list(range(len(HANDS)))
    for ax, block, title, ylab in (
        (axes[0], payload["S1"], "S1 whole-word shuffle", "excess conditional MI (bits)"),
        (axes[1], payload["steps"]["opening"], "Opening step vs a random step", "excess JS (bits)"),
    ):
        if title.startswith("S1"):
            ms = [block[f"MS_{h}"]["excess"] for h in HANDS]
            copier = [block[f"page_line_copier_{h}"]["excess"] for h in HANDS]
        else:
            ms = [block[f"MS_{h}"]["excess"] for h in HANDS]
            copier = [block[f"page_line_copier_{h}"]["excess"] for h in HANDS]
        ax.bar([i - 0.18 for i in xs], ms, width=0.36, color="#3d5a40", label="MS 408")
        ax.bar([i + 0.18 for i in xs], copier, width=0.36, color="#c4a35a", label="page_line_copier")
        ax.axhline(0.01, color="#888888", lw=0.8, ls="--")
        ax.set_xticks(xs, list(HANDS))
        ax.set_title(title)
        ax.set_ylabel(ylab)
    axes[0].legend(frameon=False)
    fig.suptitle("Word order inside the line, and the first step of a paragraph")
    fig.tight_layout()
    fig_dir = HERE / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_dir / "step_and_order.png", dpi=140)
    plt.close(fig)


def _readme(payload: dict, summary: dict) -> None:
    lines = [
        "# h55 — word order and neighbouring paragraph steps",
        "",
        "Pre-registered tests. The order null shuffles whole words inside a line. Paragraph steps are compared with other pairs of neighbouring lines, using only words two places in from either edge. A result is interpreted only when the copier stays quiet and a planted copier is detected. Nothing here is a translation.",
        "",
        f"**Slots: `{summary['slots']}`** (valid `{summary['S1_valid']}`, hands {summary['S1_hands']}, copier hits {summary['S1_copier_hits']}, plant hits {summary['S1_plant_hits']}).",
        f"**Bits: `{summary['bits']}`** (valid `{summary['S2_valid']}`, hands {summary['S2_hands']}, copier hits {summary['S2_copier_hits']}, plant hits {summary['S2_plant_hits']}).",
        f"**Paragraphs: `{summary['paragraphs']}`.** Opening `{summary['opening']}` hands {summary['opening_hands']}. Closing `{summary['closing']}` hands {summary['closing_hands']}. Shared onsets `{summary['X']}`.",
        "",
        "## S. Order",
        "",
        "| stream | S1 word shuffle | S2 folio-held-out gain |",
        "|---|---|---|",
    ]
    order = [f"MS_{h}" for h in HANDS] + [f"page_line_copier_{h}" for h in HANDS]
    for name in order:
        lines.append(f"| `{name}` | {_cell(payload['S1'][name])} | {_cell(payload['S2'][name])} |")
    lines += ["", "| plant | S1 | S2 |", "|---|---|---|"]
    for hand in HANDS:
        lines.append(f"| `plant_{hand}` | {_cell(payload['S1_plant'][hand])} | {_cell(payload['S2_plant'][hand])} |")
    lines += [
        "",
        "## P. One-line steps",
        "",
        "| stream | opening | closing |",
        "|---|---|---|",
    ]
    for name in order:
        lines.append(
            f"| `{name}` | {_step(payload['steps']['opening'][name])} | {_step(payload['steps']['closing'][name])} |"
        )
    lines += ["", "| plant | opening | closing |", "|---|---|---|"]
    for hand in HANDS:
        lines.append(
            f"| `plant_{hand}` | {_step(payload['step_plants']['opening'][hand])} | {_step(payload['step_plants']['closing'][hand])} |"
        )
    x = payload["X"]
    lines += ["", "## Shared onset shift", ""]
    if x["label"] == "not_run":
        lines.append("X was not run.")
    else:
        bits = []
        for name, cell in x["pairs"].items():
            bits.append(f"{name} r {cell['rho']:+.3f} (n {cell['n_units']}, pass `{cell['pass']}`)")
        lines.append(f"Side `{x['side']}`. `{x['label']}`. " + "; ".join(bits) + ".")
    lines += ["", "Figure: `figures/step_and_order.png`.", ""]
    (HERE / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
