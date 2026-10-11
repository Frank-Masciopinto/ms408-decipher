# Glyph catalogue (from the transcription)

> **These are descriptive statistics, not decoding.** MS 408 is undeciphered. Nothing below assigns a meaning, a part of speech or a language to any glyph or word. Frequency, entropy, Zipf/Heaps and vowel/consonant-style numbers describe one transcription; meaningless text, hand-made gibberish and certain ciphers can reproduce several of them, and no control corpora have been run yet.

Source: `ZL3b-n.txt` (alphabet `Eva-`, IVTFF 2.0). Counts are over running paragraph text (`P` loci) unless a column says otherwise; `all_loci` also includes labels, circular and radial text; `labels` is `L` loci only.

**This is a catalogue of symbols a *transcriber* used, not of physical glyph forms.** Whether the page images support the same classes is untested (image stage not done; see `docs/IMAGE_STAGE.md`).

* distinct EVA symbols: **27**; rare/high-ASCII codes (`@nnn;`): **85**
* total glyph tokens in `P` text: **175025**
* digraph/composite candidates are *flagged* in `digraph_candidates.csv` and `top_pmi_bigrams.csv`; merging is decided in `msdecipher.segment` (default preset: `collapsed`).

## Most frequent EVA symbols (P text)

| rank | glyph | count | share | initial | medial | final | line_initial_n |
|---|---|---|---|---|---|---|---|
| 1 | o | 22459 | 0.128 | 0.314 | 0.634 | 0.045 | 542 |
| 2 | e | 18165 | 0.104 | 0.005 | 0.990 | 0.004 | 2 |
| 3 | h | 16719 | 0.096 | 0.000 | 0.996 | 0.004 | 0 |
| 4 | y | 16172 | 0.092 | 0.092 | 0.026 | 0.866 | 604 |
| 5 | a | 12935 | 0.074 | 0.140 | 0.856 | 0.004 | 10 |
| 6 | c | 12353 | 0.071 | 0.528 | 0.472 | 0.000 | 156 |
| 7 | d | 11911 | 0.068 | 0.273 | 0.679 | 0.044 | 630 |
| 8 | i | 11106 | 0.063 | 0.002 | 0.998 | 0.001 | 0 |
| 9 | k | 10085 | 0.058 | 0.119 | 0.873 | 0.007 | 103 |
| 10 | l | 9517 | 0.054 | 0.131 | 0.297 | 0.555 | 69 |
| 11 | r | 6569 | 0.038 | 0.053 | 0.157 | 0.770 | 12 |
| 12 | s | 6542 | 0.037 | 0.604 | 0.223 | 0.125 | 609 |
| 13 | t | 6051 | 0.035 | 0.158 | 0.831 | 0.009 | 392 |
| 14 | n | 5830 | 0.033 | 0.000 | 0.011 | 0.988 | 0 |
| 15 | q | 5359 | 0.031 | 0.994 | 0.006 | 0.000 | 517 |
| 16 | p | 1501 | 0.009 | 0.352 | 0.628 | 0.018 | 377 |
| 17 | m | 939 | 0.005 | 0.001 | 0.031 | 0.962 | 0 |
| 18 | f | 421 | 0.002 | 0.255 | 0.702 | 0.040 | 33 |
| 19 | g | 122 | 0.001 | 0.017 | 0.041 | 0.843 | 0 |
| 20 | ' | 86 | 0.000 | 0.000 | 0.930 | 0.070 | 0 |
| 21 | x | 22 | 0.000 | 0.273 | 0.409 | 0.318 | 1 |
| 22 | b | 15 | 0.000 | 0.000 | 0.000 | 1.000 | 0 |
| 24 | j | 10 | 0.000 | 0.100 | 0.600 | 0.300 | 0 |
| 26 | u | 7 | 0.000 | 0.000 | 0.000 | 1.000 | 0 |
| 32 | z | 4 | 0.000 | 0.250 | 0.750 | 0.000 | 0 |

