# h35 pre-registration: per-hand word-shape model (written before any computing)

Builds on h33 (space predictability S from ±2 glyphs; MS held-out odd bifolia 1A .724 / 2B .798 / 3B .792)
and h34 (per-hand word-gap rule; Naibbe generators stay at S 0.84–0.85 even with the rule; C0 already in range).

## Method
- Split: even-indexed bifolia = train, odd = test (as h34).
- Word-shape model per hand (train only): glyph 3-gram LM with word-start/end markers (`^`, `$`), add-k smoothing.
  Also record, per glyph, P(word-final) vs P(word-internal) ("ambiguity").
- Re-spelling: each generator word *type* is mapped (fixed, type-level, so repetition/copy structure is kept)
  to a fresh string sampled from the shape model, with length matched to the original ±1; distinct types stay distinct.
  The h34 gap rule (fit on train, s chosen per cell to match train junction, as h34) is applied after re-spelling.
- Generators: C0, Naibbe-Italian(Boccaccio)+5% swap copy, Naibbe-nonsense.
- Controls: (a) shape off = h34 result recomputed; (b) shuffled shape model = LM trained on train words whose
  glyphs are permuted within each word; (c) nonsense plaintext (Naibbe-nonsense).
- Fingerprint: h20 5-statistic fingerprint on the shape-on, s* streams.

## Predictions (each per hand × generator cell, 9 cells)
- P1 (main): with shape on, S falls inside 0.72–0.80 (hand's MS test S ± 0.04 also reported) in ≥ 6/9 cells.
- P2: junction link J keeps ≥ 60 % of MS train J in ≥ 7/9 cells.
- P3: PMI-table correlation T with MS test ≥ 0.85 in ≥ 7/9 cells.
- P4: inventory (types per 5k tokens) stays within ±30 % of the shape-off generator in ≥ 7/9 cells.
- P5: fingerprint 5/5 in ≥ 6/9 cells.
- P6 (control): shuffled shape model leaves |S − MS| larger than real shape model in ≥ 6/9 cells.
- P7 (control): Naibbe-Italian and Naibbe-nonsense end within 0.03 S of each other in all 3 hands
  (i.e. the effect does not depend on a real language).
- P8 (diagnostic): the glyphs with the largest per-glyph contribution to the S gap (shape off) are glyphs that
  are frequent both word-finally and word-internally in MS (expected: y, l, r, n/in-family, o-adjacent).
- H-shape supported if P1, P2, P3, P6 hold.

No translation or meaning claims.
