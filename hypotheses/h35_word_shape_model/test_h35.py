import numpy as np
import h35_lib as S

W = ["qokedy", "dal", "okain", "shedy", "lol", "chey", "daiin", "okal"] * 30


def test_sampled_words_use_training_alphabet():
    m = S.fit_shape(W); rng = np.random.default_rng(0)
    assert all(set(S.sample_word(m, rng)) <= set("".join(W)) for _ in range(50))


def test_respell_is_type_level_and_injective():
    toks = ["a", "b", "a", "c", "b", "a"]; out = S.respell(toks, S.fit_shape(W), np.random.default_rng(0))
    assert len(set(out)) == 3 and out[0] == out[2] == out[5] and out[1] == out[4]


def test_ambiguity_final_share():
    a = S.ambiguity([["ay", "yb"]]); assert a["y"][0] == 0.5
