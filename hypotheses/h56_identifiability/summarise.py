"""Write the h56 status, figure, and README from measurements.json."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent


def main() -> None:
    payload = json.loads((HERE / "results" / "measurements.json").read_text(encoding="utf-8"))
    summary = {
        "U1": payload["stage1"]["U1"],
        "alt_fraction": payload["stage1"]["alt_fraction"],
        "R1": payload["stage2"]["R1"],
        "R2_pass": payload["stage2"]["R2_pass"],
        "R2": payload["stage2"]["R2"],
        "coverage": payload["stage3"]["coverage"],
        "M1": payload["stage3"]["M1"],
        "n_roots_tested": payload["stage3"]["n_roots_tested"],
        "n_passed_roots": payload["stage3"]["n_passed"],
        "L_pass": payload["stage4"]["pass"],
        "L1": payload["stage4"]["L1"],
        "L2": payload["stage4"]["L2"],
        "C1": payload["stage5"]["C1"],
        "short_option_fraction": payload["stage5"]["short_option_fraction"],
        "multispectral": payload["stage5"]["multispectral"],
        "S6": payload["stage6"]["S6"],
        "planted_accuracy": payload["stage6"]["planted_accuracy"],
        "null_accuracy": payload["stage6"]["null_accuracy"],
        "grounded": payload["grounded"],
        "stage7": payload["stage7"],
    }
    (HERE / "results" / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (HERE / "results" / "STATUS.json").write_text(
        json.dumps({"hypothesis": "h56_identifiability", "stage7": summary["stage7"], **{k: summary[k] for k in ("U1", "R1", "R2_pass", "M1", "L_pass", "C1", "S6")}}, indent=2),
        encoding="utf-8",
    )
    _figure(summary)
    _readme(payload, summary)


def _figure(summary: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.bar(["planted signal", "no signal"], [summary["planted_accuracy"], summary["null_accuracy"]], color=["#3d5a40", "#8d6a4a"])
    ax.axhline(0.50, color="#3d5a40", lw=0.8, ls="--")
    ax.axhline(0.25, color="#8d6a4a", lw=0.8, ls="--")
    ax.set_ylim(0, 1)
    ax.set_ylabel("folios whose most common word is a topic marker")
    ax.set_title("Can the root detector recover a planted topic?")
    fig.tight_layout()
    fig_dir = HERE / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_dir / "identifiability.png", dpi=140)
    plt.close(fig)


def _fmt(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:+.4f}"
    return str(value)


def _readme(payload: dict, summary: dict) -> None:
    lines = [
        "# h56 — identifiability after the copying routine",
        "",
        "Pre-registered programme. No reading is proposed unless a detector that can recover a planted topic also finds a manuscript association that survives held-out quires. Multispectral images were not available, so erasures could not be recovered.",
        "",
        f"**Stage 7: `{summary['stage7']}`.** Grounded associations: {summary['grounded'] or 'none'}.",
        "",
        "## Stages",
        "",
        f"- U1 reading lattice: `{summary['U1']}`. Alternative groups cover {summary['alt_fraction']:.3%} of paragraph tokens." if summary["alt_fraction"] is not None else f"- U1: `{summary['U1']}`.",
        f"- R1 labels vs folio routine: contrast {_fmt(summary['R1']['contrast'])}, p {summary['R1']['p']:.4f}, pass `{summary['R1']['pass']}`.",
        f"- R2 illustrated-page surprise: pass `{summary['R2_pass']}`.",
        f"- M1 folio roots vs drawings: pass `{summary['M1']}` ({summary['n_passed_roots']} of {summary['n_roots_tested']} roots tested; component coverage {summary['coverage']:.3f}).",
        f"- L labels vs drawings: pass `{summary['L_pass']}`.",
        f"- C1 glyph-scale alternatives: `{summary['C1']}` (short-option fraction {summary['short_option_fraction']:.3f}). Multispectral: `{summary['multispectral']}`.",
        f"- S6 synthetic recovery: `{summary['S6']}` (planted {summary['planted_accuracy']:.3f}, null {summary['null_accuracy']:.3f}).",
        "",
        "## Reading lattice",
        "",
        "| reading | hand | bigram gain | edit-1 rate | onset excess | pass |",
        "|---|---|---|---|---|---|",
    ]
    for reading, hands in payload["stage1"].items():
        if not isinstance(hands, dict) or reading in {"alt_fraction", "n_paragraph_tokens", "U1"}:
            continue
        for hand, cell in hands.items():
            lines.append(
                f"| `{reading}` | {hand} | {_fmt(cell['G'])} | {_fmt(cell['E'])} | {_fmt(cell['O'])} | `{cell['pass']}` |"
            )
    lines += ["", "## Drawing tests", "", "| test | tag | statistic | p | Holm p | pass |", "|---|---|---|---|---|---|"]
    for row in summary["R2"]:
        lines.append(f"| R2 surprise | {row['tag']} | {_fmt(row['diff'])} | {row['p']:.4f} | {row['p_holm']:.4f} | `{row['pass']}` |")
    for row in summary["L1"]:
        lines.append(f"| L1 count | {row['tag']} | {_fmt(row['rho'])} | {row['p']:.4f} | {row['p_holm']:.4f} | `{row['pass']}` |")
    for row in summary["L2"]:
        lines.append(f"| L2 onset | {row['tag']} | {_fmt(row['js'])} | {row['p']:.4f} | {row['p_holm']:.4f} | `{row['pass']}` |")
    if summary["n_passed_roots"]:
        lines += ["", "Root–tag pairs that passed Holm:", ""]
        for row in payload["stage3"]["passed"]:
            lines.append(f"- `{row['root']}` × {row['tag']}: difference {_fmt(row['diff'])}, Holm p {row['p_holm']:.4f}")
    lines += ["", "Figure: `figures/identifiability.png`.", ""]
    (HERE / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
