# h51: do diagram/plant/nymph labels match the de-padded seed stems of their folio or quire?

Pre-registration: [PREREG.md](PREREG.md). Tests whether standalone diagram, jar, plant-part, nymph, and astrological labels (`L` loci with $\ge 2$ collapsed EVA units on folios with $\ge 20$ paragraph tokens) match the de-padded seed stems (`seed_W25`, `h49`) or paragraph-opening headers (`header_tokens`, `h50`) of their own folio or paired herbal folio once matching is relaxed from exact word identity to one-edit (`edit1_hit`) and prefix-stripped 3-unit stem (`stem_hit`) similarity.

## Predictions

- **L1 (own-folio label $\leftrightarrow$ seed link):** **fail** (on `seed_W25` across $n = 428$ label words on 30 folios in 4 quires, `exact_hit` $= 0.0771$ vs within-quire null $0.0681$, $p = 0.1979$; `edit1_hit` $= 0.3364$ vs $0.3215$, $p = 0.1529$; `stem_hit` $= 0.3294$ vs $0.3267$, $p = 0.4563$; minimum Holm-adjusted $p = 0.4588 \ge 0.05$. On the 399 longest-word-per-locus table `h09_lib.label_table().w`, minimum Holm-adjusted $p = 0.3088$).
- **L2 (de-padded same-plant pairs):** **fail** (matching pharmaceutical labels to the de-padded `seed_W25` of their paired herbal folio across the 16 herbal–pharma pairs gives mean rank percentile $0.5356$, $p = 0.2489$ for `edit1_hit`; $0.5830$, $p = 0.1079$ for `stem_hit`; and $0.5906$, $p = 0.0890$ for `edit1_or_stem` — all below the $> 0.65$ and $p < 0.05$ threshold. On the 12 ZL3b-only pairs, `edit1_or_stem` on `seed_W25` reaches mean rank percentile $0.6188$, $p = 0.0640$, also below $0.65$).
- **L3 (label-linked seeds spawn larger paragraph clusters):** **pass** (across $2,670$ `seed_W25` tokens on the 30 label+paragraph folios, the $362$ label-linked seeds have mean same-folio one-edit progeny size $6.9972$ vs $5.3423$ for the $2,308$ unlinked seeds, difference $+1.6549$, vs length-matched within-folio permutation null $+0.5059 \pm 0.2900$, $z = 3.96$, $p = 0.0005 < 0.05$. Diagnostic: swapping label sets across folios within the same quire produces a null mean difference of $+0.9509 \pm 0.4705$, $p = 0.0675$, showing that most of the progeny excess comes from labels being short, high-centrality EVA stems rather than folio-specific seeding).

## Test 1: Own-folio label $\leftrightarrow$ paragraph/seed enrichment (`own_folio`)

Evaluated over $428$ label tokens ($\ge 2$ collapsed EVA units) across $30$ folios with $\ge 20$ paragraph tokens ($4$ quires: Q9, Q13, Q15, Q19; 2,000 permutations, seed 51). `wq_null` permutes label folio assignments within the same quire (`h09_lib.perm_within(quire)`); `ql_null` permutes labels of the same unit length within the same quire evaluated on the same folio; `rand_w_null` samples length-matched random word types from the global manuscript vocabulary evaluated on the same folio.

