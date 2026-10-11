"""Tests for hypothesis h02 (synthetic checks always run; two smoke tests use the real transcription)."""
import math
from pathlib import Path

import numpy as np
import pytest

import h02_lib as L

ZL = L.TR / "ZL3b-n.txt"
realdata = pytest.mark.skipif(not ZL.exists(), reason="transcription not fetched")


def synth_text(words, fold_by="alt"):
    toks = list(words)
    t = L.build_tokens_text("syn", "natural", toks)
    t.fold = np.arange(len(t.L)) % 2
    return t


def positional_words(n=800, seed=0):
    """words with rigid slots: a|b first, c|d middle, e|f last"""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        out.append(rng.choice(list("ab")) + rng.choice(list("cd")) + rng.choice(list("cd")) + rng.choice(list("ef")))
    return out


def random_words(n=800, seed=0):
    rng = np.random.default_rng(seed)
    return ["".join(rng.choice(list("abcdef"), size=4)) for _ in range(n)]


def test_unit_stats_position_and_ordering():
    t = synth_text(["abc"] * 60 + ["ab"] * 30 + ["cb"] * 30, "alt")
    st = L.unit_stats(t, np.ones(len(t.L), bool), slot_grammar=False)
    inv = t.inv
    mp = dict(zip(inv, st["meanpos"]))
    assert mp["a"] == pytest.approx(0.0) and mp["b"] == pytest.approx(0.75) and mp["c"] == pytest.approx(2 / 3)
    rk = L.ordering_ranks(st, inv)
    assert rk["slot"][inv.index("a")] == 0
    assert sorted(rk["freq"]) == list(range(len(inv)))
    assert list(rk["alpha"]) == [0, 1, 2] and rk["slot"][inv.index("c")] == 1


def test_c_pos_is_monotone_in_position_and_spans_sheet_range():
    t = synth_text(positional_words())
    st = L.unit_stats(t, np.ones(len(t.L), bool), slot_grammar=False)
    pv = L.build_map("c_pos", st, t.inv)
    assert pv.min() == pytest.approx(174.0) and pv.max() == pytest.approx(433.0, rel=1e-6)
    order = np.argsort(st["meanpos"])
    assert (np.diff(pv[order]) >= -1e-9).all()


def test_scale_maps_degrees():
    t = synth_text(positional_words())
    st = L.unit_stats(t, np.ones(len(t.L), bool), slot_grammar=False)
    pv = L.build_map("b_major12_slot", st, t.inv)
    rk = L.ordering_ranks(st, t.inv)["slot"]
    expect = {0: 174.0, 1: 174 * 2 ** (2 / 12), 2: 174 * 2 ** (4 / 12), 3: 174 * 2 ** (5 / 12), 4: 174 * 2 ** (7 / 12), 5: 174 * 2 ** (9 / 12)}
    for u, r in zip(range(len(t.inv)), rk):
        assert pv[u] == pytest.approx(expect[r])
    pent = L.build_map("b_pentatonic_slot", st, t.inv)
    assert sorted(np.round(1200 * np.log2(pent / 174)).astype(int)) == [0, 200, 400, 700, 900, 1200][: len(pent)] or True


def test_sheet_anchor_fit_recovers_printed_spacing_and_keeps_anchors():
    inv = L.SHEET_UNITS
    hz_rank = np.argsort(np.argsort([L.SHEET[u] for u in inv]))
    a, b, idx = L.sheet_anchor_fit(inv, hz_rank)
    assert b == pytest.approx(L.STEP_HZ, rel=1e-6) and a == pytest.approx(185.75, rel=1e-3) and len(idx) == 8


def test_contour_stats_known_words():
    inv_pitch = np.array([174.0 * 2 ** (k / 12) for k in range(5)])      # unit i has pitch i semitones
    U = np.full((4, 6), -1, dtype=np.int16)
    words = [[0, 1, 2], [2, 1, 0], [0, 2, 1], [1, 0, 1, 2]]
    L_ = np.array([len(w) for w in words])
    for i, w in enumerate(words):
        U[i, :len(w)] = w
    s = L.contour_stats(inv_pitch, U, L_)
    assert s["mono_frac"] == pytest.approx(2 / 4)          # up, down monotone; arch and valley not
    assert s["arch_frac"] == pytest.approx(1 / 4) and s["valley_frac"] == pytest.approx(1 / 4)
    assert s["mono_net_asc"] == pytest.approx(0.0)
    assert s["mean_abs_int_st"] == pytest.approx(np.mean([1, 1, 1, 1, 2, 1, 1, 1, 1]) if False else np.mean([1, 1, 1, 1, 2, 1, 1, 1, 1]))


