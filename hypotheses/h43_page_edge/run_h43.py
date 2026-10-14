"""Measure h43 and write results/measurements.json. One process."""
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
sys.path.insert(0, str(HERE))

import h43_lib as H  # noqa: E402

OUT = HERE / "results" / "measurements.json"

# Geometry of this transcription, checked before the null is trusted.
EXPECTED_HANDS = {
    "1A": {"n_tokens": 10326, "n_folios": 112, "n_quires": 10, "80": (184, 45), "160": (0, 586)},
    "2B": {"n_tokens": 10722, "n_folios": 46, "n_quires": 6, "80": (4440, 41), "160": (2549, 2164)},
    "3B": {"n_tokens": 10835, "n_folios": 28, "n_quires": 2, "80": (6807, 23), "160": (5047, 1738)},
}
EXPECTED_CONTROLS = {
    "it_boccaccio": {"n_tokens": 61623, "n_boundaries": 20},
    "it_cucina": {"n_tokens": 12627, "n_boundaries": 180},
    "la_pliny_herbal": {"n_tokens": 76765, "n_boundaries": 155},
}


def _check(result: dict) -> None:
    for hand, expect in EXPECTED_HANDS.items():
        got = result["hands"][hand]
        for key in ("n_tokens", "n_folios", "n_quires"):
            if got[key] != expect[key]:
                raise RuntimeError(f"{hand} {key} {got[key]} != {expect[key]}")
        for distance in ("80", "160"):
            row = got["distances"][distance]
            counts = (row["n_same"], row["n_cross"])
            if counts != expect[distance]:
                raise RuntimeError(f"{hand} d={distance} pairs {counts} != {expect[distance]}")
    for name, expect in EXPECTED_CONTROLS.items():
        got = result["controls"][name]
        if got["n_tokens"] != expect["n_tokens"] or got["n_boundaries"] != expect["n_boundaries"]:
            raise RuntimeError(
                f"{name} tokens/boundaries {got['n_tokens']}/{got['n_boundaries']} "
                f"!= {expect['n_tokens']}/{expect['n_boundaries']}"
            )
        if got["quire_structure"] != "one_fake_quire" or got["n_quires"] != 1:
            raise RuntimeError(f"{name} is not one fake quire")


def main() -> None:
    t0 = time.perf_counter()
    result = H.measure_all(H.NULL_SEED)
    result["python"] = platform.python_version()
    result["runtime_sec"] = time.perf_counter() - t0
    _check(result)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    pred = result["predictions"]
    print(
        f"wrote {OUT} E1={pred['E1']} E2={pred['E2']} uncalibrated={pred['uncalibrated']} "
        f"sec={result['runtime_sec']:.1f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
