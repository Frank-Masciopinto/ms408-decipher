"""Unit and integration tests for h48_within_folio_drift."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import h48_lib as H  # noqa: E402
import h42_lib  # noqa: E402


def test_fast_en_matrix_matches_exact_loop():
    lines_units = [
        [("a", "b", "c"), ("a", "b", "d"), ("x", "y")],
        [("a", "b", "e"), ("x", "z"), ("m", "n", "o", "p")],
        [("a", "b", "c"), ("m", "n", "o", "q"), ("q",)],
    ]
    e_mat, n_mat = H.fast_en_matrix(lines_units)
    m = len(lines_units)
    for i in range(m):
        assert e_mat[i, i] == 0
        assert n_mat[i, i] == 0
        for j in range(i + 1, m):
            elig = 0
            hits = 0
            for ua in lines_units[i]:
                for ub in lines_units[j]:
                    if abs(len(ua) - len(ub)) <= 1:
                        elig += 1
                        if h42_lib.edit1(ua, ub):
                            hits += 1
            assert e_mat[i, j] == hits
            assert e_mat[j, i] == hits
            assert n_mat[i, j] == elig
            assert n_mat[j, i] == elig


def test_drifting_folio_passes_and_permuted_fails():
    # Build 12 folios of 12 lines where lines 0..5 use one 1-edit chain and lines 6..11 use a distant chain
    top_chain = [
        ["aaaa", "aaab", "aaac", "aaad"],
        ["aaab", "aaac", "aaad", "aaae"],
        ["aaac", "aaad", "aaae", "aaaf"],
        ["aaad", "aaae", "aaaf", "aaag"],
        ["aaae", "aaaf", "aaag", "aaah"],
        ["aaaf", "aaag", "aaah", "aaai"],
    ]
    bot_chain = [
        ["zzzz", "zzzy", "zzzx", "zzzw"],
        ["zzzy", "zzzx", "zzzw", "zzzv"],
        ["zzzx", "zzzw", "zzzv", "zzzu"],
        ["zzzw", "zzzv", "zzzu", "zzzt"],
        ["zzzv", "zzzu", "zzzt", "zzzs"],
        ["zzzu", "zzzt", "zzzs", "zzzr"],
    ]
    folios = [
        {"folio": f"f{k}", "quire": "q0", "lines": [list(line) for line in (top_chain + bot_chain)]}
        for k in range(12)
    ]
    res = H.measure_stream(folios, unit_kind="char", name="toy_drift", n_perm=100, seed=48)
    assert res["M1"]["S_edit"] > 0.2
    assert res["M1"]["pass"] is True
    assert res["M2"]["S_cos3"] > 0.2
    assert res["M2"]["pass"] is True
    assert res["M3"]["half_js"] < -0.2
    assert res["M3"]["drifted_apart"] is True


def test_d3_decomposition_identifies_palette_and_drift():
    # Quire 0 has two folios with distinct alphabets AND within-folio top/bottom drift
    f0_lines = [["aaaa", "aaab", "aaac"]] * 5 + [["mmmm", "mmmn", "mmmo"]] * 5
    f1_lines = [["xxxx", "xxxy", "xxxz"]] * 5 + [["qqqq", "qqqr", "qqqs"]] * 5
    folios = [
        {"folio": "f0", "quire": "q0", "lines": f0_lines},
        {"folio": "f1", "quire": "q0", "lines": f1_lines},
        {"folio": "f2", "quire": "q0", "lines": f0_lines},
        {"folio": "f3", "quire": "q0", "lines": f1_lines},
    ]
    res = H.measure_stream(
        folios, unit_kind="char", name="toy_d3", n_perm=100, seed=48, compute_d3=True
    )
    d3 = res["D3"]
    assert d3 is not None
    assert d3["folio_palette_component"] > 0.0
    assert d3["within_folio_drift_component"] > 0.0
    assert abs(
        (d3["folio_palette_component"] + d3["within_folio_drift_component"]) - d3["total_excess"]
    ) < 1e-12
    assert d3["both_positive_gt_2sd"] is True


def test_score_predictions_rules():
    mock = {
        "MS_1A": {"M1": {"pass": True}, "M2": {"pass": True}, "D3": {"both_positive_gt_2sd": True}},
        "MS_2B": {"M1": {"pass": True}, "M2": {"pass": False}, "D3": {"both_positive_gt_2sd": True}},
        "MS_3B": {"M1": {"pass": False}, "M2": {"pass": True}, "D3": {"both_positive_gt_2sd": False}},
    }
    pred = H.score_predictions(mock)
    assert pred["D1"] is True
    assert pred["D1_pass_hands"] == ["1A", "2B"]
    assert pred["D2"] is True
    assert pred["D2_pass_hands"] == ["1A", "3B"]
    assert pred["D3"] is True
    assert pred["D3_pass_hands"] == ["1A", "2B"]


def test_saved_outputs_if_present():
    meas_path = HERE / "results" / "measurements.json"
    sum_path = HERE / "results" / "summary.json"
    stat_path = HERE / "results" / "STATUS.json"
    fig_path = HERE / "figures" / "within_folio_drift.png"
    if not meas_path.is_file():
        return
    data = json.loads(meas_path.read_text(encoding="utf-8"))
    assert set(data["streams"].keys()) == set(H.STREAM_ORDER)
    assert H.score_predictions(data["streams"]) == data["predictions"]
    assert sum_path.is_file()
    assert stat_path.is_file()
    assert fig_path.is_file()
