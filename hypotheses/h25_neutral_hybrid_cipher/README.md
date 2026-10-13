# h25: neutral hybrid cipher with Naibbe's structure but random tables

This stage was pre-registered in [PREREG.md](PREREG.md) (commit be8e60e) before any computing. It makes no translation claims.

## Question
Naibbe-Italian plus copying is close to MS (h23/h24), but ciphers that were not built from MS are far off. Is Naibbe's **design** enough on its own, without its MS-derived tables? The design here is:
- random respacing into 1–2-letter chunks;
- homophonic tables chosen by card draw;
- prefix + suffix codes concatenated into one word.

## Method
- **Cipher:** the repo's `NaibbeCipher` engine, driven by **random tables** of made-up glyphs ("NH"). The tables are in `tables/`.
- **Baseline:** alphabet 20; 6 tables with Naibbe card weights; p_unigram 17/36; unigram codes 1–3 glyphs, prefix/suffix codes 1–2.
- **Sensitivity:** one parameter changed at a time:
  - alphabet 15 / 25;
  - code length short / long;
  - 1 / 3 tables;
  - uniform card weights;
  - p_unigram 0.3 / 0.7.
- **Copy layers:** the h23/h24 generic layers (suffix swap, within-line, unit splice).
- **Segmentation:** char segmentation (one glyph = one unit). There is also an **EVA-like rendering**: each glyph becomes a randomly assigned EVA unit (not by MS frequency), scored with EVA segmentation like Naibbe and MS.
- **Scoring:** the h20 five statistics and distance, on bifolium folds.

**Reduced grid (runtime).** The machine was heavily loaded and the run was interrupted once. The baseline used **6 table seeds instead of the pre-registered 10**, in every baseline block. The sensitivity variants kept their 3 seeds; everything else is as pre-registered.

## Results (bifolium folds; Boccaccio unless stated)

| setting | n seeds | ≥ 4/5 | 5/5 | distance, mean [95 % CI] | D2 | λ5 | D4 | D5 |
|---|---|---|---|---|---|---|---|---|
| NH base, no copy (char) | 6 | 33 % | 0 | 17.9 | 0.25 | 0.053 | −0.11 | 2.39 |
| NH base + swap (char) | 6 | 0 | 0 | 54.6 [43.9, 65.3] | 0.53 | 0.095 | −0.30 | 2.50 |
| NH base, no copy (EVA-rendered) | 6 | 0 | 0 | 75.6 | 0.04 | 0.006 | −0.75 | 1.78 |
| NH base + swap (EVA-rendered) | 6 | 50 % | 0 | 67.5 [53.6, 81.4] | 0.14 | 0.019 | −0.75 | 1.84 |
| **NH long codes, no copy (char)**, best | 3 | 0 | 0 | **8.9** | 0.08 | 0.011 | −0.03 | 2.04 |
| NH long + swap (EVA), all 4 sources | 12 | 0 | 0 | 345–689 | 0.15–0.23 | 0.01 | −1.8 … −2.6 | 1.71–1.84 |
| *Naibbe + swap (h24)* | 20 | 100 % | 35 % | 3.61 [3.21, 4.01] | | | | |
| *best h24 neutral cipher* | | 0 | 0 | ≥ 89 | | | | |
| *C0 cross-hand (h21/h22)* | 30 | 100 % | 93 % | 1.9–6.0 | | | | |

- **No NH cell reaches 5/5** in any seed, segmentation or source (138 cells on bifolium folds; 7 reach 5/5 on the wider quire range). Sixteen cells reach 4/5, all without copying or with EVA rendering.
- **Transfer of NH base** (char segmentation, no copy): Cucina, Sidrach and Cennini come out at 18.8–19.3, with ≥ 4/5 in 0–50 % of seeds.
- **Copying hurts NH.** Random short codes already collide, so NH without copying has a cache gain and copy rate at or above MS (D2 0.25, λ5 0.05). Adding the copy layer overshoots, and D4 falls. Naibbe needed copying because its MS-like tables have few collisions.
- **The EVA rendering** fixes bits/glyph: |D5 − MS| falls from 0.46 to 0.18. But it wrecks D4 (−0.75 to −2.6). Spelled out in EVA units, random codes are long and have no internal glyph regularity, so character models pay many bits per word. Naibbe's tables have exactly that regularity (MS-like glyph sequences such as *qokchdy*, *chey*), and NH cannot reproduce it.

**Sensitivity:** mean |log distance change| from the baseline, averaged over no-copy and swap, highest per parameter.

| parameter | effect | direction |
|---|---|---|
| **number of tables** (homophony) | **1.01** | 1 table: D1 +0.5 (n-gram gain returns), distance 92; 3 tables: 12.5 |
| code length | 0.87 | long codes best (8.9; decodable 0.97) |
| p_unigram | 0.25 | |
| alphabet size | 0.15 | |
| card weights | 0.10 | |

**Plaintext survival.** At the best setting (long codes), 97 % of unaltered tokens are uniquely decodable under the true tables, and 95 % of tokens are untouched by copying. The baseline gives 0.78 and one table gives 0.46, because short random codes collide.

## Predictions

| | prediction | outcome |
|---|---|---|
| T1 | NH base + swap ≥ 4/5 in ≥ 50 % of seeds, mean distance ≤ 10; "design enough" only if also a 5/5 | **fail**: char 0 % / 54.6; EVA 50 % but 67.5; no 5/5 |
| T2 | NH without copying closer than every h24 neutral cipher (< 89) | **pass** (17.9 char) |
| T3 | EVA rendering lowers \|D5 − MS\| | **pass** (0.46 → 0.18) |
| T4 | the largest effect is code length or p_unigram | **fail** (the number of tables is largest; code length second) |
| T5 | decodable ≥ 0.8 at best setting | **pass** (0.97) |

## Verdict
- **Naibbe's design alone is not enough.**
  - With random tables, the structure gets much closer than other neutral ciphers: distance 9–19 against ≥ 89, and 4/5 in some seeds.
  - But it never reproduces the fingerprint. It does no better with the copy layers that made real Naibbe match.
  - When rendered in EVA-like units it falls far off on word-vs-character dominance.
- **What closes the gap in Naibbe** is the internal glyph structure of its MS-derived tables: low per-glyph entropy with a word-internal grammar. Homophony (several tables) is the most important structural parameter, then code length.
- This confirms h24: the h23 match is carried by MS-like tables, not by "a cipher of Italian plus copying" in general.

## Limits
- Base seeds were reduced from 10 to 6, and the variants have 3 seeds.
- Only one-at-a-time sensitivity was run, with no interactions; the long-code variant got the EVA rendering only together with copying.
- Random tables have no glyph-order grammar at all. A test of tables with a neutral (non-MS) glyph grammar is the missing middle case.
- The EVA rendering is one random unit assignment per seed.
- A table-file race between parallel workers broke phase 2 once. It was fixed by building cells serially; no phase 1 cell was affected (a truncated table would have raised an error).

## Files
- Code and tests: `h25_lib.py`, `run_h25.py`, `summarise.py`, `test_h25.py`.
- `tables/`: the random cipher tables.
- Results: `results/fingerprints_*.csv`, `groups_*.csv`, `summary.json`, `best_variant.json`, `cell_*.json`.
- Figure: `figures/nh_sensitivity.png`.
- Per-token tables are git-ignored.
