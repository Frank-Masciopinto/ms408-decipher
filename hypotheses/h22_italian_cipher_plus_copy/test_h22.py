import numpy as np

import h22_lib as L


def test_copy_layer_rate_and_labels():
    toks = [f"qo{i % 50}" for i in range(4000)]; labs = list(range(4000))
    out, ol, n = L.copy_layer(toks, labs, .2, 5, seed=1)
    assert len(out) == 4000 and abs(n / 4000 - .2) < .03 and sum(l is None for l in ol) == n
    assert L.copy_layer(toks, labs, 0, 5, 1)[0] == toks


def test_build_clean_nulls_come_from_own_ciphertext():
    rng = np.random.default_rng(0); nb = ["aa", "bb", "cc"] * 300
    lines, labs, info = L.build(None, "naibbe", None, nb, rng, r=.5, nulls="clean")
    assert set(w for l in lines for w in l) <= {"aa", "bb", "cc"} and 0.6 < info["signal_share"] < 0.75 and info["layers"] == 2


def test_recovery_bounds():
    r = L.plaintext_recovery(["x", "y", "x", "z"], ["a", "b", "a", None])
    assert r["oracle_acc"] == .75 and abs(r["mi_frac"] - 1) < 1e-9
    r = L.plaintext_recovery(["x"] * 4, ["a", "b", "a", "b"]); assert r["mi_frac"] == 0
