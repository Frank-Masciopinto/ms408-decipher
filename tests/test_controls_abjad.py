"""Hebrew / Arabic abjad controls: normalisation, transliteration invariance, generic transforms, fetch plumbing."""
import json

import pandas as pd
import pytest

from msdecipher import controls_fetch as F
from msdecipher import controls_metrics as M
from msdecipher import controls_run as R
from msdecipher import controls_text as X
from msdecipher import controls_transforms as T

HE = "בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים אֵ֥ת הַשָּׁמַ֖יִם וְאֵ֥ת הָאָֽרֶץ׃ {פ} [x] כל־העם"
AR = "بِسْمِ ٱللَّهِ الرَّحْمَٰنِ الرَّحِيمِ ـ أَحْمَدُ وإبراهيم وآدم ١٢٣ abc"


def test_hebrew_normalisation():
    toks = X.normalise_abjad_text(HE, "hebrew")
    assert toks == ["בראשית", "ברא", "אלהים", "את", "השמים", "ואת", "הארץ", "כל", "העם"]    # maqaf splits, marks/brackets gone
    assert all(0x5D0 <= ord(c) <= 0x5EA for t in toks for c in t)
    fold = X.normalise_abjad_text(HE, "hebrew", "folded")
    assert fold[2] == "אלהימ" and fold[4] == "השמימ" and fold[6] == "הארצ"        # final forms folded
    assert not set("ךםןףץ") & set("".join(fold))


def test_arabic_normalisation():
    toks = X.normalise_abjad_text(AR, "arabic")
    assert toks == ["بسم", "الله", "الرحمن", "الرحيم", "احمد", "وابراهيم", "وادم"]   # harakat/tatweel/digits/latin gone, alef variants -> alef
    red = X.normalise_abjad_text("مدرسة موسى ؤ ء", "arabic", "folded")
    assert red == ["مدرسه", "موسي", "و"]                                              # reduced alphabet, empty tokens dropped
    with pytest.raises(ValueError):
        X.normalise_abjad_text("x", "greek")


def test_strip_html_drops_citations():
    raw = 'שנאמר <small>(שמות לד כא)</small> "וביום" <sup>1</sup><i class="footnote">הערה</i> <b>סוף</b>&nbsp;.'
    toks = X.normalise_abjad_text(X.strip_html(raw), "hebrew")
    assert toks == ["שנאמר", "וביום", "סוף"]


def test_wikitext_ar_cleaning():
    wt = "{{ترويسة|عنوان={{x|y}}}}\n== باب ==\nقال [[الرجل|الرجل]] كلمة\n[[تصنيف:كتب]]"
    toks = X.normalise_abjad_text(X.clean_wikitext_ar(wt), "arabic")
    assert toks == ["قال", "الرجل", "كلمة"]


def test_translit_is_one_to_one_and_metrics_invariant():
    he = X.normalise_abjad_text("שלום עולם ושלום לכל העולם הזה ושלום ךםןףץ קרשת", "hebrew")
    ar = X.normalise_abjad_text("السلام عليكم ورحمة الله وبركاته ء ؤ ئ ة ى", "arabic")
    for toks, sc in ((he, "hebrew"), (ar, "arabic")):
        tr = X.transliterate(toks, sc)
        assert [len(t) for t in tr] == [len(t) for t in toks]                    # single character per letter
        table = X.HEBREW_TRANSLIT if sc == "hebrew" else X.ARABIC_TRANSLIT
        assert len(set(table.values())) == len(table)                          # injective
    words = (T.markov_char(he, 4000, 1, 1)) + he * 20
    tr = X.transliterate(words, "hebrew")
    a = M.metrics(words, seed=1, n_shuffles=2)
    b = M.metrics(tr, seed=1, n_shuffles=2)
    for k in ("unit_h2", "unit_h3", "shuffle_gap_h2", "pos_skewed_unit_share", "zipf_mle_s_r10_1000"):
        assert a[k] == pytest.approx(b[k])


def test_vigenere_generic_non_latin_and_seeded():
    toks = X.normalise_abjad_text("בראשית ברא אלהים את השמים ואת הארץ", "hebrew") * 30
    a = T.vigenere_generic(toks, 3, seed=1)
    assert a == T.vigenere_generic(toks, 3, seed=1) and a != T.vigenere_generic(toks, 3, seed=2)
    assert [len(w) for w in a] == [len(w) for w in toks]
    assert set("".join(a)) <= set("".join(toks))                               # same alphabet
    assert a != toks
    # a pure key shift (key_len 1) is a relabelling: entropies unchanged
    one = T.vigenere_generic(toks, 1, seed=3)
    assert M.metrics(one, seed=1, n_shuffles=1)["unit_h2"] == pytest.approx(M.metrics(toks, seed=1, n_shuffles=1)["unit_h2"])


def test_generic_transforms_run_on_hebrew():
    toks = X.normalise_abjad_text("בראשית ברא אלהים את השמים ואת הארץ והארץ היתה תהו ובהו", "hebrew") * 20
    for name, fn in T.GENERIC_TRANSFORMS.items():
        out = fn(toks, 1)
        assert len(out) == len(toks), name


