import numpy as np
import h39_lib as S

WORDS = ["daiin", "chol", "chedy", "qokeedy", "shol", "okaiin", "dy", "ar", "chor", "dain"] * 30


def test_slots_and_sub_edges_preserved():
    assert [S.slot(i, 7) for i in range(7)] == ["0", "1", "2", "mid", "-3", "-2", "-1"]
    maps = S.init_maps(WORDS, list(reversed(WORDS)))
    assert S.E_of([("chol", "chor"), ("daiin", "dain")], maps) >= .5


def test_anneal_runs():
    lines = [WORDS[i:i + 9] for i in range(0, 270, 9)]; tgt = S.Target(WORDS, lines)
    maps, info = S.anneal(WORDS * 2, tgt, WORDS, np.random.default_rng(0), steps=20, nsample=300)
    assert 0 <= info["E"] <= 1 and set(maps) == set(S.SLOTS)


def test_tuned_copier_and_proxy():
    m = S.S38.S35.fit_shape(WORDS); fd = S.S38.final_dist(WORDS)
    a = S.tuned_copier(400, m, fd, np.random.default_rng(1), p_fresh=.05, window=5, p0=.5)
    b = S.tuned_copier(400, m, fd, np.random.default_rng(1), p_fresh=.9, window=5, p0=.5)
    assert len(a) == 400 and S.copy_proxy(a) > S.copy_proxy(b)
