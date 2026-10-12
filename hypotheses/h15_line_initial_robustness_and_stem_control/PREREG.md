# h15 pre-registration (committed before computing)

## A. Robustness of the 2B/3B line-initial enrichment
**Words:** daiin, dain, saiin, sain, sar, sol, y.
**Data:** P lines of hands 2B and 3B, using h14's `table()` and its S1 strata (HL × word-count bin × glyph-count bin × first line × gap/short).
**Expected counts:** the exact hypergeometric mean under within-stratum shuffling, computed inside each unit (quire, or bifolium from `data/quires.csv` `bifolium_id`). The variance is the hypergeometric variance.
**Per unit:** log ratio = log((o + 0.5) / (e + 0.5)), with variance 1/(o + 0.5) + 1/(e + 0.5). Units with e < 1 are pooled into one "other" unit for the meta-analysis.
For each word, and for all 7 words combined, report:
- the count and share of units with ratio > 1, with a one-sided sign test;
- Cochran's Q, its p-value and I²;
- the DerSimonian–Laird random-effects pooled ratio and its 95 % CI;
- leave-one-quire-out and leave-one-bifolium-out pooled ratios (the minimum, and whether the CI still excludes 1);
- **1A power:** the probability that 1A's observed sample (its own S1 null) would reject at α = 0.05 (two-sided, Monte Carlo) if 1A's true ratio equalled the 2B/3B random-effects estimate. Also the difference test of the 1A vs 2B/3B log ratios (z).

**Predictions:**
- A1: the combined pooled ratio is > 1.5 with the CI excluding 1, and ≥ 70 % of quires have ratio > 1.
- A2: leave-one-quire-out never brings the combined CI down to 1.
- A3: the heterogeneity is moderate (I² < 75 %).
- A4: 1A power ≥ 0.8 for the combined set and for ≥ 4 of the 7 words, so 1A's absence is not a power artefact. The 1A vs 2B/3B difference has z > 3 for the combined set.

## B. Stem-controlled Procrustes
h14 procedure: per-hand PPMI context vectors (2B, 1A), 20-D SVD, leave-one-out orthogonal Procrustes 2B→1A over the top-100 words with context in both. Rule pairs: -edy/-ol, -edy/-or, -dy/-ol.
For each directed rule pair (x in 2B → y in 1A), the percentile of sim(x→y) among:
- (i) candidates sharing x's onset stem (the longest of `qok qot ok ot ch sh d s` that x starts with; candidates must have the same onset; y itself excluded);
- (ii) candidates at the same collapsed-unit edit distance from x as y, excluding the rule partner(s).

**Calibration:** the same percentile (i) for all non-rule same-onset pairs (x, z), measuring stem similarity alone. Rule pairs are compared with the calibration by a one-sided Mann–Whitney test, and against 0.5 by sign-flip.

**Predictions:**
- B1: under stem control (i), rule partners still rank above same-onset words (median percentile > 0.6, p < 0.05).
- B2: same under (ii).
- B3: rule-pair percentiles exceed the non-rule same-onset calibration (Mann–Whitney p < 0.05).
If B1–B3 fail, the h14 advantage is attributed to shared stems.

No translation or meaning claims.
