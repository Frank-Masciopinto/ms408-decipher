import pytest

from msdecipher.corpus_view import lines_for, readable_words
from msdecipher.glyphs import glyph_table, digraph_table
from msdecipher.ivtff import rare_char
from msdecipher.segment import Segmenter, PRESETS


def test_presets_and_greedy_longest_match():
    raw = Segmenter.preset("raw")
    assert raw("chedy") == ("c", "h", "e", "d", "y")
    basic = Segmenter.preset("basic")
    assert basic("chedy") == ("ch", "e", "d", "y")
    assert basic("shokchy") == ("sh", "o", "k", "ch", "y")
    col = Segmenter.preset("collapsed")
    assert col("ckhey") == ("ckh", "e", "y")          # longest match beats c + kh
    assert col("cthy") == ("cth", "y")
    ext = Segmenter.preset("extended")
    assert ext("qokaiin") == ("q", "o", "k", "a", "iin")
    assert ext("daiiin") == ("d", "a", "ii", "in")


def test_rare_and_unreadable_are_single_units():
    seg = Segmenter.preset("collapsed")
    w = "ch" + rare_char(150) + "?"
    assert seg(w) == ("ch", rare_char(150), "?")


def test_custom_spec_and_errors():
    seg = Segmenter.from_spec("ch,sh,qo")
    assert seg("qochol") == ("qo", "ch", "o", "l")
    assert Segmenter.from_spec("basic").name == "basic"
    with pytest.raises(ValueError):
        Segmenter.preset("nope")
    assert set(PRESETS) >= {"raw", "basic", "collapsed", "extended"}


def test_segmentation_is_lossless():
    seg = Segmenter.preset("extended")
    for w in ["daiin", "qokeedy", "cthhy", "shckhey", "iiin", "chchch"]:
        assert "".join(seg(w)) == w


def test_glyph_table_counts_and_positions(sample_corpus):
    P = lines_for(sample_corpus, generic="P")
    t = glyph_table({"P": P, "A": lines_for(sample_corpus, generic="P", language="A")}, main="P")
    row = t[t.glyph == "q"].iloc[0]
    assert row["count"] == 4 and row["initial"] == 1.0   # qol, qokedy, qokeedy, qokain
    assert (t["count"] >= 0).all() and t["rank"].is_monotonic_increasing
    assert "@130;" in set(t.glyph)                                 # rare code rendered, counted
    assert t[t.glyph == "@130;"].iloc[0]["kind"] == "rare-code"
    assert "count_A" in t.columns


def test_digraph_table_cohesion(sample_corpus):
    P = lines_for(sample_corpus, generic="P")
    d = digraph_table(P, candidates=["ch", "qo", "cth"])
    ch = d[d.candidate == "ch"].iloc[0]
    assert ch["occurrences"] >= 3
    assert 0 < ch["p_next_given_first"] <= 1
    assert d[d.candidate == "cth"].iloc[0]["occurrences"] >= 1
