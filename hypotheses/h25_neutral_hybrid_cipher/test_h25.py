import csv

import h25_lib as L


def test_random_tables_format_and_alphabet(tmp_path):
    f = L.write_tables(tmp_path / "t.csv", 15, "base", 1); rows = list(csv.DictReader(open(f, encoding="utf-8")))
    assert len(rows) == 3 * 6 * 23 and all(set(r["glyphs"]) <= set(L.GLYPHS[:15]) for r in rows)
    assert all(1 <= len(r["glyphs"]) <= 3 for r in rows if r["code"].startswith("unigram"))
    assert all(1 <= len(r["glyphs"]) <= 2 for r in rows if not r["code"].startswith("unigram"))


def test_nh_cipher_structure(tmp_path):
    c = L.make_cipher("T1", 2, tmp_path); w = c.encrypt(["nel", "mezzo", "del", "cammin"] * 50, seed=1)
    assert w and all(set(x) <= set(L.GLYPHS[:20]) for x in w)
    d = c._deck(__import__("random").Random(0)); assert set(d) == {"alpha"}
    u = L.make_cipher("uniform", 2, tmp_path)._deck(__import__("random").Random(0)); assert len(set(u)) == 6 and len(u) == 78


def test_eva_render_is_injective_and_not_frequency_based():
    m = L.eva_render(3, 25); assert len(set(m.values())) == 25 and set(m.values()) <= set(L.EVA_UNITS)
    assert L.eva_render(3, 25) == m and L.eva_render(4, 25) != m
