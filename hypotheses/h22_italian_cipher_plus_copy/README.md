# h22: Italian cipher plus a generic copy-and-modify layer

This stage was pre-registered in [PREREG.md](PREREG.md) (commit b37c88b) before anything was computed. It makes no translation claims.

## Question
In h21, the closest Italian encodings (Naibbe plus nulls) missed the MS fingerprint mainly on local copying. This stage asks two things:
- Is copying the one missing ingredient?
- If a copy layer is added, how much plaintext signal survives?

## Method
- **Pipeline:** Italian base cipher (Naibbe, or the h20 syllabic cipher), then an optional within-line shuffle, then optional nulls (r = 0.5), then a copy layer.
- **Copy layer:** with probability c, a token is replaced by an edited copy of a token from the last W tokens.
  - Edit mix is fixed and not fitted to MS: exact 0.30, suffix 0.35, prefix 0.15, inner 0.20.
  - Edits use the C0 operator, with units taken from the cell's own output.
- **Grid:** c ∈ {0.05, 0.1, 0.2, 0.3} × W ∈ {5, 20} on Boccaccio.
- **Nulls:**
  - *clean*: drawn from the cell's own ciphertext unigrams.
  - *leaky*: drawn from MS 2B tokens, as in h21. Shown for comparison only.
- **Transfer:** the 2 best clean settings are rerun on Cucina, Sidrach and Cennini.
- **Scoring:** the h20/h21 five statistics and distance (bifolium folds unless stated).
- **Part B:** cross-hand C0 rerun with 5 seeds (20–24).

## Results (bifolium folds)

| setting (clean nulls) | n/5 | distance | signal share |
|---|---|---|---|
| Naibbe, no copy (c = 0) | 3 | 9.0 | 1.00 |
| **Naibbe + copy c = 0.05, W = 20** (best) | **4** | **6.5** | 0.95 |
| the same, transferred: Cennini / Cucina / Sidrach | 4 / 4 / 4 | 5.4 / 6.5 / 7.9 | 0.95 |
| Naibbe + shuffle + copy c = 0.05, W = 20 (2nd); transferred | 3; 3 / 3 / 4 | 7.2; 7.8 / 6.4 / 10.5 | 0.95 |
| Naibbe + nulls + copy c = 0.05, W = 20 | 3 | 12.4 (leaky: 5.9, 4/5) | 0.63 |
| syllabic + nulls, any c | ≤ 3 | ≥ 367 (leaky ≥ 151) | 0.46–0.66 |
| c ≥ 0.1, any base | ≤ 3 | ≥ 32 | — |
| *C0 cross-hand, 30 fits (Part B)* | 4–5 | 1.9–6.0 | — |

- **What copying fixes, and what it breaks:**
  - A 5 % copy rate with W = 20 brings the 5-word copy rate D3 up from 0.007 to 0.022–0.031 and D2 into range.
  - It also pushes D4 (word-vs-char dominance) down from +0.02 to about −0.17, outside MS +0.03 … +0.08 ± 0.10.
  - So the best cells fail on D4 alone.
  - At higher c, the copy statistics overshoot (λ5 up to 0.29) and D4 collapses.
- **No setting reaches 5/5 on bifolium folds.**
  - On quire folds, where the MS range is wider, 13 cells reach 5/5. The best is Naibbe + copy c = 0.10, W = 20, at distance 6.3.
- **Clean vs leaky nulls:** removing the MS-derived nulls costs about 20 distance units for Naibbe + nulls and about 234 for syllabic + nulls. Much of h21's null benefit came from the leak.
- **Plaintext signal:**
  - In the best cells, 95 % of tokens are untouched Naibbe ciphertext.
  - For the syllabic cells, an oracle type→word decoder recovers 0.59 of all tokens, and MI(token; plaintext word) is 0.90 of H(word).
  - So at these copy rates the copy layer destroys little of the plaintext signal. This says only what an encoder *could* carry, not that MS 408 carries any.

## Part B: 5 seeds, point matches against each hand's own MS values
- **Fits that never saw a hand** (15 per target), share reaching ≥ 4/5:
  - 1A: 100 %, mean distance 1.8
  - 3B: 47 %, mean distance 4.2
  - 2B: **0 %**, mean distance 5.9
- **Why 2B fails:** every blind fit misses 2B on D1 and on D5 (bits/glyph).
- **Fits trained on 2B itself** match it at 4/5 in 4 of 5 seeds (mean 3.8).
- **Conclusion:** 2B's distinct values are stable across seeds, which points to a real hand difference rather than seed noise.
- Against the pooled MS range, 28 of 30 fits reproduce 5/5.

## Predictions

| | prediction | outcome |
|---|---|---|
| QA1 | c = 0 with clean nulls: no 5/5 | **pass** (max 3/5) |
| QA2 | some clean (c, W) ≥ 4/5 | **pass**, weak form only: 2 cells at 4/5, none 5/5 |
| QA3 | best setting transfers ≥ 4/5 on ≥ 2 of 3 sources | **pass** (3/3 at 4/5) |
| QA4 | best clean distance ≤ 6.0 | **fail** (6.5 on Boccaccio; Cennini transfer 5.4) |
| QA5 | clean vs leaky distance changes by < 2 | **fail** (mean +129; Naibbe+nulls +20, syll+nulls +234) |
| QA6 | best syll+nulls oracle accuracy ≥ 0.4 | **pass** (0.59; MI 0.90 of H) |
| QB1 | blind fits hit 2B ≥ 4/5 in ≤ 20 % of fits, 1A in ≥ 60 % | **pass** (0 % vs 100 %) |

## Verdict
- **Local copying is the main missing ingredient, but not the only one.**
  - A small generic copy layer (5 %, W = 20) on Naibbe-Italian gets 4/5 on all four sources, at distances 5.4–7.9. That is just outside to just inside the C0 cross-hand range, with no parameter fitted to MS.
  - The one remaining miss, D4, is a tension: copying adds word-level predictability that MS 408 does not show.
- **Plaintext signal:** a Naibbe-plus-copy text that comes close to MS would still carry almost all of its plaintext.

## Limits
- Naibbe itself (its tables and respacing) was designed with MS in mind.
- The syllabic codebook uses MS 2B unit n-grams (declared in the pre-registration).
- The grid is small and only Italian was tested.
- Plaintext recovery for Naibbe is reported as signal share only: no decryption was attempted.
- 5/5 is reached only on the wider quire range.

## Files
- Code and tests: `h22_lib.py`, `run_h22.py` (phase1/phase2), `summarise.py`, `test_h22.py`.
- Results: `results/partA_*.csv`, `partB*_*.csv`, `summary.json`, `search_best.json`, `cell_*.json`, and the figure `figures/copy_layer.png`.
- Per-token tables are git-ignored.
