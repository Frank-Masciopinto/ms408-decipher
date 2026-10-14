"""Unit tests for h46_folio_reset_mechanism. Synthetic data only; fast and deterministic."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
from rapidfuzz.distance import Levenshtein

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import h46_lib as H  # noqa: E402


def _brute_test1(units: list[tuple[str, ...]], folios: list[str], lo: int, hi: int, max_pairs: int = 20000):
    n = len(units)
    lengths = [len(u) for u in units]
    same_elig = []
    cross_elig = []
    for i in range(n):
        for j in range(i + lo, min(n, i + hi + 1)):
            if abs(lengths[i] - lengths[j]) <= 1:
                if folios[i] == folios[j]:
                    same_elig.append((i, j))
                else:
                    cross_elig.append((i, j))
    s_ranks = H.systematic_ranks(len(same_elig), min(max_pairs, len(same_elig)))
    c_ranks = H.systematic_ranks(len(cross_elig), min(max_pairs, len(cross_elig)))
    s_samp = [same_elig[r] for r in s_ranks]
    c_samp = [cross_elig[r] for r in c_ranks]
    s_hits = sum(1 for i, j in s_samp if H.edit1(units[i], units[j]))
    c_hits = sum(1 for i, j in c_samp if H.edit1(units[i], units[j]))
    s_rate = (s_hits / len(s_samp)) if s_samp else None
    c_rate = (c_hits / len(c_samp)) if c_samp else None
    return (
        len(same_elig),
        len(s_samp),
        s_hits,
        s_rate,
        len(cross_elig),
        len(c_samp),
        c_hits,
        c_rate,
    )


def test_edit1_matrix_matches_levenshtein():
    vocab = [
        ("ch", "e", "d", "y"),
        ("sh", "e", "d", "y"),
        ("ch", "e", "y"),
        ("q", "o", "k", "e", "d", "y"),
        ("d", "a", "i", "i", "n"),
        ("d", "a", "i", "n"),
        ("o", "l"),
        ("o", "r"),
        ("a",),
    ]
    mat = H.build_edit1_matrix(vocab)
    for i, ua in enumerate(vocab):
        for j, ub in enumerate(vocab):
            expected = (abs(len(ua) - len(ub)) <= 1) and (Levenshtein.distance(ua, ub) == 1)
            assert bool(mat[i, j]) is expected
            assert H.edit1(ua, ub) is expected


def test_fast_test1_matches_brute_force_and_rotation_geometry():
    rng = np.random.default_rng(7)
    alphabet = ("a", "e", "o", "ch", "sh", "d", "y", "k", "t")
    words = []
    units = []
    folios = []
    quires = []
    lines = []
    for q_idx in range(2):
        for f_idx in range(3):
            folio_name = f"f{q_idx * 3 + f_idx + 1}{'r' if f_idx % 2 == 0 else 'v'}"
            for l_idx in range(1, 7):
                for _ in range(6):
                    length = int(rng.integers(2, 5))
                    u = tuple(alphabet[int(x)] for x in rng.integers(0, len(alphabet), size=length))
                    units.append(u)
                    words.append("".join(u))
                    folios.append(folio_name)
                    quires.append(str(q_idx + 1))
                    lines.append(l_idx)

    data = H.build_hand_data("1A", words, folios, quires, lines, units=units)
    scored = H.score_test1_hand(
        data,
        np.random.default_rng(46),
        bins=(("6-20", 6, 20), ("21-100", 21, 100)),
        max_pairs=80,
        min_eligible=10,
        n_null=5,
    )
    for bname, lo, hi in (("6-20", 6, 20), ("21-100", 21, 100)):
        row = scored["bins"][bname]
        se, ss, sh, sr, ce, cs, ch, cr = _brute_test1(units, folios, lo, hi, max_pairs=80)
        assert row["n_same_eligible"] == se
        assert row["n_same_sampled"] == ss
        assert row["n_same_edit1"] == sh
        assert abs(row["same_rate"] - sr) < 1e-12
        assert row["n_cross_eligible"] == ce
        assert row["n_cross_sampled"] == cs
        assert row["n_cross_edit1"] == ch
        assert abs(row["cross_rate"] - cr) < 1e-12

    # Check first rotation matches explicit rotate_tokens + split_lengths
    rng_check = np.random.default_rng(46)
    shifts = [int(rng_check.integers(0, sum(len(f) for f in q))) for q in data.quires_grouped]
    rebuilt_units = []
    for quire, shift in zip(data.quires_grouped, shifts):
        flat = [u for folio in quire for u in folio]
        flens = [len(folio) for folio in quire]
        for r_folio in H.split_lengths(H.rotate_tokens(flat, shift), flens):
            rebuilt_units.extend(r_folio)
    _, _, _, sr0, _, _, _, cr0 = _brute_test1(rebuilt_units, folios, 6, 20, max_pairs=80)
    assert abs(scored["bins"]["6-20"]["null_effects"][0] - (sr0 - cr0)) < 1e-12


def test_test2_first_line_seeding_signal_and_null():
    words = []
    units = []
    folios = []
    quires = []
    lines = []
    # Construct 10 folios with 6 lines each where line 1 has ("a", "b") and lines 2..6 have ("a", "c"), ("x", "y")
    # Every pair between line 1 ("a", "b") and ("a", "c") is edit1=True, while interior ("a", "c") vs ("a", "c") is edit1=False
    for f_idx in range(10):
        folio = f"f{f_idx + 1}r"
        for l_idx in range(1, 7):
            line_units = [("a", "b")] * 6 if l_idx == 1 else [("a", "c")] * 6
            for u in line_units:
                units.append(u)
                words.append("".join(u))
                folios.append(folio)
                quires.append("1")
                lines.append(l_idx)

    data = H.build_hand_data("1A", words, folios, quires, lines, units=units)
    res = H.score_test2_hand(data, np.random.default_rng(46), min_lines=6, n_null=50)
    assert res["n_folios_eligible"] == 10
    assert res["seed_rate"] == 1.0
    assert res["interior_rate"] == 0.0
    assert res["effect"] == 1.0
    assert res["pass"] is True


def test_test3_spread_vs_page_turn_and_nonconsecutive_exclusion():
    words = []
    units = []
    folios = []
    quires = []
    lines = []
    # Manuscript order has f1r, f1v, f2r, f2v, f3r, f3v, f4r
    ms_order = {"f1r": 0, "f1v": 1, "f2r": 2, "f2v": 3, "f3r": 4, "f3v": 5, "f4r": 6}
    # Include f1r -> f1v (r_to_v, consecutive), f1v -> f2r (v_to_r, consecutive),
    # and skip f2v/f3r so f2r -> f3v is non-consecutive (folio_index 2 -> 5) and must be excluded!
    folio_seq = [
        ("f1r", [("a", "b")] * 25),
        ("f1v", [("c", "d")] * 25),
        ("f2r", [("c", "e")] * 25),
        ("f3v", [("c", "d")] * 25),
    ]
    for f_name, f_units in folio_seq:
        for idx, u in enumerate(f_units):
            units.append(u)
            words.append("".join(u))
            folios.append(f_name)
            quires.append("1")
            lines.append((idx // 5) + 1)

    data = H.build_hand_data("2B", words, folios, quires, lines, ms_order=ms_order, units=units)
    res = H.score_test3_hand(data, np.random.default_rng(46), bins=(("21-100", 21, 100),), min_eligible=200, n_null=20)
    b = res["bins"]["21-100"]
    # Only f1r->f1v and f1v->f2r are consecutive (f2r->f3v has index diff 3)
    assert b["n_transitions"] == 2
    assert b["n_v_to_r_transitions"] == 1
    assert b["n_r_to_v_transitions"] == 1
    assert b["v_to_r_rate"] == 1.0
    assert b["r_to_v_rate"] == 0.0
    assert b["effect"] == 1.0
    assert b["scored"] is True


def test_predictions_logic():
    t1 = {
        "1A": {"bins": {"6-20": {"scored": True, "pass": True}, "21-100": {"scored": True, "pass": True}, "101-500": {"scored": True, "pass": False}}},
        "2B": {"bins": {"6-20": {"scored": True, "pass": True}, "21-100": {"scored": True, "pass": False}, "101-500": {"scored": True, "pass": False}}},
        "3B": {"bins": {"6-20": {"scored": True, "pass": True}, "21-100": {"scored": True, "pass": True}, "101-500": {"scored": True, "pass": True}}},
    }
    t2 = {"1A": {"pass": False}, "2B": {"pass": False}, "3B": {"pass": False}}
    t3 = {
        "1A": {"bins": {"21-100": {"scored": True, "pass": False}, "101-500": {"scored": True, "pass": False}}},
        "2B": {"bins": {"21-100": {"scored": True, "pass": False}, "101-500": {"scored": True, "pass": False}}},
        "3B": {"bins": {"21-100": {"scored": True, "pass": False}, "101-500": {"scored": True, "pass": False}}},
    }
    pred = H.predictions(t1, t2, t3)
    assert pred["F1"] is False
    assert pred["F2"] is False
    assert pred["F3"] is False

    t1["2B"]["bins"]["21-100"]["pass"] = True
    t2["1A"]["pass"] = True
    t2["2B"]["pass"] = True
    t3["2B"]["bins"]["101-500"]["pass"] = True
    pred2 = H.predictions(t1, t2, t3)
    assert pred2["F1"] is True
    assert pred2["F2"] is True
    assert pred2["F3"] is True
