# h25: a neutral hybrid cipher with Naibbe's structure but random tables (pre-registration)

Written and committed before any h25 computing. No translation claims.

## Background
- h24: Naibbe-Italian plus a light copy layer is ≥ 4/5 robustly (distance about 3–4). Six cipher families not built from MS never exceed 3/5 (distance ≥ 89).
- Open question: is it Naibbe's *structure* that matters, or its MS-derived glyph tables?
- Structure here means: random respacing into 1–2-letter chunks, homophonic tables chosen by card draw, and prefix/suffix codes concatenated into one word.

## Cipher ("NH", neutral hybrid)
- **Engine:** the repo's `NaibbeCipher` (same respacing, card draw, prefix + suffix word formation, unambiguous-bigram rejection with ≤ 50 retries), driven by **random tables** written to `tables/`.
- **Tables:** for each (state ∈ {unigram, prefix, suffix}, table, letter), a random string drawn uniformly from a made-up alphabet of A glyphs (Unicode letters, not EVA). Nothing is fitted to MS; MS frequencies are never used.
- **Baseline:**
  - alphabet A = 20;
  - 6 tables with Naibbe's card weights (28:14:11:11:7:7);
  - p_unigram = 17/36;
  - unigram codes 1–3 glyphs, prefix/suffix codes 1–2 glyphs.
- **Sensitivity**, one parameter at a time from the baseline:
  - A ∈ {15, 25};
  - code lengths "short" (all 1–2) / "long" (unigram 2–5, prefix/suffix 1–3);
  - tables ∈ {1, 3} (less homophony);
  - card weights uniform;
  - p_unigram ∈ {0.3, 0.7}.
  
  That gives 8 variants plus the baseline.
- **Copy layers** (h23/h24 generic rules; units = glyphs; "suffix" = last unit): none, `swap` c = .05, `inline` c = .03, `unit` c = .05.
- **Segmentation:**
  - Primary: one made-up glyph = one unit (`seg="char"`).
  - **EVA-like rendering** (fixes the h24 comparability limit): each made-up glyph is replaced by a distinct EVA unit drawn at random, per seed, from the EVA unit inventory {o, a, i, e, y, d, l, r, s, n, m, k, t, p, f, q, g, x, ch, sh, cth, ckh, cph, cfh, in, iin, ain, aiin, ee, eee, …}, uniformly, *not* by MS frequency. The result is scored with EVA segmentation, exactly as for Naibbe and MS.

## Grid
| block | settings | sources | seeds (tables) | cells |
|---|---|---|---|---|
| baseline × 4 copy conditions | char seg | Boccaccio | 10 | 40 |
| baseline × {none, swap} | char seg | Cucina, Sidrach, Cennini | 10 | 60 |
| baseline × {none, swap} | EVA-like rendering | Boccaccio | 10 | 20 |
| 8 variants × {none, swap} | char seg | Boccaccio | 3 | 48 |
| best variant × swap | EVA-like rendering | all 4 | 3 | 12 |

## Scoring
- **Statistics:** the h20 statistics D1–D5 against the MS range ± δ, plus distance. The primary scheme is bifolium folds; quire is also reported.
- **Comparisons:**
  - Naibbe + copy (h24): swap distance 3.61 [3.21, 4.01];
  - neutral ciphers (h24): ≥ 89;
  - C0 cross-hand: 1.9–6.0.
- **Plaintext survival:**
  - signal share (tokens not altered by copying);
  - uniquely-decodable share (unaltered tokens that decode to exactly one plaintext chunk under the true tables).

## Predictions
- **T1 (main):** the NH baseline + swap reaches ≥ 4/5 in ≥ 50 % of its Boccaccio seeds, with mean distance ≤ 10, under at least one segmentation. "Naibbe-like design alone is enough" is accepted only if T1 holds **and** NH + swap reaches 5/5 in ≥ 1 cell.
- **T2:** NH without copying is ≥ 3/5 closer than every h24 neutral cipher; its mean distance is < 89.
- **T3:** the EVA-like rendering lowers |D5 − MS mean| relative to char segmentation for the same tables.
- **T4 (sensitivity):** the parameter that changes mean distance the most is either code length or p_unigram (word-length formation), not alphabet size.
- **T5:** at the best NH setting, uniquely-decodable share ≥ 0.8. The plaintext would survive.
