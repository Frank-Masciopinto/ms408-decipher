import numpy as np
import h13_lib as L


def test_tokens_raw_keeps_slots_and_para():
    t, para = L.tokens_raw("<%>fachys.ykal<->ar.{x}dy")
    assert para and [w for w, _ in t] == ["fachys", "ykal", "ar", "?dy"] and not t[3][1]


def test_rule_pairs_prereg_only():
    assert L.rule_pairs(["chedy", "chol", "qokeey", "qokol"]) == [("chedy", "chol", "-edy/-ol")]


def test_ppmi_nonneg_and_cosine():
    M = np.array([[2., 0, 1], [0, 3, 1]]); P = L.ppmi(M)
    assert (P >= 0).all() and np.allclose(np.diag(L.cosine(P + 1e-9)), 1)


def test_unit_edit():
    assert L.unit_edit("chedy", "chedy") == 0 and L.unit_edit("chedy", "shedy") >= 1


def test_token_table_basic():
    d = L.token_table(); P = d[d.gtype == "P"]
    assert len(d) > 30000 and 0.05 < P.line_initial.mean() < 0.2 and P.para_initial.sum() > 100
    assert L.top_words(d)[0] == "daiin"
