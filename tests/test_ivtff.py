from msdecipher.ivtff import (parse_lines, parse_text, words_of, render, rare_char, is_rare,
                              iter_word_lines, readable)


def test_header_pages_and_loci(sample_corpus):
    c = sample_corpus
    assert (c.alphabet, c.version, c.mode) == ("Eva-", "2.0", "M")
    assert list(c.pages) == ["f1r", "f1v"]
    assert c.pages["f1r"].vars["I"] == "T"
    assert c.pages["f1r"].comments == ["page 1"]
    assert len(c.loci) == 11
    first = c.loci[0]
    assert (first.folio, first.num, first.locator, first.ltype) == ("f1r", 1, "@", "P0")
    assert first.generic == "P"
    assert first.section == "text-only"
    assert first.language == "A" and first.hand == "1" and first.currier_hand == "1"


def test_comments_paragraph_marks_and_tokens(sample_corpus):
    l1 = sample_corpus.loci[0]
    assert l1.paragraph_start and not l1.paragraph_end
    assert l1.comments == ["strange r"]
    assert [t.text for t in l1.tokens][:5] == ["fachys", "ykal", "ar", "ataiin", "shol"]
    assert [t.space_after for t in l1.tokens][-1] is None
    pt = sample_corpus.loci[2]
    assert pt.ltype == "Pt" and pt.paragraph_end and not pt.starts_own_line


def test_uncertain_spaces_alternatives_ligatures_rare_unreadable(sample_corpus):
    l2 = sample_corpus.loci[1]
    toks = l2.tokens
    assert toks[2].text == "or" and toks[2].space_after == ","
    assert [t.text for t in toks][:4] == ["sory", "ckhar", "or", "y"]
    assert toks[4].text == "kair"
    lig = toks[5]
    assert lig.text == "c'y" and lig.ligature
    alt = toks[6]
    assert alt.uncertain_reading
    assert alt.text == "dai" + "cto" + "y"
    assert alt.alternatives == [("cto", rare_char(194))]
    assert alt.ligature
    last = toks[7]
    assert last.text == "d?n" and last.unreadable
    # first-option policy for l1: [cth:oto]res -> cthres
    assert sample_corpus.loci[0].tokens[6].text == "cthres"


def test_rare_codes_drawing_intrusions_unknown_runs(sample_corpus):
    l4 = sample_corpus.loci[3]
    texts = [t.text for t in l4.tokens]
    assert texts[0] == "odar"
    assert texts[1] == rare_char(130) + "chy" and is_rare(texts[1][0])
    assert render(texts[1]) == "@130;chy"
    assert texts[2] == "?" and l4.tokens[2].unreadable          # '???' is one unreadable marker
    assert (texts[3], l4.tokens[3].space_after) == ("qol", "<->")
    assert (texts[4], l4.tokens[4].space_after) == ("daiin", ".")
    assert l4.tokens[5].text == "ok" and l4.tokens[5].space_after == "<~>"
    assert l4.paragraph_start and l4.comments == ["@252;"]
    assert l4.tokens[1].has_rare


def test_locator_bang_and_continuation(sample_corpus):
    nonexist = sample_corpus.loci[4]
    assert nonexist.locator == "!"
    cont = sample_corpus.loci[5]
    # '/' continuation: pieces are concatenated literally ("eee" + "fff.ggg")
    assert [t.text for t in cont.tokens] == ["aaa", "bbb", "ccc", "ddd", "eeefff", "ggg"]


def test_text_tags_and_unset(sample_corpus):
    c = sample_corpus
    l = {lc.locus_id: lc for lc in c.loci}
    assert l["f1v.1"].language is None          # page var $L=@ and no tag yet
    assert l["f1v.2"].language == "B" and l["f1v.2"].hand == "2"
    assert l["f1v.3"].language == "B" and l["f1v.3"].hand == "2"   # tag persists to later lines
    assert l["f1v.5"].language is None           # <@L=@> unsets
    assert l["f1v.5"].hand == "2"


def test_select_filters(sample_corpus):
    c = sample_corpus
    ids = [lc.locus_id + lc.ltype for lc in c.select("P")]
    assert "f1r.5P0" not in ids            # '!' locator dropped
    assert all(lc.generic == "P" for lc in c.select("P"))
    assert [lc.ltype for lc in c.select("L")] == ["Lp"]   # Lx extraneous dropped
    assert len(c.select("P", language="B")) == 2
    assert len(c.select("L", exclude_extraneous=False)) == 2
    assert c.locus_type_counts()["P"] == 9


def test_words_of_join_vs_split(sample_corpus):
    l2 = sample_corpus.loci[1]
    split = words_of(l2, "split")
    join = words_of(l2, "join")
    assert "or" in split and "y" in split
    assert "ory" in join and len(join) == len(split) - 1
    import pytest
    with pytest.raises(ValueError):
        words_of(l2, "bogus")


def test_iter_word_lines_and_readable(sample_corpus):
    lines = list(iter_word_lines(sample_corpus.select("P")))
    assert lines and all(isinstance(w, str) for ln in lines for w in ln)
    assert not readable("d?n") and readable("dan")


def test_parse_text_warnings():
    toks, comments, ps, pe, tags, warns = parse_text("abc..def")
    assert [t.text for t in toks] == ["abc", "def"]
    assert warns
    toks, *_rest, warns = parse_text("<unknown>abc")
    assert warns and toks[0].text == "abc"
    toks, comments, ps, pe, tags, warns = parse_text("<@H=3>x")
    assert tags == {"H": "3"}


def test_bad_lines_do_not_crash():
    c = parse_lines(["#=IVTFF Eva- 2.0 M", "garbage", "<f1r>", "<f1r.1,+P0>"], "x")
    assert len(c.loci) == 1 and c.loci[0].tokens == []
