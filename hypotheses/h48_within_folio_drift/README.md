# h48: within-folio copy drift vs fixed page palette

Pre-registration: [PREREG.md](PREREG.md). Tests whether within-folio lexical and one-edit similarity in MS 408 decays with line distance $\Delta \ell = \ell_2 - \ell_1$ inside a single folio (top-to-bottom sequential drift) or is stationary across line positions on the folio (fixed page vocabulary palette).

## Predictions

- **D1 (within-folio one-edit drift):** **pass** (passing MS hands: 1A, 2B, 3B — 3/3 hands exceed the 95th percentile of 200 within-folio line permutations, seed 48).
- **D2 (within-folio unit-3gram drift):** **pass** (passing MS hands: 1A, 2B, 3B — 3/3 hands exceed the 95th percentile of 200 within-folio line permutations, seed 48).
- **D3 (drift vs palette decomposition):** **pass** (passing MS hands: 1A, 2B, 3B — in 3/3 hands, both the folio-palette component and the within-folio sequential drift component are strictly positive and $> 2$ null SDs).

## Summary of slopes (M1, M2) and half-folio drift (M3)

| stream | n_folios | n_lines | n_tokens | S_edit | S_edit_p95 | S_edit_z | D1_pass | S_cos3 | S_cos3_p95 | S_cos3_z | D2_pass | half_js | half_js_z |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MS_1A | 103 | 1418 | 9870 | 0.008568 | 0.003269 | 5.210000 | True | 0.041939 | 0.017609 | 10.470000 | True | -0.013080 | -2.250000 |
| MS_2B | 44 | 1215 | 10602 | 0.009348 | 0.000019 | 11.470000 | True | 0.042373 | -0.002891 | 19.080000 | True | -0.038691 | -5.150000 |
| MS_3B | 27 | 1093 | 10775 | 0.005960 | 0.000749 | 7.810000 | True | 0.030469 | 0.000248 | 13.960000 | True | -0.037550 | -5.330000 |
| it_boccaccio | 47 | 1175 | 10575 | -0.000610 | 0.001901 | -0.540000 | False | 0.008739 | 0.002878 | 4.800000 | True | -0.023398 | -3.440000 |
| la_pliny_herbal | 51 | 1171 | 10539 | -0.000133 | 0.000861 | 0.030000 | False | 0.009669 | 0.001998 | 7.040000 | True | -0.018066 | -3.100000 |
| self_citation | 49 | 1209 | 10500 | 0.010562 | 0.001443 | 12.060000 | True | 0.057157 | 0.003216 | 22.360000 | True | -0.071811 | -10.040000 |
| h39_native_tuned | 47 | 1167 | 10500 | 0.021378 | 0.001718 | 19.400000 | True | 0.106205 | 0.004476 | 38.210000 | True | -0.269081 | -31.940000 |
| palette_ctrl | 44 | 1215 | 10602 | -0.001525 | 0.000005 | 0.020000 | False | -0.007502 | -0.003880 | 0.070000 | False | -0.003654 | -0.510000 |

## M1: Within-folio one-edit rate `P(edit1 | Delta_l)` by line lag

| stream | lag_1 | lag_2 | lag_3-4 | lag_5-8 | lag_9+ |
|---|---|---|---|---|---|
| MS_1A | 0.084625 | 0.075054 | 0.073783 | 0.073796 | 0.068167 |
| MS_2B | 0.082876 | 0.077123 | 0.075131 | 0.071991 | 0.070334 |
| MS_3B | 0.061823 | 0.057601 | 0.058403 | 0.055713 | 0.053363 |
| it_boccaccio | 0.067151 | 0.067019 | 0.068907 | 0.069714 | 0.066596 |
| la_pliny_herbal | 0.016236 | 0.017615 | 0.015841 | 0.017019 | 0.017058 |
| self_citation | 0.065476 | 0.058686 | 0.059841 | 0.054222 | 0.050164 |
| h39_native_tuned | 0.072233 | 0.072274 | 0.069992 | 0.062883 | 0.044075 |
| palette_ctrl | 0.070072 | 0.072415 | 0.070308 | 0.070722 | 0.073363 |

## M2: Within-folio unit-3gram cosine (`cos3`) and word-type Jaccard (`jac`) by line lag

