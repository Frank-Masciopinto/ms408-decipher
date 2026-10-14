"""h42 unit tests. No full-hand scoring."""
import numpy as np
from rapidfuzz.distance import Levenshtein

import h42_lib as H


def _brute(units, lo, hi):
    lengths = [len(unit) for unit in units]
    n = len(units)
    pairs = []
    for i in range(n):
        for j in range(i + lo, min(n, i + hi + 1)):
            if abs(lengths[i] - lengths[j]) <= 1:
                pairs.append((i, j))
    return pairs


def test_gap1_repeated_near_edits_rate_one():
    units = [tuple("ab"), tuple("ac")] * 40
    assert H.gap_rate(units, 1, 1) == 1.0


def test_unrelated_equal_length_rate_zero():
    units = [tuple(word) for word in ("aa", "bb", "cc", "dd", "ee", "ff")] * 20
    assert H.gap_rate(units, 1, 1) == 0.0


def test_all_elevated_profile_is_flat():
    shape, decay = H.profile_shape([True, True, True, True, True, True])
    assert shape == "flat"
    assert decay is None


def test_shape_labels():
    assert H.profile_shape([False] * 6) == ("none", None)
    assert H.profile_shape([True, False, False, False, False, False]) == ("local", "2-5")
    assert H.profile_shape([True, True, False, False, False, False]) == ("local", "6-20")
    assert H.profile_shape([True, True, True, False, False, False]) == ("page", "21-100")
    assert H.profile_shape([True, True, True, True, False, False]) == ("page", "101-500")
    assert H.profile_shape([True, True, True, True, True, False]) == ("long", "501-1000")
    assert H.profile_shape([False, False, True, True, True, True]) == ("flat", None)


def test_edit1_is_unit_levenshtein():
    assert Levenshtein.distance(("ch",), ("c", "h")) == 2
    assert H.edit1(("ch",), ("c", "h")) is False
    assert H.edit1(("ch", "e"), ("sh", "e")) is True
    assert H.edit1(("a", "b"), ("a", "b")) is False
    assert H.edit1(("a", "b"), ("b", "a")) is False
    samples = [(("ch", "e", "d", "y"), ("ch", "e", "d")), (("a", "b"), ("a", "c")), (("cth", "o"), ("c", "t", "h", "o"))]
    for a, b in samples:
        assert H.edit1(a, b) is (Levenshtein.distance(a, b) == 1)


def test_length_filter_drops_distant_lengths():
    units = [("a",), ("b", "b", "b", "b")]
    assert H.gap_rate(units, 1, 1) is None


def test_sample_matches_brute_and_caps_at_4000():
    rng = np.random.default_rng(0)
    alphabet = ("a", "b", "c", "ch", "sh")
    units = []
    for _ in range(70):
        size = int(rng.integers(1, 6))
        units.append(tuple(alphabet[int(i)] for i in rng.integers(0, len(alphabet), size=size)))
    lengths = [len(unit) for unit in units]
    by = H.index_lengths(lengths)
    for _name, lo, hi in H.BINS:
        if hi > 30:
            continue
        brute = _brute(units, lo, hi)
        assert H.count_eligible(lengths, by, lo, hi) == len(brute)
        ranks = H.systematic_ranks(len(brute), min(4000, len(brute)))
        assert len(ranks) <= 4000
        got = H.take_ranks(lengths, by, lo, hi, ranks)
        assert got == [brute[k] for k in ranks]
    assert H.systematic_ranks(0, 10) == []
    assert H.systematic_ranks(5, 5) == [0, 1, 2, 3, 4]
    wide = H.systematic_ranks(10000, 4000)
    assert len(wide) == 4000 and wide == sorted(set(wide)) and wide[0] == 0 and wide[-1] > 9900


def test_stride_keeps_rate_when_every_pair_is_edit1():
    units = [tuple("ab"), tuple("ac")] * 2500
    assert len(units) > 4000
    assert H.gap_rate(units, 1, 1) == 1.0


def test_null_shuffle_is_within_block_and_repeatable():
    units = [(str(i),) for i in range(20)]
    blocks = [i // 5 for i in range(20)]
    a = H.shuffle_units(units, blocks, np.random.default_rng(42))
    b = H.shuffle_units(units, blocks, np.random.default_rng(42))
    assert a == b
    assert a != units
    for k in range(4):
        assert sorted(a[5 * k:5 * k + 5]) == sorted(units[5 * k:5 * k + 5])


def test_constant_null_is_not_elevated():
    _mean, sd, excess, elevated = H.summarise_bin(0.5, [0.1] * 10)
    assert sd == 0.0 and excess == 0.4 and elevated is False
    nulls = [0.10, 0.12, 0.08, 0.11, 0.09, 0.10, 0.13, 0.07, 0.10, 0.10]
    _mean, sd, excess, elevated = H.summarise_bin(0.5, nulls)
    assert elevated is True and excess > 2 * sd


def test_null_shuffles_use_one_count():
    units = [("a",)] * 40 + [("bbbb",)] * 40
    blocks = [0] * len(units)
    rec = H.score_units(units, blocks, n_null=10, seed=42)
    for info in rec["bins"].values():
        assert info["null_n_sampled"] == [info["n_sampled"]] * 10


def test_predictions_on_a_synthetic_profile():
    ms = {"shape": "local", "decay_point": "6-20", "bins": {"1": {"excess": 0.2}}}
    native = {"shape": "flat", "decay_point": None, "bins": {"1": {"excess": 0.3}}}
    boc = {"shape": "none", "decay_point": None, "bins": {"1": {"excess": 0.01}}}
    got = H.predictions({"MS_2B": ms, "h39_native_tuned": native, "boccaccio": boc})
    assert got == {"N1": True, "N2": True, "N3": True}
