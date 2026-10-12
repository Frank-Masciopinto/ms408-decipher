import numpy as np
import h10_lib as L


def test_js_identical_zero_and_disjoint_one():
    X = np.array([[5, 0], [5, 0], [0, 5]], float)
    assert L.js_classes(X[:2], np.array(["a", "b"])) < 1e-12
    assert abs(L.js_classes(X[1:], np.array(["a", "b"])) - 1) < 1e-9


def test_nb_perfect_separation():
    X = np.array([[9, 0], [8, 1], [0, 9], [1, 8]], float); y = np.array(["a", "a", "b", "b"])
    assert L.nb_ba(X, y, np.array([1, 2, 3, 4])) == 1.0


def test_strat_perms_and_rotations_stay_in_stratum():
    st = np.array(list("aaabb")); rng = np.random.default_rng(0)
    for p in L.strat_perms(st, rng, 20) + L.rotations(st, np.arange(5)):
        assert (st[p] == st).all()


def test_r2_bounds():
    rng = np.random.default_rng(1); Y = rng.random((30, 4)); Z = rng.random((30, 3))
    assert 0 <= L.r2(Y, Z) <= 1 and abs(L.r2(Y, Y) - 1) < 1e-9


def test_inventory_finds_q15():
    import pandas as pd
    inv = pd.read_csv(L.HERE / "results" / "inventory.csv")
    assert ((inv.unit == "15") & (inv.by == "section")).any()
