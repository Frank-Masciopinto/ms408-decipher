from collections import Counter
import numpy as np
import h31_lib as L


def test_bayes_finds_shared_suffix():
    ty = Counter({s + x: 3 for s in ("tal", "mor", "pen", "bus", "kir", "dov") for x in ("a", "um", "is")})
    seg, _ = L.seg_bayes(ty, sweeps=150)
    assert np.mean([seg[w][1] in ("a", "um", "is") for w in ty]) > 0.6


def test_metrics_independent_generator_has_low_constraint():
    rng = np.random.default_rng(0); st = ["ka", "pe", "lo", "ri", "mu"]; sx = ["s", "n", "t", ""]
    toks = [st[rng.integers(5)] + sx[rng.integers(4)] for _ in range(3000)]
    seg = {w: ((w[:2], w[2:], [w[:2], w[2:]] if w[2:] else [w])) for w in set(toks)}
    m = L.metrics(toks, [toks[i:i + 100] for i in range(0, 3000, 100)], seg, rng, n_null=40)
    assert abs(m["C1"]) < 0.02 and 0.9 < m["P1"] <= 1.05 and abs(m["A1"]) < 0.02


def test_morphlm_normalisable_ish():
    lm = L.MorphLM(["ab", "abc", "c"] * 10, lambda w: [w[:2], w[2:]] if len(w) > 2 else [w])
    assert lm.logp("ab") > lm.logp("zzzz")
