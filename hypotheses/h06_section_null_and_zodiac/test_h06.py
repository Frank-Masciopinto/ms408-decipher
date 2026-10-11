"""Tests for h06 (run: pytest hypotheses/h06_section_null_and_zodiac -q)."""
import random
from collections import Counter

import numpy as np
import pytest

import h06_lib as L
import h06_zodiac as Z


@pytest.fixture(scope="module")
def data():
    d = L.HR.ms_data()
    return d, L.T.folio_layout(d)


@pytest.fixture(scope="module")
def sh(data):
    d, _ = data
    return L.Shared(d["words"][:6000], seed=1, n_big=5000)


def test_tilt_and_pool_counts(sh, data):
    d, _ = data
    words = [w for w, s in zip(d["words"], d["section"]) if s == "pharmaceutical"][:800]
    gm = L.make_group_model(sh, words, dict(L.DEFAULT_BASE), 20, True)
    assert gm.k_pool == 20 and gm.k_tilt == sh.n_units - 1
    assert abs(gm.tilt_cum[-1] - 1.0) < 1e-9 and abs(gm.pool_cum[-1] - 1.0) < 1e-9
    gm3 = L.make_group_model(sh, words, dict(L.DEFAULT_BASE), 0, True, top=3)
    assert gm3.k_tilt == 3 and gm3.pool == []


def test_pool_only_generation_draws_from_pool(sh, data):
    d, _ = data
    words = [w for w, s in zip(d["words"], d["section"]) if s == "herbal"][:800]
    gm = L.make_group_model(sh, words, {**L.DEFAULT_BASE, "p_copy": 0.0, "p_pool": 1.0}, 15, False)
    out = L.sv_generate([{"group": "g", "n": 300, "page": 0}], {"g": gm, "__all__": gm}, sh, 1)[0]
    assert set(out) <= set(gm.pool)


def test_determinism_and_scope(sh, data):
    d, _ = data
    gm = L.make_group_model(sh, d["words"][:800], {**L.DEFAULT_BASE, "p_copy": 1.0, "p_exact": 1.0, "p_suffix": 0.0, "p_prefix": 0.0, "p_prev": 1.0}, 0, False)
    specs = [{"group": "g", "n": 1, "page": i} for i in range(2)]
    m = {"g": gm, "__all__": gm}
    assert L.sv_generate(specs, m, sh, 5) == L.sv_generate(specs, m, sh, 5)
    # copy with certainty: scope 'window' carries the first innovation across pages (both tokens identical), 'page' restarts the history on every page
    win = [w for part in L.sv_generate(specs, m, sh, 5) for w in part]
    pg = [w for part in L.sv_generate(specs, m, sh, 5, scope="page") for w in part]
    assert len(set(win)) == 1 and len(set(pg)) == 2


def test_group_assignment_schemes(data):
    import run_h06_section as RS
    _, entries = data
    rand = ["r0", "r1", "r2"] * 100
    assert RS.group_of(entries[0], 0, "none", rand) == "__all__"
    assert RS.group_of(entries[0], 0, "section", rand) == (entries[0]["cls"] or "other")
    assert RS.group_of(entries[0], 0, "rand", rand) == rand[0]
    assert "|" in RS.group_of(entries[0], 0, "seclang", rand)


def test_zodiac_data_counts():
    ring, lab = Z.zodiac_data()
    assert list(ring) == Z.PAGES and len(Z.PAGES) == 12
    assert 900 < sum(map(len, ring.values())) < 960
    assert 300 < sum(map(len, lab.values())) < 340
    assert all(w.isalpha() and w.islower() for p in Z.PAGES for w in ring[p] + lab[p])


def test_circ_dist_and_months():
    assert Z.circ_dist(3, 12) == 3 and Z.circ_dist(1, 12) == 1 and Z.circ_dist(4, 4) == 0
    assert sorted(set(Z.MONTH.values())) == [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]       # Jan, Feb (Aquarius, Capricorn) missing


def test_calendar_test_detects_planted_structure_and_not_noise():
    n = len(Z.PAGES)
    rng = np.random.default_rng(0)
    months = np.array([Z.MONTH[p] for p in Z.PAGES])
    M = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            M[i, j] = 1.0 / (1 + Z.circ_dist(months[i], months[j])) + 0.02 * rng.standard_normal()
    M = (M + M.T) / 2
    np.fill_diagonal(M, np.nan)
    r = Z.calendar_tests(M, n_perm=400, seed=1)
    assert r["spearman_circular"] > 0.7 and r["p_circular"] < 0.01
    N = rng.random((n, n))
    N = (N + N.T) / 2
    np.fill_diagonal(N, np.nan)
    assert Z.calendar_tests(N, n_perm=400, seed=1)["p_circular"] > 0.05


def test_locality_detects_local_copying():
    rng = random.Random(0)
    vocab = ["".join(rng.choice("abcdefgh") for _ in range(5)) for _ in range(400)]
    seqs = {}
    for p in range(6):
        local = [rng.choice(vocab) for _ in range(8)]
        seqs[f"p{p}"] = [rng.choice(local) for _ in range(60)]            # every page recycles its own small pool
    allw = [w for s in seqs.values() for w in s]
    near = Z.near_sets(allw, set(allw))
    rest = [rng.choice(vocab) for _ in range(2000)]
    nr = Z.near_sets(allw, set(rest))
    r = Z.locality(seqs, near, rest, nr, W=10, n_draw=3, perm=50, seed=1)
    assert r["local"] > r["other_pages"] + 0.2 and r["perm_p_local"] < 0.05


def test_zodiac_stats_basic():
    ring, lab = Z.zodiac_data()
    rest = Z.Rest(["qokeedy", "chedy", "daiin", "okaiin", "shedy"] * 50)
    st = Z.zodiac_stats(ring, lab, rest.words, rest.types, rest.units, rest.counter)
    assert 0.6 < st["label_o_initial"] < 0.75 and st["label_q_share"] < 0.02       # the h05 numbers (67 %, near-absence of q)
    assert set(Z.STAT_LABELS) <= set(st)
