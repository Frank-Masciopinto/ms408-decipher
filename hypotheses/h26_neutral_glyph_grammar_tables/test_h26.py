import csv

import h26_lib as L


def test_slot_grammar_respects_order_and_parts():
    g = L.SlotGrammar(1, S=6, alpha=.5, p_fill=1.0)
    w = g.sample("unigram"); assert len(w) == 6 and all(ch in inv for ch, (inv, _) in zip(w, g.slots))
    assert len(g.sample("prefix")) == 3 and len(g.sample("suffix")) == 3


def test_chain_grammar_and_tables(tmp_path):
    g = L.ChainGrammar([tuple("abc"), tuple("abd"), tuple("bcd")] * 10, 1)
    f = L.write_tables(tmp_path / "t.csv", g); rows = list(csv.DictReader(open(f, encoding="utf-8")))
    assert len(rows) == 3 * 6 * 23 and all(set(r["glyphs"]) <= set("abcd?") for r in rows)


def test_grammar_props():
    p = L.grammar_props(["ab", "ab", "ab"], tuple); assert p["rigidity"] == 1.0 and p["H1"] == 1.0 and p["mean_len"] == 2
    q = L.grammar_props(["ab", "ba"], tuple); assert q["rigidity"] == 0.0
