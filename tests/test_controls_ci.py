import math
import random

import numpy as np
import pytest

from msdecipher import controls_ci as CI
from msdecipher import controls_metrics as M
from msdecipher import controls_text as X
from msdecipher import controls_fetch as F


def test_blocks_and_resampling():
    pages = [["a", "b"], ["c"], ["d", "e", "f"], ["g"]]
    assert CI.make_blocks(pages, 1) == [["a", "b"], ["c"], ["d", "e", "f"], ["g"]]
    assert CI.make_blocks(pages, 2) == [["a", "b", "c"], ["d", "e", "f", "g"]]
    blocks = CI.make_blocks(pages, 1)
    r = CI.resample_blocks(blocks, random.Random(1))
    assert all(w in "abcdefg" for w in r)
    assert CI.resample_blocks(blocks, random.Random(1)) == r                      # deterministic
    ch = CI.chunk_blocks(list("abcdefghi"), 4)
    assert ch == [list("abcd"), list("efghi")]                                    # short tail merged


def test_summarize():
    s = CI.summarize(list(range(101)))
    assert s["mean"] == pytest.approx(50) and s["lo"] == pytest.approx(2.5) and s["hi"] == pytest.approx(97.5)
    assert math.isnan(CI.summarize([1.0])["se"])


def test_interval_verdict_basic():
    fam = [3.0, 3.1, 3.2, 2.9, 3.05]
    assert CI.interval_verdict(3.05, 0.05, fam)["verdict"] == "≈"
    far = CI.interval_verdict(2.0, 0.05, fam)
    assert far["verdict"] == "↓" and far["z"] < -5
    assert CI.interval_verdict(4.0, 0.05, fam)["verdict"] == "↑"
    # too few members -> '?', not a verdict
    assert CI.interval_verdict(2.0, 0.05, [3.0, 3.1])["verdict"] == "?"
    assert CI.interval_verdict(float("nan"), 0.0, fam)["verdict"] == "–"
    # larger MS uncertainty widens the interval
    assert CI.interval_verdict(3.6, 0.0, fam)["verdict"] == "↑"
    assert CI.interval_verdict(3.6, 0.5, fam)["verdict"] == "≈"
    # percentile of MS within the family
    assert CI.interval_verdict(3.05, 0.0, fam)["ms_percentile"] == pytest.approx(0.5)


def test_control_z():
    assert CI.control_z(2.0, 0.1, 3.0, 0.1) == pytest.approx(-1.0 / math.sqrt(0.02))
    assert CI.control_z(1.0, 0.0, 1.0, 0.0) == 0.0
    assert math.isinf(CI.control_z(1.0, 0.0, 2.0, 0.0))


def test_alphabet_adjusted_recovers_linear_trend():
    x = np.log2([20, 22, 24, 26, 28, 30, 33])
    y = 0.8 * x + 0.5 + np.array([0.01, -0.02, 0.0, 0.02, -0.01, 0.0, 0.01])
    on = CI.alphabet_adjusted(x, y, math.log2(25), 0.8 * math.log2(25) + 0.5)
    assert on["verdict"] == "≈" and abs(on["z"]) < 1 and on["slope"] == pytest.approx(0.8, abs=0.05)
    off = CI.alphabet_adjusted(x, y, math.log2(25), 0.8 * math.log2(25) + 1.5)
    assert off["verdict"] == "↑"
    assert CI.alphabet_adjusted(x[:3], y[:3], 4.0, 3.0)["verdict"] == "?"


def test_pmap_matches_serial():
    def f(i):
        return i * i
    assert CI.pmap(f, range(7), workers=3) == [i * i for i in range(7)]
    assert CI.pmap(f, range(3), workers=1) == [0, 1, 4]


def test_normalised_entropies():
    n = M.normalised_entropies({"alphabet_size_ge20": 16, "unit_H1": 4.0, "unit_h2": 3.0, "unit_h3": 2.0, "shuffle_gap_h2": 0.4})
    assert n["unit_H1_norm"] == pytest.approx(1.0)          # uniform over 16 symbols
    assert n["unit_h2_over_H1"] == pytest.approx(0.75)
    assert n["unit_mi_adjacent"] == pytest.approx(1.0)
    assert n["shuffle_gap_over_H1"] == pytest.approx(0.1)
    m = M.metrics(["abc", "abd", "bca"] * 400, seed=1, n_shuffles=1)
    assert "unit_h2_over_H1" in m and 0 <= m["unit_h2_over_H1"] <= 1


def test_perseus_book_text_drops_apparatus_notes():
    xml = (b'<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><div type="edition">'
           b'<div subtype="book" n="1"><p>alpha<note>variant x</note> beta</p></div>'
           b'<div subtype="book" n="2"><p>gamma delta</p></div></div></body></text></TEI>')
    assert X.perseus_book_text(xml, [1]).split() == ["alpha", "beta"]
    assert X.perseus_book_text(xml, [2, 1]).split() == ["gamma", "delta", "alpha", "beta"]


def test_load_windows_are_disjoint_and_size_matched(tmp_path, monkeypatch):
    toks = [f"w{i}" for i in range(250)]
    monkeypatch.setattr(X, "load_tokens", lambda cid, n=None, directory=None, variant="main": toks[:n])
    w = X.load_windows("la_vulgate", 100, max_windows=5)
    assert [len(x) for x in w] == [100, 100]                     # remainder 50 < 0.8*100 dropped
    assert w[0][-1] == "w99" and w[1][0] == "w100"
    w1 = X.load_windows("la_vulgate", 300, max_windows=3)
    assert len(w1) == 1 and len(w1[0]) == 250                    # short text: one shorter window


def test_new_sources_registered():
    ids = {s["id"] for s in F.SOURCES}
    assert {"la_pliny_herbal", "la_pliny_general", "la_celsus", "la_macer", "la_isidore", "it_sidrach", "it_ariosto", "de_faust"} <= ids
    for s in F.SOURCES:
        assert s["licence"] and s["desc"]
    assert "CC BY-SA" in X.source_by_id("la_pliny_herbal")["licence"]


def test_jackknife_helpers():
    g = CI.group_split(list("abcdefghij"), 5)
    assert [len(x) for x in g] == [2] * 5 and sum(g, []) == list("abcdefghij")
    assert CI.leave_out(g, 1) == list("abefghij")
    # jackknife SE of the mean of iid data is close to sd/sqrt(n)
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, 400)
    vals = [np.delete(x, slice(i * 20, (i + 1) * 20)).mean() for i in range(20)]
    assert CI.jackknife_se(vals) == pytest.approx(1 / math.sqrt(400), rel=0.35)
    assert math.isnan(CI.jackknife_se([1.0]))


def test_resampling_with_replacement_lowers_type_count_but_jackknife_does_not():
    words = [f"w{i}" for i in range(2000)]                     # every word once: a strongly 'rich' text
    blocks = CI.group_split(words, 40)
    boot = CI.resample_blocks(blocks, random.Random(3))
    assert len(set(boot)) < 0.75 * len(set(words))             # bootstrap duplicates -> fewer types
    assert len(set(CI.leave_out(blocks, 5))) == len(CI.leave_out(blocks, 5))   # jackknife: no duplicates
