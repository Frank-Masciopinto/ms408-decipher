"""h44 unit tests. No manuscript load and no generator fit."""
from __future__ import annotations

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np

import h44_lib as H


def _types_by_page(tokens, pages):
    found: dict = {}
    for token, page in zip(tokens, pages):
        found.setdefault(page, set()).add(token)
    return found


def test_positive_control_burst_exceeds_one_shuffle_of_the_same_tokens():
    tokens, pages, quires = H.positive_control(800, page_len=200, seed=7)
    assert len(tokens) == 800
    assert pages[199] == 0 and pages[200] == 1
    assert quires[0] == 0 and quires[-1] == 0
    by_page = _types_by_page(tokens, pages)
    assert len(by_page) == 4
    vocab = list(by_page.values())
    for i, left in enumerate(vocab):
        assert len(left) <= 40
        for right in vocab[i + 1:]:
            assert left.isdisjoint(right)
    rng = np.random.default_rng(0)
    shuffled = [tokens[int(i)] for i in rng.permutation(len(tokens))]
    assert shuffled != tokens
    assert sorted(shuffled) == sorted(tokens)
    assert H.burst(tokens) > H.burst(shuffled)


def test_positive_control_last_page_is_short_and_has_its_own_types():
    tokens, pages, _quires = H.positive_control(250, page_len=100, seed=1)
    assert pages[-1] == 2
    assert sum(page == 2 for page in pages) == 50
    by_page = _types_by_page(tokens, pages)
    assert by_page[0].isdisjoint(by_page[2])
    assert by_page[1].isdisjoint(by_page[2])


def test_page_length_rounds_a_half_token_median_up():
    assert H.page_len_from_median(229.5) == 230
    assert H.page_len_from_median(229.0) == 229
    pages, quires = H.layout(10500, 230)
    assert pages[229] == 0 and pages[230] == 1
    assert quires[8 * 230 - 1] == 0 and quires[8 * 230] == 1
    assert pages[-1] == 45 and len(pages) == 10500


def test_within_page_shuffle_keeps_each_page_and_repeats_from_seed_44():
    tokens = [f"w{i}" for i in range(20)]
    pages = [i // 5 for i in range(20)]
    first = H.shuffle_within(tokens, pages, np.random.default_rng(44))
    second = H.shuffle_within(tokens, pages, np.random.default_rng(44))
    assert first == second
    assert first != tokens
    for page in range(4):
        assert sorted(word for word, group in zip(first, pages) if group == page) == sorted(
            word for word, group in zip(tokens, pages) if group == page
        )


def test_score_excess_and_quire_share_on_the_positive_control():
    tokens, pages, quires = H.positive_control(600, page_len=100, seed=2)
    rec = H.score_stream(tokens, pages, quires)
    again = H.score_stream(tokens, pages, quires)
    assert rec == again
    assert rec["excess"] == rec["orig"] - rec["full"]
    assert rec["excess"] > 0.0
    assert rec["share_kept_in_quire"] == (rec["in_quire"] - rec["full"]) / rec["excess"]
    assert rec["orig"] > rec["full"]


def test_prediction_rules_are_strict():
    def row(excess, in_page, in_quire, full):
        return {"excess": excess, "in_page": in_page, "in_quire": in_quire, "full": full, "orig": excess + full}

    streams = {
        "MS_1A": row(3.0, 8.0, 7.0, 1.0),
        "MS_2B": row(4.0, 8.0, 7.0, 1.0),
        "MS_3B": row(5.0, 6.0, 7.0, 1.0),
        "positive_control": row(5.1, 0.0, 0.0, 0.0),
    }
    for name in H.GENERATOR_NAMES:
        streams[name] = row(2.9, 0.0, 0.0, 0.0)
    assert H.predictions(streams) == {
        "B1": True,
        "B1_fail": [],
        "B2": True,
        "B3": True,
        "B3_hands": ["MS_1A", "MS_2B"],
        "ms_excess_min": 3.0,
        "ms_excess_max": 5.0,
    }
    streams["fitted_s1"] = row(3.0, 0.0, 0.0, 0.0)
    assert H.predictions(streams)["B1"] is False
    streams["fitted_s1"] = row(2.9, 0.0, 0.0, 0.0)
    streams["positive_control"] = row(5.0, 0.0, 0.0, 0.0)
    assert H.predictions(streams)["B2"] is False
    streams["positive_control"] = row(5.1, 0.0, 0.0, 0.0)
    streams["MS_2B"] = row(4.0, 6.0, 7.0, 1.0)
    failed = H.predictions(streams)
    assert failed["B3"] is False
    assert failed["B3_hands"] == ["MS_1A"]
