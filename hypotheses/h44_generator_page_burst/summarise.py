"""Write h44 predictions, summary, status, figure, and README from results/streams.json."""
from __future__ import annotations

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import h44_lib as H

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
FIG = HERE / "figures" / "generator_burst.png"
LABELS = {
    "MS_1A": "MS 1A",
    "MS_2B": "MS 2B",
    "MS_3B": "MS 3B",
    "fitted_s1": "fitted s1",
    "fitted_s2": "fitted s2",
    "C0": "C0",
    "h06_pool": "h06 pool 0.5",
    "h06_p0": "h06 p_pool 0",
    "h39_native_tuned": "h39 native tuned",
    "h39_C0_graph": "h39 C0 graph",
    "positive_control": "positive control",
}
SCORE_KEYS = ("orig", "in_page", "in_quire", "full")


def _check(rec: dict) -> None:
    excess = float(rec["orig"]) - float(rec["full"])
    if abs(excess - float(rec["excess"])) > 1e-9:
        raise SystemExit(f"{rec['name']} stored excess does not match orig - full")
    if excess > 0.0:
        share = (float(rec["in_quire"]) - float(rec["full"])) / excess
        if rec["share_kept_in_quire"] is None or abs(share - float(rec["share_kept_in_quire"])) > 1e-9:
            raise SystemExit(f"{rec['name']} stored quire share does not match")
    elif rec["share_kept_in_quire"] is not None:
        raise SystemExit(f"{rec['name']} has a quire share with non-positive excess")


def _fmt(value) -> str:
    if value is None:
        return "null"
    return f"{float(value):.10f}"


def _cell(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.10f}"
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


def _figure(streams: dict, pred: dict) -> None:
    labels = [LABELS[name] for name in H.ORDER]
    xs = np.arange(len(H.ORDER))
    width = 0.18
    fig, ax = plt.subplots(figsize=(12.4, 5.8))
    colors = ("#4C78A8", "#F58518", "#54A24B", "#E45756")
    for i, key in enumerate(SCORE_KEYS):
        ys = [float(streams[name][key]) for name in H.ORDER]
        ax.bar(xs + (i - 1.5) * width, ys, width=width, color=colors[i], label=key)
    bits = "  ".join(f"{key} {'pass' if pred[key] else 'fail'}" for key in ("B1", "B2", "B3"))
    ax.set_xticks(xs, labels, rotation=30, ha="right")
    ax.set_ylabel("burst")
    ax.set_title(f"Page and quire burst\n{bits}")
    ax.legend(ncol=4, frameon=False)
    fig.tight_layout()
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=150)
    plt.close(fig)