def test_load_tokens_tanzil_and_variants(tmp_path):
    (tmp_path / "ar_quran_tanzil_simple_clean.txt").write_text(
        "1|1|بسم الله الرحمن الرحيم\n1|2|الحمد لله رب العالمين\n\n# PLEASE DO NOT REMOVE\n#  License: CC\n", encoding="utf-8")
    t = X.load_tokens("ar_quran", 100, directory=tmp_path)
    assert t == "بسم الله الرحمن الرحيم الحمد لله رب العالمين".split()
    assert X.load_tokens("ar_quran", 3, directory=tmp_path) == t[:3]
    (tmp_path / "he_tanakh_genesis_exodus.txt").write_text("בראשית ברא אלהים\nואת הארץ\n", encoding="utf-8")
    assert X.load_tokens("he_tanakh", 100, directory=tmp_path, variant="folded")[2] == "אלהימ"


def test_fetch_sefaria_parses_nested_lists(monkeypatch):
    class R_:
        def json(self):
            return {"versions": [{"text": [["א ב", "ג"], ["ד"]]}]}
    monkeypatch.setattr(F, "_get", lambda url, params=None: R_())
    out = F.fetch_sefaria(["Genesis", "Exodus"], "hebrew|v").decode()
    assert out.split("\n")[:4] == ["א ב", "ג", "ד", "א ב"]


def test_fetch_all_merges_manifest_when_only(tmp_path, monkeypatch):
    (tmp_path / "MANIFEST.json").write_text(json.dumps({"files": [{"id": "la_vulgate", "file": "x", "sha256": "abc"}]}))
    monkeypatch.setattr(F, "fetch_sefaria", lambda refs, version: "בראשית\n".encode())
    man = F.fetch_all(tmp_path, only=["he_tanakh"])
    ids = [e["id"] for e in man["files"]]
    assert ids == ["la_vulgate", "he_tanakh"]                                  # existing entry kept, SOURCES order
    assert (tmp_path / "he_tanakh_genesis_exodus.txt").exists()
    assert {s["id"] for s in F.SOURCES} >= {"he_tanakh", "he_mishneh_torah", "ar_quran", "ar_muqaddimah"}
    q = F.source_by_id("ar_quran") if hasattr(F, "source_by_id") else X.source_by_id("ar_quran")
    assert "verbatim" in q["licence"]


def _row(family, base, **kw):
    cols = {m: 1.0 for m in M.METRIC_INFO}
    cols.update(kw)
    return dict(family=family, base=base, **cols)


def test_verdict_shift_detects_band_change():
    rows = {R.MS_MAIN: _row("MS 408", "-", unit_h2=2.2), R.MS_RAW: _row("MS 408", "-", unit_h2=2.0),
            "nat_a": _row("nat", "la", unit_h2=3.2), "nat_b": _row("nat", "it", unit_h2=3.0),
            "nat_he": _row("nat", "he_tanakh", unit_h2=2.1),
            "plain:he_tanakh": _row(R.FAMILY_ABJAD, "he_tanakh", unit_h2=2.1)}
    sh = R.verdict_shift(pd.DataFrame.from_dict(rows, orient="index"))
    r = sh.set_index(["family", "metric"])
    assert r.loc[("nat", "unit_h2"), "verdict_before"] == "↓" and r.loc[("nat", "unit_h2"), "verdict_after"] == "≈"
    assert r.loc[("nat", "unit_h2"), "changed"]
    assert r.loc[(R.FAMILY_ABJAD, "unit_h2"), "verdict_before"] == "(family is new)"
    assert not r.loc[("nat", "unit_H1"), "changed"]
    # no abjad rows -> None
    assert R.verdict_shift(pd.DataFrame.from_dict({k: v for k, v in rows.items() if "he" not in k}, orient="index")) is None


def test_run_controls_small_with_abjad(tmp_path, monkeypatch):
    lat = ("in principio creavit deus caelum et terram terra autem erat inanis et vacua "
           "tenebrae erant super faciem abyssi spiritus dei ferebatur super aquas dixitque fiat lux").split()
    heb = X.normalise_abjad_text("בראשית ברא אלהים את השמים ואת הארץ והארץ היתה תהו ובהו וחשך על פני תהום ורוח אלהים מרחפת על פני המים", "hebrew")

    def fake_load(cid, n_tokens=0, directory=None, variant="main"):
        base = heb if cid.startswith(("he_", "ar_")) else lat
        if variant == "folded":
            base = X.normalise_abjad_text(" ".join(base), "hebrew", "folded")
        return (base * 200)[:n_tokens]
    monkeypatch.setattr(R, "load_tokens", fake_load)
    monkeypatch.setattr(R, "ms_variants", lambda *a, **k: ({}, None))
    R.run_controls(n_tokens=600, seeds=1, out_dir=tmp_path, make_plots=False, quiet=True)
    df = pd.read_csv(tmp_path / "comparison.csv")
    names = set(df["name"])
    assert {"plain:he_tanakh", "plain_folded:ar_quran", "vigenere_k3:he_mishneh_torah", "naibbe_like:ar_muqaddimah",
            "markov_o2:he_tanakh", "iid_letters:ar_quran", "shuffle_letters:he_tanakh"} <= names
    fam = df.set_index("name")["family"]
    assert fam["plain:he_tanakh"] == R.FAMILY_ABJAD and fam["plain_folded:he_tanakh"] == R.FAMILY_ABJAD_VARIANT
    assert fam["alphagram:ar_quran"] == R.TRANSFORM_FAMILY["alphagram"]
