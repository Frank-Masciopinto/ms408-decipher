"""Tests for the image glyph stage on SYNTHETIC images (no manuscript data needed)."""
import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")
pytest.importorskip("scipy")
pytest.importorskip("skimage")
pytest.importorskip("sklearn")
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from msdecipher import imgproc as ip  # noqa: E402
from msdecipher import glyph_stage as gs  # noqa: E402
from msdecipher.segment import Segmenter  # noqa: E402

WORDS = [["daiin", "qokeedy", "chol"], ["shedy", "okaiin", "ar", "chedy"], ["qokal", "dar", "olkeey"],
         ["ytchy", "otar", "ol", "shol", "dy"], ["chor", "qokain", "sheody"]]


def synthetic_page(skew=0.0, pitch=44, size=(1000, 700), words=WORDS, border=True):
    """Gray 'parchment' with dark scanner border and black text lines (PIL default font, scalable)."""
    W, H = size
    img = Image.new("L", (W, H), 205)
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=26)
    y = 70
    for line in words:
        x = 90
        for w in line:
            d.text((x, y), w, fill=30, font=font)
            x += int(d.textlength(w, font=font)) + 34
        y += pitch
    if skew:
        img = img.rotate(skew, resample=Image.BILINEAR, fillcolor=205)
    a = np.array(img)
    if border:
        a[:, :25] = 10
        a[:, -25:] = 10
        a[:20] = 10
        a[-20:] = 10
    return a


def test_page_region_excludes_dark_border():
    a = synthetic_page()
    reg = ip.page_region(a)
    assert not reg[:, :15].any() and not reg[:10].any()
    assert reg[H := a.shape[0] // 2, a.shape[1] // 2]


def test_binarize_finds_text_not_background():
    a = synthetic_page()
    reg = ip.page_region(a)
    ink = ip.binarize_ink(a, None, reg)
    assert 0.005 < ink.mean() < 0.15
    assert not ink[:, :20].any()                       # border is never ink
    assert ink[60:110, 80:400].any()


def test_deskew_and_line_detection():
    a = synthetic_page(skew=1.5)
    reg = ip.page_region(a)
    ink = ip.clean_components(ip.binarize_ink(a, None, reg))
    ang = ip.estimate_skew(ink)
    assert abs(abs(ang) - 1.5) <= 0.75                 # sign convention aside, close to the applied skew
    ink_r = ip.rotate(ink, ang)
    lines, diag = ip.detect_lines(ink_r)
    assert len(lines) == len(WORDS)
    assert 25 <= diag["pitch"] <= 70
    assert all(l.x1 > l.x0 and l.y1 > l.y0 for l in lines)


def test_word_segmentation_counts_on_wide_gaps():
    a = synthetic_page()
    ink = ip.clean_components(ip.binarize_ink(a, None, ip.page_region(a)))
    lines, diag = ip.detect_lines(ink)
    xh = ip.estimate_xheight(diag["pitch"])
    words, thr = ip.segment_words(ink, lines, xh, threshold=12)
    assert [len(w) for w in words] == [len(l) for l in WORDS]
    # glyph candidates exist and lie inside their word
    w = words[0][1]
    gl = ip.segment_glyph_candidates(ink, w, xh)
    assert len(gl) >= 2
    assert all(w.x0 <= g.x0 < g.x1 <= w.x1 for g in gl)


def test_estimate_xheight_and_gap_threshold_bounds():
    assert ip.estimate_xheight(40) == pytest.approx(14.0)
    t = ip.word_gap_threshold([1, 2, 1, 2, 12, 14, 13, 2, 1, 15, 12, 2, 1, 14], 10.0)
    assert 3.5 <= t <= 11.0


def test_align_lines_skips_spurious_line():
    chars = [30, 28, 31, 12, 29]
    widths = [a * 15 for a in chars]
    widths.insert(2, 40.0)                              # spurious detected line
    pairs, a = gs.align_lines(widths, chars)
    assert (3, 2) in pairs and (0, 0) in pairs and (5, 4) in pairs
    assert 2 not in [i for i, _ in pairs]
    assert a == pytest.approx(15, rel=0.1)


def test_guided_word_split_and_margin():
    has = np.array([1] * 10 + [0] * 8 + [1] * 12 + [0] * 3 + [1] * 8 + [0] * 9 + [1] * 10, bool)
    ext, margin = gs.guided_word_split(has, 3)
    assert ext == [(0, 10), (18, 41), (50, 60)]
    assert margin == pytest.approx(8 / 3)                # gaps 9 and 8 chosen over the rejected 3
    ext2, margin2 = gs.guided_word_split(has, 4)
    assert len(ext2) == 4 and margin2 == pytest.approx(3.0)   # nothing rejected: margin vs a 1 px gap
    assert gs.guided_word_split(has, 5)[0] == []             # not enough gaps


def test_forced_cuts_follow_valleys():
    prof = np.array([9, 9, 9, 8, 0, 8, 9, 9, 9, 9, 8, 0, 7, 9, 9, 9], float)
    cuts = gs.forced_cuts(prof, 3)
    assert cuts == [4, 11]
    assert gs.forced_cuts(prof, 1) == []


def test_normalise_crop_shape_and_range():
    bh = np.zeros((60, 80), np.uint8)
    bh[20:40, 30:45] = 120
    c = gs.normalise_crop(bh, (28, 18, 47, 42))
    assert c.shape == (gs.CROP, gs.CROP) and c.dtype == np.uint8
    assert c.max() == 255 and c[0, 0] == 0


def test_process_page_end_to_end_labels_are_aligned():
    a = synthetic_page()
    path = None
    import tempfile, os
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "p.png")
        Image.fromarray(a).save(path)
        seg = gs.segment_page(path, 1, "fX")
    crops = []
    page, wrows, grows = gs.process_page(seg, [list(l) for l in WORDS], Segmenter.preset("collapsed"), crops=crops)
    assert page["lines_detected"] == len(WORDS) == page["lines_transcribed"]
    assert page["lines_aligned"] >= len(WORDS) - 1
    assert wrows and grows
    assert len(crops) == len(grows)                     # one crop per glyph row
    assert {g.source for g in grows} <= {"cand", "forced", "randcut"}
    # labels, where present, are real EVA units of the aligned word
    for g in grows:
        lab = g.unit_strict or g.unit_forced
        if lab:
            assert lab in Segmenter.preset("collapsed")(g.aligned_word)
    for g in grows:
        if g.source == "cand":
            assert g.unit_forced == ""


def test_agreement_metrics_perfect_and_shuffled():
    from msdecipher.image_report import agreement
    lab = np.array(list("aaaabbbbccccdddd") * 4)
    perfect = agreement(lab, lab.copy())
    assert perfect["nmi"] == pytest.approx(1.0) and perfect["purity"] == 1.0
    rng = np.random.RandomState(0)
    bad = agreement(lab, rng.randint(0, 4, len(lab)))
    assert bad["nmi"] < 0.3


def test_confusable_pairs_ranks_confused_first():
    from msdecipher.image_report import confusable_pairs
    y = np.array(["a"] * 20 + ["e"] * 20 + ["o"] * 20)
    pred = y.copy()
    pred[:8] = "e"                                      # a read as e
    pred[20:24] = "a"                                   # e read as a
    df, C, classes = confusable_pairs(y, pred)
    assert (df.iloc[0].unit_a, df.iloc[0].unit_b) == ("a", "e")
    assert classes == ["a", "e", "o"] and C.sum() == 60
