# h50: do paragraph-initial or line-initial words form a hidden header or acrostic stream?

Pre-registration: [PREREG.md](PREREG.md). Tests whether the vertical sequences of
paragraph-initial words (`para_words`), line-initial words (`line_words_raw` and `h16`
onset-stripped `line_words_stripped`), or line-initial first units (`line_first_unit`) in
MS 408 (`1A`, `2B`, `3B`) exhibit sequential linguistic structure beyond the no-plaintext
`h47` `page_line_copier` generator and within-folio / within-quire permutation nulls.
No translation or semantic claims are made.

## Predictions and Verdict (`A1`–`A3`)

- **Overall verdict:** **`partially_supported`** (`A1 = fail`, `A2 = fail`, `A3 = pass`).
- **A1 (vertical word stream has sequential syntax):** **fail** (passing MS hands: `[]`).
  In all three MS hands (`1A`, `2B`, `3B`), 5-fold cross-validated Kneser–Ney bigram gain over unigram (`D1_vert = bits(KN1) - bits(KN2)`) is negative on `line_words_raw` (`-0.2333`, `-0.2286`, `-0.2073`), `line_words_stripped` (`-0.2196`, `-0.1979`, `-0.1834`), and `para_words` (`-0.0834`, `-0.0757`, `-0.1026`), matching the non-semantic `page_line_copier` streams (`-0.2437` to `-0.2584` on `line_words_stripped`). By contrast, the Italian recipe control (`cucina`), where paragraph openings form genuine recurring recipe headers, passes `A1` with `D1_vert = +0.4271` bits/word and lag-1 class MI `1.5862 > p95 = 1.0012` (`z = 7.77`).
- **A2 (vertical glyph acrostic spells words):** **fail** (passing MS hands: `[]`).
  While `line_first_unit` has modest within-folio redundancy $R_{\text{acro}} = H_1 - h_2$ above the within-folio permutation 95th percentile (`0.3941` in `1A`, `0.2613` in `2B`, `0.2702` in `3B` — driven by paragraph-initial gallows followed by line-initial continuation prefixes), it reaches only `24.3%`, `13.7%`, and `15.2%` of the horizontal within-word unit redundancy $R_{\text{horiz}}$ (`1.6227`, `1.9125`, `1.7779` bits), far below the `50%` threshold for spelled words. Moreover, vertical `line_first_unit` shows near-zero or negative Sukhotin vowel/consonant alternation excess (`-0.0170`, `+0.0080`, `-0.0056`) compared to strong positive C/V alternation inside horizontal words (`+0.0756`, `+0.0886`, `+0.0956`).
- **A3 (onset-stripped Line 1 headers match their own folio):** **pass** (passing MS hands: `['1A', '2B', '3B']`).
  In all three MS hands (`1A`, `2B`, `3B`), onset-stripped Line-1 words have higher unit-3gram cosine similarity (`header_body_cos`) with their own folio body than the 95th percentile of 200 within-quire Line-1 swaps across folios (`0.4041 > 0.3756` in `1A`; `0.5329 > 0.5225` in `2B`; `0.5565 > 0.5286` in `3B`). Crucially, the no-plaintext `h47` synthetic streams (`page_line_copier_1A/2B/3B`) **also pass `A3` in all three hands** (`0.4262 > 0.3962`, `0.5348 > 0.5306`, `0.5940 > 0.5728`), and unstripped `header_body_cos_raw` (`0.4006`, `0.5313`, `0.5540`) is virtually identical to stripped `header_body_cos`. This shows that `A3` reflects folio-level vocabulary persistence and lookback copying (`h47`/`h48`) rather than a hidden steganographic header key.

## M1 — Vertical Word-Order Gain (`D1_vert`), Lag-1 Class MI, and Adjacent Repetition

| Stream | Kind | Lines | Paras | Folios | `line_words_raw` $D_1$ | `line_words_stripped` $D_1$ | `line_words_stripped` MI (p95) | `line_words_stripped` `adj_rep_z` | `para_words` $D_1$ | `para_words` MI (p95) | A1 Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `MS_1A` | `eva` | 1477 | 209 | 112 | -0.2120 | -0.2196 | 0.2943 (0.2975) | -1.42 | -0.0834 | 0.8175 (0.7636) | **fail** |
| `MS_2B` | `eva` | 1227 | 148 | 46 | -0.1825 | -0.1979 | 0.3925 (0.3883) | -0.39 | -0.0757 | 1.2453 (1.3220) | **fail** |
| `MS_3B` | `eva` | 1100 | 279 | 28 | -0.1917 | -0.1834 | 0.3219 (0.3312) | 0.63 | -0.1026 | 0.5870 (0.5654) | **fail** |
| `page_line_copier_1A` | `eva` | 1477 | 209 | 112 | -0.2402 | -0.2437 | 0.3180 (0.3438) | 0.69 | -0.2001 | 1.2690 (1.2720) | **fail** |
| `page_line_copier_2B` | `eva` | 1197 | 147 | 46 | -0.2412 | -0.2580 | 0.3722 (0.3971) | -0.32 | -0.2002 | 1.6451 (1.7882) | **fail** |
| `page_line_copier_3B` | `eva` | 1069 | 277 | 28 | -0.2579 | -0.2584 | 0.3651 (0.4225) | -0.61 | -0.1487 | 0.7754 (0.8451) | **fail** |
| `it_boccaccio` | `char` | 1197 | 147 | 46 | -0.2198 | -0.2215 | 0.2901 (0.3243) | 0.67 | -0.1525 | 1.3914 (1.5517) | **fail** |
| `cucina` | `char` | 1058 | 313 | 43 | 0.0038 | 0.0077 | 0.6086 (0.3942) | -2.72 | 0.4271 | 1.5862 (1.0012) | **pass** |
| `la_pliny_herbal` | `char` | 1197 | 147 | 46 | -0.1636 | -0.1648 | 0.1995 (0.2289) | -0.12 | -0.0621 | 1.3841 (1.4006) | **fail** |

