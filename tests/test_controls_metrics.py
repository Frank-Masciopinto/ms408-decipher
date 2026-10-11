import math

import pandas as pd
import pytest

from msdecipher import controls_metrics as M
from msdecipher import controls_run as R
from msdecipher import controls_text as X
from msdecipher import controls_transforms as T


def test_edit_distance_le1():
    assert M.edit_distance_le1("abc", "abc")
    assert M.edit_distance_le1("abc", "abd")
    assert M.edit_distance_le1("abc", "ab")
    assert M.edit_distance_le1("ab", "abc")
    assert M.edit_distance_le1("abc", "xabc")
    assert not M.edit_distance_le1("abc", "bca")
    assert not M.edit_distance_le1("abc", "a")


def test_repeat_rates():
    ident, near = M.repeat_rates(["a", "a", "ab", "xyz", "xyz"])
    assert ident == pytest.approx(2 / 4)     # (a,a) and (xyz,xyz)
    assert near == pytest.approx(1 / 4)      # (a,ab)
    assert math.isnan(M.repeat_rates(["x"])[0])


def test_positional_skew_detects_positional_units():
    # 'q' only initial, 'y' only final, 'o' only medial
    words = [tuple("qoy")] * 200 + [tuple("qooy")] * 200
    r = M.positional_skew(words, min_count=50)
    assert r["pos_jsd_initial_final"] == pytest.approx(1.0)
    assert r["pos_skewed_unit_share"] == pytest.approx(1.0)
    # position-free text: random letters -> no skew
    free = T.iid_letters(["abcdefgh"] * 50, 4000, 1)
    r2 = M.positional_skew([tuple(w) for w in free], min_count=50)
    assert r2["pos_jsd_initial_final"] < 0.05 and r2["pos_skewed_unit_share"] < 0.2


def test_metrics_keys_and_known_values():
    words = T.slot_grammar(3000, 1)
    m = M.metrics(words, seed=1, n_shuffles=2)
    for k in M.METRIC_INFO:
        assert k in m, k
    assert m["n_tokens"] == 3000
    assert 0 < m["type_token_ratio"] <= 1
    assert m["shuffle_gap_h2"] > 0.2          # slot words lose structure when shuffled
    iid = M.metrics(T.iid_letters(words, 3000, 1), seed=1, n_shuffles=2)
    assert abs(iid["shuffle_gap_h2"]) < 0.1   # nothing to destroy


def test_metrics_respects_segmenter():
    from msdecipher.segment import Segmenter
    words = ["chedy", "shedy", "qokedy", "chol"] * 100
    a = M.metrics(words, Segmenter.preset("raw"), n_shuffles=1)
    b = M.metrics(words, Segmenter.preset("collapsed"), n_shuffles=1)
    assert a["mean_word_length_units"] > b["mean_word_length_units"]


def test_verdict():
    assert M.verdict(1.0, 0.9, 1.1, 0.0) == "≈"
    assert M.verdict(1.3, 0.9, 1.1, 0.1) == "↑"
    assert M.verdict(0.5, 0.9, 1.1, 0.1) == "↓"
    assert M.verdict(1.15, 0.9, 1.1, 0.1) == "≈"
    assert M.verdict(float("nan"), 0.9, 1.1, 0.1) == "–"


def test_normalise_and_strip():
    assert X.normalise_word_text("Æneas, vivat! [3] {iv} 12") == ["aeneas", "vivat"]
    toks = X.normalise_word_text("In principio creavit Deus; jam VIDIT 12 [x] l'amor straße")
    assert toks == ["in", "principio", "creavit", "deus", "jam", "vidit", "l", "amor", "strasse"]
    lat = X.normalise_word_text("creavit jam", latin=True)
    assert lat == ["creauit", "iam"]
    raw = "front\n*** START OF THE PROJECT GUTENBERG EBOOK X ***\nbody text\n*** END OF THE PROJECT GUTENBERG EBOOK X ***\nlicence"
    assert X.strip_gutenberg(raw).strip() == "body text"
    wt = "{{titulus|x}}\n==Caput 1==\n<sup>1</sup> In principio [[creavit|creauit]] Deus"
    assert X.normalise_word_text(X.clean_wikitext(wt)) == ["in", "principio", "creauit", "deus"]


