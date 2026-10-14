"""Summarise h47 results: write summary.json, STATUS.json, figures/page_line_benchmarks.png, and README.md."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import h47_lib as H  # noqa: E402

RES = HERE / "results"
STREAMS_PATH = RES / "streams.json"
SUMMARY_PATH = RES / "summary.json"
STATUS_PATH = RES / "STATUS.json"
FIG_PATH = HERE / "figures" / "page_line_benchmarks.png"
README_PATH = HERE / "README.md"

STREAM_ORDER = (
    "page_line_copier_1A",
    "page_line_copier_2B",
    "page_line_copier_3B",
    "h39_native_tuned_2B",
    "h39_C0_graph_2B",
)

STREAM_LABELS = {
    "page_line_copier_1A": "PLC 1A",
    "page_line_copier_2B": "PLC 2B",
    "page_line_copier_3B": "PLC 3B",
    "h39_native_tuned_2B": "h39 native 2B",
    "h39_C0_graph_2B": "h39 C0 graph 2B",
}

BENCHMARKS = ("B1", "B2", "B3", "B4", "B5", "B6")


def _fmt(val: float | int | bool | None, digits: int = 4) -> str:
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "pass" if val else "fail"
    if isinstance(val, int):
        return str(val)
    return f"{float(val):.{digits}f}"


def _build_figure(streams: dict, predictions: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.2))
    ax_mat, ax_edge, ax_page, ax_decay = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]

    # Panel A: Benchmark pass matrix (streams x B1..B6)
    mat = np.zeros((len(STREAM_ORDER), len(BENCHMARKS)), dtype=float)
    for r, sname in enumerate(STREAM_ORDER):
        flags = streams[sname]["pass_flags"]
        for c, bkey in enumerate(BENCHMARKS):
            mat[r, c] = 1.0 if flags[bkey] else 0.0
    im = ax_mat.imshow(mat, cmap="RdYlGn", vmin=0.0, vmax=1.0, aspect="auto")
    ax_mat.set_xticks(np.arange(len(BENCHMARKS)), BENCHMARKS)
    ax_mat.set_yticks(
        np.arange(len(STREAM_ORDER)),
        [f"{STREAM_LABELS[s]} ({streams[s]['n_passed']}/6)" for s in STREAM_ORDER],
    )
    for r in range(len(STREAM_ORDER)):
        for c in range(len(BENCHMARKS)):
            passed = bool(mat[r, c] > 0.5)
            ax_mat.text(
                c,
                r,
                "PASS" if passed else "FAIL",
                ha="center",
                va="center",
                color="black",
                fontweight="bold",
                fontsize=9,
            )
    u_str = "  ".join(
        f"{uk}: {'PASS' if predictions[uk]['passed'] else 'FAIL'}" for uk in ("U1", "U2", "U3")
    )
    ax_mat.set_title(f"A. Benchmark Pass Matrix ({u_str})")
    fig.colorbar(im, ax=ax_mat, fraction=0.046, pad=0.04)

    # Panel B: B2 Junction MI & B3 Line-edge signals
    xs = np.arange(len(STREAM_ORDER))
    w = 0.24
    j_vals = [float(streams[s]["benchmarks"]["B2"]["J"]) for s in STREAM_ORDER]
    onset_vals = [float(streams[s]["benchmarks"]["B3"]["onset_excess"]) for s in STREAM_ORDER]
    end_vals = [float(streams[s]["benchmarks"]["B3"]["end_excess"]) for s in STREAM_ORDER]
    ax_edge.bar(xs - w, j_vals, width=w, color="#4C78A8", label="B2 Junction MI J (bits)")
    ax_edge.bar(xs, onset_vals, width=w, color="#F58518", label="B3 Line-initial onset excess")
    ax_edge.bar(xs + w, end_vals, width=w, color="#54A24B", label="B3 Line-final end excess")
    ax_edge.axhline(0.060, color="#4C78A8", linestyle="--", linewidth=1.0, label="B2 J min (0.060)")
    ax_edge.set_xticks(xs, [STREAM_LABELS[s] for s in STREAM_ORDER], rotation=20, ha="right")
    ax_edge.set_ylabel("Bits (MI / Excess MI)")
    ax_edge.set_title("B. Interior Junction MI (B2) & Line-Edge Excess (B3)")
    ax_edge.legend(fontsize=8, frameon=False)

    # Panel C: B5 Page burst excess & page vs quire gap
    b5_excess = [float(streams[s]["benchmarks"]["B5"]["excess"]) for s in STREAM_ORDER]
    b5_inpage = [float(streams[s]["benchmarks"]["B5"]["page_gap"]) for s in STREAM_ORDER]
    b5_inquire = [float(streams[s]["benchmarks"]["B5"]["quire_gap"]) for s in STREAM_ORDER]
    ax_page.bar(xs - w, b5_excess, width=w, color="#E45756", label="B5 Burst excess (orig - full)")
    ax_page.bar(xs, b5_inpage, width=w, color="#72B7B2", label="B5 Page gap (in_page - full)")
    ax_page.bar(xs + w, b5_inquire, width=w, color="#B279A2", label="B5 Quire gap (in_quire - full)")
    ax_page.axhline(0.8, color="#E45756", linestyle="--", linewidth=1.0, label="B5 min (0.8)")
    ax_page.axhline(3.5, color="#E45756", linestyle=":", linewidth=1.0, label="B5 max (3.5)")
    ax_page.set_xticks(xs, [STREAM_LABELS[s] for s in STREAM_ORDER], rotation=20, ha="right")
    ax_page.set_ylabel("Burst excess (h41_lib.burst)")
    ax_page.set_title("C. Page Burstiness & Quire Share (B5)")
    ax_page.legend(fontsize=8, frameon=False)

    # Panel D: B6 Near-repeat decay profile across lag bins
    bins = ["1", "2-5", "6-20", "21-100", "101-500", "501-1000"]
    bx = np.arange(len(bins))
    colors = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd")
    styles = ("-o", "-s", "-^", "--d", ":x")
    for idx, sname in enumerate(STREAM_ORDER):
        b6 = streams[sname]["benchmarks"]["B6"]
        rates = [float(b6["bins"][b]["rate"]) for b in bins]
        shape = b6["shape"]
        ax_decay.plot(
            bx,
            rates,
            styles[idx],
            color=colors[idx],
            linewidth=1.8,
            label=f"{STREAM_LABELS[sname]} ({shape})",
        )
    ax_decay.set_xticks(bx, bins)
    ax_decay.set_xlabel("Token lag bin")
    ax_decay.set_ylabel("1-edit + exact match rate")
    ax_decay.set_title("D. Near-Repeat Decay Profile (B6)")
    ax_decay.legend(fontsize=8, frameon=False)

    fig.tight_layout()
    FIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_PATH, dpi=150)
    plt.close(fig)


def _build_readme(payload: dict) -> str:
    streams = payload["streams"]
    pred = payload["predictions"]
    lines = [
        "# h47: Page-and-Line-Aware Non-Semantic Generator (`page_line_copier`)",
        "",
        "Pre-registration: `PREREG.md`. This experiment tests whether adding explicit line-edge",
        "slot conditioning (`h30`/`h34`) and partial lookback-buffer reset at folio boundaries",
        "(`rho_keep = 0.15`, `W_buf = 90`) to the `h39` non-semantic copier architecture allows a",
        "single mechanical generator (`page_line_copier`) to simultaneously pass all six manuscript",
        "structural benchmarks (`B1`–`B6`) across hands `1A`, `2B`, and `3B` without semantic content.",
        "",
        "## Verdict and Predictions (`U1`–`U3`)",
        "",
        f"- Overall verdict: **{pred['verdict']}**",
        f"- **U1** (`page_line_copier` on Hand `2B` passes at least `5/6` benchmarks `B1`–`B6`): **{_fmt(pred['U1']['passed'])}** (`{pred['U1']['n_passed_2B']}/6` passed on `2B`).",
        f"- **U2** (`page_line_copier` passes at least `5/6` benchmarks on at least two of `1A`, `2B`, `3B`): **{_fmt(pred['U2']['passed'])}** (`1A`: `{pred['U2']['n_passed_by_hand']['1A']}/6`, `2B`: `{pred['U2']['n_passed_by_hand']['2B']}/6`, `3B`: `{pred['U2']['n_passed_by_hand']['3B']}/6` [`5/6` if `d=80` unscored is counted strictly on `3B`]).",
        f"- **U3** (Previous `h39` best generators pass `<= 3/6` when evaluated on all six simultaneously): **{_fmt(pred['U3']['passed'])}** (`h39_native_tuned_2B` passes `{pred['U3']['n_passed_h39_native_tuned_2B']}/6`; `h39_C0_graph_2B` passes `{pred['U3']['n_passed_h39_C0_graph_2B']}/6`).",
        "",
        "## Summary Table (`B1`–`B6` Pass/Fail)",
        "",
        "| Stream | Hand | Tokens | Lines | Folios | B1 (h20 5/5) | B2 (S & J) | B3 (Line Edge) | B4 (Page Drop) | B5 (Page Burst) | B6 (Page Decay) | Total Passed |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for sname in STREAM_ORDER:
        rec = streams[sname]
        bm = rec["benchmarks"]
        fl = rec["pass_flags"]
        b4_note = "pass" if fl["B4"] else "fail"
        if sname == "page_line_copier_3B" and not bm["B4"]["d80_scored"]:
            b4_note = "pass (d160; d80 unscored)"
        lines.append(
            f"| `{sname}` | `{rec['hand']}` | {rec['n_tokens']} | {rec['n_lines']} | {rec['n_folios']} | "
            f"**{_fmt(fl['B1'])}** ({bm['B1']['n_match']}/5) | **{_fmt(fl['B2'])}** | **{_fmt(fl['B3'])}** | "
            f"**{b4_note}** | **{_fmt(fl['B5'])}** | **{_fmt(fl['B6'])}** (`{bm['B6']['shape']}`) | "
            f"**{rec['n_passed']}/6** |"
        )

    lines.extend([
        "",
        "## Detailed Benchmark Metrics",
        "",
        "### B1: `h20` Bifolium 5-Metric Fingerprint (`D1`–`D5`)",
        "",
        "| Stream | Match | D1 (KN2-KN1) | D2 (alpha2) | D3 (lam5) | D4 (line delta) | D5 (char H) |",
        "|---|---|---|---|---|---|---|",
    ])
    for sname in STREAM_ORDER:
        b1 = streams[sname]["benchmarks"]["B1"]
        st = b1["stats"]
        lines.append(
            f"| `{sname}` | {b1['n_match']}/5 (**{_fmt(b1['passed'])}**) | "
            f"{_fmt(st['D1'])} | {_fmt(st['D2'])} | {_fmt(st['D3'])} | {_fmt(st['D4'])} | {_fmt(st['D5'])} |"
        )

    lines.extend([
        "",
        "### B2: `h40` Interior Space Predictability $S$ and Cross-Word Junction MI $J$",
        "",
        "| Stream | $S_{\\text{interior}}$ | Target $S_{\\text{MS}} \\pm 0.02$ | $S$ in band | $J$ (bits) | $J \\ge 0.060$ | B2 Pass |",
        "|---|---|---|---|---|---|---|",
    ])
    for sname in STREAM_ORDER:
        b2 = streams[sname]["benchmarks"]["B2"]
        lines.append(
            f"| `{sname}` | {_fmt(b2['S_interior'])} | [{_fmt(b2['band_lo'])}, {_fmt(b2['band_hi'])}] | "
            f"{_fmt(b2['in_band'])} | {_fmt(b2['J'])} | {_fmt(b2['j_ok'])} | **{_fmt(b2['passed'])}** |"
        )

    lines.extend([
        "",
        "### B3: `h30` / `h34` Line-Edge Asymmetry and Line-Break Junction Reset",
        "",
        "| Stream | Onset Excess ($z$) | End Excess ($z$) | Cross/Within Ratio | Para Initial $z$ | B3 Pass |",
        "|---|---|---|---|---|---|",
    ])
    for sname in STREAM_ORDER:
        b3 = streams[sname]["benchmarks"]["B3"]
        lines.append(
            f"| `{sname}` | {_fmt(b3['onset_excess'])} ({_fmt(b3['onset_z'], 1)}) | "
            f"{_fmt(b3['end_excess'])} ({_fmt(b3['end_z'], 1)}) | {_fmt(b3['cross_to_within_ratio'])} | "
            f"{_fmt(b3['para_onset_z'], 1)} | **{_fmt(b3['passed'])}** |"
        )

    lines.extend([
        "",
        "### B4: `h43` Page-Boundary Drop at $d = 80$ and $d = 160$",
        "",
        "| Stream | $d=80$ Scored ($n_{\\text{cross}}$) | $d=80$ Effect vs Null p95 | $d=80$ Pass | $d=160$ Effect vs Null p95 | $d=160$ Pass | B4 Pass |",
        "|---|---|---|---|---|---|---|",
    ])
    for sname in STREAM_ORDER:
        b4 = streams[sname]["benchmarks"]["B4"]
        d80 = b4["d80"]
        d160 = b4["d160"]
        lines.append(
            f"| `{sname}` | {b4['d80_scored']} ({d80['n_cross']}) | "
            f"{_fmt(d80['effect'])} vs {_fmt(d80['null_p95'])} | {_fmt(b4['d80_pass'])} | "
            f"{_fmt(d160['effect'])} vs {_fmt(d160['null_p95'])} | {_fmt(b4['d160_pass'])} | **{_fmt(b4['passed'])}** |"
        )

    lines.extend([
        "",
        "### B5: `h44` Page-Scale Burstiness (`h41_lib.burst`)",
        "",
        "| Stream | Orig | In-Page | In-Quire | Full | Excess (`orig - full`) | `in_page - full` | `in_quire - full` | Quire Share | B5 Pass |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])
    for sname in STREAM_ORDER:
        b5 = streams[sname]["benchmarks"]["B5"]
        lines.append(
            f"| `{sname}` | {_fmt(b5['orig'])} | {_fmt(b5['in_page'])} | {_fmt(b5['in_quire'])} | "
            f"{_fmt(b5['full'])} | {_fmt(b5['excess'])} | {_fmt(b5['page_gap'])} | "
            f"{_fmt(b5['quire_gap'])} | {_fmt(b5['share_kept_in_quire'])} | **{_fmt(b5['passed'])}** |"
        )

    lines.extend([
        "",
        "### B6: `h42` Near-Repeat Page-Decay Profile",
        "",
        "| Stream | Shape | Decay Point | Lag 1 | Lag 2–5 | Lag 6–20 | Lag 21–100 | Lag 101–500 | Lag 501–1000 | B6 Pass |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])
    for sname in STREAM_ORDER:
        b6 = streams[sname]["benchmarks"]["B6"]
        bins = b6["bins"]
        lines.append(
            f"| `{sname}` | `{b6['shape']}` | `{b6['decay_point']}` | "
            f"{_fmt(bins['1']['rate'])} | {_fmt(bins['2-5']['rate'])} | {_fmt(bins['6-20']['rate'])} | "
            f"{_fmt(bins['21-100']['rate'])} | {_fmt(bins['101-500']['rate'])} | {_fmt(bins['501-1000']['rate'])} | "
            f"**{_fmt(b6['passed'])}** |"
        )

    lines.extend([
        "",
        "## Reproduction",
        "",
        "```bash",
        "export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1",
        "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1",
        "python3 hypotheses/h47_page_line_generator/run_h47.py",
        "python3 hypotheses/h47_page_line_generator/summarise.py",
        "pytest hypotheses/h47_page_line_generator/test_h47.py",
        "```",
        "",
        f"Environment: Python `{payload['python']}`, NumPy `{payload['numpy']}`, seed `{payload['seed']}`.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    if not STREAMS_PATH.exists():
        raise SystemExit(f"Missing {STREAMS_PATH}; run run_h47.py first.")
    payload = json.loads(STREAMS_PATH.read_text(encoding="utf-8"))
    streams = payload["streams"]
    predictions = H.evaluate_predictions(streams)
    payload["predictions"] = predictions

    _build_figure(streams, predictions)

    summary_streams = {}
    for sname in STREAM_ORDER:
        rec = streams[sname]
        bm = rec["benchmarks"]
        summary_streams[sname] = {
            "hand": rec["hand"],
            "n_lines": rec["n_lines"],
            "n_tokens": rec["n_tokens"],
            "n_folios": rec["n_folios"],
            "n_quires": rec["n_quires"],
            "n_passed": rec["n_passed"],
            "pass_flags": rec["pass_flags"],
            "B1": {
                "passed": bm["B1"]["passed"],
                "n_match": bm["B1"]["n_match"],
                "stats": bm["B1"]["stats"],
                "match": bm["B1"]["match"],
            },
            "B2": bm["B2"],
            "B3": bm["B3"],
            "B4": {
                "passed": bm["B4"]["passed"],
                "d80_scored": bm["B4"]["d80_scored"],
                "d80_pass": bm["B4"]["d80_pass"],
                "d80_effect_gt_p95": bm["B4"]["d80_effect_gt_p95"],
                "d160_pass": bm["B4"]["d160_pass"],
                "d80_effect": bm["B4"]["d80"]["effect"],
                "d80_null_p95": bm["B4"]["d80"]["null_p95"],
                "d80_n_cross": bm["B4"]["d80"]["n_cross"],
                "d160_effect": bm["B4"]["d160"]["effect"],
                "d160_null_p95": bm["B4"]["d160"]["null_p95"],
                "d160_n_cross": bm["B4"]["d160"]["n_cross"],
            },
            "B5": bm["B5"],
            "B6": {
                "passed": bm["B6"]["passed"],
                "shape": bm["B6"]["shape"],
                "decay_point": bm["B6"]["decay_point"],
                "rates": {b: bm["B6"]["bins"][b]["rate"] for b in ("1", "2-5", "6-20", "21-100", "101-500", "501-1000")},
            },
        }

    summary = {
        "hypothesis": "h47_page_line_generator",
        "verdict": predictions["verdict"],
        "seed": payload["seed"],
        "n_stream": payload["n_stream"],
        "rho_keep": payload["rho_keep"],
        "w_buf": payload["w_buf"],
        "predictions": predictions,
        "streams": summary_streams,
    }
    status = {
        "hypothesis": "h47_page_line_generator",
        "complete": True,
        "verdict": predictions["verdict"],
        "U1": predictions["U1"]["passed"],
        "U2": predictions["U2"]["passed"],
        "U3": predictions["U3"]["passed"],
        "n_passed_1A": predictions["U2"]["n_passed_by_hand"]["1A"],
        "n_passed_2B": predictions["U1"]["n_passed_2B"],
        "n_passed_3B": predictions["U2"]["n_passed_by_hand"]["3B"],
        "baseline_native_2B_passed": predictions["U3"]["n_passed_h39_native_tuned_2B"],
        "baseline_C0_graph_2B_passed": predictions["U3"]["n_passed_h39_C0_graph_2B"],
        "seed": payload["seed"],
        "runtime_sec": payload["runtime_sec"],
    }

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    STATUS_PATH.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    README_PATH.write_text(_build_readme(payload), encoding="utf-8")
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
