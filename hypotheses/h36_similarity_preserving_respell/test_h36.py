import numpy as np
import h36_lib as S


def test_pos_map_preserves_one_edit():
    gen = ["abc", "abd", "ab", "cab"] * 20; ms = ["xyz", "xyw", "xz", "zxy"] * 20
    m = S.fit_map(gen, ms); a, b = S.apply_map("abc", m), S.apply_map("abd", m)
    assert S.lev(a, b) <= 1 and set(a) <= set("xyzw")


def test_edit_preservation_identity_is_one():
    toks = ["dal", "dar", "dair", "okal"]; assert S.edit_preservation(toks, toks)[0] == 1.0


def test_lev():
    assert S.lev("qokedy", "qokeedy") == 1 and S.lev("", "ab") == 2
