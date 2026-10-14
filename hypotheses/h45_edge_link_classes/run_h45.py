"""Run every h45 stream and write results/streams.json."""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import h45_lib as H


def main() -> None:
    payload = H.run_all()
    out = Path(__file__).resolve().parent / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "streams.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["predictions"], indent=2), flush=True)


if __name__ == "__main__":
    main()