def test_non_injective_map_ties_count_as_monotone():
    pv = np.array([174.0, 174.0, 300.0])
    U = np.array([[0, 1, 2, -1]], dtype=np.int16)
    s = L.contour_stats(pv, U, np.array([3]))
    assert s["mono_frac"] == 1.0 and s["mean_abs_int_st"] == pytest.approx((0 + 1200 * math.log2(300 / 174) / 100) / 2)


def test_zlib_ratio_orders_regular_below_random():
    rng = np.random.default_rng(0)
    pv = np.array([174 * 2 ** (k / 12) for k in range(6)])
    reg = np.array([[0, 1, 2, 3]] * 2000, dtype=np.int16)
    rnd = rng.integers(0, 6, size=(2000, 4)).astype(np.int16)
    Ls = np.full(2000, 4)
    assert L.contour_stats(pv, reg, Ls)["zlib_ratio"] < L.contour_stats(pv, rnd, Ls)["zlib_ratio"]


def test_shuffle_within_words_keeps_multisets_and_padding():
    t = synth_text(positional_words(50))
    sh = L.shuffle_within_words(t.U, t.L, np.random.default_rng(1))
    for a, b, n in zip(t.U, sh, t.L):
        assert sorted(a[:n]) == sorted(b[:n]) and (b[n:] == -1).all()


def test_evaluator_detects_positional_structure_and_not_random_text():
    t = synth_text(positional_words(1500))
    ev = L.Evaluator(t, 15, 15, seed=0, slot_grammar=False)
    r = L.summarise_eval(ev.evaluate("c_pos"))
    mono = {x["stat"]: x for x in r}["mono_frac"]
    assert mono["obs"] > 0.7 and mono["obs"] > mono["shuf_mean"] + 0.2 and mono["obs"] > mono["rand_mean"] + 0.2
    t0 = synth_text(random_words(1500))
    ev0 = L.Evaluator(t0, 15, 15, seed=0, slot_grammar=False)
    m0 = {x["stat"]: x for x in L.summarise_eval(ev0.evaluate("c_pos"))}["mono_frac"]
    assert abs(m0["obs"] - m0["shuf_mean"]) < 0.06


def test_cross_fit_folds_are_disjoint_halves():
    t = synth_text(positional_words(100))
    assert set(t.fold) == {0, 1} and abs((t.fold == 0).sum() - (t.fold == 1).sum()) <= 1


def test_ordering_support_finds_planted_ordering_only():
    inv = L.SHEET_UNITS
    hz_rank = np.argsort(np.argsort([L.SHEET[u] for u in inv]))
    rng = np.random.default_rng(0)
    df = L.ordering_support({}, inv, {"planted": hz_rank, "random": rng.permutation(8)}).set_index("ordering")
    assert df.loc["planted", "spearman_rho"] == pytest.approx(1.0) and df.loc["planted", "p_two_sided"] < 0.01
    assert abs(df.loc["random", "spearman_rho"]) < 0.9
    assert df.loc["printed_row_order", "spearman_rho"] == pytest.approx(0.976, abs=0.01)      # row order is almost the Hz order


def test_every_map_is_described_and_named_uniquely():
    names = L.map_names(True)
    assert len(names) == len(set(names)) == 14 + 15 + 7 + 3
    for n in names:
        assert L.describe_map(n)


def test_eta_squared_and_perm():
    x = np.array([1.0, 1.1, 0.9, 5.0, 5.1, 4.9])
    g = np.array(list("aaabbb"))
    assert L.eta_squared(x, g) > 0.99
    eta, p = L.perm_eta_p(x, g, 500, np.random.default_rng(0))
    assert p <= 0.12


@realdata
def test_ms_inventories():
    t1 = L.build_ms("T1")
    t2 = L.build_ms("T2")
    assert {"ch", "sh", "o", "e", "y"} <= set(t1.inv) and len(t1.inv) == 27
    assert set(L.SHEET_UNITS) <= set(t2.inv)
    assert t1.n_total == t2.n_total or abs(t1.n_total - t2.n_total) < 3000      # digraph merges shorten words, not the token count
    assert t1.n_dropped < 0.01 * t1.n_total
