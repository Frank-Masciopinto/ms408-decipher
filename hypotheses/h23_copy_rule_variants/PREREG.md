# h23 — copy-rule variants and what makes hand 2B distinct (pre-registration)

Written and committed before any h23 computing. No translation claims.

## Background
- h22: Naibbe-Italian with 5 % generic copying (W = 20) reaches 4/5 on all four Italian sources (distance 5.4–7.9). Its only miss is D4, the word-vs-character dominance: about −0.17 against MS +0.03 … +0.08 (δ 0.10).
- Copying raises λ5 but hands word models extra predictability.
- Hand 2B is missed by every C0 fit that did not see it, on D1 (n-gram gain) and D5 (bits/glyph).

## Part A: copy-rule variants (primary)
- **Pipeline:** h22 pipeline on Naibbe-Italian (no nulls, no shuffle), 9-word lines. Copy edits use units from the cell's own output; nothing is fitted to MS.
- **Variants.** With probability c, a token is replaced; its source is drawn uniformly from the window unless stated.

| id | rule |
|---|---|
| ref | the h22 rule: W = 20; exact .30 / suffix .35 / prefix .15 / inner .20 |
| heavy | W = 20; two successive non-exact edits (suffix / prefix / inner equally likely) |
| slot | W = 20; one edit, suffix .6 / prefix .4, never exact or inner |
| swap | W = 20; the source's final unit is replaced by a *different* final unit (an -edy/-ol style suffix swap) |
| inline | source drawn only from earlier tokens of the same line; h22 edit mix; no copy at line start |
| prevline | source drawn only from the previous line; h22 edit mix |
| unit | copy-of-code-unit: the current token keeps its form except one random unit, which is replaced by a random unit taken from a random token in the last 20 |

- **Grid:**
  - every variant × c ∈ {0.03, 0.05, 0.10} on Boccaccio (21 cells), plus a c = 0 baseline;
  - secondary: syllabic + own-ciphertext nulls (r = 0.5), each variant at c = 0.05 (7 cells).
- **Transfer:** the 2 best Naibbe settings by bifolium distance go to Cucina, Sidrach and Cennini.
- **Scoring:** the h20 statistics D1–D5, match within MS range ± δ, distance; bifolium primary, quire reported.
- **Plaintext survival:**
  - signal share: tokens not touched by the copy layer;
  - for syllabic cells, oracle decoding accuracy and MI fraction, as in h22.

## Predictions (Part A)
- **RA1:** at least one variant reaches D4 ≥ −0.07 (inside range) while λ5 ≥ 0.022 (the h22 best level).
- **RA2:** some Naibbe setting reaches 5/5 on bifolium folds.
- **RA3:** the best setting transfers at ≥ 4/5 to all 3 other sources, and at 5/5 on ≥ 2 if RA2 holds.
- **RA4:** at the best setting, signal share ≥ 0.9.
- **RA5:** at equal c, "unit" and "swap" have higher D4 than "ref" (less whole-word predictability).

## Part B: what makes 2B distinct (secondary, diagnostic)
- **Descriptives** per hand: section mix, top-50 type share, number of types, -edy and qo- token shares, line-initial onset distribution (top glyph shares).
- **Fingerprint cells** from MS pages, with the same pipeline and statistics:
  - (i) **size-matched subsets** of about 4.5k tokens: 2B biological pages, 2B non-biological pages, and the first pages of 1A and of 3B up to the same size;
  - (ii) **-edy removed:** 2B and 3B with every token ending in "edy" dropped (1A has almost none).
- **Exploratory predictions:**
  - **RB1:** 2B-biological and 2B-non-biological both keep D5 below the size-matched 1A and 3B. A hand effect, not a section effect.
  - **RB2:** removing -edy raises 2B's D5 by ≥ 0.05 and makes D1 more negative.
- **Caveat:** hand and section are confounded (2B is 58 % biological; 3B is stars). No causal claim.
