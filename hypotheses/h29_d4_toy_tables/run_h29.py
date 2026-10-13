"""Run h29. Part 1 writes results/regression.json, then 25 bifolium cells, one at a time.

Quire folds are not scored. Token tables are removed after each cell.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h25_neutral_hybrid_cipher"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h20_generators_vs_italian"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h19_heldout_likelihood"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import numpy as np
import pandas as pd

import fetch_italian as FI
import h20_lib as H20
import h25_lib as H25
import h29_lib as H
import run_h19 as R19
import run_h20 as R20

sys.path.insert(0, str(HERE))

R = HERE / "results"
TD = HERE / "tables"
R20.R = R
NTOK = R19.NTOK
LENGTHS = (1, 2, 3, 4, 5)
POOLS = (8, 16, 32, 64, 128)
SEED = 1
SKIP_BITS = ("page", "fold", "init", "glyphs")


def _write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, default=float)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _bump_runtime(seconds):
    path = R / "runtime_acc.txt"
    prev = float(path.read_text()) if path.exists() else 0.0
    path.write_text(f"{prev + seconds:.3f}\n")


def _delete_tokens():
    for path in R.glob("tokens_*.csv.gz"):
        path.unlink()


def part1():
    report = H.spearman_report(H.H26_CSV, H.H25_CSV, H.H24_CSV)
    _write_json(R / "regression.json", report)
    print("wrote", R / "regression.json", flush=True)
    return report


def cell_name(code_len, pool_v):
    return f"D4_L{code_len}_V{pool_v}_s{SEED}"


def build_cell(plain, code_len, pool_v):
    name = cell_name(code_len, pool_v)
    path = H.write_toy_tables(TD / f"toy_L{code_len}_V{pool_v}_s{SEED}.csv", code_len, pool_v, SEED)
    cipher = H25.NH(path, 6, "naibbe", 17 / 36)
    toks = [str(t) for t in cipher.encrypt(plain, seed=SEED, n_words_out=2 * NTOK)]
    if len(toks) < NTOK:
        raise RuntimeError(f"{name} produced {len(toks)} words, need {NTOK}")
    labs = ["#"] * NTOK
    dec = H25.decodable_share(cipher, toks[:NTOK], labs)
    cell = R20.lines_to_cell([toks[i:i + 9] for i in range(0, len(toks), 9)], name, "ctrl", "char")
    cell["fit"] = {
        "L": code_len,
        "V": pool_v,
        "seed": SEED,
        "decodable": dec,
        "suffix_pool": min(pool_v, H.ALPHABET_N ** code_len),
        "src": "it_boccaccio",
        "render": "char",
    }
    return name, cell


def score_bifolium(name, cell):
    """Same bifolium models as run_h20.run_cell. No quire scheme, no W=100 cross-fit."""
    rng = np.random.default_rng(19)
    pages = cell["pages"]
    res = {
        "cell": name,
        "kind": cell["kind"],
        "n_tokens": sum(len(p["words"]) for p in pages),
        "fit": cell.get("fit"),
        "schemes": {},
    }
    folds = R19.group_folds(pages, "bif", 5)
    tok_path = R / f"tokens_{name}_bifolium.csv.gz"
    parts, extras = [], []
    try:
        for fi_, (tr, te) in enumerate(folds):
            print(f"  {name} fold {fi_ + 1}/{len(folds)}", flush=True)
            trp = [pages[i] for i in tr]
            tep = [pages[i] for i in te]
            bt, ex = R19.run_split(trp, tep, cell, rng)
            extras.append(ex)
            pc = H20.PosCharLM().fit([w for p in trp for w in p["words"]])
            bt["PCLM"] = np.array([pc.logp(w) for p in tep for w in p["words"]])
            df = pd.DataFrame(bt)
            df["page"] = [p["id"] for p in tep for _ in p["words"]]
            df["fold"] = fi_
            df["init"] = [x for p in tep for x in p["init"]]
            df["glyphs"] = [len(w) + 1 for p in tep for w in p["words"]]
            parts.append(df)
        tok = pd.concat(parts, ignore_index=True)
        tok.to_csv(tok_path, index=False)
        res["schemes"]["bifolium"] = {
            "bits": {c: float(-tok[c].mean()) for c in tok.columns if c not in SKIP_BITS},
            "glyphs_per_word": float(tok.glyphs.mean()),
            "extras": extras,
        }
        res["crossfit_W5"] = R19.crossfit_lambda(cell, folds, 5, rng)
        _write_json(R / f"cell_{name}.json", res)
    finally:
        _delete_tokens()
    return name


def part2(plain):
    for code_len in LENGTHS:
        for pool_v in POOLS:
            name = cell_name(code_len, pool_v)
            dest = R / f"cell_{name}.json"
            if dest.exists():
                print("skip", name, flush=True)
                continue
            print("start", name, flush=True)
            t0 = time.perf_counter()
            try:
                _name, cell = build_cell(plain, code_len, pool_v)
                score_bifolium(_name, cell)
            finally:
                _bump_runtime(time.perf_counter() - t0)
            print("done", name, flush=True)


def main():
    R.mkdir(exist_ok=True)
    TD.mkdir(exist_ok=True)
    t0 = time.perf_counter()
    try:
        part1()
        plain = FI.load_italian("it_boccaccio")
    finally:
        _bump_runtime(time.perf_counter() - t0)
    part2(plain)


if __name__ == "__main__":
    main()
