import numpy as np
import pandas as pd
import h17_lib as L


def test_lev():
    assert L.lev("kooiin", "koaiin") == 1 and L.lev("", "abc") == 3 and L.esim("abc", "abc") == 1


def test_tables_wellformed():
    t = pd.read_csv(L.HERE / "data" / "plant_ids.csv")
    assert {"folio", "source", "genus", "family"} <= set(t.columns) and t.notna().all().all()
    assert t.groupby("folio").genus.apply(lambda s: "Viola" in set(s)).get("f9v")
    assert set(pd.read_csv(L.HERE / "data" / "bax_cribs.csv").folio) == {"f2r", "f3v", "f29v", "f41v"}


def test_bstat_weights():
    S = {("a", "b"): (1.0, 1.0, 1.0), ("a", "c"): (0.0, 0.0, 0.0), ("b", "c"): (0.0, 0.0, 0.0)}
    T = {"a": {"X": 2}, "b": {"X": 1}, "c": {"Y": 1}}
    m, n = L.b_stat(T, S, ["a", "b", "c"]); assert n == 1 and np.allclose(m, 1)
    m, n = L.b_stat(T, S, ["a", "b", "c"], min_cons=2); assert n == 0


def test_pairs_and_strata():
    C = L.load(); P = L.pharma_pairs(C)
    assert len(P) >= 10 and all(C["q"].section[t] == "pharmaceutical" for p in P for t in p["pharma_pages"].split())
    for p in P:
        m = L.strata_members(p["herbal"], C)
        assert p["herbal"] in m and all(C["HL"][f] == C["HL"][p["herbal"]] for f in m)
