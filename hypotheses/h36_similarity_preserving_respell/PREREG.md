# h36 pre-registration: similarity-preserving re-spelling

Written and committed before any computing. Builds on h35 (type-level word-shape re-spelling fixed space
predictability S but broke the fingerprint to 2–3/5 because one-glyph near-copies became unrelated words).
No translation or meaning claims.

**Hypothesis H-sim.** If the re-spelling acts at the glyph level (each glyph re-written by its position in the word),
edit-distance relations survive, so the S fix of h35 and the 5/5 fingerprint can hold at the same time.

**Method.** Per hand, train = even bifolia, test = odd bifolia (h34 split). Generators: C0, Naibbe-Italian Boccaccio
+ 5 % swap copy, Naibbe-nonsense (h34 base streams). Re-spelling variants, fitted on train only:
- `pos`: deterministic glyph map per position class (initial / internal / final; one-glyph words = final), built by
  frequency-rank matching of generator glyphs to MS-train glyphs within each class.
- `ctx`: same, with class × previous original glyph buckets (fallback to `pos` when a bucket has < 30 tokens).
The h34 gap rule is applied after re-spelling (s* matched to train junction J). Controls: `off` (h34), `shuf`
(random per-class bijection of the MS-train glyph set), nonsense plaintext, and h35 type-level re-spelling (reference).

**Measures.** S (space predictability, MS test), J (h31 gap link), T (h34 table r), inventory ratio V, fingerprint
n/5 (h20), and E = share of base type pairs at edit distance 1 (top 2000 types) still at distance ≤ 1 after re-spelling.

**Predictions** (9 cells = 3 hands × 3 generators, best of pos/ctx chosen per prereg: `pos` is primary, `ctx` secondary):
- P1: S in [.72, .80] in ≥ 6/9 (primary variant).
- P2: J ≥ .6 × MS-train J in ≥ 7/9. P3: T ≥ .85 in ≥ 7/9. P4: |V−1| ≤ .3 in ≥ 7/9.
- P5: fingerprint 5/5 in ≥ 6/9.
- P6: E ≥ .9 in ≥ 7/9 (h35 reference expected ≈ 0).
- P7: `shuf` moves S further from MS than primary in ≥ 6/9.
- P8: Italian vs nonsense S within .03 in 3/3 hands.
H-sim supported if P1, P5, P6 pass. If P1 passes but P5 fails, the S fix and the copy structure are in conflict at the
glyph level too; if P5 passes but P1 fails, positional glyph maps are too weak for space placement.