| rep | hit_type | obs_hits | n_labels | obs_rate | wq_null | wq_z | p_wq | p_holm | ql_null | p_ql | rand_w_null | p_rand_w |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| seed_W25 | exact_hit | 33 | 428 | 0.0771 | 0.0681 | 1.0000 | 0.1979 | 0.4588 | 0.0737 | 0.3933 | 0.0124 | 0.0005 |
| seed_W25 | edit1_hit | 144 | 428 | 0.3364 | 0.3215 | 1.1400 | 0.1529 | 0.4588 | 0.3258 | 0.2189 | 0.2035 | 0.0005 |
| seed_W25 | stem_hit | 141 | 428 | 0.3294 | 0.3267 | 0.1800 | 0.4563 | 0.4588 | 0.3339 | 0.6502 | 0.2256 | 0.0005 |
| full_para | exact_hit | 48 | 428 | 0.1121 | 0.0992 | 1.3700 | 0.1039 | 0.2324 | 0.1041 | 0.2149 | 0.0183 | 0.0005 |
| full_para | edit1_hit | 163 | 428 | 0.3808 | 0.3641 | 1.3500 | 0.1014 | 0.2324 | 0.3691 | 0.1929 | 0.2569 | 0.0005 |
| full_para | stem_hit | 173 | 428 | 0.4042 | 0.3814 | 1.4700 | 0.0775 | 0.2324 | 0.3868 | 0.1384 | 0.2624 | 0.0005 |
| header_tokens_raw | exact_hit | 15 | 428 | 0.0350 | 0.0268 | 1.3600 | 0.1184 | 0.2369 | 0.0336 | 0.4783 | 0.0046 | 0.0005 |
| header_tokens_raw | edit1_hit | 85 | 428 | 0.1986 | 0.1724 | 1.9800 | 0.0275 | 0.0825 | 0.1898 | 0.2439 | 0.0947 | 0.0005 |
| header_tokens_raw | stem_hit | 74 | 428 | 0.1729 | 0.1592 | 0.9800 | 0.1899 | 0.2369 | 0.1620 | 0.2274 | 0.0974 | 0.0005 |
| header_tokens_stripped | exact_hit | 16 | 428 | 0.0374 | 0.0253 | 1.9600 | 0.0375 | 0.1124 | 0.0325 | 0.2804 | 0.0043 | 0.0005 |
| header_tokens_stripped | edit1_hit | 84 | 428 | 0.1963 | 0.1726 | 1.8200 | 0.0435 | 0.1124 | 0.1904 | 0.3323 | 0.0958 | 0.0005 |
| header_tokens_stripped | stem_hit | 65 | 428 | 0.1519 | 0.1362 | 1.2100 | 0.1384 | 0.1384 | 0.1449 | 0.3228 | 0.0959 | 0.0005 |
| header_tokens | exact_hit | 17 | 428 | 0.0397 | 0.0308 | 1.3200 | 0.1284 | 0.1559 | 0.0387 | 0.5012 | 0.0054 | 0.0005 |
| header_tokens | edit1_hit | 92 | 428 | 0.2150 | 0.1903 | 1.8400 | 0.0420 | 0.1259 | 0.2080 | 0.3018 | 0.1068 | 0.0005 |
| header_tokens | stem_hit | 83 | 428 | 0.1939 | 0.1721 | 1.5500 | 0.0780 | 0.1559 | 0.1803 | 0.1649 | 0.1093 | 0.0005 |

## Test 2: De-padded herbal $\leftrightarrow$ pharmaceutical same-plant pairs (`same_plant_seeds`)

Evaluated across $128$ herbal folios with $\ge 20$ paragraph tokens (2,000 random partner permutations, seed 51) for both the 16-pair set (12 ZL3b header pairs with pharmaceutical labels + 4 `h17` extra pairs) and the 12-pair ZL3b-only subset.

