"""Tests for h03 (synthetic checks plus a few smoke tests on the real transcription)."""
import math
import random

import numpy as np
import pytest

import h03_lib as L

ZL = L.TR / "ZL3b-n.txt"
realdata = pytest.mark.skipif(not ZL.exists(), reason="transcription not fetched")


def rigid_words(n=1500, seed=0):
    rng = random.Random(seed)
    return [rng.choice("ab") + rng.choice("cd") + rng.choice("ef") + rng.choice("gh") for _ in range(n)]


def test_slot_hz_endpoints_match_sheet_range():
    assert L.slot_hz_log(0) == pytest.approx(174.0)
    assert L.slot_hz_log(11) == pytest.approx(433.0, rel=1e-6)
    assert (np.diff(L.slot_hz_log(np.arange(12))) > 0).all()


def test_learned_grammar_recovers_rigid_slot_order_and_paths_increase():
    words = rigid_words()
    uw = [tuple(w) for w in words]
    fit = L.SlotFit("learned").fit(uw, iters=40)
    paths = fit.decode(uw)
    assert all(p is not None and all(b > a for a, b in zip(p, p[1:])) for p in paths)
    tab = L.slot_unit_table(fit, uw, paths).set_index("unit")
    # first-position letters sit in earlier slots than last-position letters
    assert max(tab.loc[list("ab"), "mean_slot"]) < min(tab.loc[list("gh"), "mean_slot"])
    assert fit.covered_hard(uw).mean() > 0.99


def test_decode_none_for_word_longer_than_K_and_for_impossible_zattera_word():
    fit = L.SlotFit("zattera").fit([L.G.zattera_segment("qokeedy")] * 20 + [L.G.zattera_segment("chedy")] * 20)
    assert fit.decode_one(tuple("abcdefghijklm")) is None
    assert fit.decode_one(("y", "q")) is None            # y (slot 2 or 12) cannot precede q (slot 1)
    p = fit.decode_one(L.G.zattera_segment("qokeedy"))
    assert p is not None and list(p) == sorted(set(p))


def test_pattern_stats_known():
    paths = [(0, 2), (0, 2), (0, 2), (1, 3, 5), None]
    s = L.pattern_stats(paths)
    assert s["n_pattern_types"] == 2 and s["coverage"] == pytest.approx(0.8) and s["top1_share"] == pytest.approx(0.75)
    assert s["mean_slots_filled"] == pytest.approx((2 * 3 + 3) / 4)
    assert s["mean_skipped_inside_span"] == pytest.approx(((3 - 2) * 3 + (5 - 3)) / 4)


def test_cond_gain_detects_planted_dependency_and_not_noise():
    rng = np.random.default_rng(0)
    n = 6000
    f = rng.integers(0, 10, n)
    y = np.where(rng.random(n) < 0.7, f % 4, rng.integers(0, 4, n))
    noise = rng.integers(0, 10, n)
    train = np.arange(n) % 2 == 0
    test = ~train
    assert L.cond_gain(f, y, 10, 4, train, test).mean() > 0.4
    assert abs(L.cond_gain(noise, y, 10, 4, train, test).mean()) < 0.03


def test_block_bootstrap_ci_contains_mean():
    rng = np.random.default_rng(1)
    v = rng.normal(0.3, 1, 2000)
    blocks = np.arange(2000) // 20
    b = L.block_bootstrap({"x": v}, blocks, 500, 0)
    lo, hi = L.ci(b["x"])
    assert lo < v.mean() < hi and hi - lo < 0.25


def test_sheet_spearman_perfect_order_and_permutation_p():
    # planted: each digraph's slot increases with its Hz rank
    order = sorted(L.SHEET_UNITS, key=lambda u: L.SHEET[u])
    occ = {u: [(i, i + 1)] * 5 for i, u in enumerate(order)}
    d = L.sheet_slot_spearman(occ, n_boot=50).set_index("variant")
    assert d.loc["mean_slot", "spearman_rho"] == pytest.approx(1.0)
    assert d.loc["mean_slot", "p_two_sided_perm"] == pytest.approx(2 / 40320, rel=0.01) or d.loc["mean_slot", "p_two_sided_perm"] < 1e-3
    rev = {u: [(7 - i, 8 - i)] * 5 for i, u in enumerate(order)}
    assert L.sheet_slot_spearman(rev, n_boot=50).set_index("variant").loc["mean_slot", "spearman_rho"] == pytest.approx(-1.0)


def test_sheet_spearman_handles_missing_units():
    occ = {u: [(2, 3)] * 3 for u in L.SHEET_UNITS[:5]}
    occ.update({u: [] for u in L.SHEET_UNITS[5:]})
    d = L.sheet_slot_spearman(occ, n_boot=20)
    assert (d.n_units == 5).all()


def test_cv_stats_alternation_and_nuclei():
    rng = random.Random(0)
    words = ["".join(rng.choice("bcd") + rng.choice("ae") for _ in range(rng.randint(1, 3))) for _ in range(800)]
    uw = [tuple(w) for w in words]
    vowels, _ = L.vowel_classes(uw)
    assert vowels == {"a", "e"}
    s = L.cv_stats(uw, vowels, random.Random(1))
    assert s["cv_switch_rate"] == pytest.approx(1.0) and s["cv_switch_excess"] > 0.2
    assert s["share_words_no_vowel"] == 0.0 and s["nuclei_per_extra_unit_slope"] == pytest.approx(0.5, abs=0.02)


def test_slot_segregation_detects_segregated_slots():
    paths = [(0, 1, 2)] * 300
    uw = [("b", "a", "c")] * 300
    seg = L.slot_segregation(uw, paths, {"a"}, np.random.default_rng(0), 50)
    assert seg["segregation_index"] > 0.9


def test_predictive_tasks_slot_pattern_informative_on_planted_corpus():
    # section-dependent slot patterns: language labels follow pattern, planted
    rng = random.Random(0)
    lines, folio = [], []
    for fi in range(40):
        for _ in range(6):
            lang_b = (fi // 2) % 2
            lines.append([("ab" + rng.choice("ef") + "g") if lang_b else ("c" + rng.choice("ef") + "g") for _ in range(8)])
            folio.append(fi)
    c = L._from_lines("plant", "ms408", lines, True, folio, ([f"f{i}" for i in range(40)], ["herbal"] * 40, ["B" if (i // 2) % 2 else "A" for i in range(40)]))
    rows = {(r["task"], r["feature"]): r for r in L.predictive_tasks(c, "learned", n_boot=100)}
    assert rows[("currier_language_AB", "slot_pattern")]["gain_bits_per_word"] > 0.3
    assert rows[("currier_language_AB", "none")]["gain_bits_per_word"] == pytest.approx(0.0, abs=1e-9)


@realdata
def test_real_ms_corpus_and_grammar_smoke():
    c = L.ms_corpus()
    assert 30000 < len(c.words) < 40000 and set(c.fold) == {0, 1}
    uw = L.segment_words(c.words, "zattera", True)
    cov = np.mean([u is not None for u in uw])
    assert 0.95 < cov < 1.0
    fit = L.SlotFit("zattera").fit(uw, seed=1)
    p = fit.decode_one(L.G.zattera_segment("daiin"))
    assert p is not None and p[0] < p[1] < p[2]
    assert 0.75 < np.mean([x is not None for x in fit.decode(uw)]) < 0.9        # Zattera covers about 82% of tokens here
