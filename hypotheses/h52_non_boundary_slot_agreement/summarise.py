"""Write the h52 summary, status, figure, and README from measurements.json."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
HANDS = ("1A", "2B", "3B")


def _cell(streams: dict, name: str, lag: str, feature: str) -> dict:
    return streams[name][lag][feature]


def main() -> None:
    payload = json.loads((HERE / "results" / "measurements.json").read_text(encoding="utf-8"))
    streams = payload["streams"]
    pred = payload["predictions"]
    synthetic = payload["synthetic_bind_2B"]
    summary = {
        "verdict": pred["verdict"],
        "G1": pred["G1"],
        "G1_feature": pred["G1_feature"],
        "G1_hands": pred["G1_hands"],
        "G2": pred["G2"],
        "valid": pred["valid"],
        "synthetic_excess": synthetic["excess"],
        "synthetic_z": synthetic["z"],
        "lag1": {},
    }
    for feature in ("F1", "F2", "F3"):
        summary["lag1"][feature] = {}
        for name in list(streams):
            cell = _cell(streams, name, "lag1", feature)
            summary["lag1"][feature][name] = {
                "excess": cell["excess"],
                "z": cell["z"],
                "cmi": cell["cmi"],
                "n_pairs": cell["n_pairs"],
                "null_mean": cell["null_mean"],
            }
    (HERE / "results" / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (HERE / "results" / "STATUS.json").write_text(
        json.dumps(
            {
                "hypothesis": "h52_non_boundary_slot_agreement",
                "verdict": pred["verdict"],
                "G1": pred["G1"],
                "G2": pred["G2"],
                "valid": pred["valid"],
                "G1_hands": pred["G1_hands"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _figure(streams)
    _readme(streams, pred, synthetic)


def _figure(streams: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.2), sharey=True)
    for ax, feature, title in zip(axes, ("F1", "F2"), ("F1 prefix to next suffix", "F2 interior to interior")):
        xs = range(len(HANDS))
        ms = [_cell(streams, f"MS_{h}", "lag1", feature)["excess"] for h in HANDS]
        plc = [_cell(streams, f"page_line_copier_{h}", "lag1", feature)["excess"] for h in HANDS]
        ax.bar([i - 0.18 for i in xs], ms, width=0.36, label="MS 408", color="#3d5a40")
        ax.bar([i + 0.18 for i in xs], plc, width=0.36, label="page_line_copier", color="#c4a35a")
        ax.axhline(0.01, color="#888888", lw=0.8, ls="--")
        ax.set_xticks(list(xs), list(HANDS))
        ax.set_title(title)
        ax.set_ylabel("excess conditional MI (bits)" if feature == "F1" else "")
    axes[0].legend(frameon=False)
    fig.suptitle("Residual slot agreement after the boundary junction")
    fig.tight_layout()
    fig_dir = HERE / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_dir / "slot_agreement.png", dpi=140)
    plt.close(fig)


def _fmt(cell: dict) -> str:
    return f"{cell['excess']:+.4f} (z {cell['z']:+.2f}, n {cell['n_pairs']})"


def _readme(streams: dict, pred: dict, synthetic: dict) -> None:
    lines = [
        "# h52 — non-touching slot agreement",
        "",
        "Pre-registered test of whether the opening of a word still predicts the ending of the next word, or the interior of a word predicts the next interior, after the touching pair `(end of word t, onset of word t+1)` is held fixed. The null shuffles the right-hand slot inside each touching pair. Nothing here is a translation.",
        "",
        f"**Verdict: `{pred['verdict']}`.** Validity check `synthetic_bind_2B` excess {synthetic['excess']:+.3f}, z {synthetic['z']:+.1f} (requires excess ≥ 0.05 and z ≥ 5): `{pred['valid']}`.",
        f"G1 (one of F1, F2 passes on ≥ 2 hands): `{pred['G1']}` {pred['G1_hands']}. G2 (the copier accounts for every lag-1 F1 and F2 cell): `{pred['G2']}`.",
        "",
        "## Lag 1 excess over the stratum shuffle",
        "",
        "| stream | F1 onset(t) → end(t+1) | F2 core(t) → core(t+1) | F3 end(t) → end(t+1) |",
        "|---|---|---|---|",
    ]
    order = [f"MS_{h}" for h in HANDS] + [f"page_line_copier_{h}" for h in HANDS] + ["it_cucina", "it_sidrach"]
    for name in order:
        lines.append(
            "| "
            + " | ".join(
                [f"`{name}`"] + [_fmt(_cell(streams, name, "lag1", feature)) for feature in ("F1", "F2", "F3")]
            )
            + " |"
        )
    lines += [
        "",
        "## Lag 2, reported only",
        "",
        "| stream | F1 | F2 |",
        "|---|---|---|",
    ]
    for name in order:
        lines.append(
            "| "
            + " | ".join([f"`{name}`"] + [_fmt(_cell(streams, name, "lag2", feature)) for feature in ("F1", "F2")])
            + " |"
        )
    lines += [
        "",
        "F3 conditions only on the next word's onset, so it is a suffix-to-suffix reference and is not part of G1 or G2. Prose rows are references and do not change the verdict.",
        "",
        "Figure: `figures/slot_agreement.png`.",
        "",
    ]
    (HERE / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
