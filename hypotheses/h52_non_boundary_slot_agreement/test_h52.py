"""Unit tests for the h52 statistics. They do not read the manuscript."""
from __future__ import annotations

import h52_lib as H


def test_stratum_cutoff_drops_pairs_below_20():
    small = [("L", "R", ("only",))] * 19
    assert H.cmi(small)["n_pairs"] == 0
    large = [("L", "R", ("only",))] * 20
    assert H.cmi(large)["n_pairs"] == 20
    assert H.cmi(large)["cmi"] == 0.0


def test_pairs_do_not_cross_a_line_break():
    slotted = [[("a", "b", "c"), ("d", "e", "f")], [("g", "h", "i")]]
    rows = H.pair_rows(slotted, "F1", 1)
    assert rows == [("a", "e", ("b", "d"))]
    f3 = H.pair_rows(slotted, "F3", 1)
    assert f3 == [("b", "e", ("d",))]


def test_bound_slots_exceed_the_stratum_shuffle():
    rows = []
    for i in range(400):
        left = "a" if i % 2 == 0 else "b"
        rows.append((left, "x", ("e", "o")))
    bound = H.bind_rights_to_lefts(rows)
    scored = H.score_rows(bound, n_perm=40, seed=0)
    assert scored["excess"] > 0.2
    assert scored["z"] > 5


def test_independent_slots_have_no_excess():
    rows = []
    for i in range(600):
        left = "a" if i % 2 == 0 else "b"
        right = "x" if (i // 2) % 2 == 0 else "y"
        rows.append((left, right, ("e", "o")))
    scored = H.score_rows(rows, n_perm=40, seed=1)
    assert abs(scored["excess"]) < 0.05
    assert scored["z"] < 2.58


def test_short_core_is_not_rebinned():
    lines = [["ab", "cd"] for _ in range(10)]
    slotted = H.slotted_lines(lines, "char")
    assert all(word[2] == "SHORT" for line in slotted for word in line)


def test_cell_rule_requires_a_gap_over_the_copier():
    ms = {"n_pairs": 800, "excess": 0.02, "z": 3.0}
    copier = {"n_pairs": 800, "excess": 0.015, "z": 2.0}
    assert not H.cell_passes(ms, copier)
    copier["excess"] = 0.005
    assert H.cell_passes(ms, copier)
    assert H.copier_accounts({"z": 1.0, "excess": 0.2}, {"excess": 0.0})
    assert H.copier_accounts({"z": 4.0, "excess": 0.011}, {"excess": 0.005})