| pair_set | rep | hit_mode | pool | n_pairs | mean_hit_frac | null_hit_frac | mean_rank_pct | null_rank_pct | p_rank_pct |
|---|---|---|---|---|---|---|---|---|---|
| 16_pairs | seed_W25 | exact_hit | all_herbal | 16 | 0.0094 | 0.0124 | 0.4758 | 0.5007 | 0.7056 |
| 16_pairs | seed_W25 | exact_hit | within_hand | 16 | 0.0094 | 0.0144 | 0.4552 | 0.4994 | 0.8366 |
| 16_pairs | seed_W25 | edit1_hit | all_herbal | 16 | 0.1021 | 0.0948 | 0.5356 | 0.4987 | 0.2489 |
| 16_pairs | seed_W25 | edit1_hit | within_hand | 16 | 0.1021 | 0.0971 | 0.5212 | 0.4980 | 0.3323 |
| 16_pairs | seed_W25 | stem_hit | all_herbal | 16 | 0.1691 | 0.1481 | 0.5830 | 0.4998 | 0.1079 |
| 16_pairs | seed_W25 | stem_hit | within_hand | 16 | 0.1691 | 0.1517 | 0.5739 | 0.5011 | 0.1319 |
| 16_pairs | seed_W25 | edit1_or_stem | all_herbal | 16 | 0.2317 | 0.2065 | 0.5906 | 0.4996 | 0.0890 |
| 16_pairs | seed_W25 | edit1_or_stem | within_hand | 16 | 0.2317 | 0.2105 | 0.5683 | 0.4997 | 0.1554 |
| 16_pairs | full_para | exact_hit | all_herbal | 16 | 0.0209 | 0.0240 | 0.4878 | 0.4987 | 0.5957 |
| 16_pairs | full_para | exact_hit | within_hand | 16 | 0.0209 | 0.0260 | 0.4636 | 0.4999 | 0.7716 |
| 16_pairs | full_para | edit1_hit | all_herbal | 16 | 0.1251 | 0.1189 | 0.5437 | 0.4980 | 0.1864 |
| 16_pairs | full_para | edit1_hit | within_hand | 16 | 0.1251 | 0.1203 | 0.5234 | 0.4976 | 0.3168 |
| 16_pairs | full_para | stem_hit | all_herbal | 16 | 0.2582 | 0.1942 | 0.6250 | 0.4986 | 0.0260 |
| 16_pairs | full_para | stem_hit | within_hand | 16 | 0.2582 | 0.2042 | 0.6063 | 0.5002 | 0.0570 |
| 16_pairs | full_para | edit1_or_stem | all_herbal | 16 | 0.3240 | 0.2567 | 0.6362 | 0.4991 | 0.0215 |
| 16_pairs | full_para | edit1_or_stem | within_hand | 16 | 0.3240 | 0.2628 | 0.6367 | 0.4994 | 0.0185 |
| 16_pairs | header_tokens | exact_hit | all_herbal | 16 | 0.0047 | 0.0051 | 0.5034 | 0.4982 | 0.4693 |
| 16_pairs | header_tokens | exact_hit | within_hand | 16 | 0.0047 | 0.0070 | 0.4797 | 0.4985 | 0.7231 |
| 16_pairs | header_tokens | edit1_hit | all_herbal | 16 | 0.0354 | 0.0417 | 0.4834 | 0.5000 | 0.6202 |
| 16_pairs | header_tokens | edit1_hit | within_hand | 16 | 0.0354 | 0.0413 | 0.4812 | 0.5005 | 0.6522 |
| 16_pairs | header_tokens | stem_hit | all_herbal | 16 | 0.0938 | 0.0516 | 0.5854 | 0.5016 | 0.0780 |
| 16_pairs | header_tokens | stem_hit | within_hand | 16 | 0.0938 | 0.0619 | 0.5492 | 0.5018 | 0.2119 |
| 16_pairs | header_tokens | edit1_or_stem | all_herbal | 16 | 0.1206 | 0.0809 | 0.6057 | 0.5015 | 0.0495 |
| 16_pairs | header_tokens | edit1_or_stem | within_hand | 16 | 0.1206 | 0.0883 | 0.5806 | 0.5017 | 0.0980 |
| zl3b_12_pairs | seed_W25 | exact_hit | all_herbal | 12 | 0.0099 | 0.0087 | 0.5120 | 0.5015 | 0.4188 |
| zl3b_12_pairs | seed_W25 | exact_hit | within_hand | 12 | 0.0099 | 0.0101 | 0.4991 | 0.5005 | 0.5012 |
| zl3b_12_pairs | seed_W25 | edit1_hit | all_herbal | 12 | 0.0931 | 0.0751 | 0.5869 | 0.5001 | 0.0520 |
| zl3b_12_pairs | seed_W25 | edit1_hit | within_hand | 12 | 0.0931 | 0.0759 | 0.5850 | 0.4985 | 0.0595 |
| zl3b_12_pairs | seed_W25 | stem_hit | all_herbal | 12 | 0.1594 | 0.1396 | 0.5977 | 0.5018 | 0.1024 |
| zl3b_12_pairs | seed_W25 | stem_hit | within_hand | 12 | 0.1594 | 0.1362 | 0.6141 | 0.5004 | 0.0700 |
| zl3b_12_pairs | seed_W25 | edit1_or_stem | all_herbal | 12 | 0.2138 | 0.1854 | 0.6188 | 0.5016 | 0.0640 |
| zl3b_12_pairs | seed_W25 | edit1_or_stem | within_hand | 12 | 0.2138 | 0.1822 | 0.6197 | 0.4990 | 0.0595 |
| zl3b_12_pairs | full_para | exact_hit | all_herbal | 12 | 0.0136 | 0.0155 | 0.5078 | 0.5013 | 0.4373 |
| zl3b_12_pairs | full_para | exact_hit | within_hand | 12 | 0.0136 | 0.0147 | 0.5011 | 0.5001 | 0.5107 |
| zl3b_12_pairs | full_para | edit1_hit | all_herbal | 12 | 0.1019 | 0.0936 | 0.5508 | 0.4994 | 0.1864 |
| zl3b_12_pairs | full_para | edit1_hit | within_hand | 12 | 0.1019 | 0.0920 | 0.5442 | 0.4990 | 0.2119 |
| zl3b_12_pairs | full_para | stem_hit | all_herbal | 12 | 0.2525 | 0.1800 | 0.6530 | 0.4998 | 0.0255 |
| zl3b_12_pairs | full_para | stem_hit | within_hand | 12 | 0.2525 | 0.1833 | 0.6452 | 0.5010 | 0.0350 |
| zl3b_12_pairs | full_para | edit1_or_stem | all_herbal | 12 | 0.3048 | 0.2310 | 0.6598 | 0.5002 | 0.0185 |
| zl3b_12_pairs | full_para | edit1_or_stem | within_hand | 12 | 0.3048 | 0.2299 | 0.6665 | 0.5003 | 0.0180 |
| zl3b_12_pairs | header_tokens | exact_hit | all_herbal | 12 | 0.0000 | 0.0027 | 0.4733 | 0.5011 | 1.0000 |
| zl3b_12_pairs | header_tokens | exact_hit | within_hand | 12 | 0.0000 | 0.0036 | 0.4629 | 0.4996 | 1.0000 |
| zl3b_12_pairs | header_tokens | edit1_hit | all_herbal | 12 | 0.0218 | 0.0311 | 0.4655 | 0.5020 | 0.7471 |
| zl3b_12_pairs | header_tokens | edit1_hit | within_hand | 12 | 0.0218 | 0.0271 | 0.4798 | 0.4996 | 0.6402 |
| zl3b_12_pairs | header_tokens | stem_hit | all_herbal | 12 | 0.1001 | 0.0451 | 0.6042 | 0.5004 | 0.0585 |
| zl3b_12_pairs | header_tokens | stem_hit | within_hand | 12 | 0.1001 | 0.0537 | 0.5745 | 0.5008 | 0.1289 |
| zl3b_12_pairs | header_tokens | edit1_or_stem | all_herbal | 12 | 0.1219 | 0.0677 | 0.6364 | 0.5023 | 0.0190 |
| zl3b_12_pairs | header_tokens | edit1_or_stem | within_hand | 12 | 0.1219 | 0.0712 | 0.6279 | 0.5007 | 0.0300 |

