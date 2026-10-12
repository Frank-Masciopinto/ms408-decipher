import numpy as np
import pandas as pd
import h14_lib as L


def _toy():
    rows = []
    for l in range(200):
        ws = ["a"] + ["b"] * 4 + ["c"]
        for i, w in enumerate(ws): rows.append(dict(w=w, lid=str(l), S=str(l % 2), is_init=i == 0, is_final=i == 5, ulen=len(w)))
    return pd.DataFrame(rows)


def test_strat_null_detects_fixed_initial():
    d = _toy(); r = L.strat_null(d, ["a", "b"], "is_init", "S", n=2000)
    assert r["a"][0] == 200 and r["a"][1].mean() < 50 and L.mc_p(*r["a"]) < .01
    assert r["b"][0] == 0


def test_line_null_mean():
    d = _toy(); r = L.line_null(d, ["a"], "is_init", n=2000)
    assert abs(r["a"][1].mean() - 200 / 6) < 3


def test_final_length_null_equal_when_uniform():
    d = _toy(); d["ulen"] = 3; f = L.final_length(d, "S")
    assert f["obs_mean"] == f["null_mean"] == 3


def test_table_columns():
    d = L.table()
    assert {"S1", "S1L", "gapshort", "first_line"} <= set(d.columns) and d.is_init.sum() > 3000
