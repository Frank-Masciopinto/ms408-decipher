# h21 pre-registration: Italian encodings that break word order, and cross-hand C0

Committed before any text is generated or scored.

## Pipeline and fingerprint
- h20's pipeline unchanged (`run_h20.run_cell`: the h19 models + PCLM, bifolium and quire folds, seed 19), 10 500 tokens per condition.
- Same five statistics, D1–D5, with h20's tolerances δ = (0.10, 0.10, 0.015, 0.10, 0.15).
- MS reference values are read from h20 (`cell_MS_*.json`); MS is not re-scored.
- **Part A target:** the MS range over 1A/2B/3B ± δ, as in h20; distance as in h20.
- **Part B target:** each hand's own values ± δ ("point match"). The h20 range-based match is also reported.
- Pseudo-lines for shuffling and for the onset feature: 9 words.

## A. Order-breaking Italian encodings
**Sources:** Boccaccio, Cucina, Sidrach, Cennini (first 10 500 tokens or more as needed).

**Building blocks** (applied in this order: encode, then homophones, then shuffle, then nulls; truncate to 10 500):
- `syll`: the h20 word-preserving syllabic cipher into EVA (MS 2B unit-n-gram codebook).
- `naibbe`: h20 Naibbe Italian (78-card deck).
- `hom(K)`: each word type has K variants, its code + suffix from ["", "y", "dy", "ol", "ain", "or", "al", "am"][:K]. Selection: if the word occurred in the last 20 tokens, its last variant is reused with probability 0.5; otherwise a variant is drawn uniformly. Repeats thus become exact or near copies (≤ 3 glyphs apart).
- `shuf`: words are permuted uniformly within each 9-word pseudo-line.
- `null(r)`: after each word, a geometric number of null words (mean r) is inserted. Each null is drawn from the MS 2B word-token distribution ("Voynich-like").

**Single-mechanism / base conditions, on all 4 sources (24 cells):** plain+shuf, syll+shuf, syll+null(0.5), syll+hom(4), naibbe+shuf, naibbe+null(0.5).

**Parameter search, on Boccaccio only (18 cells):** syll + hom(K ∈ {2, 4, 8}) × shuf ∈ {no, yes} × null(r ∈ {0, 0.3, 0.7}).
- The **2 settings with the smallest distance** are then run on Cucina, Sidrach and Cennini (6 cells) as transfer checks.
- **"Contrivance"** of a setting = the number of layered mechanisms (syll/naibbe, hom, shuf, null) + the share of tokens that are nulls.

## B. Cross-hand C0
- C0 engine (`run_h12.fit`) fitted on 1A, 2B or 3B alone (h20 seed-20 texts reused; one new text with seed 21 each).
- Pooled-other-hands fits for each target (2B+3B → 1A; 1A+3B → 2B; 1A+2B → 3B), seeds 20 and 21 (6 cells).
- **Match matrix:** generator × target hand, with point matches and distance to the target hand.

## Predictions
- **PA1:** shuffling removes most of the n-gram gain (D1 ≤ 0.1 for plain+shuf and syll+shuf), but D4 stays < −0.5, because word unigram/cache models still beat char models. No base condition reproduces (5/5).
- **PA2:** no single-mechanism condition matches ≥ 4/5.
- **PA3:** at least one search setting matches ≥ 4/5. Any 5/5 setting needs ≥ 3 layered mechanisms. The best setting, transferred, matches ≥ 4/5 on ≥ 2 of the 3 other sources.
- **PB1:** single-hand C0 fitted on X point-matches hand Y ≠ X on ≥ 4/5 in ≥ 4 of the 6 off-diagonal pairs.
- **PB2:** pooled-other-hands C0 point-matches its target on ≥ 4/5 for all 3 targets (both seeds).
- **PB3:** the cross-hand C0 distance to the MS range is smaller than that of the best Italian encoding found in A.

No translation or meaning claims.
