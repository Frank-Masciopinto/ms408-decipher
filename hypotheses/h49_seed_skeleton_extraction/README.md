# h49: Does Stripping Same-Folio One-Edit Echoes Uncover a Language-Like Seed Skeleton?

Pre-registration: [PREREG.md](PREREG.md). Tests whether stripping same-folio exact repeats and unit-edit-distance-1 echoes (`local_W25` with lookback window $W = 25$, and `folio_comp` across the entire folio) uncovers a language-like seed skeleton in MS 408 (`1A`, `2B`, `3B`) with positive held-out word-order gain ($D_1 > 0$) or sequential within-folio seed syntax, or whether the stripped MS 408 skeleton matches the no-plaintext `h47` `page_line_copier` generator.

## Predictions and Verdicts (`S1`–`S3`)

- Overall verdict: **`mixed`**
- **S1 (de-padding uncovers positive word-order syntax):** **fail** (passing MS hands: `0/3` []). Stripping one-edit echoes does not flip $D_1$ positive in any MS hand: on `local_W25`, `D1_seed` is `-0.2249` (`1A`), `-0.2325` (`2B`), and `-0.2402` (`3B`); on `folio_comp`, `D1_seed` is `-0.2133` (`1A`), `-0.1534` (`2B`), and `-0.1243` (`3B`).
- **S2 (sequential order among seeds inside a folio):** **pass** (passing MS hands: `2/3` ['1A', '2B']). On `folio_comp`, adjacent top-50 stem bigram MI exceeds the 95th percentile (`mi_adj_z > 1.96`) of 100 within-folio seed permutations in `2/3` hands (`1A`: `z = +2.29`, `2B`: `z = +2.00`, `3B`: `z = +1.26`; on `local_W25`: `z = +2.72`, `+2.24`, `+3.59`). However, the no-plaintext `page_line_copier_2B` also reaches `z = +2.15` on `folio_comp` from line-initial/final character-state bias, whereas plain Italian prose (`it_boccaccio`) reaches `z = +11.70` on `local_W25` and `z = +3.91` on `folio_comp`.
- **S3 (MS seed skeleton vs `h47` no-plaintext skeleton):** **pass** (passing MS hands: `3/3` ['1A', '2B', '3B']). Across all three hands (`1A`, `2B`, `3B`), the `local_W25` retention rate (`keep_rate`), word-order gain (`D1_seed`), and Bayesian piece inventory (`morphs_per_type`) of MS 408 lie within $\pm 0.08$ of the no-plaintext `page_line_copier` generator.

## S3 Comparison: MS 408 vs `page_line_copier` on `local_W25` ($\pm 0.08$ equivalence band)

| hand | MS_keep | PLC_keep | diff_keep | MS_D1 | PLC_D1 | diff_D1 | MS_morphs | PLC_morphs | diff_morphs | within_0.08 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1A | 0.5195 | 0.5688 | 0.0493 | -0.2249 | -0.2439 | 0.0190 | 0.2853 | 0.2920 | 0.0067 | pass |
| 2B | 0.4495 | 0.5222 | 0.0727 | -0.2325 | -0.2523 | 0.0198 | 0.2966 | 0.2853 | 0.0113 | pass |
| 3B | 0.5463 | 0.5656 | 0.0193 | -0.2402 | -0.2407 | 0.0005 | 0.2776 | 0.2822 | 0.0047 | pass |

## Measures 1–3: Retention Rate (`keep_rate`), Word-Order Gain (`D1_seed`, `mi_adj_z`), and Piece Inventory (`morphs_per_type`)

