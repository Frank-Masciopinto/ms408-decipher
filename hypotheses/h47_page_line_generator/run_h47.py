"""Run h47: generate page_line_copier streams and score B1..B6 on hands 1A, 2B, 3B and h39 baselines."""
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

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import h47_lib as H  # noqa: E402

RES = HERE / "results"
STREAMS_PATH = RES / "streams.json"
H39_DIR = H.ROOT / "hypotheses" / "h39_graph_respell_and_tuned_copier" / "results"


def _clean_temp_tokens() -> None:
    for root_dir in (
        RES,
        H.ROOT / "hypotheses" / "h19_heldout_likelihood" / "results",
        H.ROOT / "hypotheses" / "h20_generators_vs_italian" / "results",
        H39_DIR,
    ):
        if root_dir.exists():
            for p in root_dir.glob("tokens_*plc*.csv.gz"):
                p.unlink(missing_ok=True)
            for p in root_dir.glob("tokens_*h47*.csv.gz"):
                p.unlink(missing_ok=True)


def main() -> None:
    t0 = time.perf_counter()
    RES.mkdir(parents=True, exist_ok=True)
    streams: dict[str, dict] = {}
    generated_lines: dict[str, list[list[str]]] = {}

    for hand in H.HANDS:
        name = f"page_line_copier_{hand}"
        print(f"Generating and scoring {name}...", flush=True)
        t1 = time.perf_counter()
        lines, records = H.generate_page_line_copier(hand, seed=H.SEED)
        generated_lines[name] = lines
        rec = H.score_all_benchmarks(lines, records, hand=hand, name=name, n_boot=100)
        rec["kind"] = "page_line_copier"
        rec["seed"] = H.SEED
        rec["rho_keep"] = H.RHO_KEEP
        rec["seconds"] = time.perf_counter() - t1
        streams[name] = rec
        print(
            f"  done {name}: passed {rec['n_passed']}/6 {rec['pass_flags']} ({rec['seconds']:.1f}s)",
            flush=True,
        )

    baselines = (
        ("h39_native_tuned_2B", "lines_2B_native_tuned.json", "2B"),
        ("h39_C0_graph_2B", "lines_2B_C0_graph.json", "2B"),
    )
    for name, fname, hand in baselines:
        print(f"Scoring baseline {name} from {fname}...", flush=True)
        t1 = time.perf_counter()
        raw_lines = json.loads((H39_DIR / fname).read_text(encoding="utf-8"))
        lines, records = H.layout_flat_lines_on_template(raw_lines, hand)
        generated_lines[name] = lines
        rec = H.score_all_benchmarks(lines, records, hand=hand, name=name, n_boot=100)
        rec["kind"] = "h39_baseline"
        rec["source"] = fname
        rec["seconds"] = time.perf_counter() - t1
        streams[name] = rec
        print(
            f"  done {name}: passed {rec['n_passed']}/6 {rec['pass_flags']} ({rec['seconds']:.1f}s)",
            flush=True,
        )

    predictions = H.evaluate_predictions(streams)
    payload = {
        "hypothesis": "h47_page_line_generator",
        "seed": H.SEED,
        "n_stream": H.N_STREAM,
        "rho_keep": H.RHO_KEEP,
        "w_buf": H.W_BUF,
        "numpy": np.__version__,
        "python": platform.python_version(),
        "runtime_sec": time.perf_counter() - t0,
        "predictions": predictions,
        "streams": streams,
        "generated_lines": generated_lines,
    }
    STREAMS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _clean_temp_tokens()
    print(
        f"wrote {STREAMS_PATH} verdict={predictions['verdict']} "
        f"U1={predictions['U1']['passed']} U2={predictions['U2']['passed']} U3={predictions['U3']['passed']} "
        f"({payload['runtime_sec']:.1f}s)",
        flush=True,
    )


if __name__ == "__main__":
    main()
