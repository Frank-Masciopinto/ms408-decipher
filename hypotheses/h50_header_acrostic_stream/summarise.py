"""Summarise h50 results: write summary.json, STATUS.json, figures/header_acrostic_stream.png, and README.md."""
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

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import h50_lib as H  # noqa: E402

RES_PATH = HERE / "results" / "measurements.json"
SUMMARY_PATH = HERE / "results" / "summary.json"
STATUS_PATH = HERE / "results" / "STATUS.json"
FIG_PATH = HERE / "figures" / "header_acrostic_stream.png"
README_PATH = HERE / "README.md"

STREAM_LABELS = {
    "MS_1A": "MS 1A",
    "MS_2B": "MS 2B",
    "MS_3B": "MS 3B",
    "page_line_copier_1A": "PLC 1A",
    "page_line_copier_2B": "PLC 2B",
    "page_line_copier_3B": "PLC 3B",
    "it_boccaccio": "Boccaccio",
    "cucina": "Cucina",
    "la_pliny_herbal": "Pliny",
}


def _fmt(val, digits: int = 4) -> str:
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "pass" if val else "fail"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return f"{val:.{digits}f}"
    return str(val)


def _check(data: dict) -> dict:
    recomputed = H.evaluate_predictions(data["streams"])
    if recomputed != data["predictions"]:
        raise SystemExit(f"stored predictions {data['predictions']} != recomputed {recomputed}")
    return recomputed