| stream | mode | n_tokens | n_types | keep_rate | D1_seed | mi_adj_excess | mi_adj_z | morphs_per_type | morphs_affix |
|---|---|---|---|---|---|---|---|---|---|
| MS_1A | raw | 10326 | 2864 | 1.0000 | -0.1775 | 0.0616 | 12.4700 | 0.2615 | 0.3600 |
| MS_1A | local_W25 | 5364 | 2608 | 0.5195 | -0.2249 | 0.0209 | 2.7200 | 0.2853 | 0.3854 |
| MS_1A | folio_comp | 4290 | 2428 | 0.4155 | -0.2133 | 0.0146 | 2.2900 | 0.3007 | 0.3933 |
| page_line_copier_1A | raw | 10326 | 2623 | 1.0000 | -0.2504 | 0.0054 | 1.4000 | 0.2856 | 0.3546 |
| page_line_copier_1A | local_W25 | 5873 | 2514 | 0.5688 | -0.2439 | 0.0069 | 1.1200 | 0.2920 | 0.3254 |
| page_line_copier_1A | folio_comp | 4755 | 2399 | 0.4605 | -0.2199 | -0.0041 | -0.5300 | 0.3055 | 0.3610 |
| MS_2B | raw | 10494 | 2318 | 1.0000 | -0.1351 | 0.1140 | 23.2100 | 0.2783 | 0.4758 |
| MS_2B | local_W25 | 4717 | 2104 | 0.4495 | -0.2325 | 0.0210 | 2.2400 | 0.2966 | 0.4634 |
| MS_2B | folio_comp | 2550 | 1718 | 0.2430 | -0.1534 | 0.0215 | 2.0000 | 0.3516 | 0.4831 |
| page_line_copier_2B | raw | 10494 | 2432 | 1.0000 | -0.2565 | 0.0168 | 3.6800 | 0.2784 | 0.5826 |
| page_line_copier_2B | local_W25 | 5480 | 2317 | 0.5222 | -0.2523 | 0.0018 | 0.2500 | 0.2853 | 0.5744 |
| page_line_copier_2B | folio_comp | 3143 | 2000 | 0.2995 | -0.1806 | 0.0236 | 2.1500 | 0.3255 | 0.6000 |
| MS_3B | raw | 10493 | 2956 | 1.0000 | -0.1712 | 0.1224 | 27.8700 | 0.2585 | 0.4418 |
| MS_3B | local_W25 | 5732 | 2749 | 0.5463 | -0.2402 | 0.0258 | 3.5900 | 0.2776 | 0.4434 |
| MS_3B | folio_comp | 2578 | 2026 | 0.2457 | -0.1243 | 0.0111 | 1.2600 | 0.3603 | 0.5118 |
| page_line_copier_3B | raw | 10493 | 2741 | 1.0000 | -0.2570 | 0.0132 | 3.0900 | 0.2718 | 0.4436 |
| page_line_copier_3B | local_W25 | 5935 | 2615 | 0.5656 | -0.2407 | -0.0147 | -2.3700 | 0.2822 | 0.4497 |
| page_line_copier_3B | folio_comp | 2938 | 2118 | 0.2800 | -0.1567 | 0.0198 | 1.8700 | 0.3385 | 0.5236 |
| naibbe_boccaccio_swap | raw | 10494 | 3305 | 1.0000 | -0.2034 | 0.0440 | 10.0600 | 0.0980 | 0.3846 |
| naibbe_boccaccio_swap | local_W25 | 6823 | 2876 | 0.6502 | -0.2502 | 0.0249 | 3.9200 | 0.0828 | 0.3800 |
| naibbe_boccaccio_swap | folio_comp | 4309 | 2507 | 0.4106 | -0.2279 | 0.0228 | 2.3700 | 0.0949 | 0.3410 |
| it_boccaccio | raw | 10494 | 2555 | 1.0000 | 0.3996 | 0.2727 | 70.4600 | 0.5476 | 0.6888 |
| it_boccaccio | local_W25 | 6969 | 2532 | 0.6641 | 0.0317 | 0.0549 | 11.7000 | 0.5494 | 0.6805 |
| it_boccaccio | folio_comp | 4987 | 2430 | 0.4752 | -0.0839 | 0.0215 | 3.9100 | 0.5724 | 0.6909 |

## Measure 4: Cross-Folio Seed Continuity (`adj_folio_cos` and 1-Edit Overlap vs 200 Within-Quire Permutations)

