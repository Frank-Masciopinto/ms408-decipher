"""Tests for h05 (run: pytest hypotheses/h05_zodiac_cribs -q)."""
import random
from collections import Counter

import numpy as np
import pytest

import h05_lib as L


@pytest.fixture(scope="module")
def df():
    return L.extract_loci()


def test_twelve_pages_ten_signs():
    assert len(L.PAGES) == 12 and len(set(L.PAGE_SIGN.values())) == 10
    assert set(L.SIGNS) == set(L.PAGE_SIGN.values()) and not set(L.MISSING) & set(L.SIGNS)
    # Aries and Taurus appear twice
    assert Counter(L.PAGE_SIGN.values())["Aries"] == 2 and Counter(L.PAGE_SIGN.values())["Taurus"] == 2


def test_extraction_counts(df):
    lab = L.labels(df)
    assert len(lab) == 299
    per = lab.groupby("folio").size()
    assert per["f70v1"] == per["f71r"] == per["f71v"] == per["f72r1"] == 15
    assert per["f72r2"] == 29 and per["f72v1"] == 30
    ring = L.ring_text(df).groupby("folio").size()
    assert ring["f72r3"] == 4 and ring["f73v"] == 3
    # bands: Aries pages have 5 inner + 10 outer nymphs; Scorpio/Sagittarius have 4 'top' (overflow) nymphs
    b = lab.groupby(["folio", "band"]).size()
    assert b["f70v1", "inner"] == 5 and b["f70v1", "outer"] == 10
    assert b["f73r", "top"] == 4 and b["f73v", "top"] == 4


def test_roman_month_words_are_not_in_transcription(df):
    words = {w for ws in df.words for w in ws}
    for roman in ("mars", "abril", "may"):
        assert roman not in words


def test_name_lists_aligned():
    nl = L.name_lists()
    assert all(len(v) == 12 for v in nl.values())
    assert nl["sign:latin"][1] == nl["sign:latin"][2] == "aries"
    assert L.names_by_sign(nl["month:latin"])[0] == "martius"
    assert L.strip_marks("Löwe") == "lowe" and L.strip_marks("Àries") == "aries"


def test_pattern_and_holm():
    assert L.pattern("novembre") == (0, 1, 2, 3, 4, 5, 6, 3)
    assert L.pattern(("a", "b", "a")) == L.pattern("xyx")
    h = L.holm({"a": 0.01, "b": 0.02, "c": 0.5})
    assert h["a"] == pytest.approx(0.03) and h["b"] == pytest.approx(0.04) and h["c"] == pytest.approx(0.5)
    assert all(h[k] >= p for k, p in {"a": 0.01, "b": 0.02, "c": 0.5}.items())


def test_perm_corr_detects_perfect_order_and_not_noise():
    x = list(range(10))
    r, p = L.perm_corr_p(x, [i * 2 + 1 for i in x], 5000)
    assert r == pytest.approx(1.0) and p < 0.001
    rng = np.random.default_rng(1)
    ps = [L.perm_corr_p(list(range(10)), rng.permutation(10).tolist(), 2000, seed=s)[1] for s in range(20)]
    assert np.mean(np.array(ps) < 0.05) < 0.3


def test_similarity_and_same_sign_test_on_planted_pages():
    # two pairs of pages share a private vocabulary; the others are different
    rng = random.Random(0)
    base = {"f70v1": "otal okal otar", "f71r": "otal okal otar", "f71v": "chedy shedy qokain", "f72r1": "chedy shedy qokain"}
    wp = {f: (s.split() * 10) for f, s in base.items()}
    for f, s in {"f70v2": "dar daiin sal", "f72r2": "ykeey chol sheol", "f72r3": "lkar aral ol", "f72v3": "tol cthy ydy", "f72v2": "okeo opchy rar",
                 "f72v1": "aiin air am", "f73r": "kchor lchedy sor", "f73v": "teody cheo ken"}.items():
        wp[f] = s.split() * 10
    wp = {f: wp[f] for f in L.FOLIOS}
    S = L.page_similarity(wp, "type")
    assert S.loc["f70v1", "f71r"] == pytest.approx(1.0) and S.loc["f70v1", "f71v"] < 0.1
    r = L.same_sign_pair_test(S, 3000)
    assert r["p_random_pair_of_pairs"] < 0.01 and r["obs_mean_same_sign_pairs"] > r["mean_adjacent_different_sign"]


