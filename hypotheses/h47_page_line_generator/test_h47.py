"""Unit and integration tests for h47_page_line_generator."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import h47_lib as H  # noqa: E402

RES = HERE / "results"
STREAMS_PATH = RES / "streams.json"
SUMMARY_PATH = RES / "summary.json"
STATUS_PATH = RES / "STATUS.json"
FIG_PATH = HERE / "figures" / "page_line_benchmarks.png"
README_PATH = HERE / "README.md"


def test_no_inline_imports_in_h47_modules():
    for fname in ("h47_lib.py", "run_h47.py", "summarise.py", "test_h47.py"):
        lines = (HERE / fname).read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            stripped = line.lstrip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                indent = len(line) - len(stripped)
                assert indent == 0, f"Inline import in {fname}:{lineno}: {line}"


def test_load_template_respects_token_cap_and_metadata():
    for hand in H.HANDS:
        tpl = H.load_template(hand, max_tokens=H.N_STREAM)
        total_tok = sum(len(r["words"]) for r in tpl)
        assert 0 < total_tok <= H.N_STREAM
        assert all("page" in r and "quire" in r and "para_first" in r for r in tpl)


def test_artifacts_exist_and_no_temp_token_files_left():
    assert STREAMS_PATH.exists(), "results/streams.json missing"
    assert SUMMARY_PATH.exists(), "results/summary.json missing"
    assert STATUS_PATH.exists(), "results/STATUS.json missing"
    assert FIG_PATH.exists() and FIG_PATH.stat().st_size > 1000, "figures/page_line_benchmarks.png missing"
    assert README_PATH.exists() and README_PATH.stat().st_size > 500, "README.md missing"

    for check_dir in (
        RES,
        H.ROOT / "hypotheses" / "h19_heldout_likelihood" / "results",
        H.ROOT / "hypotheses" / "h20_generators_vs_italian" / "results",
    ):
        if check_dir.exists():
            leftover = list(check_dir.glob("tokens_*plc*.csv.gz")) + list(
                check_dir.glob("tokens_*h47*.csv.gz")
            )
            assert not leftover, f"Leftover temp files found: {leftover}"


def test_b1_through_b6_and_predictions_u1_u2_u3():
    payload = json.loads(STREAMS_PATH.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))

    assert status["complete"] is True
    assert status["verdict"] == "supported"
    assert status["U1"] is True
    assert status["U2"] is True
    assert status["U3"] is True

    streams = payload["streams"]
    for hand in ("1A", "2B", "3B"):
        rec = streams[f"page_line_copier_{hand}"]
        bm = rec["benchmarks"]
        assert bm["B1"]["passed"] is True and bm["B1"]["n_match"] == 5
        assert bm["B2"]["passed"] is True
        assert bm["B3"]["passed"] is True
        assert bm["B5"]["passed"] is True
        assert bm["B6"]["passed"] is True and bm["B6"]["shape"] == "page"
        assert rec["n_passed"] >= 5

    rec_2b = streams["page_line_copier_2B"]
    assert rec_2b["n_passed"] == 6
    assert rec_2b["benchmarks"]["B4"]["passed"] is True and rec_2b["benchmarks"]["B4"]["d80_pass"] is True

    base_nat = streams["h39_native_tuned_2B"]
    base_c0 = streams["h39_C0_graph_2B"]
    assert base_nat["n_passed"] <= 3
    assert base_c0["n_passed"] <= 3
    assert base_nat["n_passed"] < rec_2b["n_passed"]
    assert base_c0["n_passed"] < rec_2b["n_passed"]

    recomputed = H.evaluate_predictions(streams)
    assert recomputed == summary["predictions"]
