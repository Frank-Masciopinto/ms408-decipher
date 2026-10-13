# h24: is the h23 copy result robust to seeds and to ciphers not designed from MS?

This stage was pre-registered in [PREREG.md](PREREG.md) (commit f327363) before any computing. It makes no translation claims.

## Question
h23 found that Naibbe-Italian with a 5 % suffix-swap copy layer reproduced all five h20 statistics (5/5) on Boccaccio. That came from one seed and from Naibbe's MS-inspired tables. This stage asks three things:
1. Does the result hold over seeds?
2. Does it survive ciphers *not* built from MS?
3. Is hand 2B's low bits/glyph a hand effect or a section effect?

## Part 1: Naibbe-Italian, 5 seeds × 4 sources (bifolium folds)

| copy rule | 5/5 rate (of 20) | ≥ 4/5 rate | distance, mean [95 % CI] | D4 mean | signal share |
|---|---|---|---|---|---|
| `inline` c = .03 | 15 % | 100 % | 3.17 [2.73, 3.61] | −0.099 | 0.97 |
| `swap` c = .05 | 35 % | 100 % | 3.61 [3.21, 4.01] | −0.087 | 0.95 |
| `unit` c = .05 | 35 % | 100 % | 3.54 [3.20, 3.89] | −0.085 | 0.96 |

- **By source:**
  - The 5/5 cases are all on Boccaccio and Cennini. Cennini reaches 5/5 in 60–100 % of seeds; Boccaccio in 0–60 %.
  - Cucina and Sidrach never reach 5/5 (0/5 seeds), with distances up to 4.4.
  - Every miss is D4 alone, which sits just below the bound of −0.07 (mean −0.06 to −0.13).
- **Quire folds:** all 60 cells reach 5/5.
- **Versus the MS-fitted C0 engine:** the distances, 2.2–4.4, are inside its cross-hand range of 1.9–6.0 (h21/h22).

## Part 2: neutral ciphers (made-up glyph alphabet, random tables, 3 seeds, Boccaccio)

| cipher | best distance (copy rule) | what fails |
|---|---|---|
| homophonic, 2 per letter | 126 (`inline`) | D5 = 3.5 bits/glyph (MS 1.77–1.94); copying overshoots the cache gain D2 |
| homophonic, 4 per letter | 398 (none) | D5 = 4.8 |
| nomenclator (top-100 codewords + verbose) | 1045 (none) | n-gram gain D1 +0.4; D4 ≈ −3.1 |
| verbose, 12 glyphs | 1276 (none) | D1 +0.4 … +0.5; D4 ≈ −3.5 |
| verbose, 8 glyphs (± own-ciphertext nulls) | 2225–2428 | D4 ≈ −4.7; nulls fix D1 but not D4 |

- **Matches:** no neutral cipher reaches 4/5 in any seed, with or without copying. The maximum is 3/5, on bifolium and on quire folds alike.
- **Transfer:** the best setting (homophonic-2 + `inline`) gives distances of 89–124 on Cucina, Sidrach and Cennini.
- **What the families lack:**
  - Homophonic ciphers get the "no n-gram gain" signature (D1 ≈ −0.14) and a sensible D4, but they spend too many bits per glyph.
  - Verbose and nomenclator ciphers get low bits/glyph, but their deterministic word codes keep Italian's n-gram gain and make word models dominate (very negative D4).
  - Naibbe combines both: respaced 1–2-letter chunks with homophonic glyph strings drawn from MS-like tables.
- **Plaintext survival** with copying: 95–97 % of tokens are untouched.

## Part 3: hand vs section (D5, bits/glyph)

| subset | tokens | D5 | D1 |
|---|---|---|---|
| 2B biological | 4.6k | **1.68** | −0.16 |
| 2B non-biological | 4.5k | 1.95 | −0.18 |
| 3B stars (2 chunks) | 4.5k each | 1.93 / 1.82 | −0.20 / −0.17 |
| 1A herbal | 4.4k | 1.95 | −0.18 |
| 2B herbal | 2.3k | 1.99 | −0.18 |
| 1A herbal (2 disjoint chunks) | 2.3k each | 2.02 / 2.01 | −0.22 / −0.19 |

- Within the herbal section, 2B and 1A differ by only −0.02 bits/glyph. 2B biological is the lowest subset.
- So 2B's distinct low bits/glyph is a **section (biological) effect**, not a hand effect, at this resolution.

## Predictions

| | prediction | outcome |
|---|---|---|
| S1 | `swap` 5/5 in ≥ 40 % of seed × source cells, mean distance ≤ 4 | **fail** (35 %; 3.61) |
| S2 | no neutral cipher without copying ≥ 4/5 | **pass** (max 3/5) |
| S3 | some neutral cipher + copy reaches 5/5; "survives without Naibbe" | **fail** (max 3/5; best distance 126) |
| S4 | verbose ciphers closer than homophonic | **fail** (homophonic 126 vs verbose ≥ 1276) |
| S5 | section effect: 2B-herbal within 0.05 of 1A-herbal and 2B-biological lowest | **section effect** (−0.02; biological lowest) |

## Verdict
- **The Naibbe-plus-copy result is robust over seeds as a near-match.** It reaches ≥ 4/5 in all 60 cells, at distance 2.2–4.4, but 5/5 in only 15–35 %, and only on two of the four sources.
- **It does not survive replacing Naibbe with ciphers not designed from MS.** None of six neutral families gets close (distance ≥ 89).
- **So h23's 5/5 depends on Naibbe's MS-like glyph tables and respacing.** It says "an MS-inspired cipher of Italian plus copying can mimic the fingerprint", not "any cipher of a language plus copying can".
- This partly restores the h19/h20 fingerprint as evidence against simple natural-language ciphers. It still does not tell the two hypotheses apart in general.
- **Hand 2B:** its low bits/glyph comes from its biological pages.

## Limits
- There are only 3 seeds in Part 2.
- Neutral ciphers were scored with character segmentation, whereas Naibbe and MS use EVA units. Glyphs-per-word differs, so D5 is not perfectly comparable across segmentations.
- There are 6 cipher families and no hybrid (homophonic + verbose) family. That family is the obvious gap.
- The Part 3 subsets are small (2.3–4.6k tokens), and 3B has no herbal subset large enough to compare.

## Files
- Code and tests: `h24_lib.py`, `run_h24.py`, `summarise.py`, `test_h24.py`.
- Results:
  - per-cell fingerprints: `results/fingerprints_*.csv`
  - Part 1 summaries: `part1_by_rule.csv`, `part1_by_source.csv`
  - Part 2 summary: `part2_boccaccio.csv`
  - `summary.json`, `neutral_best.json`, `cell_*.json`
- Figure: `figures/robustness.png`.
- Per-token tables are git-ignored.
