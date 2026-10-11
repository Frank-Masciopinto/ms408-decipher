import random
from collections import Counter

import numpy as np
import pytest

from msdecipher import mech_grammars as G


def test_zattera_table_and_segmentation():
    assert len(G.ZATTERA_SLOTS) == 12
    assert G.zattera_segment("qokeedy") == ("q", "o", "k", "ee", "d", "y")
    assert G.zattera_segment("ckhey") == ("ckh", "e", "y")
    assert G.zattera_segment("daiin") == ("d", "a", "ii", "n")
    assert G.zattera_segment("xyz") is None


def test_zattera_covers_standard_words_only_in_slot_order():
    words = {("q", "o", "k", "ee", "d", "y"): 5, ("d", "a", "ii", "n"): 5, ("ch", "e", "d", "y"): 5, ("o", "l"): 3}
    m = G.SlotModel(mask=G.ZATTERA_SLOTS, order=0).fit(words, iters=15)
    assert m.covered([("q", "o", "k", "ee", "d", "y"), ("y", "q")]).tolist() == [True, False]    # y precedes q: wrong slot order
    # probability mass outside the table is exactly zero
    assert float(m.P[~m.M].sum()) == 0.0
    assert np.isfinite(m.logprob2([("d", "a", "ii", "n")])).all()


def test_slot_bigram_fits_a_planted_dependency_better_than_slot_grammar():
    """Word = a b | c d only: slots alone cannot encode the pairing, the conditioned model can."""
    rng = random.Random(0)
    data = Counter(rng.choice([("a", "b"), ("c", "d")]) for _ in range(400))
    train = dict(data)
    s0 = G.SlotModel(K=4, order=0).fit(train, iters=30, seed=1)
    s1 = G.SlotModel(K=4, order=1, beta=0.5).fit(train, iters=30, seed=1)
    test = [("a", "b"), ("c", "d")] * 20
    assert s1.logprob2(test, 1e-3).mean() > s0.logprob2(test, 1e-3).mean() + 0.3
    bad = [("a", "d")] * 10
    assert s1.logprob2(bad, 1e-3).mean() < s1.logprob2(test, 1e-3).mean() - 2


def test_slot_model_sampling_roundtrip():
    train = {("q", "o", "k", "ee", "d", "y"): 30, ("d", "a", "ii", "n"): 50, ("ch", "e", "d", "y"): 40}
    m = G.SlotModel(mask=G.ZATTERA_SLOTS, order=1, beta=0.5).fit(train, iters=20)
    smp = m.sample(200, random.Random(1))
    assert all(m.covered([w])[0] for w in smp)


def test_stolfi_grammar_unambiguous_and_probabilities():
    g = G.StolfiGrammar()
    assert g.n_rules() >= 90
    for nt, alts in g.probs.items():
        assert abs(sum(alts) - 1) < 1e-9, nt
    rng = random.Random(3)
    for w in g.sample(60, rng):
        assert g.prob(w) > 0
        assert abs(g.prob(w) - g.inside_prob(w)) <= 1e-9 * g.prob(w)     # unique derivation: fast path == sum over parses
    assert g.prob("daiin") > 0 and g.prob("chedy") > 0 and g.prob("qokeedy") > 0
    assert g.prob("xyz") == 0 and g.prob("qq") == 0


def test_stolfi_refit_counts_rules():
    g = G.StolfiGrammar()
    wts = {"daiin": 100, "chedy": 80, "ol": 60}
    cov = g.refit(wts, alpha=0.0)
    assert cov == 240
    # the refit grammar puts all its mass on the observed derivations: probability of an unseen word drops
    assert g.prob("daiin") > G.StolfiGrammar().prob("daiin")


def test_compare_grammars_runs_and_orders_models_on_a_structured_toy():
    rng = random.Random(0)
    pre, mid, suf = ["", "q", "o"], ["ch", "sh", "k"], ["y", "dy", "aiin", "ol"]
    words = ["".join([rng.choice(pre), rng.choice(mid), rng.choice(suf)]) for _ in range(3000)]
    blocks = [i // 100 for i in range(len(words))]
    seg = lambda w: tuple(G.zattera_segment(w) or w)
    res = G.compare_grammars(words, blocks, seg, K=6, n_folds=2,
                             models_fn=lambda: [G.LearnedUnit(seg, "unigram"), G.LearnedUnit(seg, "bigram"),
                                                G.LearnedUnit(seg, "slot", 6, iters=10), G.Escaped(seg, "zattera"),
                                                G.Escaped(seg, "stolfi")])
    uni = res["letter unigram"]["bits_tok"]
    assert res["letter-pair (bigram) baseline"]["bits_tok"] < uni
    assert res["learned slot grammar (K=6)"]["bits_tok"] < uni
    assert 0 < res["Stolfi grammar (rule probs re-fitted)"]["cov_tok"] <= 1
