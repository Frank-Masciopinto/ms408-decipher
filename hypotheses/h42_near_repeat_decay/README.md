# h42: where one-edit near-repeats die out

Pre-registration: `PREREG.md`. Gap is the difference in token index (gap 1 = the next token).
A pair is eligible when the unit lengths differ by at most 1. The rate is the share of sampled eligible
pairs whose unit Levenshtein distance is 1. MS, C0, self-citation, and h39 use collapsed EVA units.
Boccaccio uses characters. Each bin keeps one even grid of at most 4000 eligible pairs, and every
shuffle uses that same count on its own eligible pairs. The null is ten shuffles
(numpy seed 42) inside hand x quire for the manuscript, and inside blocks of 8 pages of 200 tokens otherwise.
Excess is the observed rate minus the mean null rate. A bin is elevated when the excess is greater than
twice the null standard deviation and that standard deviation is above 0.

## Predictions

- N1. MS 2B is local or page: **pass**. Shape `page`, decay `21-100`.
- N2. h39 native tuned decays later than MS 2B, or is flat while MS 2B is not: **pass**. Native shape `page`, decay `101-500`.
- N3. Boccaccio bin-1 excess is smaller than MS 2B bin-1 excess: **pass**. Boccaccio `-0.026881`, MS 2B `0.006575`.

## Streams

| stream | n | shape | decay | bin1_excess | bin1_rate | bin1_null_mean | bin1_null_sd |
|---|---|---|---|---|---|---|---|
| MS 1A | 10326 | page | 21-100 | 0.029525 | 0.099000 | 0.069475 | 0.003008 |
| MS 2B | 10722 | page | 21-100 | 0.006575 | 0.073750 | 0.067175 | 0.003723 |
| MS 3B | 10835 | page | 101-500 | 0.026550 | 0.071000 | 0.044450 | 0.004017 |
| Boccaccio | 10500 | none | null | -0.026881 | 0.038852 | 0.065733 | 0.003224 |
| C0 | 10500 | local | 2-5 | 0.024050 | 0.065250 | 0.041200 | 0.003811 |
| self-citation | 10500 | page | 101-500 | 0.045375 | 0.093250 | 0.047875 | 0.002739 |
| h39 native tuned | 10500 | page | 101-500 | 0.030825 | 0.070500 | 0.039675 | 0.003760 |
| h39 C0 graph | 10500 | none | null | -0.005075 | 0.034750 | 0.039825 | 0.001696 |

## Excess by bin

| stream | 1 | 2-5 | 6-20 | 21-100 | 101-500 | 501-1000 |
|---|---|---|---|---|---|---|
| MS 1A | 0.029525 | 0.015850 | 0.010150 | 0.002150 | 0.001600 | -0.000550 |
| MS 2B | 0.006575 | 0.016400 | 0.006600 | 0.003225 | 0.010125 | 0.002600 |
| MS 3B | 0.026550 | 0.013300 | 0.017775 | 0.011900 | 0.001475 | 0.000675 |
| Boccaccio | -0.026881 | 0.002375 | 0.003350 | 0.001300 | -0.004100 | 0.003825 |
| C0 | 0.024050 | 0.002500 | 0.008250 | -0.004200 | -0.005050 | -0.002500 |
| self-citation | 0.045375 | 0.009350 | 0.019350 | 0.008200 | -0.003375 | -0.001450 |
| h39 native tuned | 0.030825 | 0.030875 | 0.026050 | 0.023525 | -0.004700 | -0.004200 |
| h39 C0 graph | -0.005075 | 0.002925 | 0.001325 | 0.001575 | 0.002350 | 0.002275 |

## Elevated bins

| stream | 1 | 2-5 | 6-20 | 21-100 | 101-500 | 501-1000 |
|---|---|---|---|---|---|---|
| MS 1A | Y | Y | Y | n | n | n |
| MS 2B | n | Y | Y | n | Y | n |
| MS 3B | Y | Y | Y | Y | n | n |
| Boccaccio | n | n | n | n | n | n |
| C0 | Y | n | Y | n | n | n |
| self-citation | Y | Y | Y | Y | n | n |
| h39 native tuned | Y | Y | Y | Y | n | n |
| h39 C0 graph | n | n | n | n | n | n |

## C0 fit

- Method `run_h12.fit`, n_random `60`, n_local `10`, fit seed `0`, generation seed `1`, plaintext `empty_stub_grammar_encoder_ignores_it`.
- Train tokens `10722`, generated `10500`, fit distance `2.568791`, seconds `15.646520`.

## Run

```
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python -m pytest hypotheses/h42_near_repeat_decay/test_h42.py
python hypotheses/h42_near_repeat_decay/h42_lib.py
python hypotheses/h42_near_repeat_decay/summarise.py
```

numpy 2.5.4, rapidfuzz 3.14.6, python 3.12.3.
