# h24: neutral-cipher robustness of the h23 copy result (pre-registration)

Written and committed before any h24 computing. No translation claims.

## Background
In h23, Naibbe-Italian with a 5 % suffix-swap copy layer reproduced all five h20 statistics (5/5) on Boccaccio, at distance 3.0. It reached 4/5 on three other sources, missing only D4 and only just. That result used a single seed, and Naibbe's tables are MS-inspired.

## Part 1: seeds (Naibbe-Italian)
- **Grid:** copy layers `swap` c = 0.05, `inline` c = 0.03 and `unit` c = 0.05 (the h23 rules), on all 4 sources (Boccaccio, Cucina, Sidrach, Cennini) × 5 seeds. That is 60 cells.
- **Seeds:** each seed changes both the Naibbe encryption seed and the copy-layer seed.
- **Report:** per rule and source, the 5/5 rate and the mean distance with a 95 % t-interval over seeds.

## Part 2: ciphers not designed from MS
- **Glyph alphabet:** made up (arbitrary Unicode letters, not EVA). Scoring uses character segmentation (`seg="char"`), so one glyph = one unit.
- **Generic copy edits:** "suffix" = the last unit; "prefix" = the first unit; "inner" = any unit. Units are drawn from the cell's own output.
- **Ciphers** (word boundaries kept; plaintext lower-cased letters only; each table drawn at random per seed):
  - `homo2`, `homo4`: homophonic substitution. Each letter gets K ∈ {2, 4} single-glyph homophones, chosen uniformly per occurrence. The alphabet size is 21·K.
  - `verb8`, `verb12`: verbose cipher. Each letter maps to a fixed random string of 1–3 glyphs from an alphabet of A ∈ {8, 12}.
  - `nomen`: nomenclator. The 100 most frequent plaintext words get random 2–4-glyph codewords; the remaining words are spelled with `verb10` (A = 10). Both use the same alphabet.
  - `verb8null`: `verb8` plus nulls with mean r = 0.3, drawn from the cell's own ciphertext unigrams.
- **Copy conditions:** none, `swap` c = 0.05, `inline` c = 0.03.
- **Grid:** 6 ciphers × 3 copy conditions × 3 seeds on Boccaccio (54 cells).
- **Transfer:** the best neutral (cipher, copy) setting by mean distance → Cucina, Sidrach, Cennini × 3 seeds (9 cells).
- **Plaintext survival:** signal share (the fraction of tokens untouched by copying or nulls).

## Part 3 (secondary): hand vs section
- **Subsets:** disjoint, contiguous-page subsets.
  - About 4.4k tokens each: 2B-biological, 2B-non-biological, 3B-stars (2 chunks), 1A-herbal (2 chunks).
  - About 2.3k tokens each: 2B-herbal, 1A-herbal (2 more chunks).
- **Same-section test:** 2B-herbal vs 1A-herbal tests hand within one section.
- **Folds:** fall back to bifolium groups when a subset spans fewer than 5 quires.

## Predictions
- **S1 (seeds):** `swap` c = 0.05 reaches 5/5 in ≥ 40 % of the 20 seed × source cells, and its mean distance is ≤ 4.
- **S2 (neutral, null result expected):** no neutral cipher without copying reaches ≥ 4/5.
- **S3 (main):** some neutral cipher with a copy layer reaches 5/5 in ≥ 1 of its 3 Boccaccio seeds. **The 5/5 survives without Naibbe** if, at the best neutral setting, the mean distance is ≤ 6 and ≥ 2 of the 3 transfer sources reach ≥ 4/5 in their seed-majority.
- **S4:** verbose ciphers come closer than homophonic ones, which have high bits/glyph.
- **S5 (Part 3):** if 2B's low bits/glyph is a section effect, then 2B-herbal D5 is within 0.05 of 1A-herbal, and 2B-biological is lowest. If it is a hand effect, then 2B-herbal and 2B-non-biological both sit < 1A-herbal − 0.05.
