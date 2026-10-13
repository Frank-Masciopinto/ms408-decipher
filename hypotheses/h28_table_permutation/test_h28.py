"""Unit tests for h28 table permutations. No full scoring."""
from collections import Counter

import pytest

import h28_lib as L


def fake_rows():
    rows = []
    for state in ("unigram", "prefix", "suffix"):
        for table in ("alpha", "beta1"):
            for letter in "abc":
                rows.append({"code": f"{state}_{table}_{letter}", "glyphs": f"{state}-{table}-{letter}"})
    return rows


def char_seg(text):
    return tuple(text)


def counters(rows, states=("unigram", "prefix", "suffix")):
    grouped = {}
    for r in rows:
        state, table, _letter = r["code"].split("_")
        if state not in states:
            continue
        grouped.setdefault((state, table), []).append(r["glyphs"])
    return {k: Counter(v) for k, v in grouped.items()}


def affix_counters(rows):
    grouped = {}
    for r in rows:
        state, table, _letter = r["code"].split("_")
        if state == "unigram":
            continue
        grouped.setdefault(table, []).append(r["glyphs"])
    return {k: Counter(v) for k, v in grouped.items()}


def test_letter_fake_preserves_multiset_per_state_table():
    rows = fake_rows()
    out = L.permute_letter(rows, 4001)
    assert counters(rows) == counters(out)
    assert [r["code"] for r in out] == [r["code"] for r in rows]
    assert rows == fake_rows()


def test_letter_real_csv_preserves_multiset_and_moves_strings():
    rows = L.load_rows()
    assert len(rows) == 3 * 6 * 23
    out = L.permute_letter(rows, 4001)
    got = counters(rows)
    assert got == counters(out)
    assert all(sum(c.values()) == 23 for c in got.values())
    assert [r["glyphs"] for r in out] != [r["glyphs"] for r in rows]
    assert L.permute_letter(rows, 4001) == out
    assert L.permute_letter(rows, 4001) != L.permute_letter(rows, 4002)


def test_state_fake_keeps_unigrams_and_affix_multiset():
    rows = fake_rows()
    out = L.permute_state(rows, 4002)
    uni = lambda rs: {r["code"]: r["glyphs"] for r in rs if r["code"].startswith("unigram_")}
    assert uni(rows) == uni(out)
    assert affix_counters(rows) == affix_counters(out)
    assert rows == fake_rows()


def test_state_real_csv_keeps_unigrams_and_pools_affixes():
    rows = L.load_rows()
    out = L.permute_state(rows, 4002)
    uni = lambda rs: {r["code"]: r["glyphs"] for r in rs if r["code"].startswith("unigram_")}
    assert uni(rows) == uni(out)
    assert affix_counters(rows) == affix_counters(out)
    affix = lambda rs: [(r["code"], r["glyphs"]) for r in rs if not r["code"].startswith("unigram_")]
    assert affix(rows) != affix(out)


def test_unit_real_csv_preserves_unit_multiset():
    rows = L.load_rows()
    seg = L.segmenter()
    out, changed = L.permute_unit(rows, 4003, seg)
    assert len(out) == len(rows)
    for src, dst in zip(rows, out):
        assert Counter(seg(src["glyphs"])) == Counter(seg(dst["glyphs"]))
        if len(seg(src["glyphs"])) == 1:
            assert src["glyphs"] == dst["glyphs"]
    assert 0 < changed < len(rows)
    assert rows[0]["glyphs"] == L.load_rows()[0]["glyphs"]


def test_unit_change_counts_match_file_order_shuffle():
    rows = L.load_rows()
    seg = L.segmenter()
    got = [L.permute_unit(rows, 4000 + s, seg)[1] for s in range(1, 6)]
    assert got == [309, 313, 313, 312, 316]


def test_unit_fake_preserves_multiset_and_single_unit():
    rows = [
        {"code": "unigram_alpha_a", "glyphs": "ab"},
        {"code": "unigram_alpha_b", "glyphs": "c"},
    ]
    out, changed = L.permute_unit(rows, 4004, char_seg)
    assert out[1]["glyphs"] == "c"
    assert Counter(char_seg(out[0]["glyphs"])) == Counter("ab")
    assert changed in (0, 1)
    assert rows[0]["glyphs"] == "ab"


def test_unit_roundtrip_failure_exits():
    rows = [{"code": "unigram_alpha_a", "glyphs": "ab"}]
    with pytest.raises(SystemExit):
        L.permute_unit(rows, 1, lambda _text: ("a",))


def test_real_strings_roundtrip_readonly():
    rows = L.load_rows()
    L.assert_roundtrip(rows, L.segmenter())


def test_permute_uses_seed_4000_plus_s():
    rows = fake_rows()
    letter, _changed = L.permute(rows, "letter", 1)
    assert letter == L.permute_letter(rows, 4001)
    state, changed = L.permute(rows, "state", 4)
    assert changed is None and state == L.permute_state(rows, 4004)
    unit, n_changed = L.permute(rows, "unit", 2, char_seg)
    direct, n_direct = L.permute_unit(rows, 4002, char_seg)
    assert unit == direct and n_changed == n_direct


def test_unknown_condition_raises():
    with pytest.raises(ValueError):
        L.permute(fake_rows(), "nope", 1)


def test_assert_permutation_rejects_a_broken_map():
    rows = fake_rows()
    bad = [dict(r) for r in rows]
    bad[0] = {"code": bad[0]["code"], "glyphs": "not-in-the-multiset"}
    with pytest.raises(SystemExit):
        L.assert_permutation("letter", rows, bad)
    unit_rows = [{"code": "unigram_alpha_a", "glyphs": "ab"}]
    broken = [{"code": "unigram_alpha_a", "glyphs": "aa"}]
    with pytest.raises(SystemExit):
        L.assert_permutation("unit", unit_rows, broken, char_seg)


def test_source_csv_is_not_modified():
    digest = L.NAIBBE.read_bytes()
    rows = L.load_rows()
    L.permute_letter(rows, 4001)
    L.permute_state(rows, 4001)
    L.permute_unit(rows, 4001)
    assert L.NAIBBE.read_bytes() == digest


def test_write_refuses_original_and_outside(tmp_path):
    with pytest.raises(SystemExit):
        L.write_table(L.NAIBBE, [])
    with pytest.raises(SystemExit):
        L.write_table(tmp_path / "h28_letter_s1.csv", [])


def test_names():
    assert L.cell_name("letter", 1) == "T_boccaccio_letter_s1"
    assert L.cell_name("state", 5) == "T_boccaccio_state_s5"
    assert L.cell_name("unit", 3) == "T_boccaccio_unit_s3"
    assert L.table_path("unit", 4).name == "h28_unit_s4.csv"


def test_match_rule_predictions_and_reading():
    assert L.condition_matches(5.43, 0.60)
    assert L.condition_matches(5.43, 3 / 5)
    assert not L.condition_matches(5.4300001, 1.0)
    assert not L.condition_matches(0.0, 0.599999)
    assert not L.condition_matches(5.43, 2 / 5)
    assert L.prediction_pass("letter", True) and not L.prediction_pass("letter", False)
    assert L.prediction_pass("state", False) and not L.prediction_pass("state", True)
    assert L.prediction_pass("unit", False) and not L.prediction_pass("unit", True)
    assert L.reading(True, True, False) == "orthography"
    assert L.reading(True, False, False) == "orthography"
    assert L.reading(True, False, True) == "complementarity"
    assert L.reading(True, True, True) == "length+homophony"
    assert L.reading(False, False, False) == "none"
    assert L.reading(False, True, True) == "unlisted"
