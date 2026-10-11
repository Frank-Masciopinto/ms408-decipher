"""Image glyph stage driver: page -> lines -> words -> glyph candidates, aligned to the transcription.

Honest scope (docs/IMAGE_STAGE.md): classical CV on ~1500x2000 px scans (x-height ~12 px) with
cursive, touching strokes. There is no ground-truth box annotation, so accuracy is measured by
*proxies* against the transcription: number of text lines per page, words per line, and glyph
candidates per word versus transcribed units. Alignment uses only counts and widths, never the
identity of the EVA letters, so that comparing image clusters with EVA letters later is not circular.
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path

import numpy as np

from . import imgproc as ip
from .ivtff import readable
from .paths import repo_root, images_dir

CROP = 24                                    # normalised crop edge (px)


def native_dir() -> Path:
    return images_dir() / "native"


def processed_dir() -> Path:
    return repo_root() / "data" / "processed" / "glyph_stage"


def page_image_path(pdf_page: int) -> Path:
    p = native_dir() / f"page_{pdf_page:03d}.jpg"
    if p.exists():
        return p
    alt = images_dir() / f"page_{pdf_page:03d}.png"
    if alt.exists():
        return alt
    raise FileNotFoundError(f"no page image for PDF page {pdf_page}: run `python -m msdecipher images --native`")


# ----------------------------------------------------------------------------- page segmentation

@dataclass
class PageSeg:
    pdf_page: int
    folio: str | None
    skew: float
    pitch: int
    xh: float
    gap_thr: float
    text_x: tuple[int, int]
    lines: list[ip.Line]
    words: list[list[ip.Word]]
    glyphs: list[list[list[ip.Glyph]]]       # [line][word] -> glyph candidates
    ink: np.ndarray = field(repr=False, default=None)    # deskewed ink mask
    gray: np.ndarray = field(repr=False, default=None)   # deskewed gray
    bh: np.ndarray = field(repr=False, default=None)     # deskewed black-hat response (stroke strength)


def segment_page(path: str | Path, pdf_page: int = 0, folio: str | None = None,
                 keep_images: bool = True) -> PageSeg:
    import cv2
    gray, hsv = ip.load_page(path)
    region = ip.page_region(gray)
    ink = ip.binarize_ink(gray, hsv, region)
    ink = ip.clean_components(ink)
    skew = ip.estimate_skew(ink)
    ink_r = ip.rotate(ink, skew)
    gray_r = ip.rotate(gray, skew, 255)
    lines, diag = ip.detect_lines(ink_r)
    xh = ip.estimate_xheight(diag["pitch"])
    words, thr = ip.segment_words(ink_r, lines, xh)
    glyphs = [[ip.segment_glyph_candidates(ink_r, w, xh) for w in ws] for ws in words]
    bh = cv2.morphologyEx(cv2.GaussianBlur(gray_r, (0, 0), 0.7), cv2.MORPH_BLACKHAT,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    return PageSeg(pdf_page, folio, skew, diag["pitch"], xh, thr, (diag["x0"], diag["x1"]), lines, words, glyphs,
                   ink_r if keep_images else None, gray_r if keep_images else None, bh if keep_images else None)


# ----------------------------------------------------------------------------- transcription alignment

def tr_unit_count(word: str, segmenter) -> int:
    return len(segmenter(word))


def align_lines(img_widths: list[float], tr_chars: list[int], img_words: list[int] | None = None,
                tr_words: list[int] | None = None, skip_cost: float = 1.0,
                max_cost: float = 0.6) -> tuple[list[tuple[int, int]], float]:
    """Monotone alignment of detected lines to transcribed P-lines (dynamic programming).

    Only counts and widths are used, never the identity of letters. Cost of pairing line i with
    line j = 0.5 |log(width_i / (a * chars_j))| + |log((words_i + 1) / (words_j + 1))| (second term only
    when word counts are given); ``a`` (px per character) is re-estimated as a median of accepted
    pairs. Skipping a detected or a transcribed line costs ``skip_cost``. Pairs costing more than
    ``max_cost`` are dropped. Returns ([(img_idx, tr_idx)], px_per_char)."""
    m, n = len(img_widths), len(tr_chars)
    if m == 0 or n == 0:
        return [], 0.0
    use_w = img_words is not None and tr_words is not None

    def pair_cost(i: int, j: int, a: float) -> float:
        c = 0.5 * abs(math.log(max(img_widths[i], 1.0) / max(a * tr_chars[j], 1.0)))
        if use_w:
            c += abs(math.log((img_words[i] + 1) / (tr_words[j] + 1)))
        return c

    a = float(np.median(img_widths) / max(np.median(tr_chars), 1))
    pairs: list[tuple[int, int]] = []
    for _ in range(3):
        D = np.full((m + 1, n + 1), np.inf)
        B = np.zeros((m + 1, n + 1), np.int8)
        D[0, 0] = 0
        for i in range(m + 1):
            for j in range(n + 1):
                if i == 0 and j == 0:
                    continue
                best, bk = np.inf, 0
                if i > 0 and j > 0:
                    best, bk = D[i - 1, j - 1] + min(pair_cost(i - 1, j - 1, a), 2 * skip_cost), 1
                if i > 0 and D[i - 1, j] + skip_cost < best:
                    best, bk = D[i - 1, j] + skip_cost, 2
                if j > 0 and D[i, j - 1] + skip_cost < best:
                    best, bk = D[i, j - 1] + skip_cost, 3
                D[i, j], B[i, j] = best, bk
        i, j, out = m, n, []
        while i > 0 or j > 0:
            k = B[i, j]
            if k == 1:
                out.append((i - 1, j - 1)); i -= 1; j -= 1
            elif k == 2:
                i -= 1
            else:
                j -= 1
        out.reverse()
        pairs = [(i, j) for i, j in out if pair_cost(i, j, a) <= max_cost]
        if pairs:
            a = float(np.median([img_widths[i] / max(tr_chars[j], 1) for i, j in pairs]))
    return pairs, a


def guided_word_split(has: np.ndarray, n_words: int) -> tuple[list[tuple[int, int]], float]:
    """Cut a line into exactly ``n_words`` words at its ``n_words - 1`` widest column gaps.

    ``has`` = boolean per-column ink presence (core band). Returns ([(x0, x1)], margin) where margin is
    the width of the narrowest chosen gap divided by the widest rejected gap (>1: the choice is
    unambiguous; <=1: ties). Only the number of transcribed words is used."""
    runs = gap_runs_local(has)
    if n_words <= 1:
        idx = np.where(has)[0]
        return ([(int(idx[0]), int(idx[-1]) + 1)] if len(idx) else []), float("inf")
    runs_sorted = sorted(runs, key=lambda r: (-r[1], r[0]))
    if len(runs_sorted) < n_words - 1:
        return [], 0.0
    chosen = sorted(runs_sorted[:n_words - 1])
    rejected = runs_sorted[n_words - 1][1] if len(runs_sorted) >= n_words else 0
    margin = chosen and min(r[1] for r in chosen) / max(rejected, 1)
    idx = np.where(has)[0]
    edges = [int(idx[0])] + [x for s, n in chosen for x in (s, s + n)] + [int(idx[-1]) + 1]
    return list(zip(edges[0::2], edges[1::2])), float(margin)


def gap_runs_local(has: np.ndarray) -> list[tuple[int, int]]:
    return ip.gap_runs(has)


def forced_cuts(prof: np.ndarray, n: int, mu: float = 1.0) -> list[int]:
    """Choose n-1 cut columns in a word's column-ink profile: low ink at the cut, roughly even widths.

    Only the *number* of transcribed units is used, never their identity."""
    W = len(prof)
    if n <= 1 or W < n:
        return []
    p = prof.astype(float) / (prof.max() + 1e-9)
    w0 = W / n
    INF = 1e9
    # dp[k][x]: best cost with k cuts, last cut at column x (cut positions 1..W-1)
    dp = np.full((n, W + 1), INF)
    bk = np.zeros((n, W + 1), int)
    for x in range(1, W):
        dp[1, x] = p[x] + mu * ((x - w0) / w0) ** 2
    for k in range(2, n):
        for x in range(k, W):
            lo = max(k - 1, int(x - 2.2 * w0))
            hi = x - 1
            if hi < lo:
                continue
            prev = np.arange(lo, hi + 1)
            c = dp[k - 1, prev] + mu * ((x - prev - w0) / w0) ** 2
            j = int(np.argmin(c))
            dp[k, x] = c[j] + p[x]
            bk[k, x] = prev[j]
    last = np.arange(n - 1, W)
    tot = dp[n - 1, last] + mu * ((W - last - w0) / w0) ** 2
    x = int(last[int(np.argmin(tot))])
    cuts = [x]
    for k in range(n - 1, 1, -1):
        x = int(bk[k, x])
        cuts.append(x)
    return sorted(cuts)


# ----------------------------------------------------------------------------- crops / features

def normalise_crop(bh: np.ndarray, box: tuple[int, int, int, int], pad: int = 2, size: int = CROP) -> np.ndarray:
    """Black-hat response in the box, scaled (aspect preserved) into a size x size uint8 canvas."""
    import cv2
    x0, y0, x1, y1 = box
    H, W = bh.shape
    c = bh[max(0, y0 - pad):min(H, y1 + pad), max(0, x0 - pad):min(W, x1 + pad)]
    if c.size == 0:
        return np.zeros((size, size), np.uint8)
    h, w = c.shape
    s = (size - 2) / max(h, w)
    nh, nw = max(1, int(round(h * s))), max(1, int(round(w * s)))
    r = cv2.resize(c, (nw, nh), interpolation=cv2.INTER_AREA)
    out = np.zeros((size, size), np.uint8)
    oy, ox = (size - nh) // 2, (size - nw) // 2
    out[oy:oy + nh, ox:ox + nw] = r
    m = out.max()
    if m > 0:
        out = (out.astype(np.float32) * (255.0 / m)).astype(np.uint8)
    return out


@dataclass
class GlyphRow:
    pdf_page: int
    folio: str
    hand: str
    lang: str
    line: int
    word: int
    idx: int                 # index inside the word
    n_in_word: int
    x0: int
    y0: int
    x1: int
    y1: int
    w_xh: float              # width / x-height
    h_xh: float
    yc_xh: float             # box centre relative to the line's core centre, in x-heights
    n_cc: int
    split: int
    source: str              # 'cand' (CC/valley candidates) | 'forced' (valley cuts, n = transcribed units) | 'randcut' (control)
    aligned_word: str        # transcribed word aligned to this word ('' if none)
    unit_strict: str         # EVA unit when candidate count == transcribed unit count
    unit_forced: str         # EVA unit from forced alignment (source == 'forced')
    crop: int                # row in the crop array


@dataclass
class WordRow:
    pdf_page: int
    folio: str
    line: int
    word: int
    x0: int
    y0: int
    x1: int
    y1: int
    n_cand: int
    tr_word: str
    tr_units: int
    tr_chars: int
    word_source: str      # 'unsup' (gap threshold gave the transcribed count) | 'guided' (n-1 widest gaps) | ''
    margin: float         # guided only: narrowest chosen gap / widest rejected gap


def _core_centre(ink, ln: ip.Line) -> float:
    sub = ink[ln.y0:ln.y1, ln.x0:ln.x1]
    rp = sub.sum(axis=1).astype(float)
    if rp.sum() == 0:
        return (ln.y0 + ln.y1) / 2
    return ln.y0 + float((rp * np.arange(len(rp))).sum() / rp.sum())


def _words_from_extents(ink, ln: ip.Line, extents: list[tuple[int, int]]) -> list[ip.Word]:
    out = []
    for a, b in extents:
        sub = ink[ln.y0:ln.y1, ln.x0 + a:ln.x0 + b]
        rows = np.where(sub.any(axis=1))[0]
        if len(rows) and b - a >= 2:
            out.append(ip.Word(ln.x0 + a, ln.x0 + b, ln.y0 + int(rows[0]), ln.y0 + int(rows[-1]) + 1))
    return out


def process_page(seg: PageSeg, tr_lines: list[list[str]] | None, segmenter, hand: str = "", lang: str = "",
                 crops: list[np.ndarray] | None = None, min_margin: float = 1.0, random_control: bool = True):
    """Align one segmented page with its transcribed P-lines and emit rows.

    tr_lines: list (reading order) of word lists (tokens as in the transcription, '?' allowed).
    Returns (page_metrics dict, word rows, glyph rows). Label provenance:

    * lines    : DP alignment on widths + word counts (``align_lines``)
    * words    : the unsupervised gap threshold if it reproduces the transcribed word count of the
                 line, else a *guided* split at the n-1 widest gaps, accepted only if unambiguous
                 (``margin`` > ``min_margin``)
    * glyphs   : 'cand' crops (CC + valley candidates) get an EVA unit only if their number equals the
                 number of transcribed units ('strict'); otherwise 'forced' crops are cut at ink valleys
                 into exactly that number of pieces. Letter identity is never used for cutting."""
    crops = crops if crops is not None else []
    folio = seg.folio or ""
    n_img = len(seg.lines)
    n_tr = len(tr_lines) if tr_lines else 0
    page = {"pdf_page": seg.pdf_page, "folio": folio, "skew_deg": round(seg.skew, 2), "pitch_px": seg.pitch,
            "x_height_px": round(seg.xh, 1), "word_gap_px": round(seg.gap_thr, 1),
            "lines_detected": n_img, "lines_transcribed": n_tr,
            "words_detected": sum(len(w) for w in seg.words),
            "words_transcribed": sum(len(l) for l in tr_lines) if tr_lines else 0,
            "glyph_candidates": sum(len(g) for ws in seg.glyphs for g in ws)}
    wrows: list[WordRow] = []
    grows: list[GlyphRow] = []
    pairs: list[tuple[int, int]] = []
    a = 0.0
    if tr_lines:
        widths = [ln.x1 - ln.x0 for ln in seg.lines]
        chars = [sum(len(w) for w in l) + max(len(l) - 1, 0) for l in tr_lines]
        pairs, a = align_lines(widths, chars, [len(w) for w in seg.words], [len(l) for l in tr_lines])
    page["lines_aligned"] = len(pairs)
    n_unsup = n_guided = n_rej = 0
    for li, ti in pairs:
        tw = tr_lines[ti]
        ln = seg.lines[li]
        cy = _core_centre(seg.ink, ln)
        if len(seg.words[li]) == len(tw):
            words, src, margin = seg.words[li], "unsup", 0.0
            glyph_lists = seg.glyphs[li]
            n_unsup += 1
        else:
            sub = seg.ink[ln.y0:ln.y1, ln.x0:ln.x1]
            rp = sub.sum(axis=1)
            core = rp >= 0.45 * rp.max() if rp.max() > 0 else np.ones(len(rp), bool)
            ext, margin = guided_word_split(sub[core].any(axis=0), len(tw))
            if not ext or margin <= min_margin:
                n_rej += 1
                continue
            words, src = _words_from_extents(seg.ink, ln, ext), "guided"
            if len(words) != len(tw):
                n_rej += 1
                continue
            glyph_lists = [ip.segment_glyph_candidates(seg.ink, w, seg.xh) for w in words]
            n_guided += 1
        for wi, w in enumerate(words):
            trw = tw[wi]
            width_ok = a > 0 and 0.45 <= (w.x1 - w.x0) / max(a * len(trw), 1.0) <= 2.2
            ok = width_ok and readable(trw) and "?" not in trw
            units = segmenter(trw) if ok else ()
            cands = glyph_lists[wi]
            wrows.append(WordRow(seg.pdf_page, folio, li, wi, w.x0, w.y0, w.x1, w.y1, len(cands), trw, len(units),
                                 len(trw), src if width_ok else "", round(float(margin), 2)))
            strict = ok and len(cands) == len(units)
            for gi, g in enumerate(cands):
                crops.append(normalise_crop(seg.bh, (g.x0, g.y0, g.x1, g.y1)))
                grows.append(GlyphRow(seg.pdf_page, folio, hand, lang, li, wi, gi, len(cands), g.x0, g.y0, g.x1, g.y1,
                                      round((g.x1 - g.x0) / seg.xh, 3), round((g.y1 - g.y0) / seg.xh, 3),
                                      round(((g.y0 + g.y1) / 2 - cy) / seg.xh, 3), g.n_cc, int(g.split), "cand",
                                      trw if ok else "", units[gi] if strict else "", "", len(crops) - 1))
            if ok and len(units) >= 2 and not strict:
                sub = seg.ink[w.y0:w.y1, w.x0:w.x1]
                core = sub.sum(axis=1)
                core_rows = core >= 0.3 * core.max() if core.max() > 0 else np.ones(len(core), bool)
                Wd = sub.shape[1]
                cut_sets = [("forced", forced_cuts(sub[core_rows].sum(axis=0), len(units)))]
                if random_control and Wd > len(units) * 2:
                    # control: same number of pieces, cut positions drawn uniformly at random
                    rng = np.random.RandomState((seg.pdf_page * 7919 + li * 104729 + wi) % (2 ** 31))
                    cut_sets.append(("randcut", sorted(rng.choice(np.arange(1, Wd), len(units) - 1, replace=False))))
                for source, cuts in cut_sets:
                    edges = [0] + list(cuts) + [Wd]
                    for gi, (x0, x1) in enumerate(zip(edges[:-1], edges[1:])):
                        part = sub[:, x0:x1]
                        rr = np.where(part.any(axis=1))[0]
                        if x1 - x0 < 2 or len(rr) == 0:
                            continue
                        box = (w.x0 + x0, w.y0 + int(rr[0]), w.x0 + x1, w.y0 + int(rr[-1]) + 1)
                        crops.append(normalise_crop(seg.bh, box))
                        grows.append(GlyphRow(seg.pdf_page, folio, hand, lang, li, wi, gi, len(units), *box,
                                              round((box[2] - box[0]) / seg.xh, 3), round((box[3] - box[1]) / seg.xh, 3),
                                              round(((box[1] + box[3]) / 2 - cy) / seg.xh, 3), 1, 0, source, trw, "",
                                              units[gi], len(crops) - 1))
    page.update({"px_per_char": round(a, 2), "lines_words_unsup": n_unsup, "lines_words_guided": n_guided,
                 "lines_rejected": n_rej})
    return page, wrows, grows


# ----------------------------------------------------------------------------- driver

def _write_csv(path: Path, rows: list, fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dicts = [asdict(r) if hasattr(r, "__dataclass_fields__") else r for r in rows]
    fields = fields or (list(dicts[0]) if dicts else [])
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(dicts)


def select_pages(index_rows: list[dict], pages: list[int] | None = None, mode: str = "text") -> list[dict]:
    """Pages to process: explicit PDF page numbers, or 'text' (text_page_candidate) / 'exact' (all 1:1 pages)."""
    if pages:
        by = {int(r["pdf_page"]): r for r in index_rows}
        return [by[p] for p in pages if p in by]
    if mode == "exact":
        return [r for r in index_rows if r["match"] == "exact" and int(r["n_p_lines"]) > 0]
    return [r for r in index_rows if int(r["text_page_candidate"])]


def run_segmentation(pages: list[int] | None = None, mode: str = "text", units: str = "collapsed",
                     out: Path | None = None, corpus=None, verbose: bool = True) -> dict:
    """Segment the selected pages, align with the transcription, write tables + crops to data/processed/.

    Returns a dict of the in-memory tables. Needs the page index (built on demand) and the images."""
    from .pageindex import build_index, read_index, index_path
    from .segment import Segmenter
    from .corpus_view import lines_for
    from .analysis import load_corpus
    out = out or processed_dir()
    corpus = corpus or load_corpus()
    if not index_path().exists():
        build_index(corpus=corpus)
    idx = read_index()
    sel = select_pages(idx, pages, mode)
    seg_fn = Segmenter.from_spec(units)
    crops: list[np.ndarray] = []
    prow, wrow, grow = [], [], []
    for r in sel:
        pg = int(r["pdf_page"])
        folio = r["folios"].split(";")[0] if r["match"] == "exact" else ""
        try:
            seg = segment_page(page_image_path(pg), pg, folio)
        except FileNotFoundError as e:
            if verbose:
                print(f"skip PDF page {pg}: {e}")
            continue
        tr = None
        if folio:
            tr = [ln.words for ln in lines_for(corpus, generic="P", folios=[folio])]
        p, w, g = process_page(seg, tr, seg_fn, r.get("hand", ""), r.get("language", ""), crops)
        p["illustration"] = r.get("illustration", "")
        prow.append(p); wrow += w; grow += g
        if verbose:
            print(f"p{pg:03d} {folio:7s} lines {p['lines_detected']:3d}/{p['lines_transcribed']:3d} aligned {p['lines_aligned']:3d} "
                  f"(words: unsup {p['lines_words_unsup']}, guided {p['lines_words_guided']}, rej {p['lines_rejected']}) "
                  f"cand {p['glyph_candidates']:5d} strict {sum(1 for x in g if x.unit_strict)} forced {sum(1 for x in g if x.unit_forced)}")
    arr = np.stack(crops) if crops else np.zeros((0, CROP, CROP), np.uint8)
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "crops.npy", arr)
    _write_csv(out / "pages.csv", prow)
    _write_csv(out / "words.csv", wrow, [f for f in WordRow.__dataclass_fields__])
    _write_csv(out / "glyphs.csv", grow, [f for f in GlyphRow.__dataclass_fields__])
    (out / "run.json").write_text(json.dumps({"units": units, "mode": mode, "pages": [p["pdf_page"] for p in prow]}))
    return {"pages": prow, "words": wrow, "glyphs": grow, "crops": arr}
