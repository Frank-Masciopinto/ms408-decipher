"""Tests for hypothesis h01. Run: python -m pytest hypotheses/h01_tone_sheet -q
(synthetic checks always run; the realdata ones need data/transcriptions/ZL3b-n.txt)."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

import h01_lib as L

HERE = Path(__file__).resolve().parent
ZL = L.ROOT / "data" / "transcriptions" / "ZL3b-n.txt"
realdata = pytest.mark.skipif(not ZL.exists(), reason="transcription not fetched")


def test_table_matches_sheet_image_transcription():
    t = L.load_table()
    assert list(t.glyph) == ["qo", "ka", "dy", "ri", "ae", "ya", "ny", "ly"]
    assert list(t.tone_hz) == [174, 233, 294, 261, 322, 365, 400, 433]
    j = json.loads((HERE / "table.json").read_text())
    assert [(r["glyph"], r["tone_hz"], r["action"], r["meaning"]) for r in j["rows"]] == \
        list(zip(t.glyph, t.tone_hz, t.action, t.meaning))
    assert (HERE / "codex_translation_sheet.png").exists()


def test_predictions_cover_every_unit():
    p = L.load_predictions()
    assert list(p.glyph) == L.sheet_units()
    for r in p.itertuples():                       # strict is a subset of liberal
        assert set(x for x in r.strict_sections.split(";") if x) <= set(r.liberal_sections.split(";"))


def test_tilings_dp():
    U = ["qo", "ka", "dy", "ly"]
    assert L.tilings("qokaly", U) == (6, 1)
    assert L.tilings("qokal", U) == (4, 0)
    assert L.tilings("chedy", U) == (2, 0)
    assert L.tilings("", U) == (0, 1)
    assert L.tilings("aya", ["ay", "ya"])[1] == 0 and L.tilings("aya", ["ay", "ya"])[0] == 2
    assert L.tilings("ayay", ["ay", "ya", "a", "y"])[1] == 5       # ambiguous tilings are counted


def test_coverage_stats_simple():
    toks = ["qo", "qo", "dy", "daiin", "chedy"]
    c = L.coverage_stats(toks, ["qo", "dy"])
    assert c["tokens_fully_tileable"] == pytest.approx(3 / 5)
    assert c["types_fully_tileable"] == pytest.approx(2 / 4)
    assert c["tokens_containing_a_unit"] == pytest.approx(4 / 5)
    assert c["char_cov"] == pytest.approx((2 + 2 + 2 + 0 + 2) / (2 + 2 + 2 + 5 + 5))


def test_pair_expectation_matches_brute_force_shuffle():
    rng = np.random.default_rng(0)
    words = ["qokedy", "chedy", "dyqody", "okaiin", "aab", "ab"]
    exp = L.pair_obs_exp(words, "d", "y")["exp"]["all"]
    tot = 0
    n = 20000
    for _ in range(n):
        for w in words:
            s = "".join(rng.permutation(list(w)))
            tot += s.count("dy")
    assert exp == pytest.approx(tot / n, rel=0.03)
    # a == b case
    e2 = L.pair_obs_exp(["aaab", "aa"], "a", "a")["exp"]["all"]
    tot = 0
    for _ in range(n):
        for w in ["aaab", "aa"]:
            tot += sum(1 for x, y in zip(*(lambda s: (s, s[1:]))("".join(rng.permutation(list(w))))) if x == y == "a")
    assert e2 == pytest.approx(tot / n, rel=0.03)


def test_position_classes_sum_to_total():
    words = ["dy", "dyx", "xdy", "xdyx", "xxdyxx", "qdydy"]
    r = L.pair_obs_exp(words, "d", "y")
    assert sum(v for k, v in r["obs"].items() if k != "all") == r["obs"]["all"]
    assert sum(v for k, v in r["exp"].items() if k != "all") == pytest.approx(r["exp"]["all"])


def test_grid_fit_recovers_exact_12tet():
    tones = [220 * 2 ** (k / 12) for k in (0, 2, 3, 7, 10, 14)]
    rms, f0, mx = L.best_grid_fit(tones, 100.0, 0.5)
    assert rms < 1.0 and mx < 2.0
    assert L.grid_rms(tones, 440.0, 100.0) < 1e-6
    # whole-tone grid cannot fit a semitone
    assert L.best_grid_fit([220, 220 * 2 ** (1 / 12)], 200.0, 1.0)[0] > 40


def test_scale_models_exact_major_scale():
    f0 = 261.63
    tones = [f0 * 2 ** (k / 12) for k in (0, 2, 4, 5, 7, 9, 11)]
    m = L.scale_models(tones)
    assert m["12-TET major scale (free tonic)"] < 1.5
    assert m["12-TET chromatic (free ref)"] < 1.5
    assert m["12-TET chromatic (free ref)"] <= m["whole-tone 6-TET (free ref)"]


def test_nearest_12tet():
    assert L.nearest_12tet(440.0)[0] == "A4" and abs(L.nearest_12tet(440.0)[1]) < 1e-6
    n, d = L.nearest_12tet(174.0)
    assert n == "F3" and -10 < d < 0


def test_linear_rank_fit_exact():
    f = L.linear_rank_fit([100, 130, 160, 190])
    assert f["r2"] == pytest.approx(1.0) and f["step_hz"] == pytest.approx(30)


def test_kendall_inversions_exact_p():
    inv, p = L.kendall_inversions_p([0, 1, 2, 3])
    assert inv == 0 and p == pytest.approx(1 / 24)
    inv, p = L.kendall_inversions_p([1, 0, 2, 3])
    assert inv == 1 and p == pytest.approx(4 / 24)      # identity + 3 adjacent swaps
    inv, p = L.kendall_inversions_p([0, 1, 2, 4, 3, 5, 6, 7])
    assert inv == 1 and p == pytest.approx(8 / 40320)


def test_tone_null_small_is_deterministic_and_shaped():
    n1, s1 = L.tone_null([174, 233, 294, 261, 322, 365, 400, 433], n_sets=40, seed=1)
    n2, s2 = L.tone_null([174, 233, 294, 261, 322, 365, 400, 433], n_sets=40, seed=1)
    assert s1.equals(s2) and len(n1) == 40
    assert ((s1.p_null_as_good > 0) & (s1.p_null_as_good <= 1)).all()


def test_holm():
    adj = L.holm([0.01, 0.04, 0.03])
    assert adj == pytest.approx([0.03, 0.06, 0.06])


def _fake_folios():
    secs = ["a"] * 6 + ["b"] * 6
    out = []
    for i, s in enumerate(secs):
        words = ["xxyy"] * 5 + (["dy"] * 12 if s == "b" else ["qa"] * 3 + ["zz"] * 9)
        out.append(L.Folio(f"f{i}", s, "A", [words]))
    return out


def test_enrichment_detects_planted_effect_and_not_null():
    fo = _fake_folios()
    e = L.enrichment_matrix(fo, ["dy", "xx"], ["b"], n_perm=400)
    dy = e[e.unit == "dy"].iloc[0]
    xx = e[e.unit == "xx"].iloc[0]
    assert dy.log2_ratio > 2 and dy.p_enriched < 0.01
    assert xx.p_enriched > 0.05 and abs(xx.log2_ratio) < 0.3


def test_mapping_permutation_ranks_planted_assignment_first():
    fo = _fake_folios()
    units = ["dy", "qa"]
    assign = {"dy": ["b"], "qa": ["a"]}
    r = L.mapping_permutation_test(fo, units, assign, n_label_perm=200)
    assert r["frac_of_8!_pairings_at_least_as_good"] == pytest.approx(1 / 2)  # 2 pairings, the planted one ties for best
    assert r["sheet_score"] == pytest.approx(r["max_pairing_score"])
    swapped = L.mapping_permutation_test(fo, units, {"dy": ["a"], "qa": ["b"]}, n_label_perm=200)
    assert swapped["sheet_score"] < r["sheet_score"]


def test_nb_loo_learns_separable_classes_and_not_shuffled():
    rng = np.random.default_rng(0)
    y = np.array(["a"] * 30 + ["b"] * 30)
    X = np.vstack([rng.poisson([20, 2], (30, 2)), rng.poisson([2, 20], (30, 2))]).astype(float)
    assert L.nb_loo(X, y)["accuracy"] > 0.95
    assert L.nb_loo(X, rng.permutation(y))["accuracy"] < 0.75


def test_neighbour_mi_detects_planted_dependence():
    rng = np.random.default_rng(0)
    toks = []
    for _ in range(600):
        toks += ["dy", "dy"] if rng.random() < 0.3 else ["ab", "cd"]
    fo = [L.Folio("f", "a", "A", [toks])]
    r = L.neighbour_mi(fo, "dy", n_perm=50, rng=np.random.default_rng(1))
    assert r["mi_bits"] > r["null_mean"] and r["z"] > 3


def test_cross_boundary_and_order():
    fo = [L.Folio("f", "a", "A", [["qodyka", "n", "yx", "qo", "dy"]])]
    xb = L.cross_boundary_counts(fo, ["ny", "qo", "dy"]).set_index("unit")
    assert xb.loc["ny", "across_word_break"] == 1 and xb.loc["ny", "inside_word"] == 0
    assert xb.loc["qo", "inside_word"] == 2
    o = L.order_asymmetry(["qodyka", "dyqo"], ["qo", "dy", "ka"])
    row = o[(o["first"] == "qo") & (o.second == "dy")].iloc[0]
    assert row["count"] == 1 and row["reverse_count"] == 1


@realdata
def test_real_corpus_headline_counts_are_stable():
    fo = L.load_folios(ZL, "P")
    toks = L.all_tokens(fo)
    assert len(toks) == 34977                              # same size as the controls stage
    cov = L.coverage_stats(toks, L.sheet_units())
    assert cov["char_cov"] < 0.25                          # nowhere near 100%
    assert cov["tokens_fully_tileable"] < 0.05
    assert sum(w.count("qo") for w in toks) > 5000
    assert sum(w.count("ae") for w in toks) < 10
    assert L.line_coverage(fo, L.sheet_units())["lines_fully_tileable"] == 0
    # 'ka' is not an EVA glyph in the repo's glyph catalogue; its letters are
    import pandas as pd
    cat = pd.read_csv(L.ROOT / "glyphs" / "catalog.csv")
    assert not (cat.glyph == "ka").any() and (cat.glyph == "k").any() and (cat.glyph == "a").any()


@realdata
def test_results_file_if_present_is_consistent_with_lib():
    p = HERE / "results" / "results.json"
    if not p.exists():
        pytest.skip("run run_h01.py first")
    r = json.loads(p.read_text())
    fo = L.load_folios(ZL, "P")
    toks = L.all_tokens(fo)
    assert r["corpus"]["tokens"] == len(toks)
    assert r["coverage"]["char_cov"] == pytest.approx(L.coverage_stats(toks, L.sheet_units())["char_cov"])
