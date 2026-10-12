import importlib.util
import sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("run_h12", Path(__file__).with_name("run_h12.py")); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)


def test_top_js_identity_and_bounds():
    w = ["a", "b", "b", "c"] * 50
    assert R.top_js(w, w) < 1e-12 and 0 < R.top_js(["x"] * 200, w) <= 1


def test_rewrite_helper():
    assert R._rw("chedy", [("end", "edy", "ol")]) == "chol"


def test_results_cover_predictions():
    import pandas as pd
    s = pd.read_csv(Path(__file__).with_name("results") / "scores.csv")
    assert {"OWN", "POOLED", "SHUF"} <= set(s.model) and s.model.str.startswith("MAPPED").any()
