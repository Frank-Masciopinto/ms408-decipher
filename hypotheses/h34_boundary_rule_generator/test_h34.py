import numpy as np

import h34_lib as L

LINES = [["qokedy", "dal", "okain", "shedy", "lol", "chey"], ["dain", "nol", "lchedy", "yshey", "daiin", "okal"]] * 20


def test_rule_keeps_inventory_and_strength0_is_identity():
    toks = [w for l in LINES for w in l]; r = L.fit_table(LINES)
    out0 = [w for l in L.apply_rule(toks, r, 0.0, np.random.default_rng(0)) for w in l]
    out2 = [w for l in L.apply_rule(toks, r, 2.0, np.random.default_rng(0)) for w in l]
    assert out0 == toks and sorted(out2) == sorted(toks)


def test_shuffle_table_permutes_rows():
    r = L.fit_table(LINES); s = L.shuffle_table(r, np.random.default_rng(1))
    assert set(s) == set(r) and sorted(map(str, s.values())) == sorted(map(str, r.values()))


def test_junction_positive_for_linked_pairs():
    assert L.junction(LINES, np.random.default_rng(0)) > 0
