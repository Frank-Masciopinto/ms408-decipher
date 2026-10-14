"""Summarise h40: predictions R1, R2, R3, the figure, and the README."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "hypotheses" / "h20_generators_vs_italian"))

import h20_lib as H20  # noqa: E402
import h40_lib as H  # noqa: E402

RESULTS = HERE / "results"
DKEYS = ("D1", "D2", "D3", "D4", "D5")
OLD_BAND = (0.72, 0.80)
COLORS = {"1A": "#0072B2", "2B": "#D55E00", "3B": "#009E73"}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _md_tables(text: str) -> dict[str, list[dict[str, str]]]:
    lines = text.splitlines()
    out: dict[str, list[dict[str, str]]] = {}
    i = 0
    while i < len(lines):
        heading = lines[i].strip()
        if not heading.startswith("## "):
            i += 1
            continue
        i += 1
        while i < len(lines) and not lines[i].startswith("|"):
            i += 1
        if i >= len(lines):
            break
        header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        i += 1
        rows = []
        while i < len(lines) and lines[i].startswith("|"):
            cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            i += 1
            if all(set(c) <= set("-: ") and c for c in cells):
                continue
            rows.append(dict(zip(header, cells)))
        out[heading] = rows
    return out


def load_h39_a() -> list[dict]:
    """Nine variant-A rows. The README points at results/summary.md, which holds the table."""
    root = ROOT / "hypotheses" / "h39_graph_respell_and_tuned_copier"
    readme = (root / "README.md").read_text(encoding="utf-8")
    tables = _md_tables(readme)
    source = root / "README.md"
    if "## Variant A (graph)" not in tables:
        source = root / "results" / "summary.md"
        tables = _md_tables(source.read_text(encoding="utf-8"))
    shown = tables["## Variant A (graph)"]
    if len(shown) != 9 or not {"hand", "gen", "S"} <= set(shown[0]):
        raise SystemExit(f"variant A table in {source} does not have nine hand/gen/S rows")
    precise = _load(root / "results" / "summary.json")["A"]
    if len(precise) != 9:
        raise SystemExit("h39 summary.json variant A does not have nine rows")
    rows = []
    for table_row, raw in zip(shown, precise):
        if table_row["hand"] != raw["hand"] or table_row["gen"] != raw["gen"]:
            raise SystemExit("variant A table order disagrees with summary.json")
        exact = float(raw["S"])
        displayed = float(table_row["S"])
        if f"{exact:.3f}" != f"{displayed:.3f}":
            raise SystemExit(f"stored S {exact} does not round to table S {displayed}")
        rows.append({"hand": raw["hand"], "gen": raw["gen"], "S": exact, "S_table": displayed})
    return rows


def generator_junctions() -> dict:
    base = ROOT / "hypotheses" / "h33_word_boundary_resegmentation" / "results"
    rows = []
    for path in sorted(base.glob("c_*.json")):
        data = _load(path)
        if data.get("group") != "GEN":
            continue
        for variant in ("full", "interior"):
            for transform, block in data[variant].items():
                if not isinstance(block, dict) or "M5_junction" not in block:
                    continue
                rows.append(
                    {
                        "corpus": data["corpus"],
                        "variant": variant,
                        "transform": transform,
                        "M5_junction": float(block["M5_junction"]),
                    }
                )
    orig = [r for r in rows if r["transform"] == "orig"]
    small = [r for r in rows if r["M5_junction"] <= 0.004]
    if not orig or not small:
        raise SystemExit("no stored generator junctions")
    return {
        "orig": orig,
        "orig_max": max(r["M5_junction"] for r in orig),
        "max_at_most_0.004": max(r["M5_junction"] for r in small),
        "all_orig_le_0.004": all(r["M5_junction"] <= 0.004 for r in orig),
        "n_values_at_most_0.004": len(small),
    }


def ms_rows() -> list[dict]:
    base = ROOT / "hypotheses" / "h20_generators_vs_italian" / "results"
    rows = []
    for hand in H.HANDS:
        cell = _load(base / f"cell_MS_{hand}.json")
        bif = cell["schemes"]["bifolium"]
        rows.append(H20.dstats(bif["bits"], bif["glyphs_per_word"], cell["crossfit_W5"]["lam"]))
    return rows


def load_measures() -> list[dict]:
    rows = []
    for hand in H.HANDS:
        for cond in H.CONDITIONS:
            path = RESULTS / f"m_{hand}_{cond}.json"
            if not path.exists():
                raise SystemExit(f"missing {path.name}")
            rows.append(_load(path))
    return rows


def load_fingerprints(reference: list[dict]) -> list[dict]:
    rows = []
    for hand in H.HANDS:
        for cond in H.CONDITIONS:
            path = RESULTS / f"cell_{hand}_{cond}.json"
            if not path.exists():
                raise SystemExit(f"missing {path.name}")
            cell = _load(path)
            if "quire" in cell.get("schemes", {}):
                raise SystemExit(f"{path.name} contains a quire scheme")
            bif = cell["schemes"]["bifolium"]
            stats = H20.dstats(bif["bits"], bif["glyphs_per_word"], cell["crossfit_W5"]["lam"])
            matched = H20.match(stats, reference)
            rows.append(
                {
                    "hand": hand,
                    "condition": cond,
                    "n_tokens": cell["n_tokens"],
                    "D": {k: float(stats[k]) for k in DKEYS},
                    "n_match": int(matched["n_match"]),
                    "reproduces": bool(matched["reproduces"]),
                    "distance": float(matched["distance"]),
                    "glyphs_per_word": float(bif["glyphs_per_word"]),
                    "lam5": float(cell["crossfit_W5"]["lam"]),
                }
            )
    return rows


def _band(measures: list[dict]) -> dict[str, list[float]]:
    out = {}
    for hand in H.HANDS:
        vals = [r["S_interior"] for r in measures if r["hand"] == hand]
        out[hand] = [min(vals), max(vals)]
    return out


def _in_interval(value: float, lo: float, hi: float) -> bool:
    return lo <= value <= hi


def predict(measures: list[dict], fingerprints: list[dict], h39: list[dict], gen: dict) -> dict:
    bands = _band(measures)
    r1_rows = {}
    r1_pass = True
    for hand in H.HANDS:
        r1_rows[hand] = {}
        block = [r for r in fingerprints if r["hand"] == hand]
        for key in DKEYS:
            vals = [r["D"][key] for r in block]
            span = float(max(vals) - min(vals))
            limit = float(H20.DELTA[key])
            ok = span <= limit
            r1_pass = r1_pass and ok
            r1_rows[hand][key] = {
                "min": float(min(vals)),
                "max": float(max(vals)),
                "range": span,
                "delta": limit,
                "pass": ok,
            }
    scored = []
    for row in h39:
        lo, hi = bands[row["hand"]]
        inside_old = _in_interval(row["S"], OLD_BAND[0], OLD_BAND[1])
        inside_wide = _in_interval(row["S"], lo, hi)
        scored.append(
            {
                **row,
                "in_old_band": inside_old,
                "in_widened_band": inside_wide,
                "outside_old_inside_widened": (not inside_old) and inside_wide,
            }
        )
    n_rescue = sum(r["outside_old_inside_widened"] for r in scored)
    junctions = [r["junction"] for r in measures]
    junctions_interior = [r["junction_interior"] for r in measures]
    any_le = any(j <= 0.05 for j in junctions)
    above_gen = all(j > gen["orig_max"] for j in junctions)
    r3_pass = (not any_le) and above_gen and len(junctions) == 15 and gen["all_orig_le_0.004"]
    return {
        "R1": {"pass": r1_pass, "by_hand": r1_rows},
        "R2": {
            "pass": n_rescue >= 1,
            "n_in_old_band": int(sum(r["in_old_band"] for r in scored)),
            "n_in_widened_band": int(sum(r["in_widened_band"] for r in scored)),
            "n_outside_old_inside_widened": int(n_rescue),
            "cells": scored,
        },
        "R3": {
            "pass": r3_pass,
            "any_junction_le_0.05": any_le,
            "any_interior_junction_le_0.05": any(j <= 0.05 for j in junctions_interior),
            "junction_min": float(min(junctions)),
            "junction_max": float(max(junctions)),
            "junction_interior_min": float(min(junctions_interior)),
            "above_generator_orig": above_gen,
            "generator_orig_max": gen["orig_max"],
            "generator_ceiling": 0.004,
        },
        "widened_bands": bands,
    }


def _fmt(value: float, digits: int = 6) -> str:
    return f"{value:.{digits}f}"


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(row) + " |" for row in rows]
    return out


def _drops(measures: list[dict]) -> list[dict]:
    by = {(r["hand"], r["condition"]): r for r in measures}
    rows = []
    for hand in H.HANDS:
        for kind, split, join in (("zl", "zl_split", "zl_join"), ("rf", "rf_split", "rf_join")):
            a = by[(hand, split)]["junction"]
            b = by[(hand, join)]["junction"]
            rows.append(
                {
                    "hand": hand,
                    "pair": kind,
                    "junction_split": a,
                    "junction_join": b,
                    "relative_drop": float((a - b) / a),
                }
            )
    return rows


def write_figure(path: Path, measures: list[dict], pred: dict) -> None:
    by = {(r["hand"], r["condition"]): r for r in measures}
    conds = list(H.CONDITIONS)
    fig, axes = plt.subplots(1, 3, figsize=(12.4, 4.5))

    ax = axes[0]
    ax.axhspan(OLD_BAND[0], OLD_BAND[1], color="#ececec", zorder=0)
    for hand in H.HANDS:
        ys = [by[(hand, cond)]["S_interior"] for cond in conds]
        ax.plot(range(len(conds)), ys, marker="o", color=COLORS[hand], label=hand)
    ax.set_xticks(range(len(conds)), conds, rotation=30, ha="right")
    ax.set_ylabel("interior space predictability")
    ax.set_title("S_interior")
    ys_all = [r["S_interior"] for r in measures]
    pad = 0.015
    ax.set_ylim(min(OLD_BAND[0], min(ys_all)) - pad, max(OLD_BAND[1], max(ys_all)) + 0.055)
    ax.legend(frameon=False, loc="upper center", ncol=3)

    ax = axes[1]
    ax.axhline(0.05, color="black", lw=0.8, linestyle="--")
    x = np.arange(len(conds))
    width = 0.25
    for i, hand in enumerate(H.HANDS):
        ys = [by[(hand, cond)]["junction"] for cond in conds]
        ax.bar(x + (i - 1) * width, ys, width, color=COLORS[hand], label=hand)
    ax.set_xticks(x, conds, rotation=30, ha="right")
    ax.set_ylabel("junction excess")
    ax.set_title("Full-line junction")

    ax = axes[2]
    x = np.arange(len(DKEYS))
    for i, hand in enumerate(H.HANDS):
        vals = [pred["R1"]["by_hand"][hand][key]["range"] / H20.DELTA[key] for key in DKEYS]
        ax.bar(x + (i - 1) * width, vals, width, color=COLORS[hand], label=hand)
    ax.axhline(1.0, color="black", lw=0.8)
    ax.set_xticks(x, DKEYS)
    ax.set_ylabel("range / DELTA")
    ax.set_title("Fingerprint spread")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def write_readme(measures: list[dict], fingerprints: list[dict], pred: dict, drops: list[dict], gen: dict) -> None:
    bands = pred["widened_bands"]
    r1, r2, r3 = pred["R1"], pred["R2"], pred["R3"]
    verdict = lambda ok: "pass" if ok else "fail"
    lines = [
        "# h40: transcription sensitivity of the space, junction, and fingerprint targets",
        "",
        "Pre-registration: [PREREG.md](PREREG.md). Five readings of hands 1A, 2B and 3B "
        "(ZL3b split, ZL3b join, IT2a, RF1b split, RF1b join). Space predictability and junction "
        "excess use the first 10,326 paragraph tokens. The fingerprint is the bifolium D1–D5 "
        "score on up to 10,500 tokens. No reading of the manuscript is proposed.",
        "",
        "## Predictions",
        "",
        *_table(
            ["prediction", "result"],
            [
                ["R1", verdict(r1["pass"])],
                ["R2", verdict(r2["pass"])],
                ["R3", verdict(r3["pass"])],
            ],
        ),
        "",
        "R1 asks whether, for every hand and every one of D1–D5, the range across the five "
        f"readings is at most `h20_lib.DELTA`. Result: {verdict(r1['pass'])}.",
        "",
        "R2 asks whether at least one of the nine h39 variant-A cells has space predictability "
        f"outside [0.72, 0.80] and inside its hand's widened band. "
        f"{r2['n_outside_old_inside_widened']} of 9 do. "
        f"{r2['n_in_old_band']} of 9 sit in the old band and {r2['n_in_widened_band']} of 9 sit in the widened band. "
        f"Result: {verdict(r2['pass'])}.",
        "",
        "R3 asks whether full-line junction excess stays above 0.05 in all 15 cells and above the "
        f"stored h33 generator junctions (orig maximum {_fmt(gen['orig_max'], 6)}, all of those orig values ≤ 0.004). "
        f"Minimum junction is {_fmt(r3['junction_min'])}. "
        f"Any cell ≤ 0.05: {str(r3['any_junction_le_0.05']).lower()}. Result: {verdict(r3['pass'])}.",
        "",
        "## Widened bands",
        "",
        "Old band, every hand: [0.72, 0.80]. Widened band: min and max of S_interior across the five readings.",
        "",
        *_table(
            ["hand", "S_interior min", "S_interior max", "width"],
            [
                [hand, _fmt(lo), _fmt(hi), _fmt(hi - lo)]
                for hand, (lo, hi) in bands.items()
            ],
        ),
        "",
        "## Space and junction",
        "",
        "S is entropy removed by `h33_lib.space_predict`. Junction is `h33_lib.junction` with seed 33. "
        "The R3 junction is the full-line value (lines of at least two words). "
        "`J_interior` is the same function on line-interior words.",
        "",
        *_table(
            ["hand", "condition", "S_full", "S_interior", "junction", "J_interior"],
            [
                [
                    r["hand"],
                    r["condition"],
                    _fmt(r["S_full"]),
                    _fmt(r["S_interior"]),
                    _fmt(r["junction"]),
                    _fmt(r["junction_interior"]),
                ]
                for r in measures
            ],
        ),
        "",
        "Relative drop in full-line junction when uncertain spaces are joined, `(split - join) / split`:",
        "",
        *_table(
            ["hand", "pair", "split", "join", "relative drop"],
            [
                [r["hand"], r["pair"], _fmt(r["junction_split"]), _fmt(r["junction_join"]), _fmt(r["relative_drop"])]
                for r in drops
            ],
        ),
        "",
        "## Fingerprint",
        "",
        "Bifolium folds only, cell kind `ctrl`, EVA segmentation. D3 is cross-fitted λ at W=5. "
        "Match counts use `h20_lib.match` against the three committed MS cells.",
        "",
        *_table(
            ["hand", "condition", "D1", "D2", "D3", "D4", "D5", "match"],
            [
                [
                    r["hand"],
                    r["condition"],
                    _fmt(r["D"]["D1"]),
                    _fmt(r["D"]["D2"]),
                    _fmt(r["D"]["D3"]),
                    _fmt(r["D"]["D4"]),
                    _fmt(r["D"]["D5"]),
                    f"{r['n_match']}/5",
                ]
                for r in fingerprints
            ],
        ),
        "",
        *_table(
            ["hand", "statistic", "min", "max", "range", "DELTA", "within DELTA"],
            [
                [
                    hand,
                    key,
                    _fmt(block["min"]),
                    _fmt(block["max"]),
                    _fmt(block["range"]),
                    _fmt(block["delta"]),
                    "yes" if block["pass"] else "no",
                ]
                for hand, stats in r1["by_hand"].items()
                for key, block in stats.items()
            ],
        ),
        "",
        "## h39 variant A against the bands",
        "",
        "S is the stored variant-A space predictability (the table column S; full precision from the "
        "row that was printed to three decimals). The old band is [0.72, 0.80].",
        "",
        *_table(
            ["hand", "gen", "S", "S table", "old band", "widened band"],
            [
                [
                    r["hand"],
                    r["gen"],
                    _fmt(r["S"]),
                    _fmt(r["S_table"], 3),
                    "in" if r["in_old_band"] else "out",
                    "in" if r["in_widened_band"] else "out",
                ]
                for r in r2["cells"]
            ],
        ),
        "",
        "## Figure",
        "",
        "![transcription targets](figures/transcription_targets.png)",
        "",
        "Grey band on the left is [0.72, 0.80]. The dashed line on the junction panel is 0.05. "
        "The line on the fingerprint panel is range = DELTA.",
        "",
        "Run: `python3 test_h40.py` (unit tests), `python3 run_h40.py`, `python3 summarise.py`.",
        "",
    ]
    (HERE / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    measures = load_measures()
    reference = ms_rows()
    fingerprints = load_fingerprints(reference)
    h39 = load_h39_a()
    gen = generator_junctions()
    pred = predict(measures, fingerprints, h39, gen)
    drops = _drops(measures)
    numbers = {
        "old_band": list(OLD_BAND),
        "widened_bands": pred["widened_bands"],
        "D_ranges": pred["R1"]["by_hand"],
        "deltas": {k: float(H20.DELTA[k]) for k in DKEYS},
        "h39_in_old_band": pred["R2"]["n_in_old_band"],
        "h39_in_widened_band": pred["R2"]["n_in_widened_band"],
        "h39_outside_old_inside_widened": pred["R2"]["n_outside_old_inside_widened"],
        "junction_min": pred["R3"]["junction_min"],
        "junction_max": pred["R3"]["junction_max"],
        "junction_interior_min": pred["R3"]["junction_interior_min"],
        "any_junction_le_0.05": pred["R3"]["any_junction_le_0.05"],
        "any_interior_junction_le_0.05": pred["R3"]["any_interior_junction_le_0.05"],
        "generator_orig_max": gen["orig_max"],
        "generator_max_at_most_0.004": gen["max_at_most_0.004"],
        "generator_ceiling": 0.004,
        "generator_orig_all_le_0.004": gen["all_orig_le_0.004"],
        "junction_join_drops": drops,
        "measures": measures,
        "fingerprints": fingerprints,
        "h39_cells": pred["R2"]["cells"],
        "generator_orig": gen["orig"],
    }
    summary = {
        "complete": True,
        "predictions": {"R1": pred["R1"], "R2": pred["R2"], "R3": pred["R3"]},
        "numbers": numbers,
    }
    status = {
        "complete": True,
        "predictions": {"R1": pred["R1"]["pass"], "R2": pred["R2"]["pass"], "R3": pred["R3"]["pass"]},
        "numbers": {
            "old_band": numbers["old_band"],
            "widened_bands": numbers["widened_bands"],
            "D_ranges": numbers["D_ranges"],
            "deltas": numbers["deltas"],
            "h39_in_old_band": numbers["h39_in_old_band"],
            "h39_in_widened_band": numbers["h39_in_widened_band"],
            "h39_outside_old_inside_widened": numbers["h39_outside_old_inside_widened"],
            "junction_min": numbers["junction_min"],
            "junction_max": numbers["junction_max"],
            "any_junction_le_0.05": numbers["any_junction_le_0.05"],
            "generator_orig_max": numbers["generator_orig_max"],
            "generator_max_at_most_0.004": numbers["generator_max_at_most_0.004"],
            "generator_ceiling": numbers["generator_ceiling"],
            "generator_orig_all_le_0.004": numbers["generator_orig_all_le_0.004"],
        },
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (RESULTS / "STATUS.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    write_figure(HERE / "figures" / "transcription_targets.png", measures, pred)
    write_readme(measures, fingerprints, pred, drops, gen)
    print(json.dumps(status["predictions"], indent=2))
    print(json.dumps(status["numbers"]["widened_bands"], indent=2))
    print("h39 old/widened/rescue", status["numbers"]["h39_in_old_band"], status["numbers"]["h39_in_widened_band"], status["numbers"]["h39_outside_old_inside_widened"])
    print("junction min", status["numbers"]["junction_min"], "any<=0.05", status["numbers"]["any_junction_le_0.05"])


if __name__ == "__main__":
    main()
