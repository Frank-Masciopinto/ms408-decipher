"""h45 checks that do not load the manuscript."""
from __future__ import annotations

import h45_lib as H


def test_edge_pairs_do_not_cross_lines():
    lines = [[tuple("ab"), tuple("cd")], [tuple("ef"), tuple("gh")]]
    assert H.edge_pairs(lines) == [("b", "c"), ("f", "g")]


def test_no_within_line_pair_is_excluded():
    rec = H.score_unit_lines([[tuple("ab")], [tuple("ba")], [tuple("ab")]])
    assert rec["n_pairs"] == 0
    assert rec["MI_glyph"] == 0.0
    assert rec["share"] is None
    assert rec["excluded"] is True


def test_collapsed_eva_edge_keeps_ch_together():
    lines = H.as_units([["cho", "chy"]], "eva")
    assert H.edge_pairs(lines) == [("o", "ch")]


def test_alternating_ab_ba_share_is_one_when_sukhotin_separates():
    line = [tuple("ab"), tuple("ba")] * 20
    rec = H.score_unit_lines([line])
    vowels = set(rec["vowels"])
    assert vowels == {"a"} or vowels == {"b"}
    assert abs(rec["share"] - 1.0) < 1e-12
    assert abs(rec["MI_class"] - rec["MI_glyph"]) < 1e-12


def test_mi_class_equals_mi_glyph_when_glyph_pair_is_a_function_of_class_pair():
    glyph = [("a", "b"), ("b", "a")] * 15
    mapping = {"a": "V", "b": "C"}
    classes = [(mapping[a], mapping[b]) for a, b in glyph]
    # (V, C) is always (a, b) and (C, V) is always (b, a).
    assert abs(H.mutual_info(classes) - H.mutual_info(glyph)) < 1e-12


def test_mutual_info_bits():
    paired = [("a", "b"), ("b", "a")] * 10
    assert abs(H.mutual_info(paired) - 1.0) < 1e-12
    independent = [("a", "a"), ("a", "b"), ("b", "a"), ("b", "b")]
    assert abs(H.mutual_info(independent)) < 1e-12


def test_cross_line_bracket_is_dropped_with_its_newline():
    text = "de sili [sed hoc est\n vulgatae] optimum\n"
    assert H.token_lines(text, latin=True) == [["de", "sili", "optimum"]]


def test_latin_line_break_and_classical_spelling():
    lines = H.token_lines("vinum\nvia\n", latin=True)
    assert lines == [["uinum"], ["uia"]]


def test_take_tokens_cuts_inside_a_line():
    lines = [["aa", "bb", "cc"], ["dd", "ee"]]
    assert H.take_tokens(lines, 4) == [["aa", "bb", "cc"], ["dd"]]


def _streams(control, ms, self_share, gap_share):
    streams = {key: {"share": control} for key in H.CONTROL_KEYS}
    streams["boccaccio"] = {"share": control[0]}
    streams["cucina"] = {"share": control[1]}
    streams["pliny"] = {"share": control[2]}
    streams["macer"] = {"share": control[3]}
    for key, share in zip(H.MS_KEYS, ms):
        streams[key] = {"share": share}
    streams["self_citation"] = {"share": self_share}
    streams["gap_rule"] = {"share": gap_share}
    return streams


def test_predictions_c1_gates_c2_and_c3():
    high = _streams((0.40, 0.50, 0.60, 0.70), (0.10, 0.20, 0.30), 0.05, 0.15)
    pred = H.predictions(high)
    assert pred["C1"] is True
    assert pred["C2"] is True
    assert pred["C3"] is True
    assert pred["C2_scored"] is True
    assert pred["C3_scored"] is True

    tied = _streams((0.40, 0.50, 0.60, 0.70), (0.10, 0.40, 0.30), 0.05, 0.15)
    pred = H.predictions(tied)
    assert pred["C1"] is True
    assert pred["C2"] is False
    assert pred["C3"] is True

    low = _streams((0.10, 0.10, 0.10, 0.10), (0.0, 0.0, 0.0), 0.0, 0.0)
    pred = H.predictions(low)
    assert pred["C1"] is False
    assert pred["C2"] is None
    assert pred["C3"] is None
    assert pred["C2_scored"] is False
    assert pred["C3_scored"] is False


def test_c1_threshold_is_inclusive():
    pred = H.predictions(_streams((0.20, 0.20, 0.30, 0.30), (0.0, 0.0, 0.0), 0.0, 0.0))
    assert pred["median_control_share"] == 0.25
    assert pred["C1"] is True
