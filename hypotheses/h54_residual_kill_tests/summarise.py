"""Write the h54 summary, status, figure, and README from measurements.json."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
HANDS = ("1A", "2B", "3B")


def _num(cell: dict, key: str) -> str:
    value = cell.get(key)
    if value is None:
        return "—"
    return f"{value:+.4f}" if isinstance(value, float) else str(value)


def main() -> None:
    payload = json.loads((HERE / "results" / "measurements.json").read_text(encoding="utf-8"))
    summary = {
        "overall": payload["overall"],
        "slots": payload["slots"],
        "paragraphs": payload["paragraphs"],
        "A1_hands": payload["A1_hands"],
        "A2_hands": payload["A2_hands"],
        "B1_hands": payload["B1_hands"],
        "B2_hands": payload["B2_hands"],
        "B3_hands": payload["B3_hands"],
        "C": payload["conditional"]["C"]["label"],
        "D": payload["conditional"]["D"]["label"],
    }
    (HERE / "results" / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (HERE / "results" / "STATUS.json").write_text(
        json.dumps({"hypothesis": "h54_residual_kill_tests", **summary}, indent=2),
        encoding="utf-8",
    )
    _figure(payload)
    _readme(payload)


def _figure(payload: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.2))
    xs = list(range(len(HANDS)))
    for ax, key, title in (
        (axes[0], "A2", "A2 within-line core shuffle"),
        (axes[1], "B3", "B3 open/close minus matched middles"),
    ):
        block = payload[key]
        if key == "A2":
            ms = [block[f"MS_{h}"]["excess"] for h in HANDS]
            copier = [block[f"page_line_copier_{h}"]["excess"] for h in HANDS]
            ylab = "excess conditional MI (bits)"
        else:
            ms = [block[f"MS_{h}"]["excess"] for h in HANDS]
            copier = [block[f"page_line_copier_{h}"]["excess"] for h in HANDS]
            ylab = "excess D (bits)"
        ax.bar([i - 0.18 for i in xs], ms, width=0.36, color="#3d5a40", label="MS 408")
        ax.bar([i + 0.18 for i in xs], copier, width=0.36, color="#c4a35a", label="page_line_copier")
        ax.axhline(0.01, color="#888888", lw=0.8, ls="--")
        ax.set_xticks(xs, list(HANDS))
        ax.set_title(title)
        ax.set_ylabel(ylab)
    axes[0].legend(frameon=False)
    fig.suptitle("Kill tests for the slot and paragraph residuals")
    fig.tight_layout()
    fig_dir = HERE / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_dir / "residual_kill_tests.png", dpi=140)
    plt.close(fig)


def _pair(cell: dict) -> str:
    z = cell.get("z")
    zed = f", z {z:+.2f}" if isinstance(z, float) else ""
    n = cell.get("n_pairs", cell.get("n_open"))
    return f"{cell['excess']:+.4f}{zed} (n {n})"


def _readme(payload: dict) -> None:
    cond = payload["conditional"]
    lines = [
        "# h54 — kill tests for the slot and paragraph residuals",
        "",
        "Pre-registered checks of whether the h52 interior coupling is adjacency rather than near-copy or a line palette, and whether the h53 paragraph contrast is a closing role rather than the folio's first line, a short last line, or drift. Nothing here is a translation.",
        "",
        f"**Overall: `{payload['overall']}`.** Slots `{payload['slots']}` (A1 hands {payload['A1_hands']}, A2 hands {payload['A2_hands']}). Paragraphs `{payload['paragraphs']}` (B3 hands {payload['B3_hands']}).",
        f"B1 hands {payload['B1_hands']}. B2 hands {payload['B2_hands']}. Conditional C `{cond['C']['label']}`. Conditional D `{cond['D']['label']}`.",
        "",
        "## A. Second-unit coupling",
        "",
        "| stream | A1 near-copies removed | A2 within-line shuffle |",
        "|---|---|---|",
    ]
    order = [f"MS_{h}" for h in HANDS] + [f"page_line_copier_{h}" for h in HANDS]
    for name in order:
        lines.append(f"| `{name}` | {_pair(payload['A1'][name])} | {_pair(payload['A2'][name])} |")
    lines += [
        "",
        "## B. Paragraph opening against closing",
        "",
        "| stream | B1 no folio-first | B2 both lines ≥ 6 words | B3 D against matched middles |",
        "|---|---|---|---|",
    ]
    for name in order:
        lines.append(
            f"| `{name}` | {_pair(payload['B1'][name])} | {_pair(payload['B2'][name])} | {_pair(payload['B3'][name])} |"
        )
    lines += ["", "## Conditional follow-ups", ""]
    c_block = cond["C"]
    if c_block["label"] == "not_run":
        lines.append("C was not run. A2 did not pass on two hands.")
    else:
        lines.append(
            f"C `{c_block['label']}` (near-copies dropped: `{c_block['drop_near']}`). "
            f"Held-out gains: "
            + ", ".join(f"{h} {c_block['gains'][h]:+.4f}" for h in HANDS)
            + f". Cucina {c_block['cucina']:+.4f}."
        )
    d_block = cond["D"]
    if d_block["label"] == "not_run":
        lines.append("D was not run. B3 did not pass on two hands.")
    else:
        bits = []
        for name, cell in d_block["pairs"].items():
            bits.append(f"{name} r {cell['rho']:+.3f} (n {cell['n_types']}, pass `{cell['pass']}`)")
        lines.append(f"D `{d_block['label']}`. " + "; ".join(bits) + ".")
    lines += ["", "Figure: `figures/residual_kill_tests.png`.", ""]
    (HERE / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
