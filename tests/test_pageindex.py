from msdecipher.pageindex import (classify_caption, match_folios, build_rows, write_index, read_index, summarize)

TF = ["f1r", "f1v", "f67r1", "f67r2", "f69v", "f70r1", "f70r2", "f70v2", "f70v1", "f85r1", "f86v4", "f116v"]


def test_classify_caption_kinds():
    assert classify_caption("1r") == ("folio", ["1r"])
    assert classify_caption("[Front cover]")[0] == "non_folio"
    assert classify_caption("[Back flyleaf recto]")[0] == "non_folio"
    assert classify_caption("Yale University Library Digital Collections")[0] == "non_folio"
    assert classify_caption("69v and 70r") == ("multi", ["69v", "70r"])
    assert classify_caption("70v (part)") == ("part", ["70v"])
    assert classify_caption("85v and 86r (foldout)")[0] == "foldout"
    assert classify_caption("")[0] == "non_folio"


def test_match_folios_prefix_with_subfolios():
    assert match_folios("67r", TF) == ["f67r1", "f67r2"]
    assert match_folios("1r", TF) == ["f1r"]
    assert match_folios("6r", TF) == []            # must not match f67r1 / f69v prefixes
    assert match_folios("7v", TF) == []


def test_build_rows_grading_and_csv(tmp_path):
    caps = {1: "Yale University Library Digital Collections", 4: "1r", 5: "1v", 6: "67r", 7: "69v and 70r",
            8: "70v (part)", 9: "99r", 10: "[Spine]"}
    info = {"f1r": {"I": "T", "L": "A", "H": "1", "n_p_lines": 28}, "f1v": {"I": "H", "n_p_lines": 12}}
    rows = {r.pdf_page: r for r in build_rows(caps, TF, info)}
    assert rows[1].match == "non_folio" and rows[10].match == "non_folio"
    assert rows[4].match == "exact" and rows[4].folios == "f1r" and rows[4].text_page_candidate
    assert rows[5].match == "exact" and not rows[5].text_page_candidate      # herbal page
    assert rows[6].match == "multi_subfolio" and rows[6].folios == "f67r1;f67r2"
    assert rows[7].match == "multi_folio"
    assert rows[8].match == "multi_folio"
    assert rows[9].match == "no_transcription"
    p = write_index(list(rows.values()), tmp_path / "idx.csv")
    back = read_index(p)
    assert [r["pdf_page"] for r in back] == [str(i) for i in sorted(rows)]
    assert summarize(list(rows.values()))["exact"] == 2
