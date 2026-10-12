import numpy as np
import pandas as pd
import h15_lib as L


def test_dl_homogeneous():
    r = L.dersimonian_laird(np.array([.5, .5, .5]), np.array([.1, .1, .1]))
    assert abs(r["ratio"] - np.exp(.5)) < 1e-9 and r["I2"] == 0 and r["tau2"] == 0


def test_dl_heterogeneous():
    r = L.dersimonian_laird(np.array([-1., 0, 1, 2]), np.array([.01] * 4))
    assert r["I2"] > .9 and r["tau2"] > 0


def test_expected_matches_simple():
    d = pd.DataFrame(dict(w=["a", "b", "b", "b"], S1=["x"] * 4, is_init=[True, False, False, False]))
    o, e, v = L.expected(d, ["a"]); assert o == 1 and abs(e - .25) < 1e-12 and v > 0


def test_onset_and_pct():
    assert L.onset("qokedy") == "qok" and L.onset("chol") == "ch" and L.onset("ol") is None
    assert L.pct(np.array([.1, .9, .5]), 1, [0, 1, 2]) == 1.0