| stream | mode | adj_folio_cos | cos_null_mean | cos_z | edit1_overlap | edit1_null_mean | edit1_z |
|---|---|---|---|---|---|---|---|
| MS_1A | raw | 0.3546 | 0.3230 | 4.6600 | 0.6371 | 0.6262 | 2.6600 |
| MS_1A | local_W25 | 0.0837 | 0.0741 | 2.8100 | 0.4190 | 0.4060 | 2.6900 |
| MS_1A | folio_comp | 0.0502 | 0.0456 | 1.7400 | 0.3380 | 0.3278 | 2.0800 |
| page_line_copier_1A | raw | 0.2166 | 0.2170 | -0.0800 | 0.6055 | 0.5972 | 2.5500 |
| page_line_copier_1A | local_W25 | 0.0717 | 0.0739 | -0.7000 | 0.4036 | 0.3999 | 0.8600 |
| page_line_copier_1A | folio_comp | 0.0464 | 0.0478 | -0.5200 | 0.3244 | 0.3226 | 0.3900 |
| MS_2B | raw | 0.5357 | 0.5018 | 3.3900 | 0.7525 | 0.7447 | 1.9200 |
| MS_2B | local_W25 | 0.1708 | 0.1626 | 1.5400 | 0.5821 | 0.5733 | 1.5700 |
| MS_2B | folio_comp | 0.0501 | 0.0527 | -0.6600 | 0.3611 | 0.3575 | 0.5200 |
| page_line_copier_2B | raw | 0.3441 | 0.3470 | -0.4900 | 0.7200 | 0.7159 | 1.1300 |
| page_line_copier_2B | local_W25 | 0.1681 | 0.1677 | 0.0900 | 0.5567 | 0.5531 | 0.7400 |
| page_line_copier_2B | folio_comp | 0.0487 | 0.0518 | -0.8500 | 0.3463 | 0.3463 | 0.0100 |
| MS_3B | raw | 0.5195 | 0.4570 | 4.3600 | 0.7452 | 0.7346 | 2.5100 |
| MS_3B | local_W25 | 0.1986 | 0.1779 | 3.6400 | 0.6260 | 0.6105 | 2.8300 |
| MS_3B | folio_comp | 0.0384 | 0.0357 | 0.7400 | 0.3174 | 0.3068 | 1.6700 |
| page_line_copier_3B | raw | 0.3468 | 0.3498 | -0.4000 | 0.7175 | 0.7134 | 1.2300 |
| page_line_copier_3B | local_W25 | 0.2167 | 0.2060 | 1.8400 | 0.5899 | 0.5824 | 1.5300 |
| page_line_copier_3B | folio_comp | 0.0508 | 0.0471 | 0.9600 | 0.3246 | 0.3207 | 0.6200 |
| naibbe_boccaccio_swap | raw | 0.4461 | 0.4347 | 1.7800 | 0.6078 | 0.6019 | 1.4200 |
| naibbe_boccaccio_swap | local_W25 | 0.1819 | 0.1823 | -0.0900 | 0.5124 | 0.5041 | 1.4800 |
| naibbe_boccaccio_swap | folio_comp | 0.0544 | 0.0570 | -0.8300 | 0.3419 | 0.3405 | 0.2400 |
| it_boccaccio | raw | 0.5722 | 0.5431 | 3.5100 | 0.4429 | 0.4187 | 5.7100 |
| it_boccaccio | local_W25 | 0.2856 | 0.2591 | 4.0300 | 0.3516 | 0.3257 | 5.1800 |
| it_boccaccio | folio_comp | 0.1371 | 0.1211 | 4.2900 | 0.2792 | 0.2559 | 4.9300 |

## Key Findings (Distributional Only, No Translation Claims)

1. **De-padding same-folio one-edit echoes removes 45%–55% of MS tokens locally (`local_W25`) and 58%–76% whole-folio (`folio_comp`), but leaves $D_1$ strictly negative (`S1` falsified):** If negative raw $D_1$ in MS 408 (`-0.1775`, `-0.1351`, `-0.1712`) were caused by local one-edit padding echoes interrupting an ordered seed text, removing those echoes would move $D_1$ positive. Instead, `local_W25` pushes $D_1$ slightly more negative (`-0.2249`, `-0.2325`, `-0.2402`), matching `page_line_copier` (`-0.2439`, `-0.2523`, `-0.2407` within $0.020$ bits/word).
2. **Within-folio adjacent stem MI drops by ~90% once local echoes are stripped (`S2` marginally passes in 2/3 hands):** In raw MS 408, adjacent stem MI is strongly elevated (`mi_adj_z = +12.47`, `+23.21`, `+27.87`) because of within-line character-junction rules and short-lag near-repeats. Stripping same-folio one-edit components (`folio_comp`) reduces `mi_adj_z` to `+2.29` (`1A`), `+2.00` (`2B`), and `+1.26` (`3B`), comparable to `page_line_copier_2B` (`+2.15`), whereas natural prose (`it_boccaccio`) retains strong sequential order (`mi_adj_z = +11.70` on `local_W25` and `+3.91` on `folio_comp`).
3. **The stripped MS seed skeleton is quantitatively indistinguishable from the no-plaintext `h47` generator (`S3` supported):** Across all three hands on `local_W25`, maximum absolute differences between MS and `page_line_copier` are `0.0727` on `keep_rate`, `0.0198` on `D1_seed`, and `0.0113` on `morphs_per_type` — all inside the preregistered $\pm 0.08$ tolerance.

## Reproduction

```bash
python3 -m pytest hypotheses/h49_seed_skeleton_extraction/test_h49.py -p no:cacheprovider
python3 hypotheses/h49_seed_skeleton_extraction/run_h49.py
python3 hypotheses/h49_seed_skeleton_extraction/summarise.py
```
