"""Tiny-list tests for the h41 statistics. No ciphertext and no 10k scoring."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import h41_lib as H  # noqa: E402
import summarise as S  # noqa: E402


def test_new_type_is_one_when_halves_share_nothing():
    assert H.new_type(["a", "b", "c", "d"]) == 1.0
    assert H.new_type(["aa", "aa", "bb", "cc"]) == 1.0
    assert H.new_type(["a", "b", "b", "c"]) == 0.5


def test_burst_is_higher_when_a_type_is_concentrated_in_one_block():
    spread = ["a", "b", "a", "b", "b", "b", "b", "b"]
    concentrated = ["a", "a", "b", "b", "b", "b", "b", "b"]
    assert H.burst(concentrated, block=2) > H.burst(spread, block=2)


def test_mi100_is_zero_when_lag1_mi_is_zero():
    assert H.mi100(["x"] * 30) == 0.0
    assert H.mi100(["only"]) == 0.0
    assert H.mi100([]) == 0.0


def test_mi100_ratio_for_a_period_two_stream():
    # Pair counts at lag 1 and lag 100 differ by 99, so the ratio is 1 only up to that edge.
    ratio = H.mi100(["a", "b"] * 200)
    assert abs(ratio - 1.0) < 1e-4


def test_mi100_lag_with_no_pairs_is_zero():
    toks = ["a", "b"] * 10
    assert H._word_mi(toks, 100) == 0.0
    assert H.mi100(toks) == 0.0


def test_block_js_is_zero_for_identical_blocks_and_one_for_complements():
    assert H.block_js(["a", "a"], block=1) == 0.0
    assert H.block_js(["a", "b"], block=1) == 1.0


def test_separation_rule_requires_real_strictly_above_both():
    assert S.separates([3.0, 4.0], [1.0, 2.0], [0.5, 1.5])
    assert not S.separates([3.0, 4.0], [3.0, 1.0], [0.5, 1.5])
    assert not S.separates([1.0, 2.0], [3.0, 4.0], [0.0, 0.5])


def test_v2_uses_the_nearer_of_c0_and_the_cipher_mean():
    assert S.closer_to_alt(1.2, 10.0, 1.0, 2.0)
    assert not S.closer_to_alt(9.0, 10.0, 1.0, 2.0)
    assert not S.closer_to_alt(1.0, 0.0, 2.0, 100.0)
