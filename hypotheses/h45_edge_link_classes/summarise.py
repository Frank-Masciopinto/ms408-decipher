"""Write h45 predictions, README, status, and figure from results/streams.json."""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import h45_lib as H

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
FIG = HERE / "figures" / "edge_classes.png"
LABELS = {
    "MS_1A": "MS 1A",
    "MS_2B": "MS 2B",
    "MS_3B": "MS 3B",
    "boccaccio": "Boccaccio",
    "cucina": "Cucina",
    "pliny": "Pliny XX-XXVII",
    "macer": "Macer",
    "self_citation": "self-citation",
    "gap_rule": "gap rule",
}


def _fmt(value) -> str:
    if value is None:
        return "null"
    return repr(float(value))


def _verdict(flag, scored: bool) -> str:
    if not scored:
        return "not scored"
    return "pass" if flag else "fail"


def _check(streams: dict) -> None:
    missing = [name for name in H.STREAM_ORDER if name not in streams]
    if missing:
        raise SystemExit(f"missing streams: {missing}")
    for name in H.STREAM_ORDER:
        rec = streams[name]
        mi_glyph = float(rec["MI_glyph"])
        mi_class = float(rec["MI_class"])
        share = rec["share"]
        if mi_glyph == 0.0:
            if share is not None or not rec["excluded"]:
                raise SystemExit(f"{name} has MI_glyph 0 but was not excluded")
            continue
        if share is None:
            raise SystemExit(f"{name} has no share")
        if abs(float(share) - (mi_class / mi_glyph)) > 1e-12:
            raise SystemExit(f"{name} stored share does not equal MI_class / MI_glyph")
        if not isinstance(rec["vowels"], list):
            raise SystemExit(f"{name} vowels are not a list")


def _figure(streams: dict, pred: dict) -> None:
    names = list(H.STREAM_ORDER)
    labels = [LABELS[name] for name in names]
    shares = [float(streams[name]["share"]) for name in names]
    mi_glyph = [float(streams[name]["MI_glyph"]) for name in names]
    mi_class = [float(streams[name]["MI_class"]) for name in names]
    colors = []
    for name in names:
        if name in H.MS_KEYS:
            colors.append("#9c3b3b")
        elif name in H.CONTROL_KEYS:
            colors.append("#2f6f4e")
        else:
            colors.append("#c47b00")
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.4))
    xs = np.arange(len(names))
    axes[0].bar(xs, shares, color=colors)
    axes[0].axhline(H.C1_MIN, color="0.25", ls="--", lw=0.9, label=f"C1 minimum {_fmt(H.C1_MIN)}")
    if pred["lowest_control_share"] is not None:
        axes[0].axhline(
            pred["lowest_control_share"], color="#1d4e89", ls=":", lw=1.0,
            label=f"lowest control {_fmt(pred['lowest_control_share'])}",
        )
    axes[0].set_xticks(xs, labels, rotation=35, ha="right")
    axes[0].set_ylabel("share = MI_class / MI_glyph")
    axes[0].set_title("Class share of the edge link")
    axes[0].legend(frameon=False, fontsize=8)
    width = 0.38
    axes[1].bar(xs - width / 2, mi_glyph, width, color="#4c5b73", label="MI_glyph")
    axes[1].bar(xs + width / 2, mi_class, width, color="#d08c60", label="MI_class")
    axes[1].set_xticks(xs, labels, rotation=35, ha="right")
    axes[1].set_ylabel("mutual information (bits)")
    axes[1].set_title("Glyph pair and class pair")
    axes[1].legend(frameon=False, fontsize=8)
    bits = "  ".join(
        f"{key} {_verdict(pred[key], pred[key + '_scored'])}" for key in ("C1", "C2", "C3")
    )
    fig.suptitle(bits)
    fig.tight_layout()
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=150)
    plt.close(fig)


