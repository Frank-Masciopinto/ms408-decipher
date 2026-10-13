"""Summarise h28 bifolium results and write README.md, the figure, and results/STATUS.json.

No translation claims. The h26 anchor is not recomputed.
"""
from __future__ import annotations

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h24_neutral_cipher_robustness"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h20_generators_vs_italian"))

import h20_lib as L20  # noqa: E402
import h24_lib as L24  # noqa: E402
import h28_lib as L  # noqa: E402

RES = HERE / "results"
MS_DIR = ROOT / "hypotheses" / "h20_generators_vs_italian" / "results"
HANDS = ("1A", "2B", "3B")
FIT_KEYS = ("cond", "seed", "src", "copy", "c", "n_swap", "signal_share", "unit_change_share", "unit_changed")
READING_SENTENCE = {
    "orthography": "The match is orthography, not which letter owns which string.",
    "complementarity": "The match is the prefix/suffix split.",
    "length+homophony": "Length and homophony are enough.",
    "none": "No single one of these three cuts is the carrier.",
    "unlisted": "The three match calls do not fall under one of the four pre-registered readings.",
}


def row(path: Path, scheme: str) -> dict:
    meta = json.loads(path.read_text(encoding="utf-8"))
    scheme_block = meta["schemes"][scheme]
    stats = L20.dstats(scheme_block["bits"], scheme_block["glyphs_per_word"], meta["crossfit_W5"]["lam"])
    return {"cell": path.stem[5:], "fit": meta.get("fit") or {}, **stats}


def fingerprints(scheme: str, ms_rows: list[dict]) -> pd.DataFrame:
    records = []
    for cond in L.CONDITIONS:
        for s in L.SEEDS:
            path = RES / f"cell_{L.cell_name(cond, s)}.json"
            if not path.exists():
                raise SystemExit(f"missing {path.name}")
            records.append(row(path, scheme))
    matched = [L20.match({k: rec[k] for k in L20.DELTA}, ms_rows) for rec in records]
    for rec, match in zip(records, matched):
        for key, value in match.items():
            rec[f"m_{key}"] = value
    frame = pd.DataFrame(records)
    for key in FIT_KEYS:
        frame[key] = [fit.get(key, np.nan) for fit in frame["fit"]]
    return frame.drop(columns="fit")


