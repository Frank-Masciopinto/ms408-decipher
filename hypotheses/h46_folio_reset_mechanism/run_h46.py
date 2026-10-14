"""Measure h46 and write results/measurements.json."""
from __future__ import annotations

import json
import os
import platform
import sys
import time
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

import h46_lib as H  # noqa: E402

OUT = HERE / "results" / "measurements.json"

EXPECTED_HANDS = {
    "1A": {"n_tokens": 10326, "n_folios": 112, "n_quires": 10},
    "2B": {"n_tokens": 10722, "n_folios": 46, "n_quires": 6},
    "3B": {"n_tokens": 10835, "n_folios": 28, "n_quires": 2},
}


def _check(result: dict) -> None:
    for hand, expect in EXPECTED_HANDS.items():
        got = result["test1"][hand]
        for key in ("n_tokens", "n_folios", "n_quires"):
            if got[key] != expect[key]:
                raise RuntimeError(f"{hand} {key} {got[key]} != {expect[key]}")


def main() -> None:
    t0 = time.perf_counter()
    result = H.measure_all(H.NULL_SEED)
    result["python"] = platform.python_version()
    result["runtime_sec"] = time.perf_counter() - t0
    _check(result)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    pred = result["predictions"]
    print(
        f"wrote {OUT} F1={pred['F1']} F2={pred['F2']} F3={pred['F3']} "
        f"sec={result['runtime_sec']:.1f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
