"""Unit tests for the h56 detector. They do not score the manuscript."""
from __future__ import annotations

import numpy as np

import h56_lib as H


def test_distance_cap():
    assert H.lev("abcd", "abcd") == 0
    assert H.lev("abcd", "abxd") == 1
    assert H.lev("abcd", "abcde") == 1
    assert H.lev("abcd", "abxy") == 2


def test_holm_is_ordered():
    adj = H.holm([0.01, 0.04, 0.2])
    assert adj[0] <= adj[1] <= 1
    assert adj[0] >= 0.01


def test_planted_roots_are_easier_to_recover_than_the_null_stream():
    result = H.synthetic_streams(np.random.default_rng(56))
    assert result["planted_accuracy"] > result["null_accuracy"]
    assert result["planted_accuracy"] > 0.3


def test_alternate_substitution_replaces_one_option():
    class Token:
        text = "cthres"
        alternatives = [("cth", "oto")]

    assert H.token_text(Token(), "alternate") == "otores"
    assert H.token_text(Token(), "primary") == "cthres"
