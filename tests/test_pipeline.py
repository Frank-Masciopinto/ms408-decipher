"""Integration tests on a small synthetic corpus (always run) and on the real ZL file
(skipped when the data has not been fetched)."""
import pytest

from msdecipher import analysis
from msdecipher.paths import transcription_dir

pytestmark = []

SYN = ["#=IVTFF Eva- 2.0 M 5", "<f1r>      <! $Q=A $P=A $I=H $L=A $H=1>"]
SYN_B = ["<f2r>      <! $Q=A $P=B $I=H $L=B $H=1>"]


def _synthetic_file(tmp_path):
    import random
    rng = random.Random(5)
    onsets = ["ch", "sh", "d", "k", "qok", "ot", "ol"]
    mids = ["e", "ee", "a", "o", "ai"]
    ends = ["dy", "in", "iin", "y", "ol", "r"]

    def word():
        return rng.choice(onsets) + rng.choice(mids) + rng.choice(ends)

    lines = list(SYN)
    for i in range(1, 60):
        lines.append(f"<f1r.{i},{'@' if i == 1 else '+'}P0>       " + ".".join(word() for _ in range(rng.randint(4, 9))))
    lines += SYN_B
    for i in range(1, 60):
        lines.append(f"<f2r.{i},{'@' if i == 1 else '+'}P0>       " + ".".join(word() + ("y" if rng.random() < .3 else "") for _ in range(rng.randint(4, 9))))
    p = tmp_path / "SYN-n.txt"
    p.write_text("\n".join(lines) + "\n")
    return p


def test_full_pipeline_on_synthetic_file(tmp_path):
    f = _synthetic_file(tmp_path)
    out = analysis.run_all(f, out_reports=tmp_path / "r", out_glyphs=tmp_path / "g", replicate=False,
                           boot=10, perms=10, quiet=True)
    for name in ("stats_report.md", "summary_stats.csv", "sukhotin.csv", "unit_frequencies.csv",
                 "positional_units.csv", "currier_ab_units.csv", "currier_ab_words.csv",
                 "word_frequencies_top1000.csv", "word_length_distribution.csv"):
        assert (tmp_path / "r" / name).stat().st_size > 0, name
    for name in ("catalog.csv", "REPORT.md", "digraph_candidates.csv", "top_pmi_bigrams.csv"):
        assert (tmp_path / "g" / name).stat().st_size > 0, name
    pngs = list((tmp_path / "r" / "figures").glob("*.png"))
    assert len(pngs) == 5 and all(p.stat().st_size > 1000 for p in pngs)
    rep = (tmp_path / "r" / "stats_report.md").read_text()
    assert "not decoding" in rep and "undeciphered" in rep
    # hard rule: reports never label word classes
    low = rep.lower()
    for bad in (" verb", " noun", "is a name", "translation:"):
        assert bad not in low.replace("part of speech", "")
    assert res_ok(out)


def res_ok(res):
    s = res["summary"]
    assert s.loc["Currier A", "n_tokens"] > 100 and s.loc["Currier B", "n_tokens"] > 100
    assert 0 < res["currier_ab"]["unit_jsd"] < 1
    return True


def test_non_eva_alphabet_rejected(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("#=IVTFF v101 2.0 M 6\n<f1r>\n<f1r.1,@P0>   abc.def\n")
    with pytest.raises(ValueError, match="not EVA"):
        analysis.run_all(p, out_reports=tmp_path / "r", out_glyphs=tmp_path / "g", quiet=True)


def test_missing_file_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        analysis.load_corpus(tmp_path / "nope.txt")


def test_md_table_handles_nan():
    import pandas as pd
    out = analysis.md_table(pd.DataFrame({"a": [1.0, float("nan")], "b": ["x", "y"]}))
    assert "–" in out and out.count("\n") == 3


real = pytest.mark.skipif(not (transcription_dir() / "ZL3b-n.txt").exists(),
                          reason="run `python -m msdecipher fetch` first")


@real
@pytest.mark.realdata
def test_real_zl_counts_match_published_inventory():
    c = analysis.load_corpus()
    counts = c.locus_type_counts()
    # inventory stated in docs/DATA_SOURCES.md for ZL 3b
    assert (counts["P"], counts["L"], counts["C"], counts["R"], counts["total"]) == (4130, 1029, 84, 142, 5385)
    assert sum(len(l.warnings) for l in c.loci) == 0
    A = c.select("P", language="A")
    B = c.select("P", language="B")
    assert len(A) > 1000 and len(B) > 2000


@real
@pytest.mark.realdata
def test_real_all_transcriptions_parse():
    from msdecipher.ivtff import parse_file
    for fn in ("IT2a-n.txt", "RF1b-e.txt", "GC2a-n.txt"):
        p = transcription_dir() / fn
        if p.exists():
            c = parse_file(p)
            assert len(c.loci) > 5000 and c.version == "2.0"


@real
@pytest.mark.realdata
def test_real_headline_numbers_are_in_expected_ranges():
    from msdecipher.corpus_view import lines_for, readable_words
    from msdecipher import stats as S
    from msdecipher.segment import Segmenter
    c = analysis.load_corpus()
    P = lines_for(c, generic="P")
    words = readable_words(P)
    ws = S.word_stats(words, Segmenter.preset("collapsed"))
    assert 30000 < ws["n_tokens"] < 40000
    assert -1.3 < ws["zipf_ols_slope_r10_1000"] < -0.9          # earlier smoke test: about -1.10
    assert 0.6 < ws["heaps_beta_in_order"] < 0.85
    top = [w for w, _ in __import__("collections").Counter(words).most_common(5)]
    assert "daiin" in top or "chedy" in top
    seqs = [Segmenter.preset("collapsed")(w) for w in words]
    ep = S.entropy_profile(seqs, n_shuffles=2)
    assert ep["h2"] < ep["H1"] - 1.0 and ep["h2_within_word_shuffle"] > ep["h2"] + 0.5
    raw_v, _ = S.sukhotin([tuple(w) for w in words], min_count=20)
    seg_v, _ = S.sukhotin(seqs, min_count=20)
    assert "h" in raw_v                    # artefact of splitting ch/sh (documented)
    assert "ch" not in seg_v and "sh" not in seg_v
