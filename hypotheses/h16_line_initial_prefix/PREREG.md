# h16 pre-registration: is the 2B/3B line-start habit an added onset? Does 1A have its own line-edge words? (committed before computing)

**Data:** ZL3b P lines, h14 `table()`, with nulls S1 (HL × word-count bin × glyph-count bin × first line × gap/short) and S1L (S1 + word-length bin).

**Test statistic for a token attribute a (indicator or numeric):** the sum of a over line-initial (or line-final) slots, compared with its exact permutation mean and variance when tokens are shuffled within strata: E = Σ_s m_s·ā_s, Var = Σ_s m_s σ²_s (N_s − m_s)/(N_s − 1). Report z, a two-sided normal p, and the ratio obs/E.

## A. Onset hypothesis (2B and 3B, each separately and pooled with HL kept in the strata)
Onset set O = {d, s} (primary). As a secondary test, any first EVA glyph in {d, s, o, y, q, ch, sh}, with ch/sh treated as one onset unit.
stripped(w) = w minus its onset, if the remainder is ≥ 2 characters.
Attributes:
- a1 = has an O onset;
- a2 = stripped(w) is a "common word": among the top 200 types of NON-initial tokens of the same HL;
- a3 = stripped(w) equals the right neighbour;
- a4 = log(1 + mid-line count of stripped(w)) in the same HL, where mid-line means neither initial nor final; 0 if not strippable.

Tests:
- (i) all tokens: a1 and a2 at initial vs the S1/S1L null;
- (ii) within O-onset tokens only (strata as before): a2, a3, a4 at initial vs other positions.

**Predictions:**
- A1: initial tokens carry d/s onsets more than the null under S1 and S1L (z > 3).
- A2 (prefix hypothesis): among d/s-onset tokens, initial ones have stripped forms that are common words more often than non-initial d/s tokens (a2 and a4 enriched, z > 3, S1 and S1L).
- A3: a3 (stripped = right neighbour) is not enriched (|z| < 2).
If A2 fails, the habit is a choice of specific word types, not a productive prefix.

## B. Open search
For each HL in {1A, 2B, 3B}: every word type with ≥ 20 P tokens in that HL, at initial and final slots, under S1 and S1L. p comes from the same normal approximation, applied to the indicator "is word w". Words with expected count < 5 are only reported when obs ≥ 5. Holm correction within each HL × null over all words × 2 slots. A word is a line-edge word if it is enriched with Holm < 0.05 under both S1 and S1L.

**Predictions:**
- B1: 1A has ≥ 3 line-initial and ≥ 3 line-final words of its own.
- B2: the 1A line-initial set overlaps the 2B/3B set in ≤ 2 words.
- B3: am/dam/dy-type finals (-am, -dy) appear in all three HLs.

No translation or meaning claims.