Positional columns are shares of occurrences at word start / middle / end (single-glyph words are excluded from these three).

## Digraph / composite candidates

| candidate | length | occurrences | p_next_given_first | p_prev_given_second | pmi_bits | observed_over_expected |
|---|---|---|---|---|---|---|
| ch | 2 | 10159 | 0.824 | 0.609 | 2.787 | 6.901 |
| sh | 2 | 4257 | 0.653 | 0.255 | 2.723 | 6.604 |
| cth | 3 | 884 | – | – | – | – |
| ckh | 3 | 863 | – | – | – | – |
| cph | 3 | 198 | – | – | – | – |
| cfh | 3 | 66 | – | – | – | – |
| ee | 2 | 4665 | 0.257 | 0.257 | 1.002 | 2.002 |
| ii | 2 | 4419 | 0.399 | 0.399 | 2.335 | 5.044 |
| iii | 3 | 175 | – | – | – | – |
| in | 2 | 5695 | 0.514 | 0.980 | 3.629 | 12.370 |
| iin | 3 | 4021 | – | – | – | – |
| iiin | 4 | 158 | – | – | – | – |
| ain | 3 | 1646 | – | – | – | – |
| aiin | 4 | 3678 | – | – | – | – |
| aiiin | 5 | 114 | – | – | – | – |
| ct | 2 | 924 | 0.075 | 0.153 | 1.046 | 2.065 |
| ck | 2 | 895 | 0.073 | 0.089 | 0.194 | 1.144 |
| cp | 2 | 200 | 0.016 | 0.134 | 1.227 | 2.341 |
| cf | 2 | 70 | 0.006 | 0.167 | 1.346 | 2.542 |
| qo | 2 | 5220 | 0.976 | 0.233 | 3.162 | 8.953 |

`p_next_given_first` = P(second glyph follows | first glyph); `p_prev_given_second` = P(first glyph precedes | second glyph). Values near 1 mean the parts hardly occur apart, which supports treating the pair as one unit but does not prove it.

## Highest-PMI adjacent pairs (≥30 occurrences)

| pair | count | pmi_bits | p_second_given_first |
|---|---|---|---|
| in | 5695 | 3.629 | 0.514 |
| pc | 702 | 3.520 | 0.469 |
| fc | 173 | 3.369 | 0.412 |
| qo | 5220 | 3.162 | 0.976 |
| am | 706 | 3.045 | 0.055 |
| yt | 528 | 2.936 | 0.033 |
| ch | 10159 | 2.787 | 0.824 |
| sh | 4257 | 2.723 | 0.653 |
| ls | 419 | 2.664 | 0.044 |
| ai | 6296 | 2.630 | 0.488 |
| yp | 78 | 2.566 | 0.005 |
| dy | 6413 | 2.459 | 0.540 |
| yk | 635 | 2.395 | 0.039 |
| ra | 573 | 2.393 | 0.087 |
| ar | 2862 | 2.357 | 0.222 |

Full tables: `glyphs/catalog.csv`, `glyphs/digraph_candidates.csv`, `glyphs/top_pmi_bigrams.csv`.

## Rare / high-ASCII codes

| glyph | count | count_all_loci | count_labels |
|---|---|---|---|
| @132; | 10 | 10 | 0 |
| @133; | 9 | 11 | 2 |
| @175; | 6 | 6 | 0 |
| @191; | 4 | 4 | 0 |
| @196; | 4 | 5 | 1 |
| @206; | 4 | 4 | 0 |
| @246; | 4 | 4 | 0 |
| @138; | 3 | 3 | 0 |
| @152; | 3 | 3 | 0 |
| @162; | 3 | 4 | 0 |
| @176; | 3 | 3 | 0 |
| @243; | 3 | 3 | 0 |
| @135; | 2 | 2 | 0 |
| @136; | 2 | 2 | 0 |
| @145; | 2 | 2 | 0 |
