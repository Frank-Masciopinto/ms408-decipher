# Image stage status (WORKFLOW.md stages 1 and 3b)

> MS 408 is undeciphered. This stage finds lines, words and *glyph candidates* in the page scans and compares
> visual clusters with the transcriber's EVA alphabet. It does not decode, translate or label anything.

Full numbers, figures and limitations: [`reports/image_stage/REPORT.md`](../reports/image_stage/REPORT.md).

| Piece | Status |
|---|---|
| Render PDF pages to PNG (`python -m msdecipher images`) | **Done.** 100 dpi renders into `data/images/page_NNN.png` (git-ignored). Too small for glyph work (x-height ~5 px). |
| Native scans (`python -m msdecipher images --native`) | **Done.** `pdfimages -j` extracts the embedded JPEG of each page unchanged into `data/images/native/` (git-ignored); about 1500x2000 px, 220 ppi, x-height ~11 px. This is the best resolution the PDF holds. |
| PDF page → folio index (`python -m msdecipher page-index`) | **Done**, [`data/page_index.csv`](../data/page_index.csv). Captions read with `pdftotext`; matched to the transcription's folio list. 177 pages map 1:1 (`exact`), 6 map to several sub-folios of one scan, 20 are multi-folio/part/fold-out scans whose sub-folio assignment is **not resolved**, 1 has no transcription, 10 are covers/edges/flyleaves. `text_page_candidate` marks 28 text-dominant 1:1 pages (text-only and "stars" pages) used by the next stages. |
| Ink/parchment separation, deskew, margin handling | **Done (best effort)**, `imgproc.py`: black-hat transform + Otsu-scaled threshold, largest bright component as the leaf, projection-profile deskew (±4°). Bleed-through, pigment and stains are not modelled; red star marks are not removed. |
| Text line detection | **Done (best effort).** Smoothed row-profile peaks. On the 28 pages: 1268 lines found vs 1271 transcribed; exact line count on 25% of pages, ±1 on 57%. |
| Word segmentation | **Weak.** Column gaps in the core band of each line with a page-wide threshold (0.8 x-height). Reproduces the transcribed word count of a line in only ~18% of aligned lines. A *guided* split (use the transcribed word count, cut at the widest gaps, keep only unambiguous lines) is used to get labelled words; independent check: image word width vs transcribed length r = 0.45 (shuffled: 0.00). |
| Glyph segmentation (`python -m msdecipher segment-glyphs`) | **Done (best effort).** Connected components in a word, overlapping/tiny fragments merged, wide blobs split at projection valleys. Number of candidates equals the transcribed unit count for ~25% of words (±1: 59%). Cursive, touching strokes limit this. |
| Glyph clustering and comparison with EVA | **Done (descriptive).** HOG + geometry → PCA → k-means (k = 8…40) and HDBSCAN; agreement (NMI/ARI/purity), kNN separability, confusable pairs, with a random-cut control. |
| QA report | **Done**, `reports/image_stage/` (metrics, per-page table, sheets, three annotated page excerpts). |

## Method in one paragraph
Page → ink mask → deskew → text block → lines → words → candidates. The transcription is used only for
*counts and widths*: DP alignment of detected lines to transcribed P-lines (width and word-count cost), the number of words
in a line, and the number of units in a word. EVA letter identity never influences where a crop is cut, so comparing
clusters with EVA letters is not circular. Three labelled crop sets result: **strict** (candidate count = unit count),
**forced** (cut at ink valleys into the transcribed number of pieces) and a **random-cut control** (same counts, random cut
positions).

## Findings (28 text-dominant pages; proxies only)
- The crops are visually informative: on the strict set a kNN recovers the EVA unit 36% of the time (chance 6%, 17 units,
  grouped by page), but k-means clusters agree only weakly with EVA units (NMI ≈ 0.16 at k = 24, shuffled labels ≈ 0.01).
- On the forced set the gain over the random-cut control is small (kNN 0.17 vs 0.14), so forced labels are mostly noise.
- The shapes form a continuum: k-means silhouette is flat (~0.09) and HDBSCAN finds only 2 dense clusters (54% noise). The image
  data therefore does not pin down an inventory size and neither confirms nor refutes the ~15-20 frequent EVA symbols.
- Pairs that remain confusable even in the strict set include a/e, n/y, e/k, a/d, a/i, k/t. This reflects resolution, the
  segmentation method and the EVA convention (EVA splits many strokes, e.g. `ch`, `iin`), not a claim that the script has or lacks these letters.

## Limits (read before reusing the numbers)
- No ground-truth boxes. "Accuracy" = agreement with a transcription that has its own errors and uncertain spaces.
- Parameters were tuned for count agreement on the same 28 pages (no held-out set), so the numbers are optimistic.
- Only text-dominant pages; herbal/zodiac/biological pages (drawings, paint) and multi-folio fold-outs are not handled.
- No per-hand or per-quire analysis yet; the crop table carries `hand` and `folio` so this can be added.
- The strict set is selected by count agreement, so it over-represents easily segmented words.
- Rights: check Yale's *Access and Usage Rights* statement before redistributing images. Committed: 24x24 crops
  (`glyphs/image/sample/`, 196 files), three annotated page excerpts, tables. The scans, the full crop array and metadata
  (`data/processed/glyph_stage/`, ~77,000 crops) are git-ignored and regenerated by the CLI.

## Reproduce
```bash
pip install -e ".[images]"                 # opencv-python-headless, scipy, scikit-image, scikit-learn
python -m msdecipher page-index            # data/page_index.csv
python -m msdecipher images --native       # data/images/native/*.jpg
python -m msdecipher segment-glyphs        # ~1 min: segmentation + clustering + reports/image_stage/
python -m msdecipher segment-glyphs --pages 190,192 --no-report   # subset, segmentation only
```
Modules: `pageindex.py` (index), `imgproc.py` (CV primitives), `glyph_stage.py` (alignment, crops, tables),
`image_report.py` (features, clustering, metrics, figures, report).

## Not done
Held-out evaluation; hand-annotated ground-truth boxes for a few pages; stroke-level (skeleton) segmentation; learned embeddings
(autoencoder/CNN); herbal/zodiac pages with drawing removal; per-hand/per-quire comparison; multi-folio fold-out sub-folio assignment;
higher-resolution scans from Yale's IIIF service (the PDF only holds the ~220 ppi images).
