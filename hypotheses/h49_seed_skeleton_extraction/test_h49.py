"""Unit and integration tests for h49_seed_skeleton_extraction."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import h49_lib as H  # noqa: E402


def test_extract_seeds_raw_local_and_folio_comp():
    # On character units: "aaaa" and "aaab" are edit distance 1; "xxxx" is distant.
    # Build a 30-token sequence where token 28 is "aaaa" (lag 28 > 25 from token 0).
    folio_words = (
        ["aaaa", "aaab", "aaaa"]
        + [f"w{k:03d}" for k in range(25)]
        + ["aaaa", "aaac"]
    )
    assert len(folio_words) == 30

    raw = H.extract_seeds(folio_words, mode="raw", unit_kind="char", window=25)
    assert raw == folio_words

    w25 = H.extract_seeds(folio_words, mode="local_W25", unit_kind="char", window=25)
    # Index 0 ("aaaa") kept; index 1 ("aaab", edit1 to 0) dropped; index 2 ("aaaa", exact to 0) dropped;
    # indices 3..27 ("w000".."w024", all pairwise >=2 edits if distinct digits? Wait: w000 and w001 are edit1!)
    # Let's check index 0 vs 1 and 2 specifically:
    assert w25[0] == "aaaa"
    assert "aaab" not in w25

    # Also test with well-separated filler tokens (length >= 4, pairwise distance >= 2)
    fillers = [chr(ord("a") + (i % 13)) * 2 + chr(ord("n") + (i % 13)) * 2 for i in range(26)]
    seq = ["chedy", "shedy", "chedy"] + fillers + ["chedy"]
    # In EVA units: SEG("chedy") = ("ch", "e", "d", "y"), SEG("shedy") = ("sh", "e", "d", "y") -> edit1!
    # The final "chedy" is at index 29, which is lag 27 from index 2 ("chedy") and lag 28 from index 1 ("shedy").
    w25_eva = H.extract_seeds(seq, mode="local_W25", unit_kind="eva", window=25)
    fc_eva = H.extract_seeds(seq, mode="folio_comp", unit_kind="eva", window=25)

    # In local_W25, final "chedy" (lag 27 > 25) is retained again, so "chedy" appears twice
    assert w25_eva.count("chedy") == 2
    assert "shedy" not in w25_eva

    # In folio_comp, final "chedy" is dropped because index 0 ("chedy") is on the same folio
    assert fc_eva.count("chedy") == 1
    assert "shedy" not in fc_eva


def test_extract_seeds_on_folio_dicts_is_folio_isolated():
    folios = [
        {"id": "f1", "folio": "f1", "quire": "q1", "bif": "b1", "words": ["chedy", "shedy", "qokain"]},
        {"id": "f2", "folio": "f2", "quire": "q1", "bif": "b1", "words": ["shedy", "daiin"]},
    ]
    fc = H.extract_seeds(folios, mode="folio_comp", unit_kind="eva")
    assert fc[0]["words"] == ["chedy", "qokain"]
    # On folio f2, "shedy" is the first token on that folio so it is kept despite appearing on f1
    assert fc[1]["words"] == ["shedy", "daiin"]


def test_compute_d1_seed_recovers_positive_syntax_after_depadding():
    # Construct synthetic folios where an ordered bigram cycle (A -> B -> C -> D) is padded
    # with immediate 1-edit echoes that destroy adjacent bigram transitions in raw stream.
    cycle = [("aaaa", "aaab"), ("bbbb", "bbbc"), ("cccc", "cccd"), ("dddd", "ddde")]
    folios = []
    for f_idx in range(10):
        words = []
        for step in range(30):
            seed_w, echo_w = cycle[(step + f_idx) % len(cycle)]
            words.extend([seed_w, echo_w, seed_w])
        folios.append(
            {
                "id": f"f{f_idx}",
                "folio": f"f{f_idx}",
                "quire": f"q{f_idx // 5}",
                "bif": f"b{f_idx % 5}",
                "words": words,
            }
        )
    w25_folios = H.extract_seeds(folios, mode="local_W25", unit_kind="char", window=25)
    d1_w25 = H.compute_d1_seed(w25_folios, n_folds=5)
    assert d1_w25["D1_seed"] > 0.5


def test_evaluate_predictions_logic():
    def _mock_stream(raw_d1, w25_keep, w25_d1, w25_morph, fc_d1, fc_z):
        return {
            "modes": {
                "raw": {"D1_seed": raw_d1},
                "local_W25": {
                    "keep_rate": w25_keep,
                    "D1_seed": w25_d1,
                    "morphs_per_type": w25_morph,
                },
                "folio_comp": {
                    "D1_seed": fc_d1,
                    "mi_adj_obs": 0.20 if fc_z > 1.96 else 0.05,
                    "mi_adj_null_p95": 0.10,
                    "mi_adj_z": fc_z,
                },
            }
        }

    mock_streams = {
        "MS_1A": _mock_stream(-0.18, 0.52, -0.22, 0.28, -0.21, -0.3),
        "page_line_copier_1A": _mock_stream(-0.25, 0.57, -0.24, 0.29, -0.22, 0.1),
        "MS_2B": _mock_stream(-0.14, 0.45, -0.23, 0.30, -0.15, 1.7),
        "page_line_copier_2B": _mock_stream(-0.26, 0.52, -0.25, 0.29, -0.18, 1.8),
        "MS_3B": _mock_stream(-0.17, 0.55, -0.24, 0.28, -0.12, 2.1),
        "page_line_copier_3B": _mock_stream(-0.26, 0.57, -0.24, 0.28, -0.16, -0.8),
    }
    pred = H.evaluate_predictions(mock_streams)
    assert pred["S1"]["passed"] is False
    assert pred["S1"]["passing_hands"] == []
    assert pred["S2"]["passed"] is False
    assert pred["S2"]["passing_hands"] == ["3B"]
    assert pred["S3"]["passed"] is True
    assert pred["S3"]["passing_hands"] == ["1A", "2B", "3B"]
    assert pred["verdict"] == "no_plaintext_skeleton_matched"


def test_saved_outputs_and_consistency():
    meas_path = HERE / "results" / "measurements.json"
    sum_path = HERE / "results" / "summary.json"
    stat_path = HERE / "results" / "STATUS.json"
    fig_path = HERE / "figures" / "seed_skeleton_extraction.png"
    readme_path = HERE / "README.md"
    if not meas_path.is_file():
        return

    data = json.loads(meas_path.read_text(encoding="utf-8"))
    assert tuple(data["streams"].keys()) == H.STREAM_ORDER
    for sname in H.STREAM_ORDER:
        modes = data["streams"][sname]["modes"]
        assert tuple(modes.keys()) == H.MODES
        assert np.isclose(modes["raw"]["keep_rate"], 1.0)
        assert modes["raw"]["n_tokens"] >= modes["local_W25"]["n_tokens"] >= modes["folio_comp"]["n_tokens"]

    recomputed = H.evaluate_predictions(data["streams"])
    assert recomputed == data["predictions"]
    assert sum_path.is_file()
    assert stat_path.is_file()
    assert fig_path.is_file()
    assert readme_path.is_file()
