# h29: what moves D4, and can a short decodable table reach it?

This stage was pre-registered in [PREREG.md](PREREG.md) before any h29 computing. It makes no translation claims. The scores below are surface statistics of ciphertext. They do not read the manuscript.

## Question
h24–h26 miss the fingerprint on word-versus-character dominance (D4), which needs to clear −0.07. Two parts:

1. On the cells already scored, which stored property tracks distance and D4?
2. In a two-knob toy (code length L, suffix-pool size V), does any setting with decodable share ≥ 0.8 also reach D4 ≥ −0.07?

## Part 1 — stored fingerprints only
No new ciphertext. Spearman rank correlation on the committed bifolium CSVs from h24, h25, and h26.

h26 subset: `src == it_boccaccio`, `render == eva`, `grammar != naibbe` (n = 66). ρ of `m_distance` and of `D4` against four stored properties:

| property | ρ with distance | ρ with D4 |
|---|---:|---:|
| mean word length | **+0.847** | −0.812 |
| decodable share | +0.711 | −0.772 |
| positional rigidity | −0.367 | +0.413 |
| per-unit entropy H1 | +0.223 | −0.289 |

h25, `src == it_boccaccio`, ρ of decodable share, split by rendering:

| render | n | ρ with distance | ρ with D4 |
|---|---:|---:|---:|
| char | 78 | −0.356 | +0.180 |
| eva | 15 | +0.675 | −0.679 |

h24 is reported only as a family table (mean distance and mean D4 by cipher). Rows with no cipher are omitted.

| cipher | n | mean distance | mean D4 |
|---|---:|---:|---:|
| naibbe | 60 | 3.44 | −0.091 |
| homo2 | 18 | 132.3 | −0.040 |
| homo4 | 9 | 435.2 | −0.018 |
| nomen | 9 | 1081 | −3.17 |
| verb12 | 9 | 1310 | −3.51 |
| verb8null | 9 | 2306 | −4.73 |
| verb8 | 9 | 2399 | −4.79 |

## Part 2 — toy tables
Engine: `h25_lib.NH`, 6 tables, Naibbe card weights, p_unigram = 17/36, glyph alphabet `GLYPHS[:20]`. No copy layer. Plaintext: Boccaccio. One seed, s = 1. Char segmentation. Bifolium folds only (the quire scheme was not run). D1–D5 follow `h20_lib.dstats`, matched to the three committed MS hand rows with `h20_lib.match`. Decryptability is `h25_lib.decodable_share` on the 10,500 scored tokens.

Code strings have length L. Unigram and prefix codes are distinct inside each (state, table), resampling on collision. The suffix pool is one shared list of V distinct length-L strings, built first; every suffix slot draws from it with replacement.

A length-1 string has only 20 possibilities in this alphabet, and each table has 23 letters. For L = 1 the suffix pool is capped at 20, and the last unigram and prefix letters reuse a code once the 20 strings are exhausted. V = 32, 64, and 128 at L = 1 are therefore the same table and the same ciphertext. From L = 2 upward the pool has size V and the unigram and prefix codes are unique within each (state, table).

## Results (bifolium, Boccaccio, char segmentation)

MS hand D4 on the same definition is +0.031, +0.048, and +0.080 (hands 3B, 2B, 1A). The two-sided D4 match window is −0.069 to +0.180. MS D5 is 1.77–1.94.