def test_load_tokens_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        X.load_tokens("la_vulgate", 10, directory=tmp_path)


def test_family_verdicts_on_handmade_table():
    cols = {m: 1.0 for m in M.METRIC_INFO}
    rows = {R.MS_MAIN: dict(family="MS 408", base="-", **{**cols, "unit_h2": 2.2}),
            R.MS_RAW: dict(family="MS 408", base="-", **{**cols, "unit_h2": 2.0}),
            "natural_a": dict(family="nat", base="x", **{**cols, "unit_h2": 3.2}),
            "natural_b": dict(family="nat", base="x", **{**cols, "unit_h2": 3.0}),
            "natural_c": dict(family="nat", base="x", **{**cols, "unit_h2": 3.1}),
            "natural_d": dict(family="nat", base="x", **{**cols, "unit_h2": 3.15}),
            "slot_a": dict(family="slot", base="-", **{**cols, "unit_h2": 2.3}),
            "slot_b": dict(family="slot", base="-", **{**cols, "unit_h2": 2.1}),
            "slot_c": dict(family="slot", base="-", **{**cols, "unit_h2": 2.2}),
            "pair_a": dict(family="pair", base="-", **{**cols, "unit_h2": 2.2}),
            "pair_b": dict(family="pair", base="-", **{**cols, "unit_h2": 2.3})}
    comp = pd.DataFrame.from_dict(rows, orient="index")
    ranges, verd, summ = R.family_verdicts(comp, {"collapsed": {"unit_h2": 0.05}, "raw": {}})
    v = verd.set_index(["family", "metric"])
    assert v.loc[("nat", "unit_h2"), "verdict_collapsed"] == "↓"
    assert v.loc[("nat", "unit_h2"), "z_collapsed"] < -5
    assert v.loc[("slot", "unit_h2"), "verdict_collapsed"] == "≈"
    assert v.loc[("nat", "unit_H1"), "verdict_collapsed"] == "≈"      # identical values: zero spread, MS equal -> inside
    assert v.loc[("pair", "unit_h2"), "verdict_collapsed"] == "?"      # 2 members: no honest SD
    assert summ.iloc[0]["family"] in ("slot", "nat")


def test_run_controls_end_to_end_small(tmp_path, monkeypatch):
    base = ("in principio creavit deus caelum et terram terra autem erat inanis et vacua "
            "tenebrae erant super faciem abyssi spiritus dei ferebatur super aquas dixitque fiat lux").split()
    def fake_windows(cid, n_tokens=0, max_windows=None, variant="main", directory=None, min_share=0.8):
        return [(base * 100)[:n_tokens], (base * 100)[7:n_tokens + 7]]
    monkeypatch.setattr(R, "load_windows", fake_windows)
    monkeypatch.setattr(R, "ms_variants", lambda *a, **k: ({}, None))
    res = R.run_controls(n_tokens=800, seeds=1, out_dir=tmp_path, make_plots=True, quiet=True, boot=0, control_jack=3, workers=1)
    df = pd.read_csv(tmp_path / "comparison.csv")
    assert {"plain:la_vulgate", "plain:la_vulgate@w1", "selfcitation_p0.3", "naibbe_like:it_manzoni"} <= set(df["name"])
    assert (tmp_path / "comparison_ci.csv").exists()
    assert (tmp_path / "comparison.md").exists() and (tmp_path / "comparison_runs.csv").exists()
    assert (tmp_path / "figures" / "scatter_panels.png").exists()
    assert "undeciphered" in (tmp_path / "comparison.md").read_text(encoding="utf-8")