def _readme(payload: dict, pred: dict) -> str:
    streams = payload["streams"]
    rows = []
    for name in H.ORDER:
        rec = streams[name]
        rows.append({
            "stream": LABELS[name],
            "n": rec["n"],
            "orig": rec["orig"],
            "in_page": rec["in_page"],
            "in_quire": rec["in_quire"],
            "full": rec["full"],
            "excess": rec["excess"],
            "quire_share": rec["share_kept_in_quire"],
        })
    gap_rows = []
    for name in H.MS_NAMES:
        rec = streams[name]
        gap_rows.append({
            "stream": LABELS[name],
            "in_page_minus_full": float(rec["in_page"]) - float(rec["full"]),
            "in_quire_minus_full": float(rec["in_quire"]) - float(rec["full"]),
        })
    fit = streams["C0"].get("fit", {})
    h06_pool = streams["h06_pool"]
    h06_p0 = streams["h06_p0"]
    lines = [
        "# h44: generator page burst",
        "",
        "Pre-registration: `PREREG.md`. Burst is `h41_lib.burst` (50 types, blocks of 200).",
        "orig is the stream. in_page, in_quire, and full are each the mean of 10 shuffles",
        "from a fresh numpy Generator seeded with 44. Excess is orig minus full.",
        "The share kept in the quire is (in_quire - full) / excess when excess is positive.",
        "",
        f"L, the median paragraph-token count of hand 2B folios, is {_fmt(payload['L'])}.",
        f"The two central folio counts are {payload['central_folio_counts'][0]} and {payload['central_folio_counts'][1]}",
        f"({payload['n_folios']} folios). Generated pages are {payload['page_tokens']} tokens,",
        "the whole number nearest L, and a quire is 8 pages. Streams are 10,500 tokens",
        "(hand 1A is the whole hand when it is shorter).",
        "Manuscript hands use their real folios and real quires.",
        "",
        "## Predictions",
        "",
        f"- B1. Every non-control, non-MS stream has excess below the smallest MS hand excess: **{'pass' if pred['B1'] else 'fail'}**.",
        f"  Smallest MS excess `{_fmt(pred['ms_excess_min'])}`. Failures: `{pred['B1_fail'] or 'none'}`.",
        f"- B2. The positive control exceeds the largest MS hand excess: **{'pass' if pred['B2'] else 'fail'}**.",
        f"  Largest MS excess `{_fmt(pred['ms_excess_max'])}`. Positive control `{_fmt(streams['positive_control']['excess'])}`.",
        f"- B3. At least two MS hands have (in_page - full) greater than (in_quire - full): **{'pass' if pred['B3'] else 'fail'}**.",
        f"  Hands: `{pred['B3_hands'] or 'none'}`.",
        "",
        "## Streams",
        "",
        *_table(rows),
        "",
        "## Manuscript page gap minus quire gap",
        "",
        *_table(gap_rows),
        "",
        "## Generators",
        "",
        f"- C0 fit method `{fit.get('method')}`, n_random `{fit.get('n_random')}`, n_local `{fit.get('n_local')}`,",
        f"  fit seed `{fit.get('fit_seed')}`, generation seed `{fit.get('gen_seed')}`, workers `{fit.get('workers')}`.",
        f"  Train tokens `{fit.get('n_train')}`, fit distance `{_fmt(fit.get('fit_distance'))}`, seconds `{_fmt(fit.get('secs'))}`.",
        f"  Plaintext: {fit.get('fit_plaintext')}.",
        f"- h06 parameters were not fitted. Shared model built from hand 2B paragraph words",
        f"  (n_train `{h06_pool['n_train']}`, shared seed `{h06_pool['shared_seed']}`), generation seed `{h06_pool['gen_seed']}`.",
        f"  `h06_pool`: p_pool `{h06_pool['p_pool']}`, pool size `{h06_pool['S']}`, pool `{h06_pool['pool']}`.",
        f"  `h06_p0`: p_pool `{h06_p0['p_pool']}`, pool size `{h06_p0['S']}`.",
        f"  Base parameters `{h06_pool['base_params']}`.",
        f"- Positive control seed `{payload['positive_seed']}`, `{payload['positive_types']}` types per page, Zipf weights 1/rank.",
        "",
        "## Run",
        "",
        "```",
        "export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1",
        "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1",
        "python -m pytest hypotheses/h44_generator_page_burst/test_h44.py",
        "python hypotheses/h44_generator_page_burst/run_h44.py",
        "python hypotheses/h44_generator_page_burst/summarise.py",
        "```",
        "",
        f"numpy {payload['numpy']}, python {payload['python']}.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    payload = json.loads((RES / "streams.json").read_text(encoding="utf-8"))
    streams = payload["streams"]
    missing = [name for name in H.ORDER if name not in streams]
    if missing:
        raise SystemExit("missing streams: " + ", ".join(missing))
    for name in H.ORDER:
        if streams[name].get("name") != name:
            raise SystemExit(f"{name} record name is {streams[name].get('name')}")
        _check(streams[name])
    if int(payload["page_tokens"]) != H.page_len_from_median(float(payload["L"])):
        raise SystemExit("page_tokens does not match the recorded median")
    if int(streams["C0"]["fit"]["n_random"]) != 20:
        raise SystemExit("C0 n_random is not 20")
    if streams["h06_pool"]["parameters_fitted"] or streams["h06_p0"]["parameters_fitted"]:
        raise SystemExit("h06 parameters were fitted")
    pred = H.predictions(streams)
    status = {
        "complete": True,
        "L": payload["L"],
        "page_tokens": payload["page_tokens"],
        "central_folio_counts": payload["central_folio_counts"],
        "n_folios_2B": payload["n_folios"],
        "B1": pred["B1"],
        "B2": pred["B2"],
        "B3": pred["B3"],
        "B1_fail": pred["B1_fail"],
        "B3_hands": pred["B3_hands"],
        "ms_excess_min": pred["ms_excess_min"],
        "ms_excess_max": pred["ms_excess_max"],
        "n_random": 20,
        "n_shuffles": payload["n_shuffles"],
        "shuffle_seed": payload["shuffle_seed"],
        "h06_parameters_fitted": False,
    }
    summary = {
        "L": payload["L"],
        "page_tokens": payload["page_tokens"],
        "predictions": pred,
        "streams": {
            name: {key: streams[name][key] for key in ("n", "orig", "in_page", "in_quire", "full", "excess", "share_kept_in_quire")}
            for name in H.ORDER
        },
    }
    _figure(streams, pred)
    (RES / "STATUS.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    (RES / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (HERE / "README.md").write_text(_readme(payload, pred), encoding="utf-8")
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
