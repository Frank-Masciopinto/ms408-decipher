import numpy as np
import pandas as pd
import h09_lib as H


def test_words_clean():
    assert H.words("<%>qokeey.dal,ar<->ol{ch}x.da?") == ["qokeey", "dal", "ar"]


def test_holm_monotone():
    a = H.holm([0.01, 0.04, 0.03]); assert np.allclose(sorted(a), a[np.argsort([0.01, 0.04, 0.03])]) and a.max() <= 1


def test_perm_within_keeps_groups():
    g = np.array([0, 0, 1, 1, 1]); P = H.perm_within(g, np.random.default_rng(0), 50)
    assert all((g[p] == g).all() for p in P)


def test_share_stat_signal():
    vals = np.array(["a"] * 10 + ["b"] * 10); types = np.array(["x"] * 10 + ["y"] * 10)
    assert H.share_stat(vals, types) > 0.9
    assert abs(H.share_stat(vals, np.array(["x", "y"] * 10))) < 0.2


def test_pairs_and_tags():
    pairs = H.same_plant_pairs(); assert ("f1v", "f102r1", "Petersen, Stolfi", False) in pairs
    t = pd.read_csv(H.HERE / "data" / "visual_tags.csv"); assert len(t) >= 220 and t.folio.is_unique
    S = H.tag_scores(t); assert S.loc["f78r", "water"] > S.loc["f1v", "water"]


def test_pattern():
    assert H.pattern("stella") == H.pattern("olaiin") and H.struct_score("stella", "olaiin") == 1.0