### Per-pair breakdown (`seed_W25`, `edit1_or_stem`, `all_herbal` pool)

| herbal | pharma | origin | n_labels | obs_hit_frac | pool_mean | rank_pct |
|---|---|---|---|---|---|---|
| f1v | f102r1 | zl3b | 4 | 0.2500 | 0.1035 | 0.7930 |
| f18v | f102r2 | zl3b | 4 | 0.0000 | 0.0957 | 0.3359 |
| f19r | f102v1 | zl3b | 8 | 0.1250 | 0.3125 | 0.2422 |
| f23r | f102r2 | zl3b | 4 | 0.2500 | 0.0957 | 0.8086 |
| f32v | f102r2 | zl3b | 4 | 0.0000 | 0.0957 | 0.3359 |
| f37v | f102r1 | zl3b | 4 | 0.2500 | 0.1035 | 0.7930 |
| f47v | f102r2 | zl3b | 4 | 0.0000 | 0.0957 | 0.3359 |
| f48r | f89v2 | zl3b | 15 | 0.4000 | 0.2740 | 0.8438 |
| f48v | f89v | zl3b | 23 | 0.3478 | 0.2415 | 0.8320 |
| f90v2 | f100r | zl3b | 19 | 0.3158 | 0.2278 | 0.8477 |
| f90v1 | f100r | zl3b | 19 | 0.2632 | 0.2278 | 0.6523 |
| f96v | f99r | zl3b | 33 | 0.3636 | 0.3393 | 0.6055 |
| f53r | f102r1 | h17_extra | 4 | 0.2500 | 0.1035 | 0.7930 |
| f55r | f99r | h17_extra | 33 | 0.4242 | 0.3393 | 0.7812 |
| f87r | f89r2 | h17_extra | 22 | 0.1818 | 0.3015 | 0.1523 |
| f90v1 | f99v | h17_extra | 28 | 0.2857 | 0.3474 | 0.2969 |

