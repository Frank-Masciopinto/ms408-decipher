# h36: similarity-preserving re-spelling

Pre-registered in [PREREG.md](PREREG.md) (commit eea4e97) before computing. Builds on h35 (type-level word-shape
re-spelling fixed space predictability S but broke the fingerprint) and h34 (word-gap rule). No translation or meaning claims.

**Method.** Per hand, train = even bifolia, test = odd bifolia. Generator words (C0, Naibbe-Italian Boccaccio + 5 % swap
copy, Naibbe-nonsense) are re-spelled glyph by glyph: `pos` maps each glyph by its position class (initial / internal /
final) via frequency-rank matching to the hand's train glyphs; `ctx` also conditions on the previous glyph. h34 gap rule
applied after. Controls: shape off (= h34), shuffled per-class map, nonsense plaintext, h35 type-level re-spelling.
E = share of edit-distance-1 type pairs still within distance 1. Run: `python run_h36.py measures && python run_h36.py fingerprint && python summarise.py`.

**Result** (full table: [results/summary.md](results/summary.md)).

| | MS S | S off | S pos | S ctx | S h35 | E pos | E ctx | E h35 | fingerprint pos |
|---|---|---|---|---|---|---|---|---|---|
| 1A | .724 | .72–.84 | .78–.95 | .74–.92 | .72–.74 | .84–.89 | .39–.82 | .01 | 4, 4, 5 |
| 2B | .798 | .80–.84 | .89–.90 | .84–.88 | .78 | .91–.95 | .54–.68 | .01 | 5, 4, 5 |
| 3B | .792 | .81–.85 | .85–.91 | .85–.89 | .79–.80 | .83–.96 | .46–.78 | .01 | 5, 5, 5 |

- **P1 fails (1/9)**: glyph-level maps push S *up* (.78–.95), further from MS than no re-spelling. `ctx` is closer but also 1/9.
- **P5 passes (6/9 at 5/5, rest 4/5)**: keeping glyph-level edit structure restores the copy statistics h35 lost (2–3/5).
- P6 fails narrowly (4/9 with E ≥ .9; all ≥ .83 for `pos`, vs .01 for h35). P2/P3/P4 pass 9/9 (link kept, table r .95–.98, inventory unchanged).
- P7 pass 7/9 (shuffled map S .93–.95). P8 pass: Italian and nonsense within .01 for every hand.

**Verdict.** H-sim not supported. There is a trade-off: a glyph-by-glyph map keeps near-copies near and the 5/5
fingerprint, but rank-matching glyphs collapses spelling variety and makes spaces *more* predictable than MS; the
word-level shape model that fixes S (h35) destroys near-copy relations. No re-spelling here does both.
Plaintext still makes no difference (nonsense = Italian).

**Limits.** One transcription (ZL3b); rank-matching is a crude map (many-to-one, not fitted to S); only position and
previous-glyph context; E counts top-2000 types only; s grid coarse.

**Next.** Copy-aware respelling: re-spell only a word's *source* type with the h35 shape model and derive its near-copies
by applying the same edit to the re-spelled source (copy edits replayed after shape), then re-test S and the fingerprint.
