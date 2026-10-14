import numpy as np
import h38_lib as S

WORDS = ["daiin", "chol", "chedy", "qokeedy", "shol", "okaiin", "dy", "ar"] * 30


def test_families_connected():
    fam = S.families(["daiin", "dain", "dan", "dal", "chol"])
    assert [r for r, _ in fam] == ["daiin", "chol"] and len(fam[0][1]) == 3


def test_siblings_stay_near():
    m = S.S35.fit_shape(WORDS); fd = S.final_dist(WORDS)
    toks = ["chol", "chor", "chod", "chos", "daiin"] * 5
    out, st = S.fam_respell(toks, m, fd, np.random.default_rng(0))
    assert S.S36.edit_preservation(toks, out)[0] >= .8 and st["root"] == 2


def test_native_copier_and_js():
    m = S.S35.fit_shape(WORDS); fd = S.final_dist(WORDS)
    out = S.native_copier(500, m, fd, np.random.default_rng(1))
    assert len(out) == 500 and all(out) and S.js_final(out, WORDS) < .3 and S.js_final(WORDS, WORDS) == 0
