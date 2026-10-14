# h44: generator page burst

Pre-registration: `PREREG.md`. Burst is `h41_lib.burst` (50 types, blocks of 200).
orig is the stream. in_page, in_quire, and full are each the mean of 10 shuffles
from a fresh numpy Generator seeded with 44. Excess is orig minus full.
The share kept in the quire is (in_quire - full) / excess when excess is positive.

L, the median paragraph-token count of hand 2B folios, is 229.5000000000.
The two central folio counts are 210 and 249
(46 folios). Generated pages are 230 tokens,
the whole number nearest L, and a quire is 8 pages. Streams are 10,500 tokens
(hand 1A is the whole hand when it is shorter).
Manuscript hands use their real folios and real quires.

## Predictions

- B1. Every non-control, non-MS stream has excess below the smallest MS hand excess: **fail**.
  Smallest MS excess `1.5025317134`. Failures: `['fitted_s1', 'h39_native_tuned']`.
- B2. The positive control exceeds the largest MS hand excess: **pass**.
  Largest MS excess `1.6921321364`. Positive control `33.1835492040`.
- B3. At least two MS hands have (in_page - full) greater than (in_quire - full): **pass**.
  Hands: `['MS_1A', 'MS_2B', 'MS_3B']`.

## Streams

| stream | n | orig | in_page | in_quire | full | excess | quire_share |
|---|---|---|---|---|---|---|---|
| MS 1A | 10326 | 5.2190128402 | 5.2467505361 | 4.4195389680 | 3.7131863388 | 1.5058265014 | 0.4690796905 |
| MS 2B | 10500 | 5.1053826699 | 4.6430138074 | 3.8453462919 | 3.4132505335 | 1.6921321364 | 0.2553558018 |
| MS 3B | 10500 | 5.1007510490 | 4.5748942202 | 3.7794633005 | 3.5982193356 | 1.5025317134 | 0.1206257167 |
| fitted s1 | 10500 | 5.1119691764 | 4.6971262979 | 3.7131627406 | 3.4853881151 | 1.6265810613 | 0.1400327539 |
| fitted s2 | 10500 | 4.9567873438 | 4.5809826969 | 3.8228882624 | 3.5514599700 | 1.4053273738 | 0.1931423933 |
| C0 | 10500 | 3.7313468702 | 3.6449551901 | 3.5234809530 | 3.5777477080 | 0.1535991623 | -0.3533011128 |
| h06 pool 0.5 | 10500 | 4.4738299968 | 4.4694884211 | 4.3183688216 | 4.2085410681 | 0.2652889287 | 0.4139929776 |
| h06 p_pool 0 | 10500 | 3.7027850100 | 3.6696311491 | 3.5269483326 | 3.6527987977 | 0.0499862123 | -2.5177035689 |
| h39 native tuned | 10500 | 9.2321288160 | 8.0929591717 | 5.1268273072 | 4.4762134480 | 4.7559153681 | 0.1368009750 |
| h39 C0 graph | 10500 | 3.7373113465 | 3.6973793817 | 3.5532234074 | 3.5517995724 | 0.1855117741 | 0.0076751732 |
| positive control | 10500 | 37.0630880052 | 37.4138216432 | 9.6825238874 | 3.8795388013 | 33.1835492040 | 0.1748753592 |

## Manuscript page gap minus quire gap

| stream | in_page_minus_full | in_quire_minus_full |
|---|---|---|
| MS 1A | 1.5335641973 | 0.7063526292 |
| MS 2B | 1.2297632739 | 0.4320957584 |
| MS 3B | 0.9766748846 | 0.1812439648 |

## Generators

- C0 fit method `run_h12.MR.fit_variant`, n_random `20`, n_local `10`,
  fit seed `0`, generation seed `1`, workers `1`.
  Train tokens `10722`, fit distance `3.4094262732`, seconds `31.4712838660`.
  Plaintext: empty_stub; grammar encoder ignores plaintext.
- h06 parameters were not fitted. Shared model built from hand 2B paragraph words
  (n_train `10722`, shared seed `0`), generation seed `1`.
  `h06_pool`: p_pool `0.5`, pool size `10`, pool `['shedy', 'ol', 'chedy', 'qokedy', 'qokain', 'or', 'qokeedy', 'daiin', 'aiin', 'dar']`.
  `h06_p0`: p_pool `0.0`, pool size `0`.
  Base parameters `{'p_copy': 0.1, 'window': 20, 'p_prev': 0.3, 'p_exact': 0.15, 'p_suffix': 0.3, 'p_prefix': 0.2, 'p_pool': 0.0}`.
- Positive control seed `1`, `40` types per page, Zipf weights 1/rank.

## Run

```
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python -m pytest hypotheses/h44_generator_page_burst/test_h44.py
python hypotheses/h44_generator_page_burst/run_h44.py
python hypotheses/h44_generator_page_burst/summarise.py
```

numpy 2.5.4, python 3.12.3.
