# h27: real Naibbe tables, plaintext removed

Pre-registered in [PREREG.md](PREREG.md) before any h27 scoring. The distances below are a match of ciphertext statistics to the MS 408 likelihood fingerprint. This note makes no decipherment claim.

## Question
h26 showed that the Naibbe–Italian match needs the author's hand-designed tables. This stage keeps those tables fixed and removes the plaintext, to see whether the fingerprint still appears.

## Method
- **Source:** Boccaccio, *Decameron* I–II (`it_boccaccio`), 61623 tokens. Every token survives `clean_plaintext` (mean cleaned length 4.567). No transfer text.
- **Cipher:** `h25_lib.NH` on `data/mechanisms/naibbe_tables.csv`, 6 tables, Naibbe card weights, p_unigram 17/36, max_retries 50. Encryption seed `s`, `n_words_out` = 21000. The h20 scorer keeps 10500 tokens.
- **Copy:** `h24_lib.copy_variant`, variant `swap`, c = 0.05, W = 20, EVA segmentation. Copy seed `100 * s + 17`.
- **Plaintexts:** `real` (unchanged tokens); `shuffle` (same multiset, seed `2000 + s`); `zipf` (4000 synthetic types, seed `3000 + s`). Zipf type lengths are drawn from the cleaned length distribution, letters i.i.d. from the cleaned unigram, and token frequencies follow P(rank) ∝ 1/rank with rank equal to generation order. Duplicate types are rejected and redrawn.
- **Scoring:** `run_h20.run_cell`, cell kind `ctrl`, segmentation `eva`. Bifolium is primary; quire is also scored. Distance and match use `h20_lib.match` / `DELTA` against the three committed hands in `cell_MS_{1A,2B,3B}.json`.
- **Seeds:** s = 1..5. One worker, serial. Wall time 750.3 s. Per-cell token tables were deleted after scoring.

## Results (bifolium)

95% confidence intervals are Student-t intervals on 5 seeds (df = 4).

| plaintext | n | ≥ 4/5 | 5/5 | distance, mean [95% CI] | D1 | D2 | D3 (λ5) | D4 | D5 |
|---|---|---|---|---|---|---|---|---|---|
| real | 5 | 5/5 | 1/5 | 3.432 [3.008, 3.857] | −0.205 | 0.213 | 0.022 | −0.083 | 1.829 |
| shuffle | 5 | 5/5 | 2/5 | 3.294 [2.476, 4.112] | −0.215 | 0.195 | 0.022 | −0.072 | 1.831 |
| zipf | 5 | 5/5 | 3/5 | 2.808 [1.315, 4.301] | −0.181 | 0.204 | 0.024 | −0.049 | 1.835 |

Seed distances (bifolium): real 3.157, 3.547, 3.041, 3.899, 3.518; shuffle 2.590, 3.074, 2.830, 4.065, 3.912; zipf 1.266, 3.910, 4.097, 2.673, 2.093.

## Results (quire)

D3 in this table is the same bifolium cross-fit λ that `run_h20.run_cell` stores once per cell.

| plaintext | n | ≥ 4/5 | 5/5 | distance, mean [95% CI] |
|---|---|---|---|---|
| real | 5 | 5/5 | 5/5 | 17.659 [15.317, 20.001] |
| shuffle | 5 | 5/5 | 5/5 | 18.021 [17.362, 18.680] |
| zipf | 5 | 5/5 | 5/5 | 18.091 [14.388, 21.794] |

The three plaintexts sit together on both fold schemes. The figure is `figures/plaintext_ablation.png`.

## Predictions

P3 passes, so P1 and P2 are interpreted.

| | rule | outcome |
|---|---|---|
| P1 | d(zipf) ≤ d(real) + 2 | **pass** (2.808 ≤ 5.432) |
| P2 | d(shuffle) ≤ d(real) + 2 and d(zipf) > d(real) + 2 | **fail** (shuffle 3.294 ≤ 5.432; zipf 2.808 is not above 5.432) |
| P3 | d(real) within 0.5 of 3.43 | **pass** (3.432, absolute difference 0.0023) |

P1 is the pre-registered statement that plaintext is irrelevant at this margin. Replacing Boccaccio with a shuffle, or with Zipf strings on the same letter distribution, leaves the bifolium distance inside the +2 band. The three 95% intervals overlap.

P2 asked for a split in which order can go and spelling cannot. Shuffle stays close to real, and so does zipf, so that split is not what happened.

P3 checks the engine. The five real-plaintext distances match the h26 Naibbe-swap anchor seeds to within 4.4×10⁻¹⁶, and the mean matches that anchor's mean 3.432347180466894. The path is the h26 path.

## Caveats
- Five seeds, one source text.
- The +2 margin is wide relative to the seed scatter of the real arm (about 3.04 to 3.90). The result is that zipf is not worse by 2, and the intervals do not separate the three arms.
- Zipf ranks follow generation order, so the most frequent type is one random string. Frequency-weighted mean length of the five zipf draws runs from 4.42 to 6.03, against a cleaned Boccaccio mean of 4.567. Rejecting duplicate types (1174–1248 redraws per seed) also shifts the type-length mean from 4.567 to about 5.40–5.45. About 3765–3797 of the 4000 types appear in a draw of 61623 tokens.
- Quire distances are larger than bifolium distances because distance is squared deviation from the hand means, while match is a band around the hand range. On quire folds every seed still matches 5/5.
- Cell kind is `ctrl`, so the fingerprint does not use the Naibbe plaintext language model.