| stream | cos3_1 | cos3_2 | cos3_3-4 | cos3_5-8 | cos3_9+ | jac_1 | jac_2 | jac_3-4 | jac_5-8 | jac_9+ |
|---|---|---|---|---|---|---|---|---|---|---|
| MS_1A | 0.300518 | 0.283602 | 0.272263 | 0.262103 | 0.236249 | 0.028081 | 0.025876 | 0.023303 | 0.023039 | 0.020881 |
| MS_2B | 0.450859 | 0.443705 | 0.425990 | 0.419653 | 0.400565 | 0.042613 | 0.041462 | 0.036994 | 0.036018 | 0.032519 |
| MS_3B | 0.432245 | 0.426049 | 0.421921 | 0.410111 | 0.396220 | 0.026752 | 0.026865 | 0.024331 | 0.023671 | 0.022065 |
| it_boccaccio | 0.127090 | 0.125023 | 0.123084 | 0.119852 | 0.115973 | 0.039010 | 0.038570 | 0.039274 | 0.037164 | 0.034532 |
| la_pliny_herbal | 0.131705 | 0.128116 | 0.123622 | 0.122801 | 0.118829 | 0.028814 | 0.028908 | 0.027506 | 0.027777 | 0.025292 |
| self_citation | 0.383150 | 0.359353 | 0.359756 | 0.327032 | 0.307432 | 0.039302 | 0.037884 | 0.034487 | 0.025740 | 0.022593 |
| h39_native_tuned | 0.361953 | 0.365685 | 0.355142 | 0.308807 | 0.229515 | 0.067127 | 0.068303 | 0.064289 | 0.039356 | 0.012859 |
| palette_ctrl | 0.407700 | 0.404555 | 0.404825 | 0.408658 | 0.415164 | 0.036403 | 0.032439 | 0.033908 | 0.034008 | 0.035065 |

## D3: Decomposition of short-lag (`Delta_l in {1,2}`) same-folio one-edit excess over quire shuffle

| hand | obs_Delta12 | folio_perm_rate | quire_shuf_rate | total_excess | palette_comp | palette_z | palette_share | drift_comp | drift_z | drift_share | both_gt_2sd |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1A | 0.080167 | 0.074845 | 0.065840 | 0.014326 | 0.009005 | 8.710000 | 0.628500 | 0.005322 | 5.150000 | 0.371500 | True |
| 2B | 0.080077 | 0.071141 | 0.065950 | 0.014127 | 0.005191 | 5.520000 | 0.367500 | 0.008936 | 10.860000 | 0.632500 | True |
| 3B | 0.059741 | 0.054076 | 0.045662 | 0.014080 | 0.008415 | 11.690000 | 0.597600 | 0.005665 | 7.300000 | 0.402400 | True |

## Key findings (distributional only, no translation claims)

1. **Sequential within-folio copy drift is present in all three MS hands (`1A`, `2B`, `3B`):** Permuting line order within each folio preserves the exact folio vocabulary multiset and line lengths, yet destroys the short-lag excess (`S_edit = +0.008568` in `1A`, `+0.009348` in `2B`, `+0.005960` in `3B`; `z = 5.21`, `11.47`, `7.81` above the within-folio permutation null). The synthetic stationary-palette control (`palette_ctrl`) has `S_edit = -0.001525` and `S_cos3 = -0.007502` (both below the null).
2. **Prose controls show mild lexical drift (`S_cos3 > 0`) but zero one-edit drift (`S_edit <= 0`):** `it_boccaccio` and `la_pliny_herbal` pass `S_cos3` (`+0.008739` and `+0.009669`) from topical continuity, but fail `S_edit` (`-0.000610` and `-0.000133`), whereas MS hands and copy-drift generators (`self_citation`, `h39_native_tuned`) show strong decay in both `S_edit` and `S_cos3`.
3. **Both a page-level vocabulary seed and top-to-bottom drift contribute (`D3`):** Decomposing short-lag (`Delta_l in {1,2}`) same-folio one-edit excess over a 200-draw within-quire shuffle shows that in `1A` (`62.8%` palette / `37.2%` drift), `2B` (`36.7%` palette / `63.3%` drift), and `3B` (`59.8%` palette / `40.2%` drift), both components exceed `5` null SDs.

## Run

```bash
python -m pytest hypotheses/h48_within_folio_drift/test_h48.py -p no:cacheprovider
python hypotheses/h48_within_folio_drift/run_h48.py
python hypotheses/h48_within_folio_drift/summarise.py
```
