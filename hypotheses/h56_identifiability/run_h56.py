"""Run the pre-registered h56 programme and write results/measurements.json."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import h56_lib as H

HERE = Path(__file__).resolve().parent


def _clean(obj):
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _clean(obj.tolist())
    if isinstance(obj, (np.floating, float)):
        value = float(obj)
        return value if np.isfinite(value) else None
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    return obj


def main() -> None:
    payload = _clean(H.run())
    out = HERE / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "measurements.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "U1": payload["stage1"]["U1"],
        "R1": payload["stage2"]["R1"]["pass"],
        "R2": payload["stage2"]["R2_pass"],
        "M1": payload["stage3"]["M1"],
        "L": payload["stage4"]["pass"],
        "C1": payload["stage5"]["C1"],
        "S6": payload["stage6"]["S6"],
        "grounded": payload["grounded"],
        "stage7": payload["stage7"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
