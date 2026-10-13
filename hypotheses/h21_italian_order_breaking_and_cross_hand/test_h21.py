import numpy as np

import h21_lib as L


def test_homophones_reuse_and_range():
    rng = np.random.default_rng(0); out = L.homophones(["ab"] * 200, 4, rng)
    assert set(out) <= {"ab" + s for s in L.SUFS[:4]} and len(out) == 200
    assert sum(a == b for a, b in zip(out, out[1:])) > 100     # recency reuse
    assert L.homophones(["ab", "cd"], 1, rng) == ["ab", "cd"]


def test_shuffle_keeps_line_multisets():
    rng = np.random.default_rng(1); lines = L.to_lines([f"w{i}" for i in range(20)])
    assert [len(l) for l in lines] == [9, 9, 2]
    sh = L.shuffle_lines(lines, rng); assert all(sorted(a) == sorted(b) for a, b in zip(lines, sh))
    assert all(type(x) is str for l in sh for x in l)


def test_nulls_rate_and_encode_info():
    rng = np.random.default_rng(2); lines = L.to_lines(["x"] * 9000)
    out = L.insert_nulls(lines, 0.5, ["n1", "n2"], [.5, .5], rng)
    n = sum(map(len, out)); assert abs((n - 9000) / 9000 - 0.5) < 0.05
    assert L.insert_nulls(lines, 0, ["n"], [1.], rng) is lines
    _, info = L.encode(["a", "b"] * 50, "plain", None, rng, K=2, shuf=True, r=.3, null_dist=(["n"], [1.]))
    assert info["layers"] == 4 and 0 < info["null_share"] < .5


def test_point_match():
    t = dict(D1=-.15, D2=.25, D3=.04, D4=.05, D5=1.8)
    assert L.point_match(t, t)["n_match"] == 5 and L.point_match(t, t)["distance"] == 0
    assert L.point_match(dict(t, D1=.5), t)["n_match"] == 4
