"""Unit tests for h55. They do not read the manuscript."""
from __future__ import annotations

import numpy as np

import h55_lib as H


def test_interior_keeps_only_the_deep_middle():
    assert H.interior(["a", "b", "c", "d", "e", "f"]) == []
    assert H.interior(["a", "b", "c", "d", "e", "f", "g"]) == ["c", "d", "e"]


def test_word_shuffle_keeps_each_word_intact():
    slotted = [[("o1", "e1", "c1"), ("o2", "e2", "c2"), ("o3", "e3", "c3")]]
    moved = H.shuffle_lines(slotted, np.random.default_rng(0))
    assert sorted(moved[0]) == sorted(slotted[0])


def test_order_plant_blocks_cores_and_keeps_words():
    lines = [["xaa", "xbb", "xab", "xba"] for _ in range(40)]
    planted = H.plant_order(lines, mode="char")
    assert sorted(planted[0]) == sorted(lines[0])
    cores = [word[1] for word in planted[0]]
    assert cores == sorted(cores)


def test_step_plant_marks_only_the_deep_interior():
    groups = [[["a", "b", "c", "d", "e", "f", "g"], ["a", "b", "c", "d", "e", "f", "g"]]]
    planted = H.plant_steps(groups)
    assert planted[0][0] == ["a", "b", "PLANT", "PLANT", "PLANT", "f", "g"]
    assert planted[0][1] == ["a", "b", "ENDPLANT", "ENDPLANT", "ENDPLANT", "f", "g"]


def test_blocked_words_beat_a_whole_word_shuffle():
    lines = []
    for _ in range(40):
        row = ["oaae"] * 6 + ["obbe"] * 6
        lines.append(row)
    scored = H.score_s1(lines, mode="char", n_perm=40, seed=1)
    assert scored["n_pairs"] >= 400
    assert scored["excess"] > 0.05
    assert scored["z"] > 2.58


def test_opening_step_detects_a_marked_first_line():
    paragraphs = []
    for _ in range(80):
        paragraphs.append([
            ["e", "e", "AA", "AA", "AA", "e", "e"],
            ["e", "e", "BB", "BB", "BB", "e", "e"],
            ["e", "e", "BB", "BB", "BB", "e", "e"],
            ["e", "e", "BB", "BB", "BB", "e", "e"],
        ])
    scored = H.score_step(paragraphs, "opening", n_perm=200, seed=55)
    assert scored["scored"]
    assert scored["observed"] > scored["null_p95"]
    assert scored["excess"] >= 0.05


def test_labels():
    assert H._three_way(2, True, ("adjacency", "no_adjacency", "partial")) == "adjacency"
    assert H._three_way(0, True, ("adjacency", "no_adjacency", "partial")) == "no_adjacency"
    assert H._three_way(1, False, ("adjacency", "no_adjacency", "partial")) == "invalid"
    assert H.paragraph_label("pass", "none") == "role"
    assert H.paragraph_label("none", "none") == "no_role"
    assert H.paragraph_label("invalid", "invalid") == "invalid"
    assert H.paragraph_label("one", "none") == "partial"
    assert H.paragraph_label("invalid", "none") == "no_role"