def _table(rows: list[dict]) -> list[str]:
    header = list(rows[0])
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
    ]
    for row in rows:
        cells = []
        for key in header:
            value = row[key]
            if isinstance(value, float):
                cells.append(_fmt(value))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def _readme(payload: dict, pred: dict) -> str:
    streams = payload["streams"]
    rows = []
    for name in H.STREAM_ORDER:
        rec = streams[name]
        rows.append({
            "stream": LABELS[name],
            "n": rec["n_tokens"],
            "lines": rec["n_lines"],
            "pairs": rec["n_pairs"],
            "MI_glyph": rec["MI_glyph"],
            "MI_class": rec["MI_class"],
            "share": rec["share"],
        })
    vowel_lines = []
    for name in H.STREAM_ORDER:
        vowels = " ".join(streams[name]["vowels"])
        vowel_lines.append(f"- {LABELS[name]}: {vowels}")
    lines = [
        "# h45: is the last-glyph link a vowel/consonant pattern?",
        "",
        "Pre-registered in `PREREG.md` before this measurement. The numbers are stream statistics. This note makes no translation claim.",
        "",
        "## Measure",
        "",
        "A pair is the last unit of a word and the first unit of the next word, and only when both words sit on the same line.",
        "Sukhotin is fit on within-word adjacent units of that same stream. Units it calls vowels are V. Every other unit it scored is C. A pair that uses an unscored unit is dropped.",
        "MI_glyph is the plug-in mutual information of the glyph pair, in bits. MI_class is the same quantity for the class pair. share = MI_class / MI_glyph. A stream with MI_glyph = 0 is excluded.",
        "Manuscript, self-citation, and gap-rule streams use collapsed EVA units (`h13_lib.SEG`). Natural-language streams use characters.",
        "",
        "## Streams",
        "",
        "Manuscript hands are the whole ZL3b paragraph hand from the h14 table (comma is a word space), in the h30 line order. Controls are the first 10,500 tokens of Boccaccio, Libro della cucina, Pliny herbal books XX-XXVII, and Macer Floridus, cut on the source lines of those tokens.",
        "Self-citation is the first 10,500 tokens of `fitted_s1`, on its own whitespace lines. The gap rule fits `h34_lib.fit_table` on collapsed units of the hand 2B lines and applies `h34_lib.apply_rule` at strength 1 to every token of `fitted_s1`, with numpy seed 45.",
        "",
    ]
    lines.extend(_table(rows))
    lines.extend([
        "",
        "## Sukhotin vowels",
        "",
        "Pick order from `msdecipher.stats.sukhotin`.",
        "",
    ])
    lines.extend(vowel_lines)
    lines.extend([
        "",
        "## Predictions",
        "",
        f"- C1. Median share of the four controls is at least 0.25: **{_verdict(pred['C1'], pred['C1_scored'])}**. Median `{_fmt(pred['median_control_share'])}`.",
        f"- C2. Scored only if C1 passes. Every manuscript hand is below the lowest control: **{_verdict(pred['C2'], pred['C2_scored'])}**. Lowest control `{_fmt(pred['lowest_control_share'])}`.",
        f"- C3. Scored only if C1 passes. Self-citation and the gap-rule stream are both below the lowest control: **{_verdict(pred['C3'], pred['C3_scored'])}**.",
        "",
        "The figure is `figures/edge_classes.png`. Per-stream records are in `results/streams.json`. The verdict is in `results/STATUS.json`.",
        "",
        "## Reproduce",
        "",
        "```",
        "export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1",
        "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1",
        "python -m pytest -p no:cacheprovider hypotheses/h45_edge_link_classes/test_h45.py",
        "python hypotheses/h45_edge_link_classes/run_h45.py",
        "python hypotheses/h45_edge_link_classes/summarise.py",
        "```",
        "",
        f"numpy {payload.get('numpy')}, python {payload.get('python')}.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    payload = json.loads((RES / "streams.json").read_text(encoding="utf-8"))
    streams = payload["streams"]
    _check(streams)
    pred = H.predictions(streams)
    stored = payload.get("predictions")
    if stored is not None and stored != pred:
        raise SystemExit("recomputed predictions do not match streams.json")
    summary = {
        "predictions": pred,
        "streams": {
            name: {
                "n_tokens": streams[name]["n_tokens"],
                "n_lines": streams[name]["n_lines"],
                "n_pairs": streams[name]["n_pairs"],
                "MI_glyph": streams[name]["MI_glyph"],
                "MI_class": streams[name]["MI_class"],
                "share": streams[name]["share"],
                "vowels": streams[name]["vowels"],
            }
            for name in H.STREAM_ORDER
        },
    }
    status = {
        "complete": True,
        "C1": pred["C1"],
        "C2": pred["C2"],
        "C3": pred["C3"],
        "C1_scored": pred["C1_scored"],
        "C2_scored": pred["C2_scored"],
        "C3_scored": pred["C3_scored"],
        "median_control_share": pred["median_control_share"],
        "lowest_control_share": pred["lowest_control_share"],
        "streams": summary["streams"],
    }
    text = _readme(payload, pred)
    RES.mkdir(parents=True, exist_ok=True)
    (RES / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (RES / "summary.md").write_text(text, encoding="utf-8")
    (RES / "STATUS.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    _figure(streams, pred)
    (HERE / "README.md").write_text(text, encoding="utf-8")
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
