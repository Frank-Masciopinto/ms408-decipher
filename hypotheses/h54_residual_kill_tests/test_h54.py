"""Unit tests for h54. They do not read the manuscript."""
from __future__ import annotations

import numpy as np

import h54_lib as H


def test_near_copy_covers_identity_edit_and_shared_interior():
    assert H.is_near_copy(("ch", "edy"), ("ch", "edy"))
    assert H.is_near_copy(("q", "o", "k"), ("q", "o", "t"))
    assert H.is_near_copy(("p", "ch", "k", "y"), ("d", "ch", "k", "edy"))
    assert not H.is_near_copy(("p", "ch", "k", "y"), ("d", "ol", "k", "edy"))


def test_core_shuffle_keeps_onsets_ends_and_the_core_bag():
    slotted = [[("o", "e", "a"), ("o", "e", "b"), ("o", "e", "c")]]
    rng = np.random.default_rng(0)
    moved = H.permute_cores(slotted, rng)
    assert [(o, e) for o, e, _ in moved[0]] == [("o", "e"), ("o", "e"), ("o", "e")]
    assert sorted(c for _, _, c in moved[0]) == ["a", "b", "c"]


def test_blocked_cores_beat_a_within_line_shuffle():
    lines = []
    for _ in range(40):
        row = []
        for i in range(12):
            core_word = "aa" if i < 6 else "bb"
            row.append("o" + core_word + "e")
        lines.append(row)
    scored = H.score_a2(lines, mode="char", n_perm=40, seed=1)
    assert scored["n_pairs"] >= 400
    assert scored["excess"] > 0.05
    assert scored["z"] > 2.58


def test_b3_picks_the_extreme_long_middles():
    lines = [
        ["a"] * 6,
        ["b"] * 3,
        ["c"] * 6,
        ["d"] * 6,
        ["e"] * 6,
    ]
    chosen = H.select_b3(lines)
    assert chosen is not None
    assert chosen[2] == ["c"] * 6
    assert chosen[3] == ["d"] * 6


def test_closing_marker_beats_matched_middles():
    paragraphs = []
    for _ in range(40):
        paragraphs.append([
            ["e", "aa", "aa", "aa", "aa", "e"],
            ["e", "mm", "mm", "mm", "mm", "e"],
            ["e", "mm", "mm", "mm", "mm", "e"],
            ["e", "zz", "zz", "zz", "zz", "e"],
        ])
    scored = H.score_b3(paragraphs, n_perm=200, seed=54)
    assert scored["scored"]
    assert scored["observed"] > scored["null_p95"]
    assert scored["excess"] >= 0.01


def test_labels_and_edy_normalization():
    assert H.overall_label("stands", "stands") == "both_stand"
    assert H.overall_label("killed", "killed") == "both_killed"
    assert H.overall_label("partial", "killed") == "mixed"
    assert H.overall_label("stands", "killed") == "slots_only"
    assert H.overall_label("killed", "stands") == "paragraphs_only"
    assert H.normalize_edy("chedy") == "chol"
    assert H.normalize_edy("daiin") == "daiin"
    assert H.b_label(2) == "stands"
    assert H.b_label(1) == "partial"
    assert H.b_label(0) == "killed"


def test_folio_first_paragraph_is_flagged_only_at_a_page_start():
    records = []
    for page in ("f1", "f2"):
        for _paragraph in range(2):
            for i in range(3):
                records.append({"page": page, "para_first": i == 0, "words": ["w"] * 4})
    groups = H.paragraphs_of(records)
    assert [g["folio_first"] for g in groups] == [True, False, True, False]