def aggregate(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cond in L.CONDITIONS:
        group = frame[frame.cond == cond]
        if len(group) != len(L.SEEDS):
            raise SystemExit(f"{cond} has {len(group)} cells")
        mean, lo, hi = L24.tci(group.m_distance)
        rate4 = float((group.m_n_match >= 4).mean())
        rate5 = float(group.m_reproduces.astype(float).mean())
        matched = L.condition_matches(mean, rate4)
        rec = {
            "cond": cond,
            "n": int(len(group)),
            "rate4": rate4,
            "rate5": rate5,
            "dist_mean": mean,
            "dist_lo": lo,
            "dist_hi": hi,
            "matches": matched,
            "pred_pass": L.prediction_pass(cond, matched),
            "prediction": L.PREDICTION_ID[cond],
        }
        for key in L20.DELTA:
            rec[key] = float(group[key].mean())
        if group.signal_share.notna().any():
            rec["signal_share"] = float(group.signal_share.mean())
        rows.append(rec)
    return pd.DataFrame(rows)


def plot(frame: pd.DataFrame, ms: dict[str, dict], path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    colors = {"letter": "C0", "state": "C1", "unit": "C2"}
    for i, cond in enumerate(L.CONDITIONS):
        group = frame[frame.cond == cond].sort_values("seed")
        x = i + (group.seed.to_numpy(dtype=float) - 3.0) * 0.13
        y = group.m_distance.to_numpy(dtype=float)
        hit = group.m_n_match.to_numpy() >= 4
        axes[0].scatter(x[hit], y[hit], c=colors[cond], s=36, zorder=3)
        axes[0].scatter(x[~hit], y[~hit], facecolors="none", edgecolors=colors[cond], s=36, zorder=3)
        axes[0].plot([i - 0.32, i + 0.32], [float(y.mean()), float(y.mean())], c="k", lw=1.6)
        axes[1].scatter(group.D4, group.D5, c=colors[cond], s=36, label=cond)
    axes[0].axhline(L.DIST_MAX, c="k", ls="--", lw=1, label="match threshold 5.43")
    axes[0].axhline(L.ANCHOR_DIST, c="0.35", ls=":", lw=1, label="h26 anchor 3.43")
    axes[0].set_xticks(range(len(L.CONDITIONS)), list(L.CONDITIONS))
    axes[0].set_ylabel("bifolium distance")
    axes[0].set_title("Filled: n_match ≥ 4")
    axes[0].legend(fontsize=8)
    axes[1].scatter([ms[h]["D4"] for h in HANDS], [ms[h]["D5"] for h in HANDS], c="k", marker="*", s=150, label="MS hands")
    axes[1].set_xlabel("D4")
    axes[1].set_ylabel("D5")
    axes[1].legend(fontsize=8)
    axes[1].set_title("Bifolium fingerprint")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _fmt(value: float, digits: int = 4) -> str:
    return f"{value:.{digits}f}"


def render_readme(bif: pd.DataFrame, quire: pd.DataFrame, seeds: pd.DataFrame, report: dict, status: dict) -> str:
    def group_table(frame: pd.DataFrame) -> str:
        lines = [
            "| condition | n | mean distance [95% CI] | ≥4/5 | 5/5 | matches | D1 | D2 | D3 | D4 | D5 |",
            "|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|",
        ]
        for rec in frame.itertuples(index=False):
            ci = f"{_fmt(rec.dist_mean)} [{_fmt(rec.dist_lo)}, {_fmt(rec.dist_hi)}]"
            lines.append(
                f"| {rec.cond} | {rec.n} | {ci} | {_fmt(rec.rate4, 3)} | {_fmt(rec.rate5, 3)} | "
                f"{'yes' if rec.matches else 'no'} | {_fmt(rec.D1)} | {_fmt(rec.D2)} | {_fmt(rec.D3)} | {_fmt(rec.D4)} | {_fmt(rec.D5)} |"
            )
        return "\n".join(lines)

    seed_lines = [
        "| cell | distance | n_match | 5/5 | D1 | D2 | D3 | D4 | D5 |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|",
    ]
    ordered = seeds.copy()
    ordered["cond"] = pd.Categorical(ordered.cond, list(L.CONDITIONS), ordered=True)
    for rec in ordered.sort_values(["cond", "seed"]).itertuples(index=False):
        seed_lines.append(
            f"| {rec.cell} | {_fmt(rec.m_distance)} | {int(rec.m_n_match)} | "
            f"{'yes' if rec.m_reproduces else 'no'} | {_fmt(rec.D1)} | {_fmt(rec.D2)} | {_fmt(rec.D3)} | {_fmt(rec.D4)} | {_fmt(rec.D5)} |"
        )
    pred_lines = [
        "| | pre-registered call | result | pass |",
        "|---|---|---|---|",
    ]
    statements = {
        "A1": "`letter` matches. The letter-to-string mapping is not required.",
        "A2": "`state` does not match. Prefix/suffix complementarity is required.",
        "A3": "`unit` does not match. Within-string order is required.",
    }
    for key in ("A1", "A2", "A3"):
        pred = status["predictions"][key]
        outcome = (
            f"distance {_fmt(pred['dist_mean'])}, ≥4/5 {_fmt(pred['rate4'], 3)}, "
            f"5/5 {_fmt(pred['rate5'], 3)}, matches={'yes' if pred['matches'] else 'no'}"
        )
        pred_lines.append(f"| {key} | {statements[key]} | {outcome} | {'pass' if pred['pass'] else 'fail'} |")
    by_seed = report["by_seed"]
    share_bits = ", ".join(
        f"s{s} {by_seed[str(s)]['changed']}/{by_seed[str(s)]['n']}" for s in L.SEEDS
    )
    reading = status["reading"]
    return f"""# h28: permutations of the real Naibbe tables

This stage was pre-registered in [PREREG.md](PREREG.md) before any h28 computing. The numbers below are the bifolium fingerprint of the fifteen scored cells. A match under the pre-registered rule is not a decipherment and not a translation.

## Question

Which level of the author's tables carries the h26 match: the letter-to-string mapping, the prefix/suffix role split, or the order of glyphs inside each string?

## Method

- Source table: `data/mechanisms/naibbe_tables.csv`, read only. Each permuted table is `tables/h28_<condition>_s<s>.csv`.
- Plaintext: Boccaccio (`it_boccaccio`), 5 seeds. No transfer.
- Shuffle seed `4000 + s`. Encryption seed `s`. Copy seed `100 * s + 17`.
- **letter:** within each (state, table), the 23 glyph strings are shuffled across the 23 letters.
- **state:** unigram strings stay in place. Within each table the 23 prefix strings and 23 suffix strings are pooled, shuffled, and written back onto those slots.
- **unit:** each glyph string is segmented with `run_h19.seg_fn("eva")`, the units are shuffled, and they are joined. `"".join(seg(s)) == s` held for every original string ({report["n_strings"]} strings, {report["n_one_unit"]} of them a single unit).
- Engine: `NH(table, 6, "naibbe", 17/36)`, then swap copying at c = 0.05 with the EVA segmenter, then `run_h20.lines_to_cell(..., "ctrl", "eva")` and `run_h20.run_cell`. Output length `2 × 10500`; the scorer keeps 10500 tokens. One worker. Token dumps were deleted after each cell.
- A condition matches when its bifolium mean distance is ≤ 5.43 and its ≥4/5 rate is ≥ 0.60. 5.43 is the h26 real-table + swap anchor 3.43 plus 2. That anchor was not recomputed.

## Results (bifolium, primary)

{group_table(bif)}

Per seed:

{chr(10).join(seed_lines)}

The unit shuffle changed the unit order of {report["changed"]} of {report["n"]} string copies ({share_bits}), share {report["unit_change_share"]:.6f}.

## Quire folds (scored, not used in the decision)

{group_table(quire)}

## Predictions

{chr(10).join(pred_lines)}

## Reading

{READING_SENTENCE[reading]}

The label is `{reading}`.

## Limits

- Five seeds, and only Boccaccio.
- The decision uses bifolium folds. Quire numbers are from the same `run_h20.run_cell` output and do not enter the pass/fail calls.
- Strings of one EVA unit cannot change under the unit shuffle. The reported share counts every original string, including those.
- The threshold is fixed from h26. It was not refit on these cells.

## Files

- Code and tests: `h28_lib.py`, `run_h28.py`, `summarise.py`, `test_h28.py`.
- Permuted tables: `tables/h28_<letter|state|unit>_s<1–5>.csv`.
- Cells and aggregates: `results/cell_*.json`, `results/fingerprints_*.csv`, `results/groups_*.csv`, `results/STATUS.json`.
- Figure: `figures/table_permutations.png`.
"""


def main() -> None:
    ms = {hand: row(MS_DIR / f"cell_MS_{hand}.json", "bifolium") for hand in HANDS}
    ms_rows = [{k: ms[hand][k] for k in L20.DELTA} for hand in HANDS]
    bif_cells = fingerprints("bifolium", ms_rows)
    quire_cells = fingerprints("quire", ms_rows)
    bif = aggregate(bif_cells)
    quire = aggregate(quire_cells)
    RES.mkdir(parents=True, exist_ok=True)
    bif_cells.to_csv(RES / "fingerprints_bifolium.csv", index=False)
    quire_cells.to_csv(RES / "fingerprints_quire.csv", index=False)
    bif.to_csv(RES / "groups_bifolium.csv", index=False)
    quire.to_csv(RES / "groups_quire.csv", index=False)
    report = L.unit_change_report()
    (RES / "unit_change.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    tests_path = RES / "tests.json"
    runtime_path = RES / "runtime_sec.json"
    if not tests_path.exists():
        raise SystemExit("results/tests.json is missing")
    if not runtime_path.exists():
        raise SystemExit("results/runtime_sec.json is missing")
    tests_passed = bool(json.loads(tests_path.read_text(encoding="utf-8"))["tests_passed"])
    runtime_sec = float(json.loads(runtime_path.read_text(encoding="utf-8"))["runtime_sec"])
    match_of = {rec.cond: bool(rec.matches) for rec in bif.itertuples(index=False)}
    label = L.reading(match_of["letter"], match_of["state"], match_of["unit"])
    predictions = {}
    for rec in bif.itertuples(index=False):
        predictions[rec.prediction] = {
            "pass": bool(rec.pred_pass),
            "cond": rec.cond,
            "matches": bool(rec.matches),
            "dist_mean": float(rec.dist_mean),
            "dist_lo": float(rec.dist_lo),
            "dist_hi": float(rec.dist_hi),
            "rate4": float(rec.rate4),
            "rate5": float(rec.rate5),
            "n": int(rec.n),
        }
    status = {
        "predictions": predictions,
        "dist_mean": {key: predictions[L.PREDICTION_ID[key]]["dist_mean"] for key in L.CONDITIONS},
        "rate4": {key: predictions[L.PREDICTION_ID[key]]["rate4"] for key in L.CONDITIONS},
        "rate5": {key: predictions[L.PREDICTION_ID[key]]["rate5"] for key in L.CONDITIONS},
        "unit_change_share": float(report["unit_change_share"]),
        "reading": label,
        "tests_passed": tests_passed,
        "runtime_sec": runtime_sec,
    }
    (RES / "STATUS.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    (RES / "summary.json").write_text(
        json.dumps(
            {
                "status": status,
                "unit_change": report,
                "bifolium": bif.to_dict("records"),
                "quire": quire.to_dict("records"),
            },
            indent=2,
            default=lambda obj: obj.item() if hasattr(obj, "item") else float(obj),
        )
        + "\n",
        encoding="utf-8",
    )
    plot(bif_cells, ms, HERE / "figures" / "table_permutations.png")
    (HERE / "README.md").write_text(render_readme(bif, quire, bif_cells, report, status), encoding="utf-8")
    print(json.dumps(status, indent=2))
    print(bif.to_string(index=False))


if __name__ == "__main__":
    main()
