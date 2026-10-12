from collections import Counter
import numpy as np
import h11_lib as L


def test_rewrite_rule_closes_pure_spelling_gap():
    A = Counter({"chol": 50, "dar": 30}); B = Counter({"chedy": 50, "dar": 30})
    rules = L.greedy_rules(B, A, 3)
    assert L.jsd(L.rewrite(B, rules), A) < 1e-9


def test_apply_rule_positions():
    assert L.apply_rule("chedy", ("end", "edy", "ol")) == "chol"
    assert L.apply_rule("qokedy", ("start", "qo", "")) == "kedy"
    assert L.apply_rule("ckheey", ("any", "ee", "e")) == "ckhey"


def test_residualise_removes_group_means():
    Y = np.array([[1., 0], [1, 0], [0, 1], [0, 1]]); R = L.residualise(Y, np.array(["a", "a", "b", "b"]))
    assert np.abs(R).max() < 1e-9


def test_log_odds_sign():
    d = L.log_odds(Counter(x=20, y=1), Counter(x=1, y=20), Counter(x=21, y=21)).set_index("feature")
    assert d.z["x"] > 0 > d.z["y"]


def test_centroid_ba_separable():
    R = np.array([[1, 0], [.9, .1], [0, 1], [.1, .9]]); y = np.array(list("aabb"))
    assert L.centroid_ba(R, y, np.arange(4)) == 1.0
