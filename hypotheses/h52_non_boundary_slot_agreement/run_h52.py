"""Run the pre-registered h52 scores and write results/measurements.json."""
from __future__ import annotations

import json
from pathlib import Path

import h52_lib as H

HERE = Path(__file__).resolve().parent


def main() -> None:
    streams = {}
    for hand in H.HANDS:
        print(f"MS {hand}", flush=True)
        streams[f"MS_{hand}"] = H.score_stream(H.load_ms_lines(hand), "eva")
        print(f"copier {hand}", flush=True)
        streams[f"page_line_copier_{hand}"] = H.score_stream(H.load_copier_lines(hand), "eva")
    print("cucina", flush=True)
    streams["it_cucina"] = H.score_stream(H.load_prose_lines("italian/pg33954.txt"), "char")
    print("sidrach", flush=True)
    streams["it_sidrach"] = H.score_stream(H.load_prose_lines("pg44549.txt"), "char")
    print("synthetic", flush=True)
    slotted = H.slotted_lines(H.load_copier_lines("2B"), "eva")
    synthetic = H.score_rows(H.bind_rights_to_lefts(H.pair_rows(slotted, "F1", 1)))
    pred = H.evaluate(streams, synthetic)
    payload = {"streams": streams, "synthetic_bind_2B": synthetic, "predictions": pred}
    out = HERE / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "measurements.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(pred, indent=2), flush=True)


if __name__ == "__main__":
    main()
