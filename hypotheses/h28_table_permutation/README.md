# h28: permutations of the real Naibbe tables

This stage was pre-registered in [PREREG.md](PREREG.md) before any h28 computing. The numbers below are the bifolium fingerprint of the fifteen scored cells. A match under the pre-registered rule is not a decipherment and not a translation.

## Question

Which level of the author's tables carries the h26 match: the letter-to-string mapping, the prefix/suffix role split, or the order of glyphs inside each string?

## Method

- Source table: `data/mechanisms/naibbe_tables.csv`, read only. Each permuted table is `tables/h28_<condition>_s<s>.csv`.
- Plaintext: Boccaccio (`it_boccaccio`), 5 seeds. No transfer.
- Shuffle seed `4000 + s`. Encryption seed `s`. Copy seed `100 * s + 17`.
- **letter:** within each (state, table), the 23 glyph strings are shuffled across the 23 letters.
- **state:** unigram strings stay in place. Within each table the 23 prefix strings and 23 suffix strings are pooled, shuffled, and written back onto those slots.
- **unit:** each glyph string is segmented with `run_h19.seg_fn("eva")`, the units are shuffled, and they are joined. `"".join(seg(s)) == s` held for every original string (414 strings, 29 of them a single unit).
- Engine: `NH(table, 6, "naibbe", 17/36)`, then swap copying at c = 0.05 with the EVA segmenter, then `run_h20.lines_to_cell(..., "ctrl", "eva")` and `run_h20.run_cell`. Output length `2 × 10500`; the scorer keeps 10500 tokens. One worker. Token dumps were deleted after each cell.
- A condition matches when its bifolium mean distance is ≤ 5.43 and its ≥4/5 rate is ≥ 0.60. 5.43 is the h26 real-table + swap anchor 3.43 plus 2. That anchor was not recomputed.

## Results (bifolium, primary)

| condition | n | mean distance [95% CI] | ≥4/5 | 5/5 | matches | D1 | D2 | D3 | D4 | D5 |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| letter | 5 | 21.9585 [17.8046, 26.1123] | 0.800 | 0.000 | no | -0.1999 | 0.2104 | 0.0188 | -0.3879 | 1.7562 |
| state | 5 | 27.4984 [19.8650, 35.1317] | 0.800 | 0.000 | no | -0.2029 | 0.2337 | 0.0178 | -0.4481 | 1.8270 |
| unit | 5 | 143.0775 [124.8387, 161.3163] | 0.400 | 0.000 | no | -0.2000 | 0.3380 | 0.0212 | -1.1219 | 2.0848 |

Per seed:

| cell | distance | n_match | 5/5 | D1 | D2 | D3 | D4 | D5 |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| T_boccaccio_letter_s1 | 18.3218 | 4 | no | -0.1995 | 0.2123 | 0.0178 | -0.3421 | 1.7341 |
| T_boccaccio_letter_s2 | 18.4081 | 4 | no | -0.2027 | 0.2355 | 0.0207 | -0.3515 | 1.7439 |
| T_boccaccio_letter_s3 | 25.3999 | 4 | no | -0.1905 | 0.1980 | 0.0214 | -0.4326 | 1.7737 |
| T_boccaccio_letter_s4 | 24.0281 | 4 | no | -0.1992 | 0.2050 | 0.0183 | -0.4121 | 1.7640 |
| T_boccaccio_letter_s5 | 23.6344 | 3 | no | -0.2074 | 0.2009 | 0.0156 | -0.4011 | 1.7651 |
| T_boccaccio_state_s1 | 25.0225 | 4 | no | -0.2042 | 0.2295 | 0.0198 | -0.4297 | 1.8528 |
| T_boccaccio_state_s2 | 30.1958 | 4 | no | -0.1894 | 0.2516 | 0.0181 | -0.4793 | 1.8398 |
| T_boccaccio_state_s3 | 21.2481 | 4 | no | -0.2023 | 0.2022 | 0.0173 | -0.3816 | 1.8122 |
| T_boccaccio_state_s4 | 36.8583 | 3 | no | -0.2205 | 0.2322 | 0.0162 | -0.5327 | 1.8199 |
| T_boccaccio_state_s5 | 24.1671 | 4 | no | -0.1983 | 0.2527 | 0.0178 | -0.4173 | 1.8104 |
| T_boccaccio_unit_s1 | 125.8756 | 4 | no | -0.1986 | 0.3519 | 0.0225 | -1.0500 | 2.0567 |
| T_boccaccio_unit_s2 | 142.4859 | 3 | no | -0.2034 | 0.3110 | 0.0228 | -1.1228 | 2.0925 |
| T_boccaccio_unit_s3 | 143.9168 | 3 | no | -0.2134 | 0.3492 | 0.0221 | -1.1244 | 2.1032 |
| T_boccaccio_unit_s4 | 137.0221 | 4 | no | -0.1857 | 0.3471 | 0.0196 | -1.0972 | 2.0702 |
| T_boccaccio_unit_s5 | 166.0870 | 3 | no | -0.1988 | 0.3309 | 0.0190 | -1.2152 | 2.1013 |

The unit shuffle changed the unit order of 1563 of 2070 string copies (s1 309/414, s2 313/414, s3 313/414, s4 312/414, s5 316/414), share 0.755072.

## Quire folds (scored, not used in the decision)

| condition | n | mean distance [95% CI] | ≥4/5 | 5/5 | matches | D1 | D2 | D3 | D4 | D5 |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| letter | 5 | 22.0454 [17.9557, 26.1352] | 0.800 | 0.000 | no | -0.2061 | 0.2167 | 0.0188 | -0.3887 | 1.7577 |
| state | 5 | 26.7299 [19.0826, 34.3772] | 0.800 | 0.000 | no | -0.2035 | 0.2332 | 0.0178 | -0.4404 | 1.8276 |
| unit | 5 | 142.5346 [125.2963, 159.7730] | 0.400 | 0.000 | no | -0.2094 | 0.3355 | 0.0212 | -1.1194 | 2.0861 |

## Predictions

| | pre-registered call | result | pass |
|---|---|---|---|
| A1 | `letter` matches. The letter-to-string mapping is not required. | distance 21.9585, ≥4/5 0.800, 5/5 0.000, matches=no | fail |
| A2 | `state` does not match. Prefix/suffix complementarity is required. | distance 27.4984, ≥4/5 0.800, 5/5 0.000, matches=no | pass |
| A3 | `unit` does not match. Within-string order is required. | distance 143.0775, ≥4/5 0.400, 5/5 0.000, matches=no | pass |

## Reading

No single one of these three cuts is the carrier.

The label is `none`.

## Limits

- Five seeds, and only Boccaccio.
- The decision uses bifolium folds. Quire numbers are from the same `run_h20.run_cell` output and do not enter the pass/fail calls.
- Strings of one EVA unit cannot change under the unit shuffle. The reported share counts every original string, including those.
- The threshold is fixed from h26. It was not refit on these cells.

## Files

- Code and tests: `h28_lib.py`, `run_h28.py`, `summarise.py`, `test_h28.py`.
- Permuted tables: `tables/h28_<letter|state|unit>_s<1–5>.csv`.
- Cells and aggregates: `results/cell_*.json`, `results/fingerprints_*.csv`, `results/groups_*.csv`, `results/STATUS.json`.
- Figure: `figures/table_permutations.png`.
