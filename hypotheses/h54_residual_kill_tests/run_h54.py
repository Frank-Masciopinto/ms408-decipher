"""Run the pre-registered h54 scores and write results/measurements.json."""
from __future__ import annotations

import json
from pathlib import Path

import h54_lib as H

HERE = Path(__file__).resolve().parent


def main() -> None:
    payload = H.run()
    out = HERE / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "measurements.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "overall": payload["overall"],
        "slots": payload["slots"],
        "A1_hands": payload["A1_hands"],
        "A2_hands": payload["A2_hands"],
        "paragraphs": payload["paragraphs"],
        "B1_hands": payload["B1_hands"],
        "B2_hands": payload["B2_hands"],
        "B3_hands": payload["B3_hands"],
        "C": payload["conditional"]["C"]["label"],
        "D": payload["conditional"]["D"]["label"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
