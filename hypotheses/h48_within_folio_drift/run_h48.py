"""Measure h48 within-folio copy drift vs fixed page palette and write results/measurements.json."""
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

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import h48_lib as H  # noqa: E402

OUT = HERE / "results" / "measurements.json"

EXPECTED_FOLIOS = {
    "MS_1A": 103,
    "MS_2B": 44,
    "MS_3B": 27,
    "palette_ctrl": 44,
}


def _check(result: dict) -> None:
    streams = result["streams"]
    for key, exp_folios in EXPECTED_FOLIOS.items():
        got = streams[key]["n_folios"]
        if got != exp_folios:
            raise RuntimeError(f"{key} n_folios={got} != expected {exp_folios}")
    for key in H.MS_KEYS:
        if streams[key]["D3"] is None:
            raise RuntimeError(f"{key} missing D3 decomposition")


def main() -> None:
    result = H.measure_all(n_perm=H.N_PERM, seed=H.SEED)
    _check(result)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    pred = result["predictions"]
    print(
        f"wrote {OUT} D1={pred['D1']} D2={pred['D2']} D3={pred['D3']} "
        f"sec={result['runtime_sec']:.2f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
