from collections import Counter
import numpy as np
import h32_lib as L


def test_enc_roundtrip():
    assert L.dec(L.enc("qokchedy")) == "qokchedy" and len(L.enc("cthol")) == 3


def test_rule_context():
    r = L.Rule("", "edy", "$", "ol")
    assert r.apply("^Cedy$") == "^Col$" and r.apply("^edyk$") == "^edyk$"


def test_align_ops():
    assert L.align_ops("^Cedy$", "^Col$") and L.lev("Cedy", "Col") == 3


def test_greedy_learns_suffix_swap():
    A = Counter({"^Col$": 50, "^Sol$": 30, "^dar$": 20}); B = Counter({"^Cedy$": 50, "^Sedy$": 30, "^dar$": 20})
    rules, tr = L.greedy(B, A, L.candidates(B, A, max_d=3))
    assert tr[-1] < 1e-9 and L.rewrite(B, rules) == A


def test_sw_finds_parallel():
    x = list("abcdefghij"); y = list("zzabcdefghzz")
    obs, p, _ = L.sw_test(x, y, n_shuf=50)
    assert obs >= 16 and p < 0.05