def test_group_cohesion_exact_counts():
    import pandas as pd
    idx = L.FOLIOS
    M = pd.DataFrame(np.full((12, 12), 0.2), index=idx, columns=idx)
    for a in ["f72v2", "f72v1", "f73r", "f73v"]:
        for b in ["f72v2", "f72v1", "f73r", "f73v"]:
            M.loc[a, b] = 0.9
    r = L.group_cohesion_test(M, ["f72v2", "f72v1", "f73r", "f73v"])
    assert r["n_subsets"] == 495 and r["p_all_subsets"] == pytest.approx(1 / 495) and r["n_windows"] == 9
    assert r["p_contiguous_windows"] == pytest.approx(1 / 9)   # the group is itself a contiguous window: the adjacency-matched null cannot reject


def test_classification_planted_vs_null():
    rng = random.Random(0)
    pages = {}
    for i, f in enumerate(L.FOLIOS[:4]):
        pool = ["".join(rng.choice("acdehklorty") for _ in range(5)) for _ in range(6)]
        pages[f] = [rng.choice(pool) for _ in range(40)]
    r = L.label_classification(pages, 20)
    assert r["acc"] > 0.5 and r["p"] < 0.1
    noise = {f: ["".join(rng.choice("acdehklorty") for _ in range(5)) for _ in range(40)] for f in L.FOLIOS[:4]}
    r2 = L.label_classification(noise, 20)
    assert r2["acc"] < 0.45


def test_isomorph_index_exact():
    rng = random.Random(3)
    alpha = "acdehklorty"
    zt = L.ZText({f: [], } if False else {f: [] for f in L.FOLIOS}, {f: [] for f in L.FOLIOS}, {f: [] for f in L.FOLIOS})
    for f in L.FOLIOS:
        zt.labels[f] = ["".join(rng.choice(alpha) for _ in range(rng.randint(3, 7))) for _ in range(30)]
    for f in ("f71v", "f72r1"):                       # plant 25 words with repeat pattern 0,1,0,1,2,3 on both Taurus pages
        zt.labels[f] += ["dadary"] * 25
    ms = [w for f in L.FOLIOS for w in zt.labels[f]]
    idx = L.IsoIndex(ms, zt, kinds=("labels",))
    z_own = idx.z("Taurus", "ababcd", "exact")[0]
    z_other = idx.z("Leo", "ababcd", "exact")[0]
    assert z_own > 3 and z_own > z_other + 3
    Z = L.iso_matrix(idx, ["x" * 0 + "abcdef"] * 10, "exact")
    assert Z.shape == (10, 10)


def test_crib_drag_recovers_planted_mapping_and_transfers():
    rng = random.Random(5)
    # the 'language': a lexicon; the cipher: a bijection letters->EVA units; plant sign names in each sign's text, plus lexicon words elsewhere
    letters = "abcdefghijklmnopqrstuvwxyz"
    cipher = {c: c.upper() + "'" for c in letters}
    names = ["pisces", "aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius"]
    lexicon = {"urbs", "terra", "mare", "nomen", "ignis", "aqua", "caelum", "luna", "sol", "stella", "homo", "deus", "lux", "nox"} | set(names)
    enc = lambda w: tuple(cipher[c] for c in w)
    sign_units = {s: [enc(n)] * 3 + [enc(rng.choice(sorted(lexicon))) for _ in range(20)] for s, n in zip(L.SIGNS, names)}
    zod_types = Counter(u for us in sign_units.values() for u in us)
    rest_types = Counter(enc(rng.choice(sorted(lexicon))) for _ in range(500))
    glob = zod_types + rest_types
    res = L.crib_run(dict(zip(L.SIGNS, names)), sign_units, glob, zod_types, rest_types, lexicon)
    assert res["n_signs_with_candidate"] == 10 and res["conflicts"] <= 2
    assert res["rest_hit_types"] >= 8                      # transfers to unseen tokens
    # a wrong pairing (names rotated) must be worse on transfer
    rot = names[3:] + names[:3]
    bad = L.crib_run(dict(zip(L.SIGNS, rot)), sign_units, glob, zod_types, rest_types, lexicon)
    assert bad["rest_hit_types"] < res["rest_hit_types"] or bad["n_signs_with_candidate"] < res["n_signs_with_candidate"]


def test_derive_mapping_reports_conflicts():
    cands = {"A": (("x", "y"), 3), "B": (("x", "z"), 2)}
    mp, conf, many = L.derive_mapping(cands, {"A": "ab", "B": "cd"})
    assert conf == 1 and len(mp) == 3


def test_transfer_hits_counts_only_fully_mapped():
    tc = Counter({("a", "b", "c"): 5, ("a", "x", "c"): 3, ("a", "b"): 9})
    mp = {"a": "m", "b": "o", "c": "n"}
    assert L.transfer_hits(tc, mp, {"mon"}) == (5, 1, 5)
