"""Write the h53 summary, status, figure, and README from measurements.json."""
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
    streams = payload["streams"]
    pred = payload["predictions"]
    summary = {"predictions": pred, "word": {}, "onset": {}, "end": {}}
    for name, block in streams.items():
        for key in ("word", "onset", "end"):
            summary[key][name] = {
                "S": block[key]["S"],
                "excess": block[key]["excess"],
                "z": block[key]["z"],
                "null_p95": block[key]["null_p95"],
                "null_mean": block[key]["null_mean"],
                "scored": block["scored"],
                "n_open": block["n_open"],
                "n_close": block["n_close"],
            }
    (HERE / "results" / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (HERE / "results" / "STATUS.json").write_text(
        json.dumps(
            {
                "hypothesis": "h53_paragraph_arc_structure",
                "verdict": pred["reading"],
                "A1": pred["A1"],
                "A1_hands": pred["A1_hands"],
                "C1": pred["C1"],
                "scored_hands": pred["scored_hands"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _figure(streams)
    _readme(streams, pred)


def _figure(streams: dict) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    xs = range(len(HANDS))
    ms = [streams[f"MS_{h}"]["word"]["excess"] for h in HANDS]
    plc = [streams[f"page_line_copier_{h}"]["word"]["excess"] for h in HANDS]
    ax.bar([i - 0.18 for i in xs], ms, width=0.36, label="MS 408", color="#3d5a40")
    ax.bar([i + 0.18 for i in xs], plc, width=0.36, label="page_line_copier", color="#c4a35a")
    ax.axhline(0.01, color="#888888", lw=0.8, ls="--")
    cucina = streams["it_cucina"]["word"]["excess"]
    ax.scatter([len(HANDS)], [cucina], color="#1f4e79", zorder=3, label="cucina")
    ax.set_xticks(list(xs) + [len(HANDS)], list(HANDS) + ["cucina"])
    ax.set_ylabel("excess JS, opening vs closing interiors (bits)")
    ax.set_title("Paragraph role after line-edge words are removed")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig_dir = HERE / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_dir / "paragraph_arc.png", dpi=140)
    plt.close(fig)


def _fmt(block: dict, key: str) -> str:
    cell = block[key]
    flag = "above p95" if cell["S"] > cell["null_p95"] else "inside null"
    return f"{cell['excess']:+.4f} (z {cell['z']:+.2f}, {flag})"


def _readme(streams: dict, pred: dict) -> None:
    lines = [
        "# h53 — paragraph interior arc",
        "",
        "Pre-registered contrast of the words left in the middle of a paragraph's first line and the middle of its last line, after the first and last word of every line are removed. The null shuffles line order inside the paragraph. Nothing here is a translation.",
        "",
        f"**Reading: `{pred['reading']}`.** A1 (at least two hands beat their null and the copier): `{pred['A1']}` hands `{pred['A1_hands']}`. C1 (cucina shows the same contrast): `{pred['C1']}`.",
        "",
        "A failed A1 together with a passed C1 means the contrast can see a recipe's paragraph roles and the hands do not show that pattern beyond the copier. A failed C1 would have made a failed A1 inconclusive.",
        "",
        "## Word-class JS, opening interior vs closing interior",
        "",
        "| stream | open / close tokens | word excess | onset excess | end excess |",
        "|---|---|---|---|---|",
    ]
    order = [f"MS_{h}" for h in HANDS] + [f"page_line_copier_{h}" for h in HANDS] + ["it_cucina"]
    for name in order:
        block = streams[name]
        lines.append(
            f"| `{name}` | {block['n_open']} / {block['n_close']} | {_fmt(block, 'word')} | {_fmt(block, 'onset')} | {_fmt(block, 'end')} |"
        )
    lines += [
        "",
        "Only the word-class column enters A1 and C1. Onset and end are reported on the same line shuffles.",
        "",
        "Figure: `figures/paragraph_arc.png`.",
        "",
    ]
    (HERE / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
