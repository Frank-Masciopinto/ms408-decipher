# h35: per-hand word-shape model (space placement)

Pre-registered in [PREREG.md](PREREG.md) (commit 1410b0a) before computing. Builds on h33 (space predictability S)
and h34 (word-gap rule generator). No translation or meaning claims.

**Method.** Per hand, a glyph 3-gram model with word-start/end markers is fitted on even-indexed bifolia.
Each generator word *type* (C0, Naibbe-Italian Boccaccio + 5 % swap copy, Naibbe-nonsense) is mapped to a fresh,
distinct word sampled from that model (length ±1); the h34 gap rule (s* matched to train junction) is applied after.
Scored on held-out odd bifolia. Controls: shape off (= h34), shape model trained on within-word shuffled glyphs,
nonsense plaintext. Run: `python run_h35.py measures && python run_h35.py fingerprint && python summarise.py`.

**Result** (full table: [results/summary.md](results/summary.md)).

| | S (MS test) | S shape off | S shape on | S shuffled shape |
|---|---|---|---|---|
| 1A | .724 | .72–.84 | .72–.74 | .23–.30 |
| 2B | .798 | .80–.84 | .78 | .31–.34 |
| 3B | .792 | .81–.85 | .79–.80 | .26–.32 |

- P1 pass: S enters 0.72–0.80 in 8/9 cells (3B Naibbe-Italian .800, just on the edge); within ±.04 of the hand in 9/9.
- P2/P3/P4 pass 9/9: junction link kept (J .10–.26 vs MS train .10–.25), gap table r .92–.97, inventory unchanged.
- **P5 fails 0/9: fingerprint drops to 2–3/5.** D2 (cache gain), D3 (5-word copy rate) and D4 (word vs glyph dominance) break.
  Independent type-level re-spelling turns near-copies (one-glyph edits) into unrelated words, so the copy structure is lost.
- P6 pass 9/9: a shuffled-glyph shape model wrecks S (.23–.34). P7 pass: Italian and nonsense plaintext land within .01–.03.
- P8 diagnostic: the S gap is driven by glyphs that are both word-final and word-internal — `l` (Naibbe ends words in `l`
  only 46 % of the time vs 74 % in 1A), `y`, `r`, plus `o`, `s`, `d` placement.

**Verdict.** H-shape supported for space placement: per-hand word-internal glyph statistics explain the h34 space gap,
and real language is not needed. But this naive re-spelling breaks the 5/5 fingerprint, so no single generator yet does both.

**Limits.** One transcription (ZL3b); 3-gram shape model; type-level re-spelling ignores edit-distance relations; s grid coarse.

**Next.** Similarity-preserving re-spelling (map glyph segments / Naibbe table entries through the shape model so
one-glyph variants stay one-glyph variants), then re-test S and the fingerprint together.
