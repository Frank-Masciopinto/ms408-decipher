import pandas as pd
import h16_lib as L


def test_strip_onset():
    assert L.strip("dshedy") == "shedy" and L.strip("daiin") == "aiin" and L.strip("dy") is None and L.strip("chol") is None
    assert L.onset("chedy", L.SECONDARY) == "ch"


def test_attr_test_detects_initial_attribute():
    rows = [dict(lid=str(l), x=float(i == 0), is_init=i == 0, S1="a") for l in range(100) for i in range(5)]
    r = L.attr_test(pd.DataFrame(rows), "x"); assert r["obs"] == 100 and abs(r["exp"] - 20) < 1e-9 and r["z"] > 10


def test_open_search_runs():
    rows = [dict(w=("q" if i == 0 else "b"), lid=str(l), is_init=i == 0, is_final=i == 4, S1="a") for l in range(60) for i in range(5)]
    r = L.open_search(pd.DataFrame(rows))
    assert r[(r.word == "q") & (r.slot == "is_init")].ratio.iloc[0] > 3
