"""Unit tests for the h53 statistics. They do not read the manuscript."""
from __future__ import annotations

import numpy as np

import h53_lib as H


def test_line_interior_drops_both_edges():
    assert H.line_interior(["a", "b", "c"]) == []
    assert H.line_interior(["a", "b", "c", "d"]) == ["b", "c"]


def test_folio_change_splits_only_when_asked():
    records = []
    first = True
    for page, words in (("f1", "abc"), ("f2", "def")):
        for word in words:
            records.append({"words": ["edge", word, word, "edge"], "para_first": first, "page": page})
            first = False
    assert len(H.paragraphs(records, split_on_page=True)) == 2
    assert len(H.paragraphs(records, split_on_page=False)) == 1


def test_null_p95_is_the_190th_order_statistic():
    assert H.null_p95(np.arange(200)) == 189


def test_closing_marker_beats_line_shuffles():
    paragraphs = []
    for _ in range(120):
        paragraphs.append([
            ["edge", "aa", "aa", "edge"],
            ["edge", "mm", "mm", "edge"],
            ["edge", "zz", "zz", "edge"],
        ])
    scored = H.score_paragraphs(paragraphs, "char")
    assert scored["scored"]
    assert scored["n_open"] == 240
    assert scored["word"]["S"] > scored["word"]["null_p95"]
    assert scored["word"]["excess"] >= 0.01


def test_exchangeable_lines_are_inside_the_null():
    paragraphs = []
    for i in range(80):
        line = ["edge", f"w{i % 5}", f"w{(i + 1) % 5}", "edge"]
        paragraphs.append([line, line, line])
    scored = H.score_paragraphs(paragraphs, "char")
    assert scored["word"]["S"] <= scored["word"]["null_p95"] + 1e-9
    assert scored["word"]["excess"] < 0.01


def test_reading_when_the_recipe_control_passes_and_the_hands_do_not():
    def block(excess: float, above: bool) -> dict:
        return {
            "scored": True,
            "word": {"S": 1.0 if above else 0.0, "null_p95": 0.5, "excess": excess, "z": 0.0},
        }
    streams = {}
    for hand in H.HANDS:
        streams[f"MS_{hand}"] = block(0.0, False)
        streams[f"page_line_copier_{hand}"] = block(0.0, False)
    streams["it_cucina"] = block(0.02, True)
    out = H.evaluate(streams)
    assert out["A1"] is False
    assert out["C1"] is True
    assert out["reading"] == "measure_sees_recipes_ms_does_not"
