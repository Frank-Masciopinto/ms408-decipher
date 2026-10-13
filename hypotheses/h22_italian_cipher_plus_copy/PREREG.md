# h22 — Italian cipher + a generic copy-and-modify layer (pre-registration)

Written and committed before any h22 computing. No translation claims: this asks only whether a mechanism can reproduce statistics, not what MS 408 says.

## Background
- h21: the closest order-breaking Italian encodings are Naibbe-Italian + about 33 % nulls (3/5 on the h20 fingerprint, distance 5.3–6.2). They fall short mainly on the 5-word copy rate (λ5 ≤ 0.016 vs MS 0.032–0.043).
- Leak: h21's nulls were drawn from MS 2B tokens.
- The cross-hand C0 engine reaches distance 2.2–6.0.
- Question: is local copying the one missing ingredient? And how much plaintext signal survives once it is added?

## Construction (Part A)
- **Sources:** Italian `it_boccaccio`, `it_cucina`, `it_sidrach`, `it_cennini`; 10.5k tokens; 9-word pseudo-lines (as in h21).
- **Pipeline:** base encoding → pseudo-lines → optional within-line shuffle → optional nulls (geometric count with mean r = 0.5 per word) → copy layer → re-cut into the same lines.
- **Copy layer** (generic, not fitted to MS):
  - Each output token is replaced with probability **c** by an edited copy of a token drawn uniformly from the previous **W** output tokens.
  - Edit op mix, fixed: exact 0.30, suffix 0.35, prefix 0.15, inner 0.20.
  - Edits use the C0 `_edit` operator (replace / add / remove one unit). The units come from the cell's own output so far (initial, final and any-unit pools), never from MS.
- **Nulls:**
  - **clean** (primary): drawn from the unigram distribution of the cell's own base ciphertext ("codebook nulls").
  - **leaky** (comparison only): drawn from MS 2B tokens, as in h21.
- **Bases:** `naibbe`, `naibbe+null`, `syll+null`, `naibbe+shuf`.
  - `syll` is the h20 syllabic cipher. Its code glyph strings are MS 2B unit n-grams, as in h20/h21; this is a remaining, declared MS-derived ingredient.
- **Grid on Boccaccio:**
  - The 4 bases × c ∈ {0.05, 0.10, 0.20, 0.30} × W ∈ {5, 20}, with clean nulls: 32 cells.
  - A c = 0 baseline per base: 4 cells.
  - Leaky versions of the two null bases at every (c, W): 16 cells.
- **Transfer:** the 2 best clean settings by distance (bifolium) go to Cucina, Sidrach and Cennini (6 cells).
- **Scoring:** the h20 statistics D1–D5 under the h19 pipeline. A statistic matches when it falls in the MS range ± δ; distance is measured to the MS mean. The primary folds are bifolium; quire is also reported.
- **Plaintext signal**, for every A cell:
  - *signal share*: the fraction of output tokens that are untouched base-cipher tokens (not null, not copy).
  - For `syll` cells, where tokens align to plaintext words:
    - **oracle decoding accuracy**, the upper bound: each token type is mapped to its most frequent aligned plaintext word, and accuracy is computed over all output tokens;
    - **MI**(token; plaintext word, with null/copy tokens labelled ∅), as a fraction of H(plaintext word).

## Part B (secondary)
- h21 Part B is rerun with 5 seeds (20–24): C0 fitted on a single hand, and on the pooled other hands (notX).
- Each fit is point-matched against each hand's own MS values (δ as before).
- Seeds already computed in h21 (20 and 21) are reused as is from h21 results; seeds 22–24 are new.

## Predictions
- **QA1:** with clean nulls and c = 0, no base reproduces (5/5). This replicates h21.
- **QA2:** some clean (c, W) setting on Boccaccio reaches ≥ 4/5 ("copying is the missing ingredient", weak form). The strong form, 5/5, is reported separately.
- **QA3:** the best clean setting, transferred, reaches ≥ 4/5 on ≥ 2 of the 3 other sources.
- **QA4:** the best clean distance is ≤ 6.0, the upper end of the h21 cross-hand C0 distances.
- **QA5:** removing the leak (clean vs leaky at the same setting) changes the distance by < 2 on average.
- **QA6:** at the best `syll+null` clean setting, oracle decoding accuracy is ≥ 0.4, meaning plaintext signal largely survives.
- **QB1:** 2B is distinct. Across seeds 20–24, C0 fits that never saw 2B (1A, 3B, not2B) point-match 2B at ≥ 4/5 in ≤ 20 % of fits, while fits that never saw 1A match 1A at ≥ 4/5 in ≥ 60 % of fits.
