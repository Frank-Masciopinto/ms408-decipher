"""Unit and integration tests for h50_header_acrostic_stream."""
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

import h50_lib as H  # noqa: E402

MEAS_PATH = HERE / "results" / "measurements.json"
SUMMARY_PATH = HERE / "results" / "summary.json"
STATUS_PATH = HERE / "results" / "STATUS.json"
FIG_PATH = HERE / "figures" / "header_acrostic_stream.png"
README_PATH = HERE / "README.md"


def test_no_inline_imports_in_h50_modules():
    for fname in ("h50_lib.py", "run_h50.py", "summarise.py", "test_h50.py"):
        lines = (HERE / fname).read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            stripped = line.lstrip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                indent = len(line) - len(stripped)
                assert indent == 0, f"Inline import in {fname}:{lineno}: {line}"


def test_strip_onset_word_and_vertical_extraction():
    # 'daiin' -> leading 'd', remainder 'aiin' has >= 2 collapsed EVA units -> stripped to 'aiin'
    assert H.strip_onset_word("daiin", "eva") == "aiin"
    # 'dy' -> leading 'd', remainder 'y' has only 1 unit -> kept as 'dy'
    assert H.strip_onset_word("dy", "eva") == "dy"
    # 'polchedy' -> leading 'p', remainder 'olchedy' has >= 2 units -> 'olchedy'
    assert H.strip_onset_word("polchedy", "eva") == "olchedy"
    # 'chedy' -> starts with 'ch', not in d/s/p/t/k/f -> kept as 'chedy'
    assert H.strip_onset_word("chedy", "eva") == "chedy"

    records = [
        {"words": ["polchedy", "qokeey"], "page": "f1r", "quire": "1", "stratum": "1A|1", "para_first": True},
        {"words": ["daiin", "chedy"], "page": "f1r", "quire": "1", "stratum": "1A|1", "para_first": False},
        {"words": ["dy", "shedy"], "page": "f1v", "quire": "1", "stratum": "1A|1", "para_first": True},
    ]
    vert = H.extract_vertical_sequences(records, unit_kind="eva")
    assert vert["para_words"] == ["polchedy", "dy"]
    assert vert["line_words_raw"] == ["polchedy", "daiin", "dy"]
    assert vert["line_words_stripped"] == ["olchedy", "aiin", "dy"]
    assert vert["line_first_unit"] == ["p", "d", "d"]


def test_m1_detects_synthetic_vertical_bigram_stream():
    # Construct 10 folios where line-initial words follow a deterministic 4-cycle
    cycle = ["alfa", "beta", "gamma", "delta"]
    records = []
    for f_idx in range(10):
        page = f"f{f_idx}r"
        quire = f"q{f_idx // 2}"
        for l_idx in range(20):
            w0 = cycle[l_idx % 4]
            records.append(
                {
                    "words": [w0, "pad1", "pad2"],
                    "page": page,
                    "quire": quire,
                    "stratum": quire,
                    "para_first": (l_idx % 4 == 0),
                }
            )
    vert = H.extract_vertical_sequences(records, unit_kind="char")
    m1 = H.measure_m1(vert, n_perm=50, seed=50)
    lws = m1["line_words_stripped"]
    assert lws["D1_vert"] > 0.5
    assert lws["lag1_class_mi"] > lws["lag1_class_mi_null_p95"]
    assert lws["pass_a1"] is True
    assert m1["pass_a1"] is True


def test_m2_detects_synthetic_vertical_acrostic():
    # Vertical first units alternate 'a', 'b', 'a', 'b' while horizontal words have flat units
    records = []
    for f_idx in range(8):
        page = f"f{f_idx}r"
        for l_idx in range(16):
            first_ch = "a" if (l_idx % 2 == 0) else "b"
            w0 = first_ch + "x"
            records.append(
                {
                    "words": [w0, "ay", "bz", "cx"],
                    "page": page,
                    "quire": "q0",
                    "stratum": "q0",
                    "para_first": (l_idx == 0),
                }
            )
    vert = H.extract_vertical_sequences(records, unit_kind="char")
    m2 = H.measure_m2(records, vert, unit_kind="char", n_perm=50, seed=50)
    assert m2["R_acro"] > 0.8
    assert m2["R_acro_above_p95"] is True
    assert m2["reaches_50pct_horiz"] is True
    assert m2["pass_a2"] is True


def test_m3_detects_folio_specific_header_alignment():
    # Quire with 6 folios, each folio has its own stem family and Line 1 has 'd' + stem variants
    stems = ["aaaa", "bbbb", "cccc", "eeee", "gggg", "mmmm"]
    records = []
    for f_idx, st in enumerate(stems):
        page = f"f{f_idx}r"
        l1 = [f"d{st}x", f"s{st}y", f"p{st}z"]
        records.append(
            {"words": l1, "page": page, "quire": "q0", "stratum": "q0", "para_first": True}
        )
        for l_idx in range(1, 8):
            body_line = [f"{st}x", f"{st}y", f"{st}w"]
            records.append(
                {"words": body_line, "page": page, "quire": "q0", "stratum": "q0", "para_first": False}
            )
    vert = H.extract_vertical_sequences(records, unit_kind="char")
    m3 = H.measure_m3(vert, unit_kind="char", n_perm=50, seed=50)
    assert m3["header_body_cos"] > 0.7
    assert m3["header_body_cos_above_p95"] is True
    assert m3["header_body_edit1"] > m3["header_body_edit1_null_p95"]
    assert m3["pass_a3"] is True


def test_artifacts_and_predictions_consistency():
    assert MEAS_PATH.is_file(), "results/measurements.json missing"
    assert SUMMARY_PATH.is_file(), "results/summary.json missing"
    assert STATUS_PATH.is_file(), "results/STATUS.json missing"
    assert FIG_PATH.is_file() and FIG_PATH.stat().st_size > 1000, "figures/header_acrostic_stream.png missing"
    assert README_PATH.is_file() and README_PATH.stat().st_size > 500, "README.md missing"

    data = json.loads(MEAS_PATH.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))

    assert set(data["streams"].keys()) == set(H.STREAM_ORDER)
    recomputed = H.evaluate_predictions(data["streams"])
    assert recomputed == data["predictions"]
    assert recomputed == summary["predictions"]
    assert status["complete"] is True
    assert status["A1"] is False
    assert status["A2"] is False
    assert status["A3"] is True
    assert status["verdict"] == "partially_supported"