## Test 3: Label-seeded chain length on own folio (`chain_size`)

Partitioning the $2,670$ `seed_W25` tokens on the $30$ label+paragraph folios into label-linked vs unlinked seeds and counting same-folio body tokens within unit edit distance $\le 1$ (`progeny_size`; 2,000 within-folio length-matched and unstratified permutations, seed 51).

| link_mode | n_seeds | n_linked | n_unlinked | progeny_linked | progeny_unlinked | obs_diff | len_null_mean | len_z | p_folio_len | folio_null_mean | p_folio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| edit1_or_stem | 2670 | 362 | 2308 | 6.9972 | 5.3423 | 1.6549 | 0.5059 | 3.9600 | 0.0005 | 0.2512 | 0.0005 |
| edit1_only | 2670 | 233 | 2437 | 8.8712 | 5.2507 | 3.6205 | 1.6902 | 5.1600 | 0.0005 | 0.7716 | 0.0005 |
| stem_only | 2670 | 216 | 2454 | 5.6713 | 5.5575 | 0.1138 | -0.3908 | 1.4700 | 0.0830 | -0.2423 | 0.1844 |

## Key findings (distributional only, no translation claims)

1. **De-padding paragraph text into `seed_W25` stems does not reveal an own-folio label-to-seed link (`L1` fails):** On `seed_W25`, own-folio hit rates (`7.71%` exact, `33.64%` one-edit, `32.94%` 3-unit stem) are nearly identical to the within-quire null (`6.81%`, `32.15%`, `32.67%`; all Holm-adjusted $p = 0.4588$). Comparing against length-matched labels from the same quire on the same folio (`ql_null`) likewise gives $p \ge 0.2189$ across all three hit types and all paragraph representations.
2. **De-padding herbal folios does not rescue same-plant pharmaceutical label matching (`L2` fails):** Matching pharmaceutical jar/root labels to `seed_W25` of their paired herbal folio via `edit1_hit` or `stem_hit` yields mean rank percentiles of `0.5356`–`0.5906` ($p = 0.0890$–$0.3323$) across the 16 pairs and `0.5850`–`0.6197` ($p = 0.0520$–$0.1024$) across the 12 ZL3b pairs, never reaching the pre-registered $> 0.65$ threshold.
3. **Label-linked seeds have larger one-edit progeny (`L3` passes) because labels and prolific seeds share high-density EVA word shapes within a quire:** Seeds within unit edit distance $\le 1$ of an own-folio label average `8.87` one-edit body neighbours vs `5.25` for unlinked seeds ($p = 0.0005$ under within-folio length-matched permutation). However, a third of that gap (`+1.69` of `+3.62`) is already present in the length-matched null because shorter seeds have both higher label-hit probability and larger body neighbourhoods, and swapping label sets across folios within the same quire still produces a large progeny gap (`+0.95` vs $+1.65$ for `edit1_or_stem`, $p = 0.0675$). Thus labels and prolific paragraph stems are drawn from the same quire-level core EVA shapes rather than folio-specific label cribs seeding the page's paragraph text.

## Run

```bash
python3 -m pytest hypotheses/h51_label_to_seed_link/test_h51.py -p no:cacheprovider
python3 hypotheses/h51_label_to_seed_link/run_h51.py
python3 hypotheses/h51_label_to_seed_link/summarise.py
```
