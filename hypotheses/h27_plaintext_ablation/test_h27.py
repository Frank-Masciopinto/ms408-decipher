"""Unit tests for h27 plaintext builders. No ciphertext scoring."""
from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import h27_lib as H  # noqa: E402


def fake_tokens() -> list[str]:
    letters = "abcdefghilmnopqrstuvxyz"
    rng = random.Random(7)
    tokens = ["".join(rng.choice(letters) for _ in range(4 + (i % 6))) for i in range(24)]
    tokens += ["ab", "ab", "casa", "casa"]
    tokens += ["", "---", "W", "J", "!!!"]
    return tokens


def test_shuffle_preserves_multiset():
    tokens = fake_tokens()
    shuffled = H.shuffle_plaintext(tokens, 2001)
    assert Counter(shuffled) == Counter(tokens)
    assert shuffled != tokens
    assert H.shuffle_plaintext(tokens, 2001) == shuffled


def test_zipf_types_use_source_letters_and_count_4000():
    tokens = fake_tokens()
    support = set("".join(H.cleaned_tokens(tokens)))
    allowed_lengths = set(H.cleaned_lengths(tokens))
    types = H.zipf_types(tokens, 3001)
    drawn = H.zipf_plaintext(tokens, 3001)
    assert len(types) == 4000
    assert len(set(types)) == 4000
    assert set("".join(types)) <= support
    assert {len(tok) for tok in types} <= allowed_lengths
    assert all(len(tok) >= 1 for tok in types)
    assert len(drawn) == len(tokens)
    assert set("".join(drawn)) <= support
    assert H.zipf_plaintext(tokens, 3001) == drawn


def test_cleaned_lengths_drop_empty_and_stay_positive():
    lengths = H.cleaned_lengths(["w", "k", "", "---", "J"])
    assert lengths == [2, 1, 1]
    assert all(n >= 1 for n in lengths)
    messy = fake_tokens()
    cleaned = H.cleaned_tokens(messy)
    assert cleaned
    assert all(len(tok) >= 1 for tok in cleaned)
    assert len(H.cleaned_lengths(messy)) == len(cleaned)


def test_real_plaintext_is_a_copy_of_the_token_list():
    tokens = fake_tokens()
    copied = H.real_plaintext(tokens)
    assert copied == tokens
    copied.append("extra")
    assert copied != tokens
