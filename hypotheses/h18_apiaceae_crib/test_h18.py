import numpy as np
import h18_lib as L


def test_shape():
    for w in ("keerodal", "ksheodal", "ke'chdy", "kchdy"): assert L.in_shape(w)
    for w in ("daiin", "chedy", "okedy", "pchodal"): assert not L.in_shape(w)


def test_regex_shape():
    f = L.regex_shape("p", "ol"); assert f("pchol") and not f("chol")


def test_perm_test_detects_planted():
    M = np.zeros((40, 3)); M[:5] = 1; flag = np.zeros(40, bool); flag[:5] = True
    _, _, p = L.perm_test(M, flag, ["a"] * 40, 500); assert (p < 0.01).all()


def test_targets_exclude_discovery_folios():
    C, pool, toks, prim, novat = L.load()
    assert not (set(prim) & L.EXCL) and set(novat) <= set(prim) and "f16v" in novat
