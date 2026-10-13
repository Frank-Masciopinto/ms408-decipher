"""Summarise h29: predictions R1, T1, T2, the bifolium grid, and the D4 figure."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h20_generators_vs_italian"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import h20_lib as H20

sys.path.insert(0, str(HERE))

R = HERE / "results"
R20 = ROOT / "hypotheses" / "h20_generators_vs_italian" / "results"
HANDS = ("1A", "2B", "3B")
LENGTHS = (1, 2, 3, 4, 5)
POOLS = (8, 16, 32, 64, 128)
D4_LINE = -0.07
DECODABLE_LINE = 0.8


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ms_rows():
    rows = []
    for hand in HANDS:
        model = _load(R20 / f"cell_MS_{hand}.json")
        scheme = model["schemes"]["bifolium"]
        rows.append(H20.dstats(scheme["bits"], scheme["glyphs_per_word"], model["crossfit_W5"]["lam"]))
    return rows


def grid_frame(ms):
    rows = []
    for path in sorted(R.glob("cell_D4_*.json")):
        model = _load(path)
        scheme = model["schemes"]["bifolium"]
        stats = H20.dstats(scheme["bits"], scheme["glyphs_per_word"], model["crossfit_W5"]["lam"])
        matched = H20.match(stats, ms)
        fit = model.get("fit") or {}
        row = {
            "cell": model["cell"],
            "L": int(fit["L"]),
            "V": int(fit["V"]),
            "seed": int(fit["seed"]),
            "suffix_pool": int(fit["suffix_pool"]),
            "decodable": float(fit["decodable"]),
            "n_tokens": int(model["n_tokens"]),
            "glyphs_per_word": float(scheme["glyphs_per_word"]),
        }
        row.update(stats)
        row.update({f"m_{key}": value for key, value in matched.items()})
        rows.append(row)
    frame = pd.DataFrame(rows).sort_values(["L", "V"]).reset_index(drop=True)
    expected = {(code_len, pool_v) for code_len in LENGTHS for pool_v in POOLS}
    got = set(zip(frame["L"].tolist(), frame["V"].tolist()))
    if got != expected or len(frame) != 25:
        raise SystemExit(f"expected the 25-cell grid, found {sorted(got)}")
    return frame


def predictions(reg, frame):
    distance = reg["h26"]["m_distance"]
    abs_rho = {key: abs(value) for key, value in distance.items()}
    top = max(abs_rho, key=abs_rho.get)
    unique = sum(value == abs_rho[top] for value in abs_rho.values()) == 1
    r1 = {
        "spearman_m_distance": distance,
        "spearman_D4": reg["h26"]["D4"],
        "n": reg["h26"]["n"],
        "top": top,
        "pass": bool(top == "mean_len" and unique),
    }
    high = frame[frame["decodable"] >= DECODABLE_LINE]
    reached = high[high["D4"] >= D4_LINE]
    cells = [
        {"cell": r.cell, "L": int(r.L), "V": int(r.V), "decodable": float(r.decodable), "D4": float(r.D4)}
        for r in high.sort_values(["D4", "L", "V"], ascending=[False, True, True]).itertuples(index=False)
    ]
    t1 = {
        "decodable_min": DECODABLE_LINE,
        "D4_min": D4_LINE,
        "n_decodable_ge_0.8": int(len(high)),
        "n_also_D4_ge": int(len(reached)),
        "cells": cells,
        "best_D4": None if high.empty else float(high["D4"].max()),
        "pass": bool(len(reached) == 0),
    }
    rho = float(spearmanr(frame["V"], frame["D4"]).correlation)
    t2 = {"rho_D4_against_V": rho, "n": int(len(frame)), "pass": bool(rho < 0)}
    return {"R1": r1, "T1": t1, "T2": t2}


def write_figure(frame):
    fig_dir = HERE / "figures"
    fig_dir.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    for code_len, group in frame.groupby("L"):
        group = group.sort_values("V")
        ax.plot(group["V"], group["D4"], marker="o", label=f"L = {int(code_len)}")
    high = frame[frame["decodable"] >= DECODABLE_LINE]
    if not high.empty:
        ax.scatter(high["V"], high["D4"], marker="*", s=160, c="k", zorder=5, label="decodable ≥ 0.8")
    ax.axhline(D4_LINE, color="0.4", ls="--", lw=1, label="D4 = −0.07")
    ax.set_xticks(list(POOLS))
    ax.set_xlabel("suffix pool size V")
    ax.set_ylabel("D4")
    ax.legend(fontsize=8, loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    fig.tight_layout()
    fig.savefig(fig_dir / "d4_grid.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def write_outputs():
    reg = _load(R / "regression.json")
    frame = grid_frame(ms_rows())
    pred = predictions(reg, frame)
    frame.to_csv(R / "grid_bifolium.csv", index=False)
    with open(R / "summary.json", "w", encoding="utf-8") as f:
        json.dump({"predictions": pred}, f, indent=1)
        f.write("\n")
    write_figure(frame)
    return pred


def write_status(tests_passed):
    reg = _load(R / "regression.json")
    summary = _load(R / "summary.json")
    pred = summary["predictions"]
    frame = pd.read_csv(R / "grid_bifolium.csv")
    high = frame[frame["decodable"] >= DECODABLE_LINE].sort_values(["D4", "L", "V"], ascending=[False, True, True])
    cells = [
        {"cell": r.cell, "D4": float(r.D4), "decodable": float(r.decodable), "L": int(r.L), "V": int(r.V)}
        for r in high.itertuples(index=False)
    ]
    runtime_path = R / "runtime_acc.txt"
    runtime = float(runtime_path.read_text()) if runtime_path.exists() else None
    status = {
        "R1_pass": bool(pred["R1"]["pass"]),
        "T1_pass": bool(pred["T1"]["pass"]),
        "T2_pass": bool(pred["T2"]["pass"]),
        "spearman": {"h26": reg["h26"], "h25": reg["h25"]},
        "decodable_ge_0.8": cells,
        "best_D4_among_decodable_ge_0.8": None if not cells else float(high["D4"].max()),
        "tests_passed": bool(tests_passed),
        "runtime_sec": runtime,
    }
    with open(R / "STATUS.json", "w", encoding="utf-8") as f:
        json.dump(status, f, indent=1)
        f.write("\n")
    return status


if __name__ == "__main__":
    out = write_outputs()
    print(json.dumps(out, indent=1))
