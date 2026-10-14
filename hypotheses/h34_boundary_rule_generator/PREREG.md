# h34 — per-hand word-gap rule generator (pre-registration)

Written and committed **before any h34 number was computed**. Statistics only; no meaning or translation claims.

## Question
h31 found that a word's last glyph predicts the next word's first glyph (excess MI 0.11/0.21/0.23 bits for 1A/2B/3B; all natural texts lower; generators ≤ 0.004). h33 found spaces are predictable from ±2 glyphs (.750/.811/.820). Does adding an explicit **word-gap rule** to existing generators reproduce both effects while keeping the generators' inventory and the h20 five-statistic fingerprint (D1–D5)?

## Data and held-out split
- MS lines per hand (1A, 2B, 3B) from `h30_lib.load_ms`. Pages are split by bifolium: sorted bifolium ids, even index = **train**, odd = **test**. All rule tables and the rule strength are fitted on train pages only; MS targets are computed on test pages only.

## Generators (base streams, ~10,500 tokens, 9-word lines)
- (a) **C0** copy-modify (h12) fitted on the hand's train pages.
- (b) **Naibbe-Italian (Boccaccio) + swap copy c=.05** (h27 `encrypt_swap`, real plaintext).
- (c) **Nonsense-plaintext Naibbe** (h27 Zipf pseudo-word plaintext, same cipher + swap copy).

## Gap-rule layer
Fitted table: r(f | l) = P(first glyph f | previous last glyph l) / P(f), add-1 smoothed, from within-line adjacent pairs of the hand's train lines. Generation: tokens are emitted from the base stream in order; at each within-line gap the next word is chosen from the next K = 10 queued base tokens with weight r(f|l)^s (a local reordering: no new word types are created). Line-initial words are taken in order (rule scope: within line). Strength s ∈ {0, 0.5, 1, 1.5, 2, 3}; s* per hand × generator = the s whose train-page junction MI is closest to the hand's train-page value.

Controls: **s = 0** (baseline = reordering-free); **shuffled table** (rows of r permuted between last glyphs, same s*); **all-gaps** variant (rule also applied across the line break).

## Measures (on generated lines; MS on test pages)
- **J**: junction MI(last glyph → next first glyph) minus within-line shuffle null (h33 `junction`), in two variants: within-line (all pairs) and **edge-excluded** (first and last word of each line dropped).
- **J_end**: the same with the h31 affix-model ending (M3) in place of the last glyph; "last-glyph-beats-ending" = J > J_end.
- **T**: table agreement = Pearson r between generated and MS-test PMI(l,f) over cells with ≥ 20 MS pairs.
- **S**: h33 space predictability (entropy removed).
- **V**: types per 5,000 tokens relative to s = 0.
- **F**: h20 fingerprint n/5 (bifolium scheme) for s* cells and s = 0, real tables.

## Predictions (pass/fail fixed now)
- **P1 (junction)**: at s*, J (within-line) falls within ±35% of the hand's test-page J for ≥ 7 of 9 hand × generator cells.
- **P2 (pattern)**: J > J_end in ≥ 7/9 s* cells.
- **P3 (specificity)**: T(real table) ≥ 0.6 and T(shuffled) ≤ 0.3 in ≥ 7/9 cells.
- **P4 (spaces)**: S ∈ [.75, .82] in ≥ 6/9 s* cells. (Expected risk: generators start at .82–.88; a reordering cannot lower S much, so P4 may fail.)
- **P5 (inventory)**: V within ±5% of 1 in all s* cells (true by construction; a sanity check).
- **P6 (fingerprint)**: generator (b) at s* keeps 5/5 for ≥ 2 of 3 hands; no s* cell loses more than one statistic vs its s = 0 version.
- **P7 (edge)**: edge-excluded J of MS test pages stays ≥ 50% of within-line J (signal is not a line-edge artifact), and generated s* cells match it within ±35% for ≥ 6/9.

Overall **H-gap supported** if P1, P2, P3, P6 pass. Supported or not, a matched rule only shows the effect can be produced by a gap rule; it says nothing about content.
