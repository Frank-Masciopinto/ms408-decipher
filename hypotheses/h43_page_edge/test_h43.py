"""Toy checks for h43. No manuscript run."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

import h43_lib as H


def test_cosine_of_word_counts():
    assert H.cosine_counts({"a": 2, "b": 1}, {"a": 2, "b": 1}) == 1.0
    assert H.cosine_counts({"a": 3}, {"b": 3}) == 0.0
    got = H.cosine_counts({"a": 2, "b": 1}, {"a": 1, "b": 2})
    assert abs(got - 0.8) < 1e-12


def test_repeated_folio_type_has_positive_effect():
    folios = [[word] * 200 for word in ("alpha", "beta", "gamma", "delta")]
    stream = H.build_stream([folios], name="toy")
    effect = H.effect_at(stream, 80, [0])
    assert effect == 1.0
    assert len(stream.same[80]) == 4 * 41
    assert len(stream.cross[80]) == 3


def test_rotation_moves_boundaries():
    tokens = ["a"] * 10 + ["b"] * 10
    lengths = [8, 12]
    before = H.split_lengths(tokens, lengths)
    rotated = H.rotate_tokens(tokens, 4)
    after = H.split_lengths(rotated, lengths)
    assert [len(folio) for folio in after] == lengths
    assert before[0] == ["a"] * 8
    assert after[0] == ["a"] * 6 + ["b"] * 2
    assert rotated == tokens[4:] + tokens[:4]
    assert sorted(rotated) == sorted(tokens)


def test_shift_matches_rebuilt_folios():
    quires = [
        [["a", "b", "c", "a"] * 70, ["b", "b", "d", "a"] * 70],
        [["c", "d", "e", "c"] * 70, ["e", "a", "d", "b"] * 70],
    ]
    stream = H.build_stream(quires, name="shift")
    shifts = [500, 520]
    for distance in (80, 160):
        fast = H.effect_at(stream, distance, shifts)
        rebuilt_quires = []
        for folios, shift in zip(quires, shifts):
            flat = [token for folio in folios for token in folio]
            lengths = [len(folio) for folio in folios]
            rebuilt_quires.append(H.split_lengths(H.rotate_tokens(flat, shift), lengths))
        rebuilt = H.build_stream(rebuilt_quires, name="rebuilt")
        slow = H.effect_at(rebuilt, distance, [0, 0])
        assert fast is not None and slow is not None
        assert abs(fast - slow) < 1e-12
        assert len(stream.same[distance]) == len(rebuilt.same[distance])
        assert len(stream.cross[distance]) == len(rebuilt.cross[distance])


def test_pass_needs_thirty_pairs_and_a_higher_effect():
    assert H.is_pass(30, 30, 0.2, 0.1) is True
    assert H.is_pass(30, 30, 0.1, 0.1) is False
    assert H.is_pass(30, 30, 0.1, 0.2) is False
    assert H.is_pass(29, 100, 0.9, 0.1) is False
    assert H.is_pass(100, 29, 0.9, 0.1) is False


def test_pure_folios_beat_the_rotation_null():
    folios = [[f"w{i}"] * 200 for i in range(31)]
    stream = H.build_stream([folios], name="pure")
    scored = H.score_stream(stream, np.random.default_rng(43))
    row = scored["distances"]["80"]
    assert row["n_cross"] == 30
    assert row["n_same"] == 31 * 41
    assert row["effect"] == 1.0
    assert row["scored"] is True
    assert row["pass"] is True
    assert row["effect"] > row["null_p95"]
