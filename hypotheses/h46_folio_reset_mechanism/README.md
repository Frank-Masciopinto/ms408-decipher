# h46: how does the folio reset work?

Pre-registration: [PREREG.md](PREREG.md). Distributional and structural checks only; no translation claims.

## Data and units

Paragraph words in reading order from `h14_lib.table()`, `ZL3b-n.txt`, comma as a word space, hands `1A`, `2B`, `3B`. Each word is segmented into collapsed EVA units via `h13_lib.SEG(w)`. Two words form a one-edit pair when `edit1(u_i, u_j)` is true (`Levenshtein.distance(u_i, u_j) == 1` on unit tuples, `u_i != u_j`, `|len(u_i) - len(u_j)| <= 1`). Eligible pairs have `|len(u_i) - len(u_j)| <= 1` in the specified lag bin.

## Predictions

- **F1 (folio boundary breaks one-edit chains):** **fail**. In Test 1 (`21-100` or `101-500`), passing bins in Hand 1A: `['21-100']`; passing bins in Hand 2B: `[]`. (All three hands pass at `6-20`, and Hands `1A` and `3B` pass at `21-100`, with `3B` also passing at `101-500`; in Hand `2B`, the observed `rate(same) - rate(cross)` is positive at `21-100` (`+0.006200`) and `101-500` (`+0.003300`), but within-quire rotation preserves the same within-folio burst structure (`null_mean = +0.006339` and `+0.004204`, `null_p95 = +0.011412` and `+0.008700`), so `2B` does not exceed the rotation null beyond `6-20`.)
- **F2 (first-line seeding):** **fail**. Passing hands in Test 2: `[]`. Across all three hands (`1A`, `2B`, `3B`), the folio-opening line-1 seed rate is *lower* than the interior baseline rate (`effect = -0.016680`, `-0.023632`, `-0.019057`), opposite to first-line seeding and consistent with line-1 vocabulary/register specialization.
- **F3 (open-spread copying in Hand 2B):** **fail**. Passing bins in Hand 2B Test 3 (`21-100` or `101-500`): `[]`. In Hand `2B`, `rate(v_to_r) - rate(r_to_v)` is `0.003978` at `21-100` (`null_p95 = 0.010048`) and `-0.001045` at `101-500` (`null_p95 = 0.005947`).

## Test 1 — Cross-folio drop in one-edit pairs at matched lag

Up to 20,000 eligible pairs per side (`h42_lib.systematic_ranks`), scored when both `same` and `cross` have at least 200 eligible pairs, compared against 100 circular rotations of the token stream inside each quire against fixed folio lengths (seed 46).

| hand | bin | same_eligible | same_sampled | same_rate | cross_eligible | cross_sampled | cross_rate | effect | null_mean | null_p95 | scored | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1A | 6-20 | 66554 | 20000 | 0.079150 | 10709 | 10709 | 0.058829 | 0.020321 | 0.000520 | 0.007831 | True | True |
| 1A | 21-100 | 157416 | 20000 | 0.073900 | 250620 | 20000 | 0.067750 | 0.006150 | -0.002088 | 0.001670 | True | True |
| 1A | 101-500 | 17348 | 17348 | 0.061967 | 1962914 | 20000 | 0.063450 | -0.001483 | -0.007693 | 0.000287 | True | False |
| 2B | 6-20 | 76814 | 20000 | 0.077600 | 4383 | 4383 | 0.054073 | 0.023527 | 0.007024 | 0.015339 | True | True |
| 2B | 21-100 | 318967 | 20000 | 0.070150 | 108128 | 20000 | 0.063950 | 0.006200 | 0.006339 | 0.011412 | True | False |
| 2B | 101-500 | 392467 | 20000 | 0.070850 | 1673664 | 20000 | 0.067550 | 0.003300 | 0.004204 | 0.008700 | True | False |
| 3B | 6-20 | 76540 | 20000 | 0.057650 | 2504 | 2504 | 0.043131 | 0.014519 | 0.000920 | 0.010989 | True | True |
| 3B | 21-100 | 354765 | 20000 | 0.055600 | 61983 | 20000 | 0.047300 | 0.008300 | 0.001641 | 0.007067 | True | True |
| 3B | 101-500 | 735562 | 20000 | 0.053600 | 1293812 | 20000 | 0.045550 | 0.008050 | 0.001905 | 0.005515 | True | True |

## Test 2 — Folio-opening line seed test

Same-folio eligible pairs `(i, j)` (`i < j` on different lines) on folios with at least 6 paragraph lines: `seed_rate` (token `i` on line 1, token `j` on a later line) minus `interior_rate` (neither token on line 1), compared against 200 within-folio line-order permutations (seed 46).

| hand | folios | seed_eligible | seed_edit1 | seed_rate | interior_eligible | interior_edit1 | interior_rate | effect | null_mean | null_p95 | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1A | 112/112 | 38669 | 2340 | 0.060514 | 208786 | 16117 | 0.077194 | -0.016680 | 0.000098 | 0.006422 | False |
| 2B | 45/46 | 44841 | 2242 | 0.049999 | 747433 | 55034 | 0.073631 | -0.023632 | -0.001686 | 0.004327 | False |
| 3B | 28/28 | 50557 | 1841 | 0.036414 | 1123983 | 62349 | 0.055471 | -0.019057 | -0.000752 | 0.005738 | False |

## Test 3 — Visible spread (`v -> r`) vs page turn (`r -> v`)

Cross-folio eligible pairs `(i, j)` across consecutive manuscript folios (`folio_index[j] == folio_index[i] + 1`) in `21-100` and `101-500`: `rate(v_to_r) - rate(r_to_v)` against 200 random permutations of the `r_to_v` / `v_to_r` labels across consecutive folio transitions within each hand (seed 46).

| hand | bin | transitions | v_to_r_eligible | v_to_r_rate | r_to_v_eligible | r_to_v_rate | effect | null_mean | null_p95 | scored | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1A | 21-100 | 37 v->r / 50 r->v | 76098 | 0.070501 | 106296 | 0.073248 | -0.002747 | 0.000455 | 0.007393 | True | False |
| 1A | 101-500 | 37 v->r / 50 r->v | 50013 | 0.066923 | 99703 | 0.069948 | -0.003025 | 0.000150 | 0.007575 | True | False |
| 2B | 21-100 | 11 v->r / 20 r->v | 26691 | 0.071297 | 47876 | 0.067320 | 0.003978 | -0.000238 | 0.010048 | True | False |
| 2B | 101-500 | 11 v->r / 20 r->v | 396156 | 0.073087 | 481368 | 0.074132 | -0.001045 | -0.000053 | 0.005947 | True | False |
| 3B | 21-100 | 10 v->r / 11 r->v | 23308 | 0.052300 | 25127 | 0.051220 | 0.001080 | 0.000272 | 0.010817 | True | False |
| 3B | 101-500 | 10 v->r / 11 r->v | 558758 | 0.046401 | 557446 | 0.049811 | -0.003410 | -0.000301 | 0.008238 | True | False |

## Run

```bash
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python -m pytest hypotheses/h46_folio_reset_mechanism/test_h46.py
python hypotheses/h46_folio_reset_mechanism/run_h46.py
python hypotheses/h46_folio_reset_mechanism/summarise.py
```

numpy 2.5.4, rapidfuzz 3.14.6, python 3.12.3, runtime 5.2s.
