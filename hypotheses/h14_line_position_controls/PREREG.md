# h14 pre-registration: do h13's line-position effects survive layout controls? (committed before computing)

**Data.** ZL3b P loci (each locus = a text line). Tokens and slots come from h13's `token_table` (unreadable tokens keep their slot but are not tested or permuted). Hand × language (HL) comes from `data/quires.csv`.
**Line covariates:**
- word count bin: 1–4, 5–7, 8–10, 11+;
- glyph (collapsed-unit) count bin: quartiles;
- first line of a paragraph (`<%>`) vs other lines;
- gap/short flag: the line contains a drawing gap `<->`, OR its word count is < 60 % of its page's median P-line word count.

**Target words:**
- the h13 line-initial enriched set (daiin, dain, saiin, sain, sar, sol, y);
- the h13 line-final enriched set (am, dam, dy);
- the h13 line-initial-depleted (24) and line-final-depleted (15) sets.

**Nulls (Monte Carlo, 10000 draws; Holm within each null over all target word × position tests):**
- **S1, stratified:** readable tokens are permuted across readable slots within strata of HL × word-bin × glyph-bin × first-line × gap/short. The count of word w in initial (final) slots is then a sum over strata of hypergeometric draws, and it is sampled exactly that way.
- **S2, within line:** words are permuted within each line. This keeps every line's composition and length, so it tests position *within* the line.
- Effect = observed / null-mean. p is two-sided Monte Carlo.

**Margin squeezing.** Mean unit length of line-final tokens vs the S1 null mean; also the same per HL. Then a test of am/dam/dy final enrichment that adds a word-length bin (unit length 1–2, 3, 4, 5+) to the S1 strata ("S1L"), so short words are only exchanged with words of the same length.

**Optional: Procrustes.**
- Build per-hand (2B, 1A) PPMI L|R context vectors of the top-100 words over a shared top-300 context vocabulary, each reduced to 20-D by SVD.
- Fit an orthogonal Procrustes map 2B→1A on all other identical words (leave one out) and report identity top-1/top-5 retrieval vs the 1/100 and 5/100 chance rates.
- For the h11/h12 rule pairs (-edy/-ol, -edy/-or, -dy/-ol), report the mapped-partner rank vs random (one-sided sign-flip on rank percentile − 0.5).

## Predictions
- **P1:** at least 5 of the 7 initial enrichments survive S1 and S2 (Holm 0.05).
- **P2:** at least 2 of the 3 final enrichments (am, dam, dy) survive S1 and S1L.
- **P3:** line-final tokens are shorter than the S1 null (margin squeezing exists), but am/dam/dy enrichment survives S1L.
- **P4:** most (≥ 60 %) of the depletions survive S1.
- **P5 (optional):** Procrustes identity top-5 retrieval > 3× chance; rule partners are not ranked better than random (p ≥ 0.05), consistent with h13.

No translation or meaning claims.
