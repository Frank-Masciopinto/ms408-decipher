# h31 — MS 408's own word-construction system

Pre-registered in [PREREG.md](PREREG.md) (commit e97c4d1). **No translation or meaning claims.**

## What was done
- **Corpora:** three MS hands (1A, 2B, 3B; ZL3b, EVA characters) were compared with two groups of about 10.5k tokens each:
  - 6 natural texts (NAT): Latin Celsus and Vulgate, Italian Sidrach and Dante, Hebrew Tanakh, Arabic Qur'an;
  - 3 generated texts (GEN): Naibbe with the real tables on Latin Pliny and on Italian Ariosto, and the no-plaintext copy-modify generator C0 fitted on MS 2B (so its similarity to MS is partly circular).
- **Segmenters:**
  - M1: Morfessor Baseline (MDL).
  - M2: a Bayesian stem + suffix model (DP priors, collapsed Gibbs).
  - M3: the project's prefix/core/suffix `AffixModel`, used as the slot/affix baseline.
- **Metrics:** inventory size, productivity (P1: observed stem × suffix pairs ÷ the number expected under independence), stem–suffix constraint (C1), paradigm reuse (R1), cross-word agreement (A1), and held-out bits/word against the h19 `CharLM(4)`.
- **Running it:**
  - `python corpora.py` builds the corpora. The cache is git-ignored for licence reasons.
  - `python run_h31.py` takes about 4 minutes on 8 processes.
  - `python summarise.py` writes the summary table and verdicts.
  - Test: `pytest test_h31.py`.

## Results (M1 unless noted; full table in `results/summary_table.csv`)

| Metric | MS 1A / 2B / 3B | NAT range | GEN range | Pre-registered verdict |
|---|---|---|---|---|
| I1 morph types per word type | 0.071 / 0.085 / 0.069 | 0.21–0.54 | 0.061–0.067 | neither: just above GEN, far below NAT |
| distinct suffixes | 135 / 136 / 149 | 278–652 | 96–151 | (descriptive) |
| P1 productivity (obs/exp pairs) | 0.73 / 0.67 / 0.70 | 0.46–0.68 | 0.71–0.79 | neither: in the gap between the groups |
| C1 stem–suffix constraint | 0.24 / 0.29 / 0.25 | 0.19–0.44 | 0.23–0.24 | overlap (M3: generator-like, 0.12–0.19 vs NAT 0.42–0.51) |
| R1 paradigm reuse (×null) | 2.1 / 2.9 / 2.7 | 1.9–3.8 | 3.0–16.1 | language-like under M1; unstable under M2 (0 or NaN in some cells) |
| A1 suffix → next word's first letter (excess bits) | 0.067 / 0.132 / 0.167 | 0.041–0.153 | 0.001–0.026 | overlap (M2: language-like) |
| A1' last letter → next first letter | 0.110 / 0.210 / 0.229 | 0.031–0.163 | 0.001–0.004 | (descriptive) |
| held-out gap, best morph model − CharLM (bits/word) | 1.42 / 1.28 / 1.36 | 2.74–3.67 | 1.29–2.10 | overlap; 1A and 3B are inside GEN, 2B is 0.005 below it |

**Pre-registered hypotheses:**
- **H-morph** (morpheme-like) is **not supported**: only 1 of 4 core metrics is language-like under M1, and 1 under M2.
- **H-decor** (independent, generator-like combination) is **not supported**: 0 of 4 under M1, and 1 under M3.

## What this shows
1. **The inventory is tiny and generator-sized.** Morfessor needs about 0.07–0.085 morphs per word type in MS, like Naibbe and C0 (0.06–0.07) and a quarter to a seventh of the natural texts. MS words are built from roughly 135–150 recurring endings, which is in the generators' range, not that of the inflecting languages.
2. **Pieces combine more freely than in language, a little less than in generators.** Productivity (0.67–0.73) sits right between the two groups. The morph models lose to a character model by only 1.3–1.4 bits/word, compared with 2.7–3.7 in natural text. Most of the structure is in letter sequences, not in reusable morphs, which fits h19 and h26–h28.
3. **The clearest language-like trait is that words depend on their neighbours, and the generators lack this.** The ending of a word predicts the next word's first letter (A1 0.07–0.17 bits beyond within-page shuffles, z 21–56), inside the natural range. All three generators are near zero (≤ 0.03).
   - But the plain last letter predicts even more (0.11–0.23, above every natural text). That points to a letter-level junction rule across word boundaries rather than agreement between morphemes. This is consistent with h30's END → ONSET dependency.
4. **Paradigms are weak evidence.** Suffix-set reuse is above its null in every corpus. MS falls in the natural range under M1 but not consistently under M2 and M3, so it doesn't discriminate.

**Overall:** MS 408 words look like a small, freely combined, generator-sized piece system, with one non-generator feature: a strong word-to-word junction dependence that none of the tested generators reproduces. That is neither inflection-like morphology nor pure decoration.

## Limits
- One transcription (ZL3b), segmented as written. Segmenter choices change some metrics a lot (R1 under M2, C1 under M3). The suffix definition (last morph) is a convention.
- **Controls:**
  - Hebrew and Arabic are consonantal script, which inflates their inventory.
  - C0 is fitted on MS 2B (circular).
  - Naibbe uses the author's MS-like tables.
- **Statistics:** each group has only 3–6 corpora, so range rules are coarse and there are no confidence intervals. The verdicts are descriptive, with no multiple-testing correction.
- A1 nulls shuffle within pages, which also breaks line-position effects (h13–h16), so part of A1 may be line-edge habits.
- **Not done:** per-hand Hebrew/Arabic native-segmentation checks, and IT2a/RF1b replication.

## Next step
Model the junction directly. Test whether a generator with a word-boundary rule (last letter of word i → first letter of word i+1, fitted per hand) closes the A1/A1' gap while keeping the generator-sized inventory. Also check whether A1' survives line-position and same-line controls, so that line-edge habits are separated from a true junction rule.