## M2 — Vertical Glyph-Acrostic Redundancy (`R_acro`) and Sukhotin Alternation (`sukhotin_alt`)

| Stream | $H_{1,\text{acro}}$ | $h_{2,\text{acro}}$ | $R_{\text{acro}} = H_1 - h_2$ | Perm p95 ($z$) | $R_{\text{horiz}}$ | $R_{\text{acro}} / R_{\text{horiz}}$ | Vert Sukhotin Excess ($z$) | Horiz Sukhotin Excess ($z$) | A2 Pass |
|---|---|---|---|---|---|---|---|---|---|
| `MS_1A` | 3.3091 | 2.9151 | 0.3941 | 0.1398 (22.85) | 1.6212 | 0.243 | 0.0569 (4.88) | 0.1558 (67.48) | **fail** |
| `MS_2B` | 3.2277 | 2.9664 | 0.2613 | 0.1524 (10.49) | 1.9062 | 0.137 | 0.0123 (1.30) | 0.1963 (93.19) | **fail** |
| `MS_3B` | 3.2563 | 2.9860 | 0.2702 | 0.1514 (10.83) | 1.7833 | 0.152 | 0.0441 (3.48) | 0.1669 (62.84) | **fail** |
| `page_line_copier_1A` | 1.8097 | 1.7076 | 0.1021 | 0.0599 (5.22) | 0.6579 | 0.155 | 0.0200 (1.55) | 0.0802 (36.41) | **fail** |
| `page_line_copier_2B` | 1.8731 | 1.8533 | 0.0198 | 0.0465 (-1.10) | 0.8314 | 0.024 | -0.0020 (-0.22) | 0.0933 (43.02) | **fail** |
| `page_line_copier_3B` | 1.6528 | 1.5239 | 0.1289 | 0.0453 (11.06) | 0.8815 | 0.146 | 0.0017 (0.20) | 0.0876 (42.01) | **fail** |
| `it_boccaccio` | 3.9499 | 3.6933 | 0.2567 | 0.2541 (1.70) | 1.0500 | 0.244 | 0.0085 (0.79) | 0.1759 (62.46) | **fail** |
| `cucina` | 3.8867 | 3.4638 | 0.4229 | 0.3155 (7.48) | 1.0653 | 0.397 | 0.0190 (1.99) | 0.1779 (93.57) | **fail** |
| `la_pliny_herbal` | 3.9094 | 3.6648 | 0.2446 | 0.2507 (1.26) | 0.7489 | 0.327 | 0.0106 (0.77) | 0.2244 (123.52) | **fail** |

## M3 — Folio-Header (`Line 1` Stripped) to Body Alignment (`header_body_cos` & One-Edit Rate)

| Stream | Folios ($\ge 2$ lines) | Quires | `header_body_cos` | `header_body_cos_raw` | Swap Null Mean | Swap Null p95 ($z$) | `header_body_edit1` | Edit1 Null Mean | Edit1 Null p95 ($z$) | A3 Pass |
|---|---|---|---|---|---|---|---|---|---|---|
| `MS_1A` | 112 | 10 | 0.4041 | 0.4273 | 0.3666 | 0.3756 (6.24) | 0.0663 | 0.0594 | 0.0623 (3.57) | **pass** |
| `MS_2B` | 46 | 6 | 0.5329 | 0.5350 | 0.5131 | 0.5225 (3.04) | 0.0530 | 0.0527 | 0.0553 (0.21) | **pass** |
| `MS_3B` | 28 | 2 | 0.5565 | 0.5581 | 0.5110 | 0.5286 (4.53) | 0.0382 | 0.0348 | 0.0373 (2.22) | **pass** |
| `page_line_copier_1A` | 112 | 10 | 0.4262 | 0.4411 | 0.3880 | 0.3962 (7.42) | 0.0491 | 0.0449 | 0.0468 (3.71) | **pass** |
| `page_line_copier_2B` | 46 | 6 | 0.5348 | 0.5583 | 0.5209 | 0.5306 (2.47) | 0.0468 | 0.0461 | 0.0490 (0.43) | **pass** |
| `page_line_copier_3B` | 28 | 2 | 0.5940 | 0.5919 | 0.5620 | 0.5728 (4.76) | 0.0367 | 0.0360 | 0.0382 (0.45) | **pass** |
| `it_boccaccio` | 46 | 6 | 0.2567 | 0.2707 | 0.2488 | 0.2587 (1.27) | 0.0744 | 0.0730 | 0.0765 (0.72) | **fail** |
| `cucina` | 43 | 11 | 0.2801 | 0.3028 | 0.2701 | 0.2793 (1.77) | 0.0958 | 0.0949 | 0.0974 (0.66) | **pass** |
| `la_pliny_herbal` | 46 | 6 | 0.2815 | 0.2845 | 0.2790 | 0.2873 (0.54) | 0.0185 | 0.0179 | 0.0200 (0.58) | **fail** |

## Reproduction

```bash
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python3 hypotheses/h50_header_acrostic_stream/run_h50.py
python3 hypotheses/h50_header_acrostic_stream/summarise.py
python3 -m pytest hypotheses/h50_header_acrostic_stream/test_h50.py -p no:cacheprovider
```
