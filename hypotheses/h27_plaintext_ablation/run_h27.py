"""Run h27 serially: 3 plaintexts × seeds 1..5. Skips a cell whose json already exists."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Literal, Never

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h20_generators_vs_italian"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h19_heldout_likelihood"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h25_neutral_hybrid_cipher"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h24_neutral_cipher_robustness"))

import h27_lib as H  # noqa: E402
import run_h20  # noqa: E402
from fetch_italian import load_italian  # noqa: E402

RES = HERE / "results"
NTOK = run_h20.NTOK
PLAINS = ("real", "shuffle", "zipf")
Plain = Literal["real", "shuffle", "zipf"]


def assert_never(value: Never) -> Never:
    raise AssertionError(repr(value))


def cell_name(plain: str, seed: int) -> str:
    return f"P_boccaccio_{plain}_s{seed}"


def plaintext_for(plain: Plain, tokens: list[str], seed: int) -> tuple[list[str], int]:
    if plain == "real":
        return H.real_plaintext(tokens), 0
    if plain == "shuffle":
        return H.shuffle_plaintext(tokens, 2000 + seed), 0
    if plain == "zipf":
        _types, drawn, redraws = H.zipf_sample(tokens, 3000 + seed)
        return drawn, redraws
    return assert_never(plain)


def build_cell(plain: Plain, seed: int, source: list[str]):
    pt, redraws = plaintext_for(plain, source, seed)
    run_h20.R = RES
    toks, n_copy = H.encrypt_swap(pt, seed, 2 * NTOK)
    if len(toks) < NTOK:
        raise RuntimeError(f"{cell_name(plain, seed)} produced {len(toks)} ciphertext tokens, need {NTOK}")
    lines = [toks[i:i + 9] for i in range(0, len(toks), 9)]
    name = cell_name(plain, seed)
    cell = run_h20.lines_to_cell(lines, name, "ctrl", "eva")
    cell["fit"] = dict(src="it_boccaccio", plaintext=plain, seed=seed, copy="swap", c=0.05, n_copy=n_copy, zipf_redraws=redraws)
    return name, cell


def drop_token_tables() -> None:
    for path in RES.glob("tokens_*.csv.gz"):
        path.unlink()


def main() -> None:
    if NTOK != 10500:
        raise RuntimeError(f"NTOK is {NTOK}, expected 10500")
    RES.mkdir(parents=True, exist_ok=True)
    times_path = RES / "cell_times.json"
    times = json.loads(times_path.read_text()) if times_path.exists() else {}
    started = time.perf_counter()
    print("load it_boccaccio", flush=True)
    source = load_italian("it_boccaccio")
    print("tokens", len(source), flush=True)
    scored_now: list[str] = []
    try:
        for plain in PLAINS:
            for seed in range(1, 6):
                name = cell_name(plain, seed)
                dest = RES / f"cell_{name}.json"
                if dest.exists():
                    print("skip", name, flush=True)
                    continue
                print("start", name, flush=True)
                t0 = time.perf_counter()
                built = build_cell(plain, seed, source)
                run_h20.R = RES
                try:
                    run_h20.run_cell(built)
                finally:
                    drop_token_tables()
                sec = time.perf_counter() - t0
                times[name] = sec
                times_path.write_text(json.dumps(times, indent=1) + "\n")
                scored_now.append(name)
                print("done", name, round(sec, 1), flush=True)
    finally:
        wall = time.perf_counter() - started
        prev = sum(float(sec) for name, sec in times.items() if name not in scored_now)
        payload = dict(runtime_sec=wall + prev, wall_sec_this_process=wall, cells=times)
        (RES / "runtime.json").write_text(json.dumps(payload, indent=1) + "\n")


if __name__ == "__main__":
    main()
