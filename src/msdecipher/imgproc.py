"""Page preprocessing and line / word / glyph-candidate segmentation (best effort, classical CV).

All functions work on numpy arrays so they can be tested on synthetic images. Requires
``opencv-python-headless``, ``scipy`` and ``scikit-image`` (``pip install -e ".[images]"``).

Pipeline for one page scan (the PDF holds ~1500x2000 px scans, x-height of a letter is only about
10-14 px):

1. ``load_page``           colour JPEG -> gray + HSV
2. ``page_region``         bright parchment region (dark scanner background and book edge removed)
3. ``binarize_ink``        background-normalised adaptive threshold; red/green/blue paint removed with a
                           saturation mask; large blobs (drawings, stains, margin stars) removed
4. ``estimate_skew``/``rotate``  projection-profile deskew (+-4 deg)
5. ``detect_lines``        smoothed row projection profile + valley splitting
6. ``segment_words``       column gaps inside a line, threshold from the gap distribution
7. ``segment_glyph_candidates``  connected components (+ merging of overlapping fragments) and
                           projection-valley splitting of wide blobs

Nothing here knows the transcription; alignment with EVA is done in ``glyph_stage``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

try:  # optional heavy deps are imported lazily so the rest of the package works without them
    import cv2
    from scipy import ndimage as ndi
    from scipy.signal import find_peaks
except ImportError as e:  # pragma: no cover
    cv2 = None
    _IMPORT_ERROR = e


def require_cv() -> None:
    if cv2 is None:  # pragma: no cover
        raise RuntimeError("image stage needs opencv-python-headless, scipy, scikit-image, scikit-learn: "
                           'pip install -e ".[images]"')


# ----------------------------------------------------------------------------- loading / region

def load_page(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """-> (gray uint8, hsv uint8)."""
    require_cv()
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)


def page_region(gray: np.ndarray, dark: int = 70, inset_frac: float = 0.012) -> np.ndarray:
    """Boolean mask of the parchment leaf (largest bright component, holes filled, eroded a bit)."""
    require_cv()
    small = cv2.resize(gray, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    m = cv2.GaussianBlur(small, (0, 0), 3) > dark
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=4)
    if n <= 1:
        return np.ones(gray.shape, bool)
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    m = ndi.binary_fill_holes(lab == k)
    inset = max(2, int(inset_frac * max(small.shape)))
    m = cv2.erode(m.astype(np.uint8), np.ones((2 * inset + 1, 2 * inset + 1), np.uint8)).astype(bool)
    return cv2.resize(m.astype(np.uint8), (gray.shape[1], gray.shape[0]), interpolation=cv2.INTER_NEAREST).astype(bool)


# ----------------------------------------------------------------------------- binarisation

def binarize_ink(gray: np.ndarray, hsv: np.ndarray | None = None, region: np.ndarray | None = None,
                 kernel: int = 11, rel_thr: float = 0.8, paint_sat: int | None = None) -> np.ndarray:
    """Boolean ink mask (True = ink).

    Black-hat (morphological closing minus image) with an ``kernel`` px ellipse highlights thin dark
    strokes on uneven parchment; the threshold is ``rel_thr`` x Otsu of the black-hat values inside
    the page region, clipped to [16, 45]. Everything outside ``region`` is background. A saturation
    paint filter (``paint_sat``) exists but is OFF by default: the brown ink itself is highly
    saturated (S about 90-110) on these scans, so it removes real strokes."""
    require_cv()
    gb = cv2.GaussianBlur(gray, (0, 0), 0.7)
    bh = cv2.morphologyEx(gb, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel, kernel)))
    vals = bh[region] if region is not None and region.any() else bh.ravel()
    t, _ = cv2.threshold(vals.reshape(-1, 1).astype(np.uint8), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thr = float(np.clip(rel_thr * t, 16, 45))
    ink = bh > thr
    if hsv is not None and paint_sat is not None:
        paint = (hsv[..., 1] > paint_sat) & (hsv[..., 2] > 90)
        paint = cv2.dilate(paint.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
        ink &= ~paint
    if region is not None:
        ink &= region
    return ink


def clean_components(ink: np.ndarray, min_area: int = 6, max_h_frac: float = 0.06,
                     max_area_frac: float = 0.002) -> np.ndarray:
    """Drop speckle and big blobs (drawings, stains, ruling) from an ink mask."""
    require_cv()
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    keep = np.zeros(n, bool)
    H, W = ink.shape
    area = st[:, cv2.CC_STAT_AREA]
    h = st[:, cv2.CC_STAT_HEIGHT]
    w = st[:, cv2.CC_STAT_WIDTH]
    keep = (area >= min_area) & (h <= max_h_frac * H) & (area <= max_area_frac * H * W) & (w <= 0.2 * W)
    keep[0] = False
    return keep[lab]


# ----------------------------------------------------------------------------- deskew

def estimate_skew(ink: np.ndarray, max_deg: float = 4.0, step: float = 0.25, scale: int = 4) -> float:
    """Skew angle in degrees (positive = text rotated counter-clockwise) maximising row-profile variance."""
    require_cv()
    small = cv2.resize(ink.astype(np.uint8) * 255, None, fx=1 / scale, fy=1 / scale, interpolation=cv2.INTER_AREA)
    h, w = small.shape
    best, best_a = -1.0, 0.0
    for a in np.arange(-max_deg, max_deg + 1e-9, step):
        M = cv2.getRotationMatrix2D((w / 2, h / 2), a, 1.0)
        r = cv2.warpAffine(small, M, (w, h), flags=cv2.INTER_LINEAR)
        prof = r.sum(axis=1).astype(np.float64)
        v = float(np.var(prof))
        if v > best:
            best, best_a = v, float(a)
    return best_a


def rotate(img: np.ndarray, angle: float, border: int = 0) -> np.ndarray:
    """Rotate about the centre (bool masks stay bool and use nearest-neighbour)."""
    require_cv()
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    if img.dtype == bool:
        return cv2.warpAffine(img.astype(np.uint8), M, (w, h), flags=cv2.INTER_NEAREST, borderValue=0).astype(bool)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=border)


# ----------------------------------------------------------------------------- text block / lines

def text_columns(ink: np.ndarray, frac: float = 0.15) -> tuple[int, int]:
    """Left/right x range of the text block: columns whose ink count exceeds ``frac`` of the
    90th percentile column count (so isolated margin marks do not stretch the block)."""
    col = ink.sum(axis=0).astype(float)
    ref = np.percentile(col[col > 0], 90) if (col > 0).any() else 0
    idx = np.where(col > frac * ref)[0]
    if len(idx) == 0:
        return 0, ink.shape[1]
    # take the largest run allowing gaps of up to 40 px
    runs, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev > 40:
            runs.append((start, prev))
            start = i
        prev = i
    runs.append((start, prev))
    a, b = max(runs, key=lambda r: col[r[0]:r[1] + 1].sum())
    return int(a), int(b) + 1


@dataclass
class Line:
    y0: int
    y1: int           # exclusive
    x0: int
    x1: int
    ink_px: int = 0

    @property
    def height(self) -> int:
        return self.y1 - self.y0


def estimate_pitch(profile: np.ndarray, lo: int = 18, hi: int = 90) -> int:
    p = profile - profile.mean()
    ac = np.correlate(p, p, mode="full")[len(p) - 1:]
    if len(ac) <= lo + 2:
        return lo
    hi = min(hi, len(ac) - 1)
    seg = ac[lo:hi]
    pk, _ = find_peaks(seg)
    if len(pk) == 0:
        return int(lo + np.argmax(seg))
    return int(lo + pk[np.argmax(seg[pk])])


def detect_lines(ink: np.ndarray, pitch: int | None = None, min_rel_ink: float = 0.18) -> tuple[list[Line], dict]:
    """Detect text lines in a (deskewed) ink mask. Returns lines and diagnostics (pitch, columns)."""
    require_cv()
    x0, x1 = text_columns(ink)
    block = ink[:, x0:x1]
    prof = block.sum(axis=1).astype(float)
    pitch = pitch or estimate_pitch(ndi.gaussian_filter1d(prof, 2))
    sm = ndi.gaussian_filter1d(prof, max(2.0, pitch / 12.0))
    # line centres = peaks of the smoothed profile; boundaries = deepest valley between neighbours
    thr = min_rel_ink * np.percentile(sm[sm > 0], 90) if (sm > 0).any() else 0
    peaks, _ = find_peaks(sm, height=thr, distance=max(5, int(0.7 * pitch)), prominence=thr * 0.3)
    lines: list[Line] = []
    if len(peaks) == 0:
        return lines, {"pitch": pitch, "x0": x0, "x1": x1, "profile": sm}
    bounds = [0]
    for a, b in zip(peaks[:-1], peaks[1:]):
        bounds.append(int(a + np.argmin(sm[a:b + 1])))
    bounds.append(len(sm))
    for k, pk in enumerate(peaks):
        y0, y1 = bounds[k], bounds[k + 1]
        # trim empty rows on both ends and limit extent to ~1.2 pitch around the centre
        y0 = max(y0, int(pk - 0.75 * pitch))
        y1 = min(y1, int(pk + 0.75 * pitch))
        seg = prof[y0:y1]
        nz = np.where(seg > 0.04 * seg.max())[0] if seg.max() > 0 else []
        if len(nz) == 0:
            continue
        y0, y1 = y0 + int(nz[0]), y0 + int(nz[-1]) + 1
        sub = ink[y0:y1, x0:x1]
        cols = np.where(sub.any(axis=0))[0]
        if len(cols) == 0:
            continue
        lines.append(Line(y0, y1, x0 + int(cols[0]), x0 + int(cols[-1]) + 1, int(sub.sum())))
    return lines, {"pitch": pitch, "x0": x0, "x1": x1, "profile": sm}


# ----------------------------------------------------------------------------- words

@dataclass
class Word:
    x0: int
    x1: int
    y0: int
    y1: int


def gap_runs(col_has_ink: np.ndarray) -> list[tuple[int, int]]:
    """(start, length) of runs of empty columns strictly between inked columns."""
    idx = np.where(col_has_ink)[0]
    if len(idx) < 2:
        return []
    d = np.diff(idx)
    return [(int(idx[i]) + 1, int(d[i]) - 1) for i in np.where(d > 1)[0]]


WORD_GAP_XH = 0.8   # word-space threshold in x-heights (tuned on a few pages, see docs/IMAGE_STAGE.md)


def word_gap_threshold(gaps: list[int], xh: float) -> float:
    """Gap width (px) separating word spaces from intra-word gaps.

    A two-class split (Otsu on the gap widths) is used when the distribution is clearly bimodal;
    otherwise a fraction of the x-height. Always bounded to [0.35, 1.1] x-height."""
    lo, hi = 0.35 * xh, 1.1 * xh
    g = np.array([x for x in gaps if x >= 1], float)
    if len(g) < 12:
        return float(np.clip(0.6 * xh, lo, hi))
    srt = np.sort(g)
    best_t, best_v = None, -1.0
    for t in np.unique(srt)[:-1]:
        a, b = g[g <= t], g[g > t]
        if len(a) < 3 or len(b) < 3:
            continue
        v = len(a) * len(b) * (a.mean() - b.mean()) ** 2
        if v > best_v:
            best_t, best_v = float(t) + 0.5, v
    if best_t is None:
        return float(np.clip(0.6 * xh, lo, hi))
    return float(np.clip(best_t, lo, hi))


def estimate_xheight(pitch: float) -> float:
    """x-height from the line pitch (about 0.35 x pitch on these scans; component heights are biased
    upwards by ascenders and touching strokes, so they are not used)."""
    return 0.35 * float(pitch)


def segment_words(ink: np.ndarray, lines: list[Line], xh: float,
                  threshold: float | None = None, core_frac: float = 0.45) -> tuple[list[list[Word]], float]:
    """Split each line at column gaps wider than a page-wide threshold. Returns (words per line, threshold)."""
    all_gaps: list[int] = []
    per_line = []
    for ln in lines:
        sub = ink[ln.y0:ln.y1, ln.x0:ln.x1]
        # gaps are measured on the core band only: ascenders/descenders of neighbouring lines
        # intrude into the band and would bridge real word spaces
        rp = sub.sum(axis=1)
        core = rp >= core_frac * rp.max() if rp.max() > 0 else np.ones(len(rp), bool)
        has = sub[core].any(axis=0)
        runs = gap_runs(has)
        all_gaps += [r[1] for r in runs]
        per_line.append((ln, has, runs))
    thr = threshold if threshold is not None else WORD_GAP_XH * xh
    out: list[list[Word]] = []
    for ln, has, runs in per_line:
        cuts = [(s, n) for s, n in runs if n >= thr]
        edges = [0]
        for s, n in cuts:
            edges += [s, s + n]
        edges.append(has.shape[0])
        words = []
        for a, b in zip(edges[0::2], edges[1::2]):
            if b - a < 2 or not has[a:b].any():
                continue
            sub = ink[ln.y0:ln.y1, ln.x0 + a:ln.x0 + b]
            rows = np.where(sub.any(axis=1))[0]
            if len(rows) == 0:
                continue
            words.append(Word(ln.x0 + a, ln.x0 + b, ln.y0 + int(rows[0]), ln.y0 + int(rows[-1]) + 1))
        out.append(words)
    return out, float(thr)


# ----------------------------------------------------------------------------- glyph candidates

@dataclass
class Glyph:
    x0: int
    x1: int
    y0: int
    y1: int
    n_cc: int = 1          # connected components merged into this candidate
    split: bool = False    # produced by projection-valley splitting of a wide blob


def _merge_overlapping(boxes: list[list[int]], min_overlap: float = 0.5) -> list[list[int]]:
    """Merge component boxes (x0,x1,y0,y1,n) that overlap horizontally by >= min_overlap of the narrower."""
    boxes = sorted(boxes, key=lambda b: b[0])
    changed = True
    while changed:
        changed = False
        out: list[list[int]] = []
        for b in boxes:
            for o in out:
                ov = min(o[1], b[1]) - max(o[0], b[0])
                if ov > 0 and ov >= min_overlap * min(o[1] - o[0], b[1] - b[0]):
                    o[0], o[1] = min(o[0], b[0]), max(o[1], b[1])
                    o[2], o[3] = min(o[2], b[2]), max(o[3], b[3])
                    o[4] += b[4]
                    changed = True
                    break
            else:
                out.append(list(b))
        boxes = sorted(out, key=lambda b: b[0])
    return boxes


def _split_wide(sub: np.ndarray, x_off: int, y_off: int, glyph_w: float, max_parts: int = 6) -> list[Glyph]:
    """Split one wide blob at deep valleys of its column profile into ~round(w/glyph_w) parts."""
    h, w = sub.shape
    k = int(np.clip(round(w / glyph_w), 1, max_parts))
    if k <= 1:
        rows = np.where(sub.any(axis=1))[0]
        return [Glyph(x_off, x_off + w, y_off + int(rows[0]), y_off + int(rows[-1]) + 1)]
    prof = ndi.gaussian_filter1d(sub.sum(axis=0).astype(float), 0.8)
    cuts: list[int] = []
    for j in range(1, k):
        target = j * w / k
        lo, hi = int(max(1, target - 0.45 * glyph_w)), int(min(w - 1, target + 0.45 * glyph_w))
        if hi <= lo:
            cuts.append(int(target))
        else:
            cuts.append(lo + int(np.argmin(prof[lo:hi + 1])))
    cuts = sorted(set(cuts))
    edges = [0] + cuts + [w]
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        part = sub[:, a:b]
        rows = np.where(part.any(axis=1))[0]
        if b - a < 2 or len(rows) == 0:
            continue
        out.append(Glyph(x_off + a, x_off + b, y_off + int(rows[0]), y_off + int(rows[-1]) + 1, 1, True))
    return out


def _merge_small_neighbours(boxes: list[list[int]], glyph_w: float, small_w: float, max_w: float) -> list[list[int]]:
    """Merge fragments narrower than ``small_w`` into the horizontally closest neighbour when the
    union stays narrower than ``max_w`` (broken pen strokes, dots, crossbars)."""
    boxes = sorted(boxes, key=lambda b: b[0])
    changed = True
    while changed and len(boxes) > 1:
        changed = False
        order = sorted(range(len(boxes)), key=lambda i: boxes[i][1] - boxes[i][0])
        for i in order:
            b = boxes[i]
            if b[1] - b[0] >= small_w:
                break
            cands = []
            for j in (i - 1, i + 1):
                if 0 <= j < len(boxes):
                    o = boxes[j]
                    gap = max(o[0], b[0]) - min(o[1], b[1])
                    union = max(o[1], b[1]) - min(o[0], b[0])
                    if union <= max_w:
                        cands.append((gap, union, j))
            if not cands:
                continue
            _, _, j = min(cands)
            o = boxes[j]
            o[0], o[1] = min(o[0], b[0]), max(o[1], b[1])
            o[2], o[3] = min(o[2], b[2]), max(o[3], b[3])
            o[4] += b[4]
            del boxes[i]
            changed = True
            break
    return boxes


GLYPH_W_XH = 1.5     # nominal glyph width in x-heights (tuned for count agreement on text pages; see docs/IMAGE_STAGE.md)
SMALL_W_XH = 0.6     # fragments narrower than this (x-heights) are merged into a neighbour


def segment_glyph_candidates(ink: np.ndarray, word: Word, xh: float, glyph_w: float | None = None,
                             split_wide: bool = True, merge_small: bool = True, min_area: int = 5) -> list[Glyph]:
    """Connected components of the word, overlapping/tiny fragments merged, wide blobs split at valleys."""
    require_cv()
    glyph_w = glyph_w or GLYPH_W_XH * xh
    sub = ink[word.y0:word.y1, word.x0:word.x1]
    n, lab, st, _ = cv2.connectedComponentsWithStats(sub.astype(np.uint8), connectivity=8)
    boxes = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < min_area:
            continue
        x, y, w, h = (st[i, cv2.CC_STAT_LEFT], st[i, cv2.CC_STAT_TOP], st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_HEIGHT])
        boxes.append([int(x), int(x + w), int(y), int(y + h), 1])
    boxes = _merge_overlapping(boxes)
    if merge_small:
        boxes = _merge_small_neighbours(boxes, glyph_w, SMALL_W_XH * xh, 1.25 * glyph_w)
    glyphs: list[Glyph] = []
    for x0, x1, y0, y1, k in boxes:
        w = x1 - x0
        if split_wide and w > 1.55 * glyph_w:
            glyphs += _split_wide(sub[:, x0:x1], word.x0 + x0, word.y0, glyph_w)
        else:
            glyphs.append(Glyph(word.x0 + x0, word.x0 + x1, word.y0 + y0, word.y0 + y1, k))
    return sorted(glyphs, key=lambda g: g.x0)
