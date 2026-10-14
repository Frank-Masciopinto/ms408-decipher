"""Run h49 seed-skeleton extraction and write results/measurements.json."""
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

import h49_lib as H  # noqa: E402

OUT = HERE / "results" / "measurements.json"

EXPECTED_FOLIOS = {
    "MS_1A": 112,
    "page_line_copier_1A": 112,
    "MS_2B": 46,
    "page_line_copier_2B": 46,
    "MS_3B": 28,
    "page_line_copier_3B": 28,
    "naibbe_boccaccio_swap": 46,
    "it_boccaccio": 46,
}


def _check(result: dict) -> None:
    streams = result["streams"]
    for key, exp_folios in EXPECTED_FOLIOS.items():
        got = streams[key]["n_folios"]
        if got != exp_folios:
            raise RuntimeError(f"{key} n_folios={got} != expected {exp_folios}")
        for mode in H.MODES:
            if mode not in streams[key]["modes"]:
                raise RuntimeError(f"{key} missing mode {mode}")


def main() -> None:
    result = H.measure_all(
        sweeps=H.BAYES_SWEEPS,
        n_perm_mi=H.N_PERM_MI,
        n_perm_folio=H.N_PERM_FOLIO,
        seed=H.SEED,
    )
    _check(result)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    pred = result["predictions"]
    print(
        f"wrote {OUT} verdict={pred['verdict']} "
        f"S1={pred['S1']['passed']} S2={pred['S2']['passed']} S3={pred['S3']['passed']} "
        f"sec={result['runtime_sec']:.2f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
