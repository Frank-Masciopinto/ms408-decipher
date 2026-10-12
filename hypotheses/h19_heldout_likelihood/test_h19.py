import itertools
import math

import numpy as np
import pytest

import h19_lib as L

pytest.importorskip("rapidfuzz")


def test_charlm_normalises_over_short_strings():
    G = L.CharLM(3).fit(["ab", "ba", "a", "abb"])
    tot = sum(2 ** G.logp("".join(s)) for n in range(0, 7) for s in itertools.product("ab", repeat=n))
    assert 0.8 < tot <= 1.0 + 1e-9


def test_kn_probs_bounded_and_context_helps():
    G = L.CharLM(3).fit(list("abcab"))
    kn = L.KN(2, G).fit([["x", "y"] * 50])
    assert 0 < kn.prob("y", ["x"]) <= 1 and kn.prob("y", ["x"]) > kn.prob("x", ["x"])
    assert sum(kn.prob(w, ["x"]) for w in ["x", "y"]) <= 1 + 1e-9


def test_copy_em_recovers_rate():
    rng = np.random.default_rng(0); vocab = [f"w{i}q" for i in range(400)]; pages = []
    for _ in range(40):
        ws = []
        for i in range(100):
            ws.append(ws[-rng.integers(1, min(5, i) + 1)] if i and rng.random() < .3 else vocab[rng.integers(400)])
        pages.append(ws)
    G = L.CharLM(3).fit([w for p in pages for w in p]); base = np.full(sum(map(len, pages)), math.log2(1 / 400))
    cd = L.CopyData(pages, Wmax=5); th, _ = L.copy_em(base, cd, L.char_unigram_log(vocab), 5)
    assert abs(th["lam"] - .3) < .05 and th["pk"] > .9


def test_naibbe_decodes_own_ciphertext():
    from msdecipher.mech_naibbe import NaibbeCipher, clean_plaintext
    ct = NaibbeCipher().encrypt("in principio creauit deus caelum et terram".split(), seed=1)
    nl = L.NaibbeLM(L.LetterLM(3).fit(clean_plaintext("in principio erat uerbum et uerbum erat apud deum" * 20)))
    assert (nl.page_probs(ct) > 0).all()


def test_onset_and_mix():
    assert L.onset_parts("dshedy") == ("d", "shedy") and L.onset_parts("dy") == (None, None)
    a = np.log2(np.full(1000, .5)); b = np.log2(np.r_[np.full(500, .9), np.full(500, .1)])
    assert 0 <= L.mix_em(a, b) <= 1
