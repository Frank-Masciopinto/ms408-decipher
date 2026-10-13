"""Summarise h27 bifolium and quire fingerprints. No translation claims."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h20_generators_vs_italian"))
sys.path.insert(0, str(ROOT / "src"))
import h20_lib as L20  # noqa: E402

RES = HERE / "results"
MS_DIR = ROOT / "hypotheses" / "h20_generators_vs_italian" / "results"
HANDS = ("1A", "2B", "3B")
PLAINS = ("real", "shuffle", "zipf")
ANCHOR = 3.43
TOL = 0.5
MARGIN = 2.0
K = list(L20.DELTA)


def _json_default(value):
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(type(value))


def t_interval(values) -> tuple[float, float, float]:
    x = np.asarray(list(values), dtype=float)
    n = int(x.size)
    mean = float(x.mean())
    if n < 2:
        return mean, float("nan"), float("nan")
    half = float(stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n))
    return mean, mean - half, mean + half


def fingerprint_row(path: Path, scheme: str, ms_rows: list[dict]) -> dict:
    meta = json.loads(path.read_text())
    scheme_block = meta["schemes"][scheme]
    stats_row = L20.dstats(scheme_block["bits"], scheme_block["glyphs_per_word"], meta["crossfit_W5"]["lam"])
    fit = meta.get("fit") or {}
    cell = meta["cell"]
    if "plaintext" in fit:
        plain, seed = fit["plaintext"], int(fit["seed"])
    else:
        body = cell.split("P_boccaccio_", 1)[1]
        plain, seed_s = body.rsplit("_s", 1)
        seed = int(seed_s)
    matched = L20.match(stats_row, ms_rows)
    return dict(cell=cell, plaintext=plain, seed=seed, **stats_row, **{f"m_{k}": v for k, v in matched.items()})


def group_table(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for plain in PLAINS:
        part = frame[frame.plaintext == plain]
        mean, lo, hi = t_interval(part.m_distance)
        row = dict(
            plaintext=plain,
            n=int(len(part)),
            dist_mean=mean,
            dist_lo=lo,
            dist_hi=hi,
            rate4=float((part.m_n_match >= 4).mean()),
            rate5=float(part.m_reproduces.mean()),
            n_match_mean=float(part.m_n_match.mean()),
        )
        for key in K:
            row[key] = float(part[key].mean())
        rows.append(row)
    return pd.DataFrame(rows)


def predictions(groups: pd.DataFrame) -> dict:
    by = groups.set_index("plaintext")
    d_real = float(by.loc["real", "dist_mean"])
    d_shuffle = float(by.loc["shuffle", "dist_mean"])
    d_zipf = float(by.loc["zipf", "dist_mean"])
    ci = {plain: [float(by.loc[plain, "dist_lo"]), float(by.loc[plain, "dist_hi"])] for plain in PLAINS}
    p1 = bool(d_zipf <= d_real + MARGIN)
    p2 = bool(d_shuffle <= d_real + MARGIN and d_zipf > d_real + MARGIN)
    p3 = bool(abs(d_real - ANCHOR) <= TOL)
    return {
        "P1": {"pass": p1, "rule": "d(zipf) <= d(real) + 2", "d_real": d_real, "d_zipf": d_zipf, "threshold": d_real + MARGIN, "ci95": ci},
        "P2": {
            "pass": p2,
            "rule": "d(shuffle) <= d(real) + 2 and d(zipf) > d(real) + 2",
            "d_real": d_real,
            "d_shuffle": d_shuffle,
            "d_zipf": d_zipf,
            "threshold": d_real + MARGIN,
            "ci95": ci,
        },
        "P3": {"pass": p3, "rule": "d(real) within 0.5 of 3.43", "d_real": d_real, "anchor": ANCHOR, "tolerance": TOL, "abs_delta": abs(d_real - ANCHOR), "ci95": ci["real"]},
        "p1_p2_interpreted": p3,
        "d_real": d_real,
        "d_shuffle": d_shuffle,
        "d_zipf": d_zipf,
        "ci95": ci,
        "rate4": {plain: float(by.loc[plain, "rate4"]) for plain in PLAINS},
    }


def plot_bifolium(frame: pd.DataFrame, groups: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    by = groups.set_index("plaintext")
    for i, plain in enumerate(PLAINS):
        part = frame[frame.plaintext == plain]
        x = np.full(len(part), i, dtype=float) + (part.seed.to_numpy() - 3) * 0.045
        ax.scatter(x, part.m_distance, s=36, zorder=3)
        mean = float(by.loc[plain, "dist_mean"])
        lo = float(by.loc[plain, "dist_lo"])
        hi = float(by.loc[plain, "dist_hi"])
        ax.errorbar([i], [mean], yerr=[[max(0.0, mean - lo)], [max(0.0, hi - mean)]], fmt="D", color="k", capsize=4, zorder=4)
    d_real = float(by.loc["real", "dist_mean"])
    ax.axhline(ANCHOR, color="0.35", ls="--", lw=1, label="h26 anchor 3.43")
    ax.axhline(d_real + MARGIN, color="C3", ls=":", lw=1, label="d(real)+2")
    ax.set_xticks(range(len(PLAINS)), list(PLAINS))
    ax.set_xlabel("plaintext")
    ax.set_ylabel("bifolium distance")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> None:
    cells = sorted(RES.glob("cell_P_boccaccio_*.json"))
    if len(cells) != 15:
        raise SystemExit(f"expected 15 cell jsons, found {len(cells)}")
    out = {"n_cells": len(cells)}
    bif = None
    bif_groups = None
    for scheme in ("bifolium", "quire"):
        ms_rows = []
        for hand in HANDS:
            meta = json.loads((MS_DIR / f"cell_MS_{hand}.json").read_text())
            block = meta["schemes"][scheme]
            ms_rows.append(L20.dstats(block["bits"], block["glyphs_per_word"], meta["crossfit_W5"]["lam"]))
        frame = pd.DataFrame([fingerprint_row(path, scheme, ms_rows) for path in cells])
        frame = frame.sort_values(["plaintext", "seed"]).reset_index(drop=True)
        counts = frame.groupby("plaintext").size()
        if set(counts.index) != set(PLAINS) or int(counts.min()) != 5:
            raise SystemExit(f"{scheme} cells are not 5 seeds × 3 plaintexts: {counts.to_dict()}")
        frame.to_csv(RES / f"fingerprints_{scheme}.csv", index=False)
        groups = group_table(frame)
        groups.to_csv(RES / f"groups_{scheme}.csv", index=False)
        out[scheme] = dict(
            groups=groups.to_dict("records"),
            seeds=frame[["cell", "plaintext", "seed", "m_distance", "m_n_match", "m_reproduces", *K]].to_dict("records"),
        )
        if scheme == "bifolium":
            bif = frame
            bif_groups = groups
    if bif is None or bif_groups is None:
        raise SystemExit("bifolium table was not built")
    pred = predictions(bif_groups)
    out["predictions"] = pred
    (RES / "summary.json").write_text(json.dumps(out, indent=1, default=_json_default) + "\n")
    plot_bifolium(bif, bif_groups, HERE / "figures" / "plaintext_ablation.png")
    print(bif_groups.round(4).to_string(index=False))
    print(json.dumps(pred, indent=1))


if __name__ == "__main__":
    main()
