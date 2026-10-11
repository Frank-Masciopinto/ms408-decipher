# Descriptive statistics report

> **These are descriptive statistics, not decoding.** MS 408 is undeciphered. Nothing below assigns a meaning, a part of speech or a language to any glyph or word. Frequency, entropy, Zipf/Heaps and vowel/consonant-style numbers describe one transcription; meaningless text, hand-made gibberish and certain ciphers can reproduce several of them, and no control corpora have been run yet.

## Setup

* transcription: `ZL3b-n.txt` (alphabet `Eva-`, IVTFF 2.0); all numbers regenerate with `python -m msdecipher run-all`
* data: running paragraph text (`P` loci). Labels, circular/radial text, extraneous writing (`Lx`) and non-existent loci (`!`) are excluded. Tokens containing `?` (unreadable) are dropped from word/unit statistics.
* alternative readings `[a:b]`: first (most likely) option; ligature braces removed; rare `@nnn;` codes are single units.
* uncertain spaces (`,`): **treated as word spaces**; the table also shows the opposite choice.
* unit segmentation: `collapsed` = ['cfh', 'ckh', 'cph', 'cth', 'ch', 'sh'] (all other EVA characters are single units); seed 1.
* a 'token' is a blank-delimited chunk of the transcription and is **not** proven to be a word; a 'unit' is not proven to be a letter.

## Summary table

| metric | P (all running text) | Currier A | Currier B | A matched (~11300 tok) | B matched (~11300 tok) | P, uncertain spaces joined |
|---|---|---|---|---|---|---|
| n_tokens | 34977 | 11300 | 23128 | 11300 | 1.13e+04 | 32514 |
| n_types | 7171 | 3298 | 4849 | 3298 | 2974 | 8126 |
| type_token_ratio | 0.205 | 0.2919 | 0.2097 | 0.2919 | 0.2632 | 0.2499 |
| hapax_share_of_types | 0.6868 | 0.6962 | 0.6834 | 0.6962 | 0.692 | 0.7198 |
| top10_token_coverage | 0.127 | 0.1604 | 0.1466 | 0.1604 | 0.1471 | 0.1139 |
| mean_word_length_units | 4.466 | 4.156 | 4.62 | 4.156 | 4.622 | 4.803 |
| zipf_ols_slope_r10_1000 | -1.102 | -0.9969 | -1.127 | -0.9969 | -1.113 | -1.063 |
| zipf_mle_s_r10_1000 | 0.9846 | 0.9433 | 1.021 | 0.9433 | 1.005 | 0.9574 |
| heaps_beta_in_order | 0.7447 | 0.7519 | 0.7491 | 0.7519 | 0.7548 | 0.7712 |
| heaps_beta_shuffled | 0.7469 | 0.7742 | 0.7369 | 0.7742 | 0.7459 | 0.7751 |
| word_entropy_H1 | 10.24 | 9.784 | 9.81 | 9.784 | 9.604 | 10.62 |
| unit_alphabet_size | 101 | 81 | 59 | 81 | 48.5 | 101 |
| unit_alphabet_size_ge20 | 27 | 26 | 27 | 26 | 24.33 | 27 |
| unit_H1 | 3.901 | 3.94 | 3.859 | 3.94 | 3.858 | 3.901 |
| unit_h2 | 2.217 | 2.321 | 2.048 | 2.321 | 2.046 | 2.239 |
| unit_h3 | 1.954 | 2.019 | 1.801 | 2.019 | 1.784 | 1.982 |
| unit_h2_mm | 2.22 | 2.328 | 2.051 | 2.328 | 2.051 | 2.241 |
| unit_h2_with_word_boundaries | 2.246 | 2.343 | 2.098 | 2.343 | 2.096 | 2.264 |
| unit_h2_within_word_shuffle | 3.564 | 3.555 | 3.506 | 3.555 | 3.5 | 3.605 |

