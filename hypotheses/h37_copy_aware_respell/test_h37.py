import numpy as np
import h37_lib as S


def test_edit_op_kinds():
    assert S.edit_op("dal", "dar") == ("s", 2, "r")
    assert S.edit_op("dal", "dail") == ("i", 2, "i")
    assert S.edit_op("okal", "kal") == ("d", 0, None)


def test_parents_roots():
    par = S.parents(["daiin", "dain", "chol", "chor", "qokedy"])
    assert par == {"dain": "daiin", "chor": "chol"}


def test_copy_preserved_after_respell():
    words = ["daiin", "chol", "chedy", "qokeedy", "shol", "okaiin"] * 30
    m = S.S35.fit_shape(words); toks = ["daiin", "dain", "chol", "chor", "chorl", "qokedy"] * 5
    out, st = S.respell(toks, m, np.random.default_rng(0))
    assert S.S36.edit_preservation(toks, out)[0] >= 0.5 and st["root"] == 3
