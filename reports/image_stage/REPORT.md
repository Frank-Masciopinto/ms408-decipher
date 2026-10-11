# Image glyph stage: QA report (best effort)

> **MS 408 is undeciphered. This stage does not decode anything.** It tries to find lines, words and glyph candidates in the page scans and to compare visual clusters with the *transcriber's* EVA alphabet. All accuracy numbers below are **proxies** measured against that transcription (there is no hand-annotated ground truth), on the same 28 pages that were used to choose the parameters, so they are optimistic.

## What was run

- Pages: 28 text-dominant single-folio pages (stars/recipes section f103-f116 plus f1r, f58, f66r, f76r), chosen from `data/page_index.csv` (`text_page_candidate`). Herbal/zodiac/biological pages with drawings were not attempted.
- Input: native scans extracted from the PDF (about 1500x2000 px, 220 ppi; letter x-height is only ~11-12 px).
- Method: black-hat ink extraction, projection-profile deskew, row-profile line detection, column-gap word splitting, connected-component + valley glyph candidates, HOG + geometry features, k-means / HDBSCAN.

## Accuracy proxies

| Stage | Metric | Value |
|---|---|---|
| Lines | detected / transcribed P-lines (all pages) | 1268 / 1271 |
| Lines | pages with exact / within ±1 / within ±3 line count | 25% / 57% / 86% |
| Lines | mean relative line-count error per page | 4% |
| Lines | transcribed lines that got a detected partner (DP alignment) | 85% |
| Words | detected / transcribed words (plain gap threshold, all pages) | 13135 / 12716 |
| Words | aligned lines where the plain threshold reproduces the exact word count | 18% |
| Words | aligned lines needing guided splitting / rejected as ambiguous | 52% / 31% |
| Words | correlation image word width vs transcribed length (n=5167; shuffled control 0.00) | 0.45 |
| Glyphs | candidate count equals transcribed unit count (n=5152 words) | 25% |
| Glyphs | candidate count within ±1 of unit count | 59% |
| Glyphs | mean (candidates - units), MAE, correlation | +0.61, 1.61, 0.40 |

Reading: line detection is decent on clean text pages (±1 line on about half the pages), word splitting by gaps is poor (the pen often joins neighbouring words and letters), and glyph candidates match the transcribed unit count exactly for only about a quarter of the words. The cursive, touching strokes and a ~11 px x-height are the limiting factors; a higher-resolution source image would help more than any clustering trick.

## Label provenance (so the EVA comparison is not circular)

Crops are cut from the image using ink structure only. The transcription supplies (a) which detected line belongs to which transcribed line (widths + word counts), (b) the *number* of words in the line, and (c) the number of units in a word. EVA letter identity is never used for cutting. Three labelled sets exist:

- **strict** (5968 crops): word where the number of image candidates equals the number of transcribed units; the i-th candidate gets the i-th unit. Biased towards easily segmented words.
- **forced** (19107 crops): words where the counts differ are cut at ink valleys into exactly the transcribed number of pieces. Noisy.
- **random-cut control** (18101 crops): same words and counts, cut positions drawn at random. Anything the forced set shows above this control is signal from the image.

## Image-derived inventory vs EVA

- k-means silhouette is flat (about 0.08 to 0.09 for k = 8 to 40; best k = 24): the crops form a continuum, not well-separated classes. HDBSCAN finds 2 dense clusters and labels 54% of crops as noise.
- The transcription-derived EVA catalogue (`glyphs/catalog.csv`, running text) has 15 symbols with share >= 1% and 17 with share >= 0.5%.
- So the image data **does not support a specific inventory size**. It neither confirms nor refutes the ~15-17 frequent EVA symbols.

Agreement between k-means clusters (fitted on unlabelled candidate crops) and EVA units, restricted to units with at least 40 labelled crops:

| k | set | units | NMI | ARI | purity | NMI with shuffled labels |
|---|---|---|---|---|---|---|
| 8 | strict | 17 | 0.081 | 0.041 | 0.22 | 0.004 |
| 8 | forced | 19 | 0.026 | 0.009 | 0.17 | 0.002 |
| 8 | random-cut | 18 | 0.016 | 0.006 | 0.16 | 0.002 |
| 12 | strict | 17 | 0.116 | 0.060 | 0.27 | 0.006 |
| 12 | forced | 19 | 0.035 | 0.011 | 0.18 | 0.002 |
| 12 | random-cut | 18 | 0.020 | 0.006 | 0.17 | 0.002 |
| 16 | strict | 17 | 0.133 | 0.070 | 0.31 | 0.008 |
| 16 | forced | 19 | 0.040 | 0.012 | 0.19 | 0.003 |
| 16 | random-cut | 18 | 0.024 | 0.008 | 0.17 | 0.003 |
| 24 | strict | 17 | 0.155 | 0.072 | 0.34 | 0.011 |
| 24 | forced | 19 | 0.050 | 0.013 | 0.20 | 0.004 |
| 24 | random-cut | 18 | 0.032 | 0.009 | 0.18 | 0.005 |
| 32 | strict | 17 | 0.167 | 0.070 | 0.35 | 0.015 |
| 32 | forced | 19 | 0.058 | 0.013 | 0.21 | 0.005 |
| 32 | random-cut | 18 | 0.036 | 0.008 | 0.18 | 0.006 |
| 40 | strict | 17 | 0.169 | 0.061 | 0.36 | 0.018 |
| 40 | forced | 19 | 0.058 | 0.012 | 0.21 | 0.006 |
| 40 | random-cut | 18 | 0.037 | 0.008 | 0.18 | 0.007 |