def _build_figure(data: dict, pred: dict) -> None:
    streams = data["streams"]
    order = H.STREAM_ORDER
    labels = [STREAM_LABELS[s] for s in order]
    x = np.arange(len(order))

    fig, axes = plt.subplots(2, 2, figsize=(14.0, 9.2))
    ax_m1, ax_m2_r, ax_m2_cv, ax_m3 = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]

    # Panel A: M1 vertical word-order bigram gain D1_vert
    w = 0.26
    d1_raw = [streams[s]["M1"]["line_words_raw"]["D1_vert"] for s in order]
    d1_strip = [streams[s]["M1"]["line_words_stripped"]["D1_vert"] for s in order]
    d1_para = [streams[s]["M1"]["para_words"]["D1_vert"] for s in order]
    ax_m1.bar(x - w, d1_raw, width=w, color="#4C78A8", label="line_words_raw")
    ax_m1.bar(x, d1_strip, width=w, color="#F58518", label="line_words_stripped")
    ax_m1.bar(x + w, d1_para, width=w, color="#54A24B", label="para_words")
    ax_m1.axhline(0.05, color="#E45756", linestyle="--", linewidth=1.1, label="A1 threshold (+0.05 bits)")
    ax_m1.axhline(0.0, color="0.35", linewidth=0.8)
    ax_m1.set_xticks(x, labels, rotation=25, ha="right")
    ax_m1.set_ylabel("$D_1 = \\mathrm{bits}(\\mathrm{KN1}) - \\mathrm{bits}(\\mathrm{KN2})$")
    ax_m1.set_title(f"A. M1 Vertical Bigram Gain $D_1$ (A1: {_fmt(pred['A1'])})")
    ax_m1.legend(fontsize=8, frameon=False)
    ax_m1.grid(True, axis="y", alpha=0.25)

    # Panel B: M2 vertical acrostic redundancy R_acro vs 0.5 * R_horiz and permutation p95
    r_acro = [streams[s]["M2"]["R_acro"] for s in order]
    r_p95 = [streams[s]["M2"]["R_acro_null_p95"] for s in order]
    r_half_horiz = [0.5 * streams[s]["M2"]["R_horiz"] for s in order]
    ax_m2_r.bar(x - 0.18, r_acro, width=0.36, color="#72B7B2", label="$R_{\\mathrm{acro}} = H_1 - h_2$ (vertical)")
    ax_m2_r.bar(x + 0.18, r_half_horiz, width=0.36, color="#B279A2", label="$0.5 \\times R_{\\mathrm{horiz}}$ (A2 target)")
    ax_m2_r.scatter(x - 0.18, r_p95, marker="_", s=160, color="black", zorder=4, label="Within-folio perm p95")
    ax_m2_r.set_xticks(x, labels, rotation=25, ha="right")
    ax_m2_r.set_ylabel("Redundancy $H_1 - h_2$ (bits/unit)")
    ax_m2_r.set_title(f"B. M2 Vertical Glyph Acrostic Redundancy (A2: {_fmt(pred['A2'])})")
    ax_m2_r.legend(fontsize=8, frameon=False)
    ax_m2_r.grid(True, axis="y", alpha=0.25)

    # Panel C: M2 Sukhotin C/V alternation excess (vertical acrostic vs horizontal words)
    cv_vert = [streams[s]["M2"]["sukhotin_vert_cv"]["excess"] for s in order]
    cv_horiz = [streams[s]["M2"]["sukhotin_horiz_cv"]["excess"] for s in order]
    ax_m2_cv.bar(x - 0.18, cv_vert, width=0.36, color="#E45756", label="Vertical line_first_unit")
    ax_m2_cv.bar(x + 0.18, cv_horiz, width=0.36, color="#4C78A8", label="Horizontal within-word units")
    ax_m2_cv.axhline(0.0, color="0.35", linewidth=0.8)
    ax_m2_cv.set_xticks(x, labels, rotation=25, ha="right")
    ax_m2_cv.set_ylabel("Sukhotin C/V switch excess over shuffle")
    ax_m2_cv.set_title("C. M2 Sukhotin C/V Alternation Excess (Vertical vs Horizontal)")
    ax_m2_cv.legend(fontsize=8, frameon=False)
    ax_m2_cv.grid(True, axis="y", alpha=0.25)

    # Panel D: M3 Onset-stripped Line-1 header-to-body cosine vs within-quire swap null
    cos_obs = [streams[s]["M3"]["header_body_cos"] for s in order]
    cos_null = [streams[s]["M3"]["header_body_cos_null_mean"] for s in order]
    cos_p95 = [streams[s]["M3"]["header_body_cos_null_p95"] for s in order]
    ax_m3.bar(x - 0.18, cos_obs, width=0.36, color="#54A24B", label="Observed same-folio cos3")
    ax_m3.bar(x + 0.18, cos_null, width=0.36, color="#BAB0AC", label="Within-quire Line-1 swap null mean")
    ax_m3.scatter(x - 0.18, cos_p95, marker="_", s=160, color="black", zorder=4, label="Within-quire swap p95")
    ax_m3.set_xticks(x, labels, rotation=25, ha="right")
    ax_m3.set_ylabel("Mean unit-3gram cosine similarity")
    ax_m3.set_title(f"D. M3 Onset-Stripped Line-1 Header-to-Body Cosine (A3: {_fmt(pred['A3'])})")
    ax_m3.legend(fontsize=8, frameon=False)
    ax_m3.grid(True, axis="y", alpha=0.25)

    fig.suptitle(
        f"h50: Vertical Header and Acrostic Stream Tests (A1={_fmt(pred['A1'])}, A2={_fmt(pred['A2'])}, A3={_fmt(pred['A3'])}, Verdict={pred['verdict']})",
        fontsize=11,
    )
    fig.tight_layout()
    FIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_PATH, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _build_readme(data: dict, pred: dict) -> str:
    streams = data["streams"]
    lines = [
        "# h50: do paragraph-initial or line-initial words form a hidden header or acrostic stream?",
        "",
        "Pre-registration: [PREREG.md](PREREG.md). Tests whether the vertical sequences of",
        "paragraph-initial words (`para_words`), line-initial words (`line_words_raw` and `h16`",
        "onset-stripped `line_words_stripped`), or line-initial first units (`line_first_unit`) in",
        "MS 408 (`1A`, `2B`, `3B`) exhibit sequential linguistic structure beyond the no-plaintext",
        "`h47` `page_line_copier` generator and within-folio / within-quire permutation nulls.",
        "No translation or semantic claims are made.",
        "",
        "## Predictions and Verdict (`A1`–`A3`)",
        "",
        f"- **Overall verdict:** **`{pred['verdict']}`** (`A1 = {_fmt(pred['A1'])}`, `A2 = {_fmt(pred['A2'])}`, `A3 = {_fmt(pred['A3'])}`).",
        f"- **A1 (vertical word stream has sequential syntax):** **{_fmt(pred['A1'])}** (passing MS hands: `{pred['A1_passing_hands']}`).",
        f"  In all three MS hands (`1A`, `2B`, `3B`), 5-fold cross-validated Kneser–Ney bigram gain over unigram (`D1_vert = bits(KN1) - bits(KN2)`) is negative on `line_words_raw` (`{_fmt(streams['MS_1A']['M1']['line_words_raw']['D1_vert'])}`, `{_fmt(streams['MS_2B']['M1']['line_words_raw']['D1_vert'])}`, `{_fmt(streams['MS_3B']['M1']['line_words_raw']['D1_vert'])}`), `line_words_stripped` (`{_fmt(streams['MS_1A']['M1']['line_words_stripped']['D1_vert'])}`, `{_fmt(streams['MS_2B']['M1']['line_words_stripped']['D1_vert'])}`, `{_fmt(streams['MS_3B']['M1']['line_words_stripped']['D1_vert'])}`), and `para_words` (`{_fmt(streams['MS_1A']['M1']['para_words']['D1_vert'])}`, `{_fmt(streams['MS_2B']['M1']['para_words']['D1_vert'])}`, `{_fmt(streams['MS_3B']['M1']['para_words']['D1_vert'])}`), matching the non-semantic `page_line_copier` streams (`{_fmt(streams['page_line_copier_1A']['M1']['line_words_stripped']['D1_vert'])}` to `{_fmt(streams['page_line_copier_3B']['M1']['line_words_stripped']['D1_vert'])}` on `line_words_stripped`). By contrast, the Italian recipe control (`cucina`), where paragraph openings form genuine recurring recipe headers, passes `A1` with `D1_vert = +{_fmt(streams['cucina']['M1']['para_words']['D1_vert'])}` bits/word and lag-1 class MI `{_fmt(streams['cucina']['M1']['para_words']['lag1_class_mi'])} > p95 = {_fmt(streams['cucina']['M1']['para_words']['lag1_class_mi_null_p95'])}` (`z = {_fmt(streams['cucina']['M1']['para_words']['lag1_class_mi_z'], 2)}`).",
        f"- **A2 (vertical glyph acrostic spells words):** **{_fmt(pred['A2'])}** (passing MS hands: `{pred['A2_passing_hands']}`).",
        f"  While `line_first_unit` has modest within-folio redundancy $R_{{\\text{{acro}}}} = H_1 - h_2$ above the within-folio permutation 95th percentile (`{_fmt(streams['MS_1A']['M2']['R_acro'])}` in `1A`, `{_fmt(streams['MS_2B']['M2']['R_acro'])}` in `2B`, `{_fmt(streams['MS_3B']['M2']['R_acro'])}` in `3B` — driven by paragraph-initial gallows followed by line-initial continuation prefixes), it reaches only `24.3%`, `13.7%`, and `15.2%` of the horizontal within-word unit redundancy $R_{{\\text{{horiz}}}}$ (`{_fmt(streams['MS_1A']['M2']['R_horiz'])}`, `{_fmt(streams['MS_2B']['M2']['R_horiz'])}`, `{_fmt(streams['MS_3B']['M2']['R_horiz'])}` bits), far below the `50%` threshold for spelled words. Moreover, vertical `line_first_unit` shows much smaller Sukhotin vowel/consonant alternation excess (`{_fmt(streams['MS_1A']['M2']['sukhotin_alt'])}`, `{_fmt(streams['MS_2B']['M2']['sukhotin_alt'])}`, `{_fmt(streams['MS_3B']['M2']['sukhotin_alt'])}`) than horizontal within-word EVA units (`{_fmt(streams['MS_1A']['M2']['sukhotin_horiz_cv']['excess'])}`, `{_fmt(streams['MS_2B']['M2']['sukhotin_horiz_cv']['excess'])}`, `{_fmt(streams['MS_3B']['M2']['sukhotin_horiz_cv']['excess'])}`).",
        f"- **A3 (onset-stripped Line 1 headers match their own folio):** **{_fmt(pred['A3'])}** (passing MS hands: `{pred['A3_passing_hands']}`).",
        f"  In all three MS hands (`1A`, `2B`, `3B`), onset-stripped Line-1 words have higher unit-3gram cosine similarity (`header_body_cos`) with their own folio body than the 95th percentile of 200 within-quire Line-1 swaps across folios (`{_fmt(streams['MS_1A']['M3']['header_body_cos'])} > {_fmt(streams['MS_1A']['M3']['header_body_cos_null_p95'])}` in `1A`; `{_fmt(streams['MS_2B']['M3']['header_body_cos'])} > {_fmt(streams['MS_2B']['M3']['header_body_cos_null_p95'])}` in `2B`; `{_fmt(streams['MS_3B']['M3']['header_body_cos'])} > {_fmt(streams['MS_3B']['M3']['header_body_cos_null_p95'])}` in `3B`). Crucially, the no-plaintext `h47` synthetic streams (`page_line_copier_1A/2B/3B`) **also pass `A3` in all three hands** (`{_fmt(streams['page_line_copier_1A']['M3']['header_body_cos'])} > {_fmt(streams['page_line_copier_1A']['M3']['header_body_cos_null_p95'])}`, `{_fmt(streams['page_line_copier_2B']['M3']['header_body_cos'])} > {_fmt(streams['page_line_copier_2B']['M3']['header_body_cos_null_p95'])}`, `{_fmt(streams['page_line_copier_3B']['M3']['header_body_cos'])} > {_fmt(streams['page_line_copier_3B']['M3']['header_body_cos_null_p95'])}`), and unstripped `header_body_cos_raw` (`{_fmt(streams['MS_1A']['M3']['header_body_cos_raw'])}`, `{_fmt(streams['MS_2B']['M3']['header_body_cos_raw'])}`, `{_fmt(streams['MS_3B']['M3']['header_body_cos_raw'])}`) is virtually identical to stripped `header_body_cos`. This shows that `A3` reflects folio-level vocabulary persistence and lookback copying (`h47`/`h48`) rather than a hidden steganographic header key.",
        "",
        "## M1 — Vertical Word-Order Gain (`D1_vert`), Lag-1 Class MI, and Adjacent Repetition",
        "",
        "| Stream | Kind | Lines | Paras | Folios | `line_words_raw` $D_1$ | `line_words_stripped` $D_1$ | `line_words_stripped` MI (p95) | `line_words_stripped` `adj_rep_z` | `para_words` $D_1$ | `para_words` MI (p95) | A1 Pass |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for s in H.STREAM_ORDER:
        rec = streams[s]
        m1 = rec["M1"]
        rw = m1["line_words_raw"]
        sw = m1["line_words_stripped"]
        pw = m1["para_words"]
        lines.append(
            f"| `{s}` | `{rec['unit_kind']}` | {rec['n_lines']} | {rec['n_paras']} | {rec['n_folios']} | "
            f"{_fmt(rw['D1_vert'])} | {_fmt(sw['D1_vert'])} | "
            f"{_fmt(sw['lag1_class_mi'])} ({_fmt(sw['lag1_class_mi_null_p95'])}) | {_fmt(sw['adj_repeat_z'], 2)} | "
            f"{_fmt(pw['D1_vert'])} | {_fmt(pw['lag1_class_mi'])} ({_fmt(pw['lag1_class_mi_null_p95'])}) | "
            f"**{_fmt(m1['pass_a1'])}** |"
        )

    lines.extend([
        "",
        "## M2 — Vertical Glyph-Acrostic Redundancy (`R_acro`) and Sukhotin Alternation (`sukhotin_alt`)",
        "",
        "| Stream | $H_{1,\\text{acro}}$ | $h_{2,\\text{acro}}$ | $R_{\\text{acro}} = H_1 - h_2$ | Perm p95 ($z$) | $R_{\\text{horiz}}$ | $R_{\\text{acro}} / R_{\\text{horiz}}$ | Vert Sukhotin Excess ($z$) | Horiz Sukhotin Excess ($z$) | A2 Pass |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])

    for s in H.STREAM_ORDER:
        m2 = streams[s]["M2"]
        vcv = m2["sukhotin_vert_cv"]
        hcv = m2["sukhotin_horiz_cv"]
        lines.append(
            f"| `{s}` | {_fmt(m2['H1_acro'])} | {_fmt(m2['h2_acro'])} | {_fmt(m2['R_acro'])} | "
            f"{_fmt(m2['R_acro_null_p95'])} ({_fmt(m2['R_acro_z'], 2)}) | {_fmt(m2['R_horiz'])} | "
            f"{_fmt(m2['acro_to_horiz_ratio'], 3)} | {_fmt(vcv['excess'])} ({_fmt(vcv['z'], 2)}) | "
            f"{_fmt(hcv['excess'])} ({_fmt(hcv['z'], 2)}) | **{_fmt(m2['pass_a2'])}** |"
        )

    lines.extend([
        "",
        "## M3 — Folio-Header (`Line 1` Stripped) to Body Alignment (`header_body_cos` & One-Edit Rate)",
        "",
        "| Stream | Folios ($\\ge 2$ lines) | Quires | `header_body_cos` | `header_body_cos_raw` | Swap Null Mean | Swap Null p95 ($z$) | `header_body_edit1` | Edit1 Null Mean | Edit1 Null p95 ($z$) | A3 Pass |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ])

    for s in H.STREAM_ORDER:
        m3 = streams[s]["M3"]
        lines.append(
            f"| `{s}` | {m3['n_folios']} | {m3['n_quires']} | {_fmt(m3['header_body_cos'])} | "
            f"{_fmt(m3['header_body_cos_raw'])} | {_fmt(m3['header_body_cos_null_mean'])} | "
            f"{_fmt(m3['header_body_cos_null_p95'])} ({_fmt(m3['header_body_cos_z'], 2)}) | "
            f"{_fmt(m3['header_body_edit1'])} | {_fmt(m3['header_body_edit1_null_mean'])} | "
            f"{_fmt(m3['header_body_edit1_null_p95'])} ({_fmt(m3['header_body_edit1_z'], 2)}) | "
            f"**{_fmt(m3['pass_a3'])}** |"
        )

    lines.extend([
        "",
        "## Reproduction",
        "",
        "```bash",
        "export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1",
        "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1",
        "python3 hypotheses/h50_header_acrostic_stream/run_h50.py",
        "python3 hypotheses/h50_header_acrostic_stream/summarise.py",
        "python3 -m pytest hypotheses/h50_header_acrostic_stream/test_h50.py -p no:cacheprovider",
        "```",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    if not RES_PATH.is_file():
        raise SystemExit(f"Missing {RES_PATH}; run run_h50.py first.")
    data = json.loads(RES_PATH.read_text(encoding="utf-8"))
    pred = _check(data)
    _build_figure(data, pred)

    summary_streams: dict[str, dict] = {}
    for s in H.STREAM_ORDER:
        rec = data["streams"][s]
        m1 = rec["M1"]
        m2 = rec["M2"]
        m3 = rec["M3"]
        summary_streams[s] = {
            "unit_kind": rec["unit_kind"],
            "n_tokens": rec["n_tokens"],
            "n_lines": rec["n_lines"],
            "n_paras": rec["n_paras"],
            "n_folios": rec["n_folios"],
            "n_quires": rec["n_quires"],
            "share_line_words_stripped": rec["share_line_words_stripped"],
            "M1": {
                "pass_a1": m1["pass_a1"],
                "line_words_raw": {
                    "D1_vert": m1["line_words_raw"]["D1_vert"],
                    "lag1_class_mi": m1["line_words_raw"]["lag1_class_mi"],
                    "lag1_class_mi_null_p95": m1["line_words_raw"]["lag1_class_mi_null_p95"],
                    "adj_repeat_z": m1["line_words_raw"]["adj_repeat_z"],
                },
                "line_words_stripped": {
                    "D1_vert": m1["line_words_stripped"]["D1_vert"],
                    "lag1_class_mi": m1["line_words_stripped"]["lag1_class_mi"],
                    "lag1_class_mi_null_p95": m1["line_words_stripped"]["lag1_class_mi_null_p95"],
                    "adj_repeat_z": m1["line_words_stripped"]["adj_repeat_z"],
                    "pass_a1": m1["line_words_stripped"]["pass_a1"],
                },
                "para_words": {
                    "D1_vert": m1["para_words"]["D1_vert"],
                    "lag1_class_mi": m1["para_words"]["lag1_class_mi"],
                    "lag1_class_mi_null_p95": m1["para_words"]["lag1_class_mi_null_p95"],
                    "adj_repeat_z": m1["para_words"]["adj_repeat_z"],
                    "pass_a1": m1["para_words"]["pass_a1"],
                },
            },
            "M2": {
                "pass_a2": m2["pass_a2"],
                "H1_acro": m2["H1_acro"],
                "h2_acro": m2["h2_acro"],
                "R_acro": m2["R_acro"],
                "R_acro_null_mean": m2["R_acro_null_mean"],
                "R_acro_null_p95": m2["R_acro_null_p95"],
                "R_acro_z": m2["R_acro_z"],
                "R_horiz": m2["R_horiz"],
                "acro_to_horiz_ratio": m2["acro_to_horiz_ratio"],
                "reaches_50pct_horiz": m2["reaches_50pct_horiz"],
                "sukhotin_alt": m2["sukhotin_alt"],
                "sukhotin_vert_z": m2["sukhotin_vert_cv"]["z"],
                "sukhotin_horiz_excess": m2["sukhotin_horiz_cv"]["excess"],
                "sukhotin_horiz_z": m2["sukhotin_horiz_cv"]["z"],
            },
            "M3": {
                "pass_a3": m3["pass_a3"],
                "header_body_cos": m3["header_body_cos"],
                "header_body_cos_raw": m3["header_body_cos_raw"],
                "header_body_cos_null_mean": m3["header_body_cos_null_mean"],
                "header_body_cos_null_p95": m3["header_body_cos_null_p95"],
                "header_body_cos_z": m3["header_body_cos_z"],
                "header_body_edit1": m3["header_body_edit1"],
                "header_body_edit1_null_mean": m3["header_body_edit1_null_mean"],
                "header_body_edit1_null_p95": m3["header_body_edit1_null_p95"],
                "header_body_edit1_z": m3["header_body_edit1_z"],
            },
        }

    summary = {
        "hypothesis": "h50_header_acrostic_stream",
        "verdict": pred["verdict"],
        "predictions": pred,
        "streams": summary_streams,
        "n_perm": data["n_perm"],
        "seed": data["seed"],
        "numpy": data["numpy"],
        "python": data["python"],
        "runtime_sec": data["runtime_sec"],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    status = {
        "hypothesis": "h50_header_acrostic_stream",
        "complete": True,
        "verdict": pred["verdict"],
        "A1": pred["A1"],
        "A1_passing_hands": pred["A1_passing_hands"],
        "A2": pred["A2"],
        "A2_passing_hands": pred["A2_passing_hands"],
        "A3": pred["A3"],
        "A3_passing_hands": pred["A3_passing_hands"],
        "n_perm": data["n_perm"],
        "seed": data["seed"],
        "runtime_sec": data["runtime_sec"],
    }
    STATUS_PATH.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    README_PATH.write_text(_build_readme(data, pred), encoding="utf-8")
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