| L | V | pool | decodable | D4 | D5 | matches | distance |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 8 | 8 | 0.000 | −1.100 | 2.70 | 1 | 3480 |
| 1 | 16 | 16 | 0.000 | −1.481 | 2.88 | 1 | 4372 |
| 1 | 32 | 20 | 0.000 | −1.640 | 2.95 | 1 | 4655 |
| 1 | 64 | 20 | 0.000 | −1.640 | 2.95 | 1 | 4655 |
| 1 | 128 | 20 | 0.000 | −1.640 | 2.95 | 1 | 4655 |
| 2 | 8 | 8 | 0.370 | +0.065 | 2.18 | 3 | 10.9 |
| 2 | 16 | 16 | 0.386 | +0.153 | 2.32 | 4 | 12.7 |
| 2 | 32 | 32 | 0.505 | +0.167 | 2.42 | 4 | 16.8 |
| 2 | 64 | 64 | 0.686 | +0.055 | 2.38 | 3 | 17.3 |
| 2 | 128 | 128 | 0.742 | +0.167 | 2.48 | 3 | 24.7 |
| 3 | 8 | 8 | 0.479 | +0.192 | 1.61 | 1 | 15.7 |
| 3 | 16 | 16 | 0.479 | +0.330 | 1.69 | 2 | 20.4 |
| 3 | 32 | 32 | 0.479 | +0.603 | 1.78 | 2 | 41.5 |
| 3 | 64 | 64 | **0.922** | **+0.377** | 1.74 | 2 | 21.5 |
| 3 | 128 | 128 | **0.977** | **+0.482** | 1.79 | 2 | 29.9 |
| 4 | 8 | 8 | 0.479 | +0.028 | 1.29 | 2 | 26.9 |
| 4 | 16 | 16 | 0.479 | +0.218 | 1.36 | 1 | 26.1 |
| 4 | 32 | 32 | 0.495 | +0.444 | 1.43 | 1 | 36.1 |
| 4 | 64 | 64 | 0.720 | +0.456 | 1.47 | 1 | 35.0 |
| 4 | 128 | 128 | **0.966** | **+0.430** | 1.44 | 1 | 34.2 |
| 5 | 8 | 8 | 0.479 | −0.414 | 1.12 | 1 | 58.3 |
| 5 | 16 | 16 | 0.479 | −0.393 | 1.21 | 1 | 50.8 |
| 5 | 32 | 32 | 0.479 | −0.412 | 1.30 | 1 | 47.4 |
| 5 | 64 | 64 | 0.748 | −0.519 | 1.32 | 1 | 57.2 |
| 5 | 128 | 128 | **0.953** | −0.540 | 1.35 | 1 | 58.8 |

Bold marks decodable share ≥ 0.8. The figure is [figures/d4_grid.png](figures/d4_grid.png): D4 against V, one series per L, stars where decodable share ≥ 0.8.

Four cells clear decodable share 0.8. Three of them also clear D4 ≥ −0.07:

| cell | decodable | D4 |
|---|---:|---:|
| D4_L3_V128_s1 | 0.977 | +0.482 |
| D4_L4_V128_s1 | 0.966 | +0.430 |
| D4_L3_V64_s1 | 0.922 | +0.377 |
| D4_L5_V128_s1 | 0.953 | −0.540 |

The best D4 among those four is +0.482. That value is above the MS band. All three cells with both decodable share ≥ 0.8 and D4 ≥ −0.07 fail the two-sided D4 match (`m_D4` is false). No cell is 5/5. The closest cells are L = 2, V = 16 and L = 2, V = 32 (4/5, distance 12.7 and 16.8), both with decodable share under 0.51. At L ≥ 3 and V ≤ 16, decodable share stays at 0.479, next to the unigram rate 17/36, and rises only once the suffix pool is large enough for bigrams to be unique.

## Predictions

| | prediction | outcome |
|---|---|---|
| R1 | On the h26 subset, mean word length has the largest \|ρ\| with distance among the four properties | **holds** (\|ρ\| = 0.847, ahead of decodable share 0.711) |
| T1 | No toy cell with decodable share ≥ 0.8 has D4 ≥ −0.07 | **does not hold** (3 cells do both; best D4 among cells with decodable share ≥ 0.8 is +0.482) |
| T2 | Spearman ρ of D4 against V, over the 25 cells, is negative | **does not hold** (ρ = +0.114) |

## Verdict
Mean rendered word length is the strongest stored correlate of distance on the h26 subset, and it moves with D4 in the opposite direction (ρ = −0.812). On the toy grid, a decodable table can sit above the D4 floor of −0.07. The cells that do so overshoot the MS hands (D4 about +0.38 to +0.48 against +0.03 to +0.08) and remain far from the five-statistic fingerprint (2/5 or 1/5, distance 21–34). Lengthening the codes to L = 5 pulls D4 back under the floor (−0.54 at the decodable cell) and makes the distance worse. Pool size V does not pull D4 down across the grid: the rank correlation is positive and small.

## Limits
- One seed.
- Bifolium folds only.
- Char segmentation, no copy layer, glyph alphabet of 20.
- L = 1 cannot realise a pool larger than 20, and 23 letters cannot all receive distinct length-1 codes.
- Scoring took 1216 seconds.
