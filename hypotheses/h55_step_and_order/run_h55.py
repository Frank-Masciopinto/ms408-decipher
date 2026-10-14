"""Run the pre-registered h55 scores and write results/measurements.json."""
from __future__ import annotations

import json
from pathlib import Path

import h55_lib as H

HERE = Path(__file__).resolve().parent


def main() -> None:
    payload = H.run()
    out = HERE / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "measurements.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "slots": payload["slots"],
        "S1_valid": payload["S1_valid"],
        "S1_hands": payload["S1_hands"],
        "S1_copier_hits": payload["S1_copier_hits"],
        "S1_plant_hits": payload["S1_plant_hits"],
        "bits": payload["bits"],
        "S2_valid": payload["S2_valid"],
        "S2_hands": payload["S2_hands"],
        "S2_copier_hits": payload["S2_copier_hits"],
        "S2_plant_hits": payload["S2_plant_hits"],
        "paragraphs": payload["paragraphs"],
        "opening": payload["sides"]["opening"],
        "closing": payload["sides"]["closing"],
        "X": payload["X"]["label"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