Definitions: **Zipf OLS slope** = slope of log10(freq) vs log10(rank), ranks 10–1000 (negative; quick look only). **Zipf MLE s** = maximum-likelihood exponent of a rank-truncated Zipf law on the same ranks (positive). **Heaps β** = exponent of V(n)=K·nᵝ (vocabulary growth) in manuscript order and averaged over random token orders. **H1** = unit entropy (bits); **h2**/**h3** = conditional entropy of a unit given the previous 1/2 units *inside the same token*; `_mm` = Miller–Madow bias-corrected; `with_word_boundaries` adds start/end markers; `within_word_shuffle` shuffles units inside each token (a within-token order control: h2 rises toward H1 when order matters). `A matched`/`B matched` are the two Currier subsets cut to the same token count. `unit_alphabet_size` counts every distinct unit including rare `@nnn;` codes; `_ge20` counts units seen at least 20 times.

Entropy values are plug-in estimates on a finite sample and are biased low, more so for h3 (large alphabet²) than h2. They are comparable only between equally sized samples and only under the same segmentation.

## Currier A vs B

114 pages are tagged language A and 83 B in the transcription's `$L` variable. Jensen–Shannon divergence between the A and B unit distributions is 0.0196 bits (page-label permutation null mean 0.0012, p = 0.003, 300 permutations); between word distributions 0.4709 (null mean 0.2076, p = 0.003). The permutation shuffles A/B labels across pages, so it asks whether A/B differ more than arbitrary page groupings do. Note that Currier's A/B split was originally made from these same texts, so this is a consistency check, not an independent test.

Tokens most over-represented in **A** (log2 ratio B/A most negative; ≥20 tokens total):

| word | count_A | count_B | log2_ratio_B_over_A |
|---|---|---|---|
| otchol | 28 | 1 | -5.281 |
| cthor | 41 | 2 | -5.086 |
| dchy | 24 | 1 | -5.063 |
| dchor | 23 | 1 | -5.003 |
| cthol | 52 | 3 | -4.940 |
| cthy | 94 | 6 | -4.895 |
| kchor | 19 | 1 | -4.734 |
| ckhol | 19 | 1 | -4.734 |

Tokens most over-represented in **B**:

| word | count_A | count_B | log2_ratio_B_over_A |
|---|---|---|---|
| qoteedy | 0 | 76 | 6.224 |
| shedy | 2 | 421 | 6.364 |
| qotedy | 0 | 87 | 6.418 |
| qokedy | 1 | 275 | 6.488 |
| okedy | 0 | 109 | 6.742 |
| otedy | 0 | 140 | 7.101 |
| chedy | 1 | 491 | 7.323 |
| qokeedy | 0 | 307 | 8.231 |

Per-unit and per-word tables: `currier_ab_units.csv`, `currier_ab_words.csv`.

## Sukhotin vowel/consonant test (run after segmentation)

Sukhotin's algorithm labels a unit 'vowel-like' if it tends to sit next to units that are not vowel-like, using adjacent pairs inside tokens. **It is a distributional proposal, not a finding that these glyphs are vowels.** Units with <20 occurrences are ignored. The table contrasts segmentations on the same text: with raw EVA, `h` is an artefact of splitting `ch`/`sh`, which is why segmentation comes first.

| subset | segmentation | vowel-like units (pick order) |
|---|---|---|
| P | raw | `o`, `h`, `a`, `y`, `n`, `g` |
| P | basic | `o`, `a`, `e`, `y`, `n`, `c`, `h` |
| P | collapsed | `o`, `a`, `e`, `y`, `n`, `c` |
| P | extended | `o`, `a`, `y`, `e`, `ee`, `c`, `i` |
| A | raw | `o`, `h`, `a`, `y`, `n`, `g` |
| A | basic | `o`, `a`, `y`, `n`, `c`, `h`, `g` |
| A | collapsed | `o`, `a`, `y`, `n`, `e`, `c`, `g` |
| A | extended | `o`, `a`, `y`, `e`, `ee`, `c`, `g` |
| B | raw | `o`, `h`, `a`, `y`, `n`, `f`, `'` |
| B | basic | `o`, `e`, `a`, `y`, `n`, `c`, `h` |
| B | collapsed | `o`, `e`, `a`, `y`, `n`, `c`, `'` |
| B | extended | `o`, `a`, `e`, `y`, `ee`, `c`, `i`, `h` |

Stability under page bootstrap (200 resamples of pages), default segmentation `collapsed`, all `P` text (fraction of resamples in which the unit is labelled vowel-like; values far from 0 or 1 mean the label is unstable):

| unit | count | sukhotin_class | bootstrap_vowel_fraction |
|---|---|---|---|
| o | 22396 | vowel-like | 1.000 |
| e | 18129 | vowel-like | 1.000 |
| y | 16147 | vowel-like | 1.000 |
| a | 12902 | vowel-like | 1.000 |
| d | 11881 | consonant-like | 0.000 |
| i | 11075 | consonant-like | 0.000 |
| ch | 10159 | consonant-like | 0.000 |
| l | 9500 | consonant-like | 0.000 |
| k | 9209 | consonant-like | 0.000 |
| r | 6562 | consonant-like | 0.000 |
| n | 5814 | vowel-like | 1.000 |
| q | 5349 | consonant-like | 0.000 |
| t | 5149 | consonant-like | 0.000 |
| sh | 4257 | consonant-like | 0.000 |
| s | 2265 | consonant-like | 0.000 |
| p | 1300 | consonant-like | 0.000 |
| m | 937 | consonant-like | 0.000 |
| cth | 884 | consonant-like | 0.000 |
| ckh | 863 | consonant-like | 0.000 |
| f | 354 | consonant-like | 0.000 |
| h | 256 | consonant-like | 0.070 |
| cph | 198 | consonant-like | 0.000 |
| c | 154 | vowel-like | 1.000 |
| g | 121 | consonant-like | 0.100 |
| ' | 86 | consonant-like | 0.095 |
| cfh | 66 | consonant-like | 0.000 |
| x | 22 | consonant-like | 0.040 |

## Replication on other transcriptions

| file | subset | n_tokens | n_types | zipf_ols_slope | zipf_mle_s | heaps_beta_in_order | heaps_beta_shuffled | word_entropy | unit_H1 | unit_h2 | unit_h3 | alphabet_size_ge20 | sukhotin_vowel_like |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ZL3b-n.txt | P | 34977 | 7171 | -1.102 | 0.985 | 0.745 | 0.747 | 10.243 | 3.901 | 2.217 | 1.954 | 27 | o a e y n c |
| ZL3b-n.txt | A | 11300 | 3298 | -0.997 | 0.943 | 0.752 | 0.774 | 9.784 | 3.940 | 2.321 | 2.019 | 26 | o a y n e c g |
| ZL3b-n.txt | B | 23128 | 4849 | -1.127 | 1.021 | 0.749 | 0.737 | 9.810 | 3.859 | 2.048 | 1.801 | 27 | o e a y n c ' |
| IT2a-n.txt | P | 34411 | 7069 | -1.085 | 0.967 | 0.750 | 0.747 | 10.280 | 3.881 | 2.215 | 1.957 | 26 | o a e y n c |
| IT2a-n.txt | A | 11081 | 3243 | -1.003 | 0.929 | 0.756 | 0.771 | 9.790 | 3.898 | 2.303 | 2.018 | 25 | o a y n e c g |
| IT2a-n.txt | B | 22797 | 4813 | -1.109 | 1.006 | 0.736 | 0.741 | 9.854 | 3.850 | 2.056 | 1.808 | 26 | o e a y n c |
| RF1b-e.txt | P | 34625 | 8325 | -1.055 | 0.946 | 0.772 | 0.772 | 10.627 | 4.010 | 2.325 | 2.067 | 33 | o a e y n @221; @222; c ' |
| RF1b-e.txt | A | 11057 | 3617 | -0.966 | 0.915 | 0.775 | 0.791 | 10.032 | 4.011 | 2.382 | 2.072 | 29 | o a y n e @221; c @222; g |
| RF1b-e.txt | B | 23030 | 5681 | -1.086 | 0.982 | 0.766 | 0.761 | 10.224 | 3.983 | 2.175 | 1.932 | 32 | o e a y n @221; @222; ' c |

An effect seen in only one transcription should be treated as a transcription artefact until shown otherwise.

## Figures

* `figures/zipf_words.png` – rank–frequency of tokens (log–log) with the fitted range
* `figures/heaps.png` – vocabulary growth, manuscript order vs shuffled
* `figures/unit_frequencies_ab.png` – unit shares, Currier A vs B
* `figures/positional_heatmap.png` – where each unit occurs inside tokens and lines
* `figures/entropies.png` – H1, h2, h3 and the within-token-shuffle control

## Not done / limits

* No control corpora (Latin, Italian, Hebrew, shuffled text, cipher or gibberish generators) have been run, so none of these numbers can yet say whether MS 408 resembles a language, a cipher or neither.
* Statistics are pooled over pages that are not independent samples; confidence intervals over quires are not yet computed (only the page bootstrap above).
* Only EVA-based transcriptions were analysed (`GC2a` uses another alphabet and is parse-tested only).
* No word-class, morphology or semantic analysis is attempted or implied.
