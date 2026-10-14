"""Score each hand x transcription: space, junction, then one bifolium fingerprint cell."""
from __future__ import annotations

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "hypotheses" / "h20_generators_vs_italian"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h19_heldout_likelihood"))

import h40_lib as H  # noqa: E402
import pandas as pd  # noqa: E402
import run_h20  # noqa: E402

RESULTS = HERE / "results"
H33 = ROOT / "hypotheses" / "h33_word_boundary_resegmentation" / "results"
_DROP = ("page", "fold", "init", "glyphs")


def _plain(obj):
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _plain(obj.tolist())
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.floating, float)):
        return float(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if obj is None:
        return None
    return obj


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(_plain(obj), indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def _log(msg: str) -> None:
    print(msg, flush=True)
    with (RESULTS / "run.log").open("a", encoding="utf-8") as fh:
        fh.write(msg + "\n")


def _delete_token_dumps() -> None:
    for path in RESULTS.glob("tokens_*.csv.gz"):
        path.unlink()


def cell_complete(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    bif = data.get("schemes", {}).get("bifolium")
    lam = data.get("crossfit_W5", {}).get("lam")
    return bool(bif and bif.get("bits") and lam is not None and "quire" not in data.get("schemes", {}))


def run_cell(args):
    """Bifolium half of h20 run_cell: folds, PosCharLM, crossfit_lambda W=5. No quire."""
    name, cell = args
    run_h20.R = RESULTS
    rng = np.random.default_rng(19)
    pages = cell["pages"]
    res = {
        "cell": name,
        "kind": cell["kind"],
        "n_tokens": sum(len(p["words"]) for p in pages),
        "fit": cell.get("fit"),
        "schemes": {},
    }
    scheme, key = "bifolium", "bif"
    folds = run_h20.R19.group_folds(pages, key, 5)
    tok = []
    extras = []
    for fi_, (tr, te) in enumerate(folds):
        trp = [pages[i] for i in tr]
        tep = [pages[i] for i in te]
        bt, ex = run_h20.R19.run_split(trp, tep, cell, rng)
        extras.append(ex)
        pc = run_h20.L.PosCharLM().fit([w for p in trp for w in p["words"]])
        bt["PCLM"] = np.array([pc.logp(w) for p in tep for w in p["words"]])
        frame = pd.DataFrame(bt)
        frame["page"] = [p["id"] for p in tep for _ in p["words"]]
        frame["fold"] = fi_
        frame["init"] = [x for p in tep for x in p["init"]]
        frame["glyphs"] = [len(w) + 1 for p in tep for w in p["words"]]
        tok.append(frame)
    tok = pd.concat(tok, ignore_index=True)
    tok.to_csv(run_h20.R / f"tokens_{name}_{scheme}.csv.gz", index=False)
    res["schemes"][scheme] = dict(
        bits={c: float(-tok[c].mean()) for c in tok.columns if c not in _DROP},
        glyphs_per_word=float(tok.glyphs.mean()),
        extras=extras,
    )
    res["crossfit_W5"] = run_h20.R19.crossfit_lambda(cell, folds, 5, rng)
    _write(run_h20.R / f"cell_{name}.json", res)
    return name


def _check_zl_split(hand: str, got: dict) -> None:
    ref = json.loads((H33 / f"c_{hand}.json").read_text(encoding="utf-8"))
    expect = {
        "S_full": ref["full"]["space"]["entropy_removed"],
        "S_interior": ref["interior"]["space"]["entropy_removed"],
        "junction": ref["full"]["orig"]["M5_junction"],
        "junction_interior": ref["interior"]["orig"]["M5_junction"],
    }
    for key, value in expect.items():
        delta = abs(got[key] - value)
        _log(f"check {hand} zl_split {key} delta={delta:.3e}")
        if delta > 1e-6:
            raise SystemExit(f"{hand} zl_split {key} disagrees with h33 by {delta}")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    for hand in H.HANDS:
        for cond in H.CONDITIONS:
            name = f"{hand}_{cond}"
            t0 = time.perf_counter()
            lines = H.load_paragraphs(hand, cond)
            if not H.loader_restored():
                raise SystemExit(f"loader was not restored after {name}")
            got = H.measure(lines)
            got.update(hand=hand, condition=cond, n_tokens_loaded=int(sum(len(line) for line in lines)))
            _write(RESULTS / f"m_{name}.json", got)
            _log(
                f"measure {name} S_full={got['S_full']:.6f} S_interior={got['S_interior']:.6f} "
                f"J={got['junction']:.6f} J_int={got['junction_interior']:.6f} "
                f"n={got['n_tokens_loaded']} ({time.perf_counter() - t0:.1f}s)"
            )
            if cond == "zl_split":
                _check_zl_split(hand, got)
            cell_path = RESULTS / f"cell_{name}.json"
            if cell_complete(cell_path):
                _log(f"skip fingerprint {name}")
                _delete_token_dumps()
                continue
            if cell_path.exists():
                cell_path.unlink()
            t1 = time.perf_counter()
            run_h20.R = RESULTS
            cell = run_h20.lines_to_cell(lines, name, "ctrl", "eva")
            try:
                run_h20.R = RESULTS
                run_cell((name, cell))
            finally:
                _delete_token_dumps()
            _log(f"fingerprint {name} ({time.perf_counter() - t1:.1f}s)")
    _log("run complete")


if __name__ == "__main__":
    main()