kNN separability of EVA units from crop features (grouped 5-fold by page, classes capped at 500):

| set | classes | accuracy | macro recall | chance |
|---|---|---|---|---|
| strict | 17 | 0.36 | 0.31 | 0.06 |
| forced | 19 | 0.17 | 0.14 | 0.05 |
| random-cut | 18 | 0.14 | 0.11 | 0.06 |

Reading: on the strict set the crops carry real information about the EVA unit (several times chance), but clusters are far from one-to-one with EVA letters (NMI ~0.15). On the forced set the gain over the random-cut control is small, so the forced labels are mostly noise: do not treat them as evidence about glyph identity. Because the strict set is selected by count agreement, it is not a representative sample of the manuscript.

### Most confusable EVA pairs (strict set, kNN)

| unit A | unit B | pair confusion rate | A read as B | B read as A |
|---|---|---|---|---|
| a | e | 0.14 | 0.11 | 0.17 |
| n | y | 0.14 | 0.25 | 0.09 |
| e | k | 0.12 | 0.09 | 0.15 |
| a | d | 0.11 | 0.09 | 0.14 |
| ch | e | 0.11 | 0.13 | 0.10 |
| e | i | 0.11 | 0.06 | 0.16 |
| a | i | 0.10 | 0.06 | 0.16 |
| k | t | 0.10 | 0.04 | 0.21 |

### Most confusable EVA pairs (forced set, kNN)

| unit A | unit B | pair confusion rate | A read as B | B read as A |
|---|---|---|---|---|
| n | y | 0.20 | 0.16 | 0.24 |
| a | d | 0.15 | 0.12 | 0.18 |
| ch | q | 0.14 | 0.12 | 0.17 |
| a | e | 0.14 | 0.10 | 0.18 |
| r | y | 0.13 | 0.14 | 0.12 |
| n | r | 0.13 | 0.10 | 0.16 |
| a | i | 0.13 | 0.07 | 0.18 |
| a | ch | 0.13 | 0.13 | 0.12 |

Pairs that stay confusable in the strict set (for example a/e, a/i, n/y, e/k) are candidates for 'EVA distinguishes them, the image at this resolution barely does'. That points at transcription/resolution limits, not at a finding about the script.

## Files

- `qa_metrics.json`, `pages.csv` (per page), `cluster_agreement_sweep.csv`, `knn_separability.csv`, `eva_vs_image.csv`, `confusable_pairs_*.csv`, `cluster_vs_eva_contingency_strict.csv`
- Figures: `cluster_sheet_k24.png`, `eva_units_strict_sheet.png`, `confusion_*.png`, `cluster_agreement_sweep.png`
- Overlays (red = line, blue = word, green/orange = glyph candidates): `overlay_p190_f106r.png`, `overlay_p138_f76r.png`, `overlay_p004_f1r.png`
- `glyphs/image/`: `image_inventory_k24.csv`, `sample_metadata.csv` and 196 tiny sample crops. The full crop array (about 77,000 crops) and metadata are in `data/processed/glyph_stage/` (git-ignored).

## Limitations

- No ground-truth boxes; accuracy is inferred from agreement with a transcription that itself has errors and uncertain spaces.
- Parameters (line smoothing, word-gap fraction, glyph width, merge size) were tuned for count agreement on these same pages. No held-out set.
- Only 28 text-dominant pages and a few scribal hands; no per-hand or per-quire analysis. Drawings, pigment and bleed-through are not handled; red star marks at line starts are sometimes detected as 'words'.
- Image resolution (x-height ~11 px) is too low to separate fine stroke differences; the Yale PDF only contains these ~220 ppi scans.
- Clusters are unlabelled shapes; matching an EVA letter does not mean the glyph is a letter, and nothing here says what the text is.
- Page-image rights: check Yale's usage statement before redistributing. Only tiny 24x24 crops and three annotated page excerpts are committed.
