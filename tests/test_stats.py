import math
import random
from collections import Counter

import numpy as np
import pytest

from msdecipher import stats as S


def test_entropy_counts_basics():
    assert S.entropy_counts([1, 1]) == pytest.approx(1.0)
    assert S.entropy_counts([5]) == 0.0
    assert S.entropy_counts([]) == 0.0
    assert S.entropy_counts([1, 1, 1, 1]) == pytest.approx(2.0)
    # Miller-Madow adds (m-1)/(2N ln2)
    assert S.entropy_counts([10, 10], True) == pytest.approx(1.0 + 1 / (2 * 20 * math.log(2)))


def test_conditional_entropy_deterministic_and_independent():
    # perfectly predictable alternation within each word: h2 = 0, H1 = 1
    seqs = [tuple("abababab")] * 20
    assert S.block_entropy(seqs, 1) == pytest.approx(1.0)
    assert S.conditional_entropy(seqs, 2) == pytest.approx(0.0, abs=1e-9)
    assert S.conditional_entropy(seqs, 3) == pytest.approx(0.0, abs=1e-9)
    # iid fair coin: h2 ~ H1 = 1
    rng = random.Random(0)
    iid = [tuple(rng.choice("ab") for _ in range(50)) for _ in range(400)]
    assert S.conditional_entropy(iid, 2) == pytest.approx(1.0, abs=0.01)
    with pytest.raises(ValueError):
        S.conditional_entropy(iid, 1)


def test_windows_never_cross_word_boundaries():
    # 'ab' and 'ba' words: if windows crossed boundaries we would see (b,b),(a,a) pairs
    seqs = [("a", "b"), ("b", "a")] * 50
    cnt = S._ngram_counts(seqs, 2)
    assert set(cnt) == {("a", "b"), ("b", "a")}


def test_boundaries_and_profile_keys():
    seqs = [tuple("abc"), tuple("abd")] * 10
    assert S.with_boundaries(seqs)[0] == ("^", "a", "b", "c", "$")
    p = S.entropy_profile(seqs, n_shuffles=3)
    for k in ("H1", "h2", "h3", "h2_mm", "h2_within_word_shuffle", "h2_with_word_boundaries", "alphabet_size_ge20"):
        assert k in p
    assert p["h2"] < p["H1"]
    assert p["h2_within_word_shuffle"] >= p["h2"] - 1e-9


def _zipf_sample(s, n_types, n_tokens, seed=0):
    ranks = np.arange(1, n_types + 1)
    p = ranks ** (-s)
    p /= p.sum()
    rng = np.random.default_rng(seed)
    draws = rng.choice(n_types, size=n_tokens, p=p)
    return [f"w{i}" for i in draws]


def test_zipf_estimators_recover_exponent():
    words = _zipf_sample(1.0, 5000, 200000)
    f = S.rank_frequency(words)
    assert S.zipf_ols_slope(f, 10, 1000) == pytest.approx(-1.0, abs=0.08)
    assert S.zipf_mle_exponent(f, 10, 1000) == pytest.approx(1.0, abs=0.05)
    words = _zipf_sample(1.3, 5000, 200000, seed=1)
    f = S.rank_frequency(words)
    assert S.zipf_mle_exponent(f, 1, 1000) == pytest.approx(1.3, abs=0.05)


def test_zipf_small_input_nan():
    assert math.isnan(S.zipf_ols_slope(np.array([3.0, 2.0, 1.0])))
    assert math.isnan(S.zipf_mle_exponent(np.array([3.0, 2.0, 1.0])))


def test_heaps_exponent_known_cases():
    # all-distinct tokens -> V(n)=n -> beta 1
    words = [f"w{i}" for i in range(5000)]
    b, k = S.heaps_exponent(words)
    assert b == pytest.approx(1.0, abs=1e-3)
    # one repeated token -> beta ~ 0
    b, _ = S.heaps_exponent(["a"] * 5000)
    assert b == pytest.approx(0.0, abs=1e-6)
    # Zipf text lies in between
    b, _ = S.heaps_exponent(_zipf_sample(1.0, 5000, 50000), shuffled=True)
    assert 0.5 < b < 0.95
    n, v = S.heaps_curve(words)
    assert (np.diff(v) >= 0).all() and n[-1] == len(words)
    assert S.heaps_curve(["a"] * 10)[0].size == 0


def test_word_stats_fields():
    seg = lambda w: tuple(w)
    ws = S.word_stats(_zipf_sample(1.0, 3000, 30000), seg)
    assert ws["n_tokens"] == 30000 and ws["n_types"] <= 3000
    assert 0 < ws["hapax_share_of_types"] < 1
    assert ws["mean_word_length_units"] > 0
    assert ws["zipf_ols_slope_r10_1000"] < 0


def test_positional_table():
    seg = lambda w: tuple(w)
    tab = S.positional_table([["abc", "d"], ["ab", "x?y"]], seg,
                             [{"own_line": True, "para_start": True}, {"own_line": True, "para_start": False}])
    assert tab["a"]["initial"] == 2 and tab["b"]["medial"] == 1 and tab["b"]["final"] == 1
    assert tab["c"]["final"] == 1 and tab["d"]["sole"] == 1
    assert tab["a"]["line_initial"] == 2 and tab["a"]["para_initial"] == 1
    assert tab["d"]["line_final"] == 1
    assert "x" not in tab                       # word with '?' skipped
    # line_final for line 2 skipped because last word is unreadable
    assert tab["b"]["line_final"] == 0
    # not own line -> no line stats
    t2 = S.positional_table([["ab"]], seg, [{"own_line": False, "para_start": False}])
    assert "line_initial" not in t2["a"]


def test_js_divergence():
    a, b = Counter("aaab"), Counter("aaab")
    assert S.js_divergence(a, b) == pytest.approx(0.0)
    assert S.js_divergence(Counter("aaa"), Counter("bbb")) == pytest.approx(1.0)
    assert 0 < S.js_divergence(Counter("aab"), Counter("abb")) < 1
    assert math.isnan(S.js_divergence(Counter(), Counter("a")))


def test_sukhotin_toy_alternating_language():
    # CV-structured toy words: vowels a,e,i ; consonants b,d,k,t. Sukhotin must recover them.
    rng = random.Random(3)
    V, C = "aei", "bdkt"
    words = []
    for _ in range(2000):
        n = rng.randint(2, 4)
        words.append(tuple(c for _ in range(n) for c in (rng.choice(C), rng.choice(V))))
    vowels, _ = S.sukhotin(words)
    assert set(vowels) == set(V)


def test_sukhotin_min_count_and_empty():
    assert S.sukhotin([]) == ([], {})
    vowels, _ = S.sukhotin([("a", "b")] * 3 + [("z", "a")], min_count=2)
    assert "z" not in vowels
    # no double-counting of identical neighbours
    assert S.sukhotin([("a", "a", "a")])[0] == []


def test_sukhotin_depends_on_segmentation():
    """The point of segmenting first: with 'ch' split, 'h' looks like a vowel-ish glue unit."""
    raw_words = [tuple("chok"), tuple("chal"), tuple("shol"), tuple("shey"), tuple("cheo")] * 40
    seg_words = [("ch", "o", "k"), ("ch", "a", "l"), ("sh", "o", "l"), ("sh", "e", "y"), ("ch", "e", "o")] * 40
    v_raw, _ = S.sukhotin(raw_words)
    v_seg, _ = S.sukhotin(seg_words)
    assert "h" in v_raw
    assert "ch" not in v_seg and "sh" not in v_seg
