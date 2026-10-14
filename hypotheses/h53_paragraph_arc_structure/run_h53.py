"""Run the pre-registered h53 scores and write results/measurements.json."""
from __future__ import annotations

import json
from pathlib import Path

import h53_lib as H

HERE = Path(__file__).resolve().parent


def main() -> None:
    streams = {}
    for hand in H.HANDS:
        print(f"MS {hand}", flush=True)
        ms_paras = H.paragraphs(H.load_ms_records(hand), split_on_page=True)
        streams[f"MS_{hand}"] = H.score_paragraphs(ms_paras, "eva")
        print(f"copier {hand}", flush=True)
        copier_paras = H.paragraphs(H.load_copier_records(hand), split_on_page=True)
        streams[f"page_line_copier_{hand}"] = H.score_paragraphs(copier_paras, "eva")
    print("cucina", flush=True)
    streams["it_cucina"] = H.score_paragraphs(H.paragraphs(H.load_cucina_records(), split_on_page=False), "char")
    pred = H.evaluate(streams)
    payload = {"streams": streams, "predictions": pred}
    out = HERE / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "measurements.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(pred, indent=2), flush=True)


if __name__ == "__main__":
    main()
