"""Write h42 predictions, summary, status, figure, and README from results/streams.json."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import h42_lib as H

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
FIG = HERE / "figures" / "near_repeat_decay.png"
ORDER = (
    "MS_1A",
    "MS_2B",
    "MS_3B",
    "boccaccio",
    "C0",
    "self_citation",
    "h39_native_tuned",
    "h39_C0_graph",
)
LABELS = {
    "MS_1A": "MS 1A",
    "MS_2B": "MS 2B",
    "MS_3B": "MS 3B",
    "boccaccio": "Boccaccio",
    "C0": "C0",
    "self_citation": "self-citation",
    "h39_native_tuned": "h39 native tuned",
    "h39_C0_graph": "h39 C0 graph",
}


def _num(value):
    if value is None:
        return float("nan")
    return float(value)


def _fmt(value):
    if value is None:
        return "null"
    return f"{float(value):.6f}"


def _cell(value):
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


def _checked(streams: dict) -> dict:
    checked = {}
    for name, rec in streams.items():
        flags = [bool(rec["bins"][bin_name]["elevated"]) for bin_name in H.BIN_NAMES]
        shape, decay = H.profile_shape(flags)
        if shape != rec["shape"] or decay != rec["decay_point"]:
            raise SystemExit(f"{name} stored shape {rec['shape']}/{rec['decay_point']} != recomputed {shape}/{decay}")
        checked[name] = rec
    return checked


def _figure(streams: dict, pred: dict) -> None:
    colors = plt.cm.tab10(np.linspace(0, 0.9, len(ORDER)))
    fig, ax = plt.subplots(figsize=(10.2, 5.8))
    xs = np.arange(len(H.BIN_NAMES))
    for color, name in zip(colors, ORDER):
        rec = streams[name]
        ys = np.array([_num(rec["bins"][bin_name]["excess"]) for bin_name in H.BIN_NAMES], dtype=float)
        yerr = np.array([2.0 * float(rec["bins"][bin_name]["null_sd"]) for bin_name in H.BIN_NAMES], dtype=float)
        ax.errorbar(xs, ys, yerr=yerr, fmt="-o", color=color, ms=4, lw=1.2, capsize=2, label=LABELS[name])
    ax.axhline(0.0, color="0.35", lw=0.8)
    ax.set_xticks(xs, list(H.BIN_NAMES))
    ax.set_xlabel("token gap (index difference)")
    ax.set_ylabel("excess rate")
    bits = "  ".join(f"{key} {'pass' if pred[key] else 'fail'}" for key in ("N1", "N2", "N3"))
    ax.set_title(f"One-edit near-repeat excess\n{bits}")
    ax.legend(ncol=4, fontsize=8, frameon=False, loc="best")
    fig.tight_layout()
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=150)
    plt.close(fig)


def _readme(payload: dict, pred: dict) -> str:
    streams = payload["streams"]
    rows = []
    for name in ORDER:
        rec = streams[name]
        b1 = rec["bins"]["1"]
        rows.append({
            "stream": LABELS[name],
            "n": rec["n_tokens"],
            "shape": rec["shape"],
            "decay": rec["decay_point"] if rec["decay_point"] else "null",
            "bin1_excess": b1["excess"],
            "bin1_rate": b1["rate"],
            "bin1_null_mean": b1["null_mean"],
            "bin1_null_sd": b1["null_sd"],
        })
    elev_rows = []
    for name in ORDER:
        rec = streams[name]
        row = {"stream": LABELS[name]}
        for bin_name in H.BIN_NAMES:
            row[bin_name] = "Y" if rec["bins"][bin_name]["elevated"] else "n"
        elev_rows.append(row)
    excess_rows = []
    for name in ORDER:
        rec = streams[name]
        row = {"stream": LABELS[name]}
        for bin_name in H.BIN_NAMES:
            row[bin_name] = rec["bins"][bin_name]["excess"]
        excess_rows.append(row)
    fit = streams["C0"].get("fit", {})
    lines = [
        "# h42: where one-edit near-repeats die out",
        "",
        "Pre-registration: `PREREG.md`. Gap is the difference in token index (gap 1 = the next token).",
        "A pair is eligible when the unit lengths differ by at most 1. The rate is the share of sampled eligible",
        "pairs whose unit Levenshtein distance is 1. MS, C0, self-citation, and h39 use collapsed EVA units.",
        "Boccaccio uses characters. Each bin keeps one even grid of at most 4000 eligible pairs, and every",
        "shuffle uses that same count on its own eligible pairs. The null is ten shuffles",
        "(numpy seed 42) inside hand x quire for the manuscript, and inside blocks of 8 pages of 200 tokens otherwise.",
        "Excess is the observed rate minus the mean null rate. A bin is elevated when the excess is greater than",
        "twice the null standard deviation and that standard deviation is above 0.",
        "",
        "## Predictions",
        "",
        f"- N1. MS 2B is local or page: **{'pass' if pred['N1'] else 'fail'}**. Shape `{streams['MS_2B']['shape']}`, decay `{streams['MS_2B']['decay_point']}`.",
        f"- N2. h39 native tuned decays later than MS 2B, or is flat while MS 2B is not: **{'pass' if pred['N2'] else 'fail'}**. Native shape `{streams['h39_native_tuned']['shape']}`, decay `{streams['h39_native_tuned']['decay_point']}`.",
        f"- N3. Boccaccio bin-1 excess is smaller than MS 2B bin-1 excess: **{'pass' if pred['N3'] else 'fail'}**. Boccaccio `{_fmt(streams['boccaccio']['bins']['1']['excess'])}`, MS 2B `{_fmt(streams['MS_2B']['bins']['1']['excess'])}`.",
        "",
        "## Streams",
        "",
    ]
    lines.extend(_table(rows))
    lines.extend(["", "## Excess by bin", ""])
    lines.extend(_table(excess_rows))
    lines.extend(["", "## Elevated bins", ""])
    lines.extend(_table(elev_rows))
    lines.extend([
        "",
        "## C0 fit",
        "",
        f"- Method `{fit.get('method')}`, n_random `{fit.get('n_random')}`, n_local `{fit.get('n_local')}`, fit seed `{fit.get('fit_seed')}`, generation seed `{fit.get('gen_seed')}`, plaintext `{fit.get('plaintext')}`.",
        f"- Train tokens `{fit.get('n_train')}`, generated `{fit.get('n_gen')}`, fit distance `{_fmt(fit.get('fit_distance'))}`, seconds `{_fmt(fit.get('secs'))}`.",
        "",
        "## Run",
        "",
        "```",
        "export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1",
        "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1",
        "python -m pytest hypotheses/h42_near_repeat_decay/test_h42.py",
        "python hypotheses/h42_near_repeat_decay/h42_lib.py",
        "python hypotheses/h42_near_repeat_decay/summarise.py",
        "```",
        "",
        f"numpy {payload.get('numpy')}, rapidfuzz {payload.get('rapidfuzz')}, python {payload.get('python')}.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    payload = json.loads((RES / "streams.json").read_text(encoding="utf-8"))
    streams = _checked(payload["streams"])
    missing = [name for name in ORDER if name not in streams]
    if missing:
        raise SystemExit(f"missing streams: {missing}")
    pred = H.predictions(streams)
    summary = {
        "predictions": pred,
        "shapes": {name: streams[name]["shape"] for name in ORDER},
        "decay_points": {name: streams[name]["decay_point"] for name in ORDER},
        "bin1_excess": {name: streams[name]["bins"]["1"]["excess"] for name in ORDER},
        "streams": streams,
        "numpy": payload.get("numpy"),
        "rapidfuzz": payload.get("rapidfuzz"),
        "python": payload.get("python"),
        "max_pairs": payload.get("max_pairs"),
        "n_null": payload.get("n_null"),
        "null_seed": payload.get("null_seed"),
    }
    status = {
        "complete": True,
        "predictions": pred,
        "N1": pred["N1"],
        "N2": pred["N2"],
        "N3": pred["N3"],
        "shapes": summary["shapes"],
        "decay_points": summary["decay_points"],
        "bin1_excess": summary["bin1_excess"],
    }
    RES.mkdir(parents=True, exist_ok=True)
    (RES / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (RES / "STATUS.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    _figure(streams, pred)
    (HERE / "README.md").write_text(_readme(payload, pred), encoding="utf-8")
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
