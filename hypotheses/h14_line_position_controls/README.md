# h14: line-position effects under layout controls

Pre-registration: `PREREG.md` (be999f9). Run with `python run_h14.py`; tests with `pytest test_h14.py` (4).
Outputs:
- `results/position_tests.csv` and `results/position_wide.csv`;
- `results/per_HL_S1.csv`;
- `results/procrustes_*.csv`;
- `results/summary.json`;
- `figures/enrichment_by_null.png`.

**Positional and distributional facts only. No meanings are claimed.**

**Data:** 4118 P lines and 34489 readable tokens. S1 uses 167 strata (HL × word-count bin × glyph-count bin × first line × gap/short). 15.0 % of lines contain a `<->` gap; 23.4 % are gap or short lines.

## Results
Ratios are observed/null mean. Holm correction is applied within each null over 49 tests.

| word | position | ratio vs HL only | S1 | S2 (within line) | S1L (+ word length) |
|---|---|---|---|---|---|
| daiin | initial | 1.52 | 1.50 | 1.50 | 1.15 (Holm 0.11, **fails**) |
| dain | initial | 1.88 | 1.84 | 1.85 | 2.00 |
| saiin | initial | 3.83 | 3.48 | 3.43 | 2.80 |
| sain | initial | 4.61 | 4.33 | 4.23 | 5.28 |
| sar | initial | 3.56 | 3.60 | 3.62 | 4.24 |
| sol | initial | 4.44 | 4.10 | 4.24 | 4.46 |
| y | initial | 2.02 | 2.04 | 2.08 | 3.18 |
| am | final | 6.49 | 6.97 | 7.06 | 4.63 |
| dam | final | 4.89 | 5.08 | 5.06 | 4.17 |
| dy | final | 2.79 | 2.94 | 3.00 | 2.40 |

- **Survival under S1 and S2:** all 10 enrichments and all 39 depletions survive.
- **Survival under S1L:** daiin's initial enrichment fails. It is largely explained by line-initial words being long: mean 4.91 units vs 4.46 null, z = +19.9. Seven depletions also lose significance (chor, chy, l, ol, otar, r, s).
- **Plain lines** (not first-of-paragraph, not gap/short), S1: all 10 enrichments survive (p ≈ 1e-4; ratios 1.76–6.68).
- **By hand × language (S1 ratios):** the initial effects are mostly a 2B/3B phenomenon. In 1A, daiin, dain, y and sain sit at ≈ 0.8–1.3; in 3B, daiin is 4.3 and saiin 7.2. The final effects of am, dam and dy hold in all three cells (3.0–9.0).
- **Margin squeezing:**
  - Line-final tokens are shorter than the null: 4.35 vs 4.46 units under S1, z = −4.9; z = −6.0 under the within-line null.
  - The shortening appears in 2B (z = −6.0) and 3B (z = −4.5), but in 1A final tokens are longer (z = +2.6).
  - am/dam/dy enrichment survives the word-length-matched null.
- **Procrustes (2B→1A, 20-D, leave-one-out, 90 words):**
  - Identity retrieval: top-1 1.1 % (chance 1.1 %), top-5 17.8 % (chance 5.6 %, so 3.2×), median rank 33.5 of 89.
  - Rule pairs (20 directed): the mapped partner ranks at a median 76th percentile (sign-flip one-sided p = 0.0005).
  - This contradicts h13's raw-cosine null result: once the hand spaces are aligned, the -edy/-ol partners are closer than random words.

## Verdicts
| | Prediction | Result |
|---|---|---|
| P1 | ≥5/7 initial enrichments survive S1 and S2 | **pass** (7/7; 6/7 also under S1L) |
| P2 | ≥2/3 final enrichments survive S1 and S1L | **pass** (3/3) |
| P3 | final tokens are shorter, yet am/dam/dy survive S1L | **pass** (z = −4.9; not true in 1A) |
| P4 | ≥60 % of depletions survive S1 | **pass** (39/39) |
| P5 | Procrustes top-5 > 3× chance AND rule pairs not better than random | **fail**: retrieval only just above 3×, and rule pairs are better than random (p = 0.0005) |

## Limits
- **Gap/short flag:** derived only from in-line `<->` markers and page-relative word counts. IVTFF does not encode where lines run into drawings, so "ends at a drawing" is approximate.
- **Line length is read from the transcription,** not measured on the vellum. S1L conditions on word length, which is itself partly positional.
- **Procrustes is small:** 90 words, 20 dimensions, 10 rule words. Rule partners share stems (ch-/sh-/qok-), which may make their contexts similar for reasons other than spelling; the identity anchors exclude only the held-out word.
- **Not independent:** the depletion sets overlap with the enrichment logic (e.g. dy is both initial-depleted and final-enriched).
