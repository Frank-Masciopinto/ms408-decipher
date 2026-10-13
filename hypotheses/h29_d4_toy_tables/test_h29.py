"""Unit tests for h29 toy tables and the part-1 Spearman report. No 10k scoring."""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h29_lib as H  # noqa: E402
import h25_lib as H25  # noqa: E402

PROPS = ("mean_len", "rigidity", "H1", "decodable")


def _rows_by_state_table(rows, state):
    groups = defaultdict(list)
    for code, glyphs in rows:
        st, table, _letter = code.split("_")
        if st == state:
            groups[(st, table)].append(glyphs)
    return groups


def test_suffix_codes_are_subset_of_pool():
    rows, pool = H.toy_codes(3, 8, 1)
    assert len(pool) == 8 and len(set(pool)) == 8
    assert all(len(s) == 3 for s in pool)
    suffixes = [g for code, g in rows if code.startswith("suffix_")]
    assert len(suffixes) == 6 * 23
    assert set(suffixes) <= set(pool)


def test_unigram_codes_length_and_unique_within_state_table():
    length = 2
    rows, _pool = H.toy_codes(length, 16, 2)
    groups = _rows_by_state_table(rows, "unigram")
    assert len(groups) == 6
    for codes in groups.values():
        assert len(codes) == 23
        assert all(len(c) == length for c in codes)
        assert len(set(codes)) == len(codes)


def test_prefix_codes_match_the_same_rule_and_csv_roundtrip(tmp_path):
    path = tmp_path / "toy.csv"
    H.write_toy_tables(path, 2, 8, 1)
    text = path.read_text(encoding="utf-8").splitlines()
    assert text[0] == "code,glyphs"
    rows = []
    for line in text[1:]:
        code, glyphs = line.split(",", 1)
        rows.append((code, glyphs))
    assert len(rows) == 3 * 6 * 23
    alphabet = set(H25.GLYPHS[:20])
    assert all(set(g) <= alphabet and len(g) == 2 for _c, g in rows)
    groups = _rows_by_state_table(rows, "prefix")
    assert len(groups) == 6
    for codes in groups.values():
        assert len(set(codes)) == 23


def test_length_one_pool_caps_at_alphabet(tmp_path):
    rows, pool = H.toy_codes(1, 128, 1)
    assert len(pool) == 20 and len(set(pool)) == 20
    suffixes = [g for code, g in rows if code.startswith("suffix_")]
    assert set(suffixes) <= set(pool)
    path = tmp_path / "t.csv"
    H.write_toy_tables(path, 1, 8, 1)
    cipher = H25.NH(path, 6, "naibbe", 17 / 36)
    words = cipher.encrypt(["nel", "mezzo", "del", "cammin"] * 30, seed=1, n_words_out=20)
    assert len(words) == 20
    assert all(set(w) <= set(H25.GLYPHS[:20]) for w in words)


def test_fake_dataframe_spearman_is_finite():
    h26 = pd.DataFrame({
        "src": ["it_boccaccio"] * 5 + ["it_boccaccio", "it_boccaccio"],
        "render": ["eva"] * 5 + ["eva", "char"],
        "grammar": ["rs", "lat", "ms", "short", "loose", "naibbe", "rs"],
        "mean_len": [1, 2, 3, 4, 5, 9, 9],
        "rigidity": [0.1, 0.4, 0.2, 0.8, 0.3, 0.0, 0.0],
        "H1": [1.0, 1.4, 1.1, 1.8, 1.2, 2.0, 2.0],
        "decodable": [0.2, 0.3, 0.5, 0.7, 0.9, 0.1, 0.1],
        "m_distance": [10.0, 8.0, 6.0, 4.0, 2.0, 100.0, 100.0],
        "D4": [-1.0, -0.8, -0.5, -0.2, 0.1, 0.5, 0.5],
    })
    h25 = pd.DataFrame({
        "src": ["it_boccaccio"] * 4 + ["it_cucina"] * 2,
        "render": ["char", "char", "eva", "eva", "char", "eva"],
        "decodable": [0.2, 0.8, 0.3, 0.9, 0.1, 0.1],
        "m_distance": [5.0, 3.0, 9.0, 4.0, 50.0, 50.0],
        "D4": [-0.4, -0.1, -0.9, -0.2, 0.2, 0.2],
    })
    h24 = pd.DataFrame({
        "cipher": ["homo2", "homo2", "verb8", None],
        "m_distance": [10.0, 30.0, 5.0, 1.0],
        "D4": [-0.2, -0.4, -1.0, 0.05],
    })
    report = H.spearman_report(h26, h25, h24)
    rho = report["h26"]["m_distance"]["mean_len"]
    assert math.isfinite(rho)
    assert report["h26"]["n"] == 5
    assert abs(rho - (-1.0)) < 1e-9
    assert math.isfinite(report["h25"]["char"]["D4"]["decodable"])
    assert math.isfinite(report["h25"]["eva"]["m_distance"]["decodable"])
    by = {row["cipher"]: row for row in report["h24_by_cipher"]}
    assert set(by) == {"homo2", "verb8"}
    assert by["homo2"]["n"] == 2
    assert abs(by["homo2"]["mean_distance"] - 20.0) < 1e-9
    assert abs(by["homo2"]["mean_D4"] - (-0.3)) < 1e-9
    for prop in PROPS:
        assert math.isfinite(report["h26"]["D4"][prop])
        assert math.isfinite(report["h26"]["m_distance"][prop])
