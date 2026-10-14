"""Measure h51 label-to-seed links and write results/measurements.json."""
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

import h51_lib as H  # noqa: E402

OUT = HERE / "results" / "measurements.json"


def _check(result: dict) -> None:
    if result["paragraph_summary"]["n_folios_ge20_para"] != 206:
        raise RuntimeError(
            f"expected 206 folios with >= 20 P tokens, got {result['paragraph_summary']['n_folios_ge20_para']}"
        )
    if result["test1_own_folio"]["n_folios"] != 30:
        raise RuntimeError(f"expected 30 label+paragraph folios, got {result['test1_own_folio']['n_folios']}")
    if result["test2_same_plant_seeds"]["pairs_16"]["seed_W25"]["edit1_or_stem"]["all_herbal"]["n_pairs"] != 16:
        raise RuntimeError("expected 16 same-plant pairs in pairs_16")


def main() -> None:
    result = H.measure_all(n_perm=H.N_PERM, seed=H.SEED)
    _check(result)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    pred = result["predictions"]
    print(
        f"wrote {OUT} L1={pred['L1']} L2={pred['L2']} L3={pred['L3']} "
        f"sec={result['runtime_sec']:.2f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
