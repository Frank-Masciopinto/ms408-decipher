"""Run h28 serially: one worker, skip finished cells, delete token dumps after each cell.

No translation claims. Does not write data/mechanisms/naibbe_tables.csv.
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
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for rel in (
    "src",
    "hypotheses/h20_generators_vs_italian",
    "hypotheses/h19_heldout_likelihood",
    "hypotheses/h25_neutral_hybrid_cipher",
    "hypotheses/h24_neutral_cipher_robustness",
):
    sys.path.insert(0, str(ROOT / rel))

import h24_lib  # noqa: E402
import h28_lib as L  # noqa: E402
import run_h20  # noqa: E402
from fetch_italian import load_italian  # noqa: E402
from h25_lib import NH  # noqa: E402

RES = HERE / "results"
NTOK = 10500
LINE = 9


def delete_tokens(name: str) -> None:
    for path in RES.glob(f"tokens_{name}_*.csv.gz"):
        path.unlink()


def finished(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 100:
        return False
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    schemes = meta.get("schemes")
    lam = meta.get("crossfit_W5")
    return isinstance(schemes, dict) and "bifolium" in schemes and "quire" in schemes and isinstance(lam, dict) and "lam" in lam


def score_cell(cond: str, s: int, rows0: list[dict], plain: list[str], seg) -> None:
    name = L.cell_name(cond, s)
    dest = RES / f"cell_{name}.json"
    if finished(dest):
        delete_tokens(name)
        print(f"skip {name}", flush=True)
        return
    permuted, changed = L.permute(rows0, cond, s, seg)
    L.assert_permutation(cond, rows0, permuted, seg)
    path = L.table_path(cond, s)
    L.write_table(path, permuted)
    if L.load_rows(path) != permuted:
        raise SystemExit(f"wrote {path.name} but did not read the same rows back")
    if run_h20.NTOK != NTOK:
        raise SystemExit(f"run_h20.NTOK is {run_h20.NTOK}, expected {NTOK}")
    cipher = NH(path, 6, "naibbe", 17 / 36)
    toks = [str(tok) for tok in cipher.encrypt(plain, seed=s, n_words_out=2 * NTOK)]
    if len(toks) != 2 * NTOK:
        raise SystemExit(f"{name} encrypted to {len(toks)} words")
    labs = ["#"] * len(toks)
    toks, labs, n_swap = h24_lib.copy_variant(toks, labs, 0.05, "swap", seed=100 * s + 17, seg=seg)
    if len(toks) != 2 * NTOK:
        raise SystemExit(f"{name} copy layer changed the token count")
    lines = [toks[i:i + LINE] for i in range(0, len(toks), LINE)]
    cell = run_h20.lines_to_cell(lines, name, "ctrl", "eva")
    fit = {
        "src": "it_boccaccio",
        "cond": cond,
        "seed": s,
        "copy": "swap",
        "c": 0.05,
        "n_swap": n_swap,
        "signal_share": sum(x is not None for x in labs[:NTOK]) / NTOK,
    }
    if changed is not None:
        fit["unit_change_share"] = changed / len(rows0)
        fit["unit_changed"] = changed
    cell["fit"] = fit
    print(f"score {name} n_swap={n_swap} signal={fit['signal_share']:.4f}", flush=True)
    t0 = time.perf_counter()
    run_h20.R = RES
    run_h20.run_cell((name, cell))
    if not finished(dest):
        raise SystemExit(f"{name} did not leave a finished cell json")
    delete_tokens(name)
    print(f"done {name} {time.perf_counter() - t0:.1f}s", flush=True)


def main() -> None:
    RES.mkdir(parents=True, exist_ok=True)
    L.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    original = L.NAIBBE.read_bytes()
    rows0 = L.load_rows()
    L.validate_real(rows0)
    seg = L.segmenter()
    L.assert_roundtrip(rows0, seg)
    report = L.unit_change_report(rows0, seg)
    (RES / "unit_change.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"unit_change_share {report['unit_change_share']:.6f} "
        f"({report['changed']}/{report['n']})",
        flush=True,
    )
    plain = load_italian("it_boccaccio")
    print(f"boccaccio_tokens {len(plain)}", flush=True)
    run_h20.R = RES
    for cond in L.CONDITIONS:
        for s in L.SEEDS:
            score_cell(cond, s, rows0, plain, seg)
    if L.NAIBBE.read_bytes() != original:
        raise SystemExit("original Naibbe table changed during the run")


if __name__ == "__main__":
    rt_path = RES / "runtime_sec.json"
    prev = 0.0
    if rt_path.exists():
        prev = float(json.loads(rt_path.read_text(encoding="utf-8"))["runtime_sec"])
    t0 = time.perf_counter()
    try:
        main()
    finally:
        RES.mkdir(parents=True, exist_ok=True)
        elapsed = prev + (time.perf_counter() - t0)
        rt_path.write_text(json.dumps({"runtime_sec": elapsed}) + "\n", encoding="utf-8")
        print(f"runtime_sec {elapsed:.1f}", flush=True)
