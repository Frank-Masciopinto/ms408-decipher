import itertools
import math
import random
import warnings

import numpy as np
import pytest

from msdecipher import controls_transforms as T
from msdecipher import slot_grammar as SG
from msdecipher import word_classes as WC
from msdecipher import word_structure as WS

warnings.filterwarnings("ignore")


def _planted(n=3000, seed=0):
    """Words from a 3-slot grammar: slot1 in {q, s} (p=.5), slot2 in {o, a}, slot3 in {d, k, y}."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        w = []
        if rng.random() < 0.5:
            w.append(rng.choice("qs"))
        w.append(rng.choice("oa"))
        w.append(rng.choice("dky"))
        out.append(tuple(w))
    return out


def test_slot_grammar_probabilities_sum_to_one():
    g = SG.SlotGrammar(K=3, floor=0.0)
    g.units = ["a", "b"]
    g.idx = {"a": 0, "b": 1}
    g.P = np.array([[0.7, 0.3], [0.2, 0.8], [0.5, 0.5]])
    g.e = np.array([0.6, 0.3, 0.9])
    total = math.prod(1 - g.e)                                            # the empty word
    for L in (1, 2, 3):
        words = list(itertools.product("ab", repeat=L))
        total += float((2.0 ** g.logprob2(words, floor=1e-12)).sum())
    assert total == pytest.approx(1.0, abs=1e-6)


def test_slot_grammar_recovers_planted_structure_and_covers():
    words = _planted()
    cnt = SG.word_counts(words)
    g = SG.SlotGrammar(K=6).fit({w: 1.0 for w in cnt}, iters=40, restarts=2)
    assert g.covered(list(cnt)).all()
    assert not g.covered([("d", "d", "d")])[0] and not g.covered([("o", "q", "d")])[0]   # order violations / unseen pattern
    assert g.n_params() < 40
    # the planted grammar is better described by slots than by a within-word bigram on held-out words
    train, test = words[:2000], words[2000:]
    tr = SG.word_counts(train)
    gs = SG.SlotGrammar(K=6).fit(dict(tr), iters=40, restarts=2)
    bg = SG.UnitNgram(1).fit(dict(tr))
    te = list(dict.fromkeys(test))
    assert -gs.logprob2(te, 1e-3).mean() <= -bg.logprob2(te, 0.05).mean() + 0.05


def test_unit_ngram_orders():
    cnt = {("a", "b"): 10, ("a", "b", "a"): 5, ("b", "a"): 3}
    uni, big = SG.UnitNgram(0).fit(cnt), SG.UnitNgram(1).fit(cnt)
    w = [("a", "b"), ("b", "b", "b")]
    assert big.logprob2(w)[0] > big.logprob2(w)[1]
    assert uni.n_params() == 3 and big.n_params() >= uni.n_params()   # 2 units + end symbol
    assert big.seen_bigrams_cover(w).tolist() == [True, False]


def test_affix_model_finds_planted_affixes():
    rng = random.Random(1)
    cores = ["".join(rng.choice("kdlr") for _ in range(rng.randint(2, 3))) for _ in range(60)]
    words = {}
    for c in cores:
        for p in ("", "qo", "s"):
            for s in ("", "y", "in"):
                words[tuple(p + c + s)] = 1.0
    am = SG.AffixModel(iters=4).fit(words)
    st = am.stats(words)
    pre = {"".join(a) for a, _ in am.top_affixes(10)[0]}
    suf = {"".join(a) for a, _ in am.top_affixes(10)[1]}
    assert "qo" in pre or "s" in pre
    assert "y" in suf or "in" in suf
    assert 0.03 < st["cores_per_type"] < 0.2     # ~50 distinct cores over 540 types


def test_structure_metrics_planted_vs_shuffled():
    toks = _planted(4000, 2)
    blocks = [i // 200 for i in range(len(toks))]
    m = WS.structure_metrics(toks, blocks, K=6, n_folds=3, iters=20, affix=True)
    assert m["slot_null_gap_type"] > 0.3 and m["slot_null_gap_tok"] > 0.3          # shuffling inside words hurts a positional grammar
    assert m["bits_type_slot"] < m["bits_type_unigram"]
    assert m["cov_slot_type"] > 0.95 and m["share_over_K"] == 0
    for k in ("slot_gain_frac_type", "mdl_type_slot", "affix_prefix_type_share", "oov_type_share"):
        assert k in m
    # a text with no positional structure: no gap
    rng = random.Random(0)
    iid = [tuple(rng.choice("abcdefgh") for _ in range(rng.randint(2, 5))) for _ in range(4000)]
    m2 = WS.structure_metrics(iid, [i // 200 for i in range(4000)], K=6, n_folds=3, iters=20, affix=False)
    assert abs(m2["slot_null_gap_type"]) < 0.15


def test_structure_metrics_excludes_long_words():
    toks = [tuple("abcdefghijklmn")] * 5 + _planted(500, 3)
    m = WS.structure_metrics(toks, [i // 50 for i in range(len(toks))], K=6, n_folds=2, iters=10, null=False, affix=False)
    assert m["share_over_K"] == pytest.approx(5 / len(toks))


def _classed_corpus(n=12000, seed=0):
    """Words of 4 planted classes, class sequence from a Markov chain with strong structure."""
    rng = random.Random(seed)
    vocab = {c: [f"{c}{i}" for i in range(12)] for c in "ABCD"}
    nxt = {"A": "B", "B": "C", "C": "D", "D": "A"}
    c = "A"
    toks = []
    for _ in range(n):
        toks.append(rng.choice(vocab[c]))
        c = nxt[c] if rng.random() < 0.9 else rng.choice("ABCD")
    return toks


def test_class_metrics_find_planted_classes_and_null_is_flat():
    toks = _classed_corpus()
    c = WC.chunk_corpus(toks, 300)
    m = WC.class_metrics(c, None, features="neighbour", k=4, B=6, n_splits=3, n_vocab=48, n_ctx=48)
    assert m["class_mi_excess_k5"] > 0.5
    assert m["k5_ari_boot"] > 0.6
    sh = list(toks)
    random.Random(1).shuffle(sh)
    m0 = WC.class_metrics(WC.chunk_corpus(sh, 300), None, features="neighbour", k=4, B=6, n_splits=3, n_vocab=48, n_ctx=48)
    assert m0["class_mi_excess_k5"] < 0.05
    assert m0["k5_ari_boot"] < m["k5_ari_boot"]


def test_class_metrics_line_features_need_line_ids():
    toks = _classed_corpus(3000)
    lines = [i // 8 for i in range(len(toks))]
    c = WC.Corpus(toks, [i // 400 for i in range(len(toks))], lines, [i % 40 == 0 for i in range(len(toks))],
                  {"section": ["h" if i < 1500 else "s" for i in range(len(toks))], "language": ["A"] * len(toks), "hand": ["1"] * len(toks)})
    m = WC.class_metrics(c, None, features="full", k=4, B=4, n_splits=2, n_vocab=48, n_ctx=48)
    assert m["n_vocab"] == 48 and "k5_ari_split" in m


def test_adjacent_class_mi_basic():
    toks = list("ababababab")
    mi, h, n = WC.adjacent_class_mi(toks, {"a": 0, "b": 1})
    assert mi == pytest.approx(1.0, abs=0.01) and h == pytest.approx(1.0, abs=0.01) and n == 9
