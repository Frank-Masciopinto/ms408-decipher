"""Run h50: measure vertical header/acrostic streams and write results/measurements.json."""
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

import h50_lib as H  # noqa: E402

OUT = HERE / "results" / "measurements.json"


def _check(result: dict) -> None:
    streams = result["streams"]
    for key in H.STREAM_ORDER:
        if key not in streams:
            raise RuntimeError(f"missing stream {key}")
        rec = streams[key]
        if rec["n_lines"] <= 0 or rec["n_folios"] <= 0:
            raise RuntimeError(f"{key} has empty lines or folios")


def main() -> None:
    result = H.measure_all(n_perm=H.N_PERM, seed=H.SEED)
    _check(result)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    pred = result["predictions"]
    print(
        f"wrote {OUT} verdict={pred['verdict']} "
        f"A1={pred['A1']} ({pred['A1_passing_hands']}) "
        f"A2={pred['A2']} ({pred['A2_passing_hands']}) "
        f"A3={pred['A3']} ({pred['A3_passing_hands']}) "
        f"sec={result['runtime_sec']:.2f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
