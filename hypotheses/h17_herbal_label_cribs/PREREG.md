# h17 pre-registration: herbal plant identifications and pharmaceutical labels as cribs

Written before any statistic below was computed. No translation claims will be made.

## Data
- `data/plant_ids.csv`: folio -> proposed taxon per source (see `sources/SOURCES.md`). Consensus for a folio's genus = number of independent sources naming it (ELV Grolier/Beinecke and Petersen count separately but are known to be related; also report with ELV merged).
- Pharma-herbal correspondences: ZL3b "Same plant as" comments + `data/pharma_herbal_pairs_extra.csv`. Pharma side = all label words (gtype L, ≥3 chars) of the pharma page/panel (row,column loci cannot be mapped to individual labels; limitation).
- Text: ZL3b, h09 tokenisation; hand × language and quire from `data/quires.csv`.

## Tests (one family, Holm across all primary p-values)
Similarity measures: S1 = max normalized edit similarity (1 − lev/maxlen) between any pharma label and the herbal folio's paragraph-initial words; S2 = Jaccard of word sets (≥3 chars); S3 = share of pharma labels whose first 3 chars match a herbal paragraph-initial word's first 3 chars.

- **A (pharma label ↔ matched herbal folio)**: mean S1, S2, S3 over pairs vs null replacing each herbal partner by a random herbal folio of the **same quire and same hand × language** (fallback: same hand × language when the quire stratum has 1 folio; reported). 10 000 draws. Also an unrestricted (any herbal folio) null as secondary.
- **B (same plant by independent sources)**: herbal folio pairs whose genus sets intersect (B-genus) / family sets intersect (B-family), weighted by min consensus; statistics = weighted mean first-word edit similarity (F1), paragraph-initial edit similarity (F2), vocabulary Jaccard (F3). Null: permute taxon assignments among folios within hand × language strata (10 000), plus a within-quire-and-HL permutation (secondary; low power expected). Also "high consensus" subset (genus named by ≥2 sources).
- **C (Bax cribs)**: for each crib word, mean max edit similarity to paragraph-initial words of other folios assigned the same genus / family by any source vs random folios of the same hand × language (10 000). Combined statistic = mean over cribs.

## Predictions
- P1 (meaning-bearing labels): A beats the quire×HL null on ≥1 measure after Holm.
- P2: B-genus or B-family beats the HL null after Holm on ≥1 measure.
- P3: C combined beats the null (Holm).
Expectation stated in advance: given h09/h13 (no image link survives quire×hand control), we expect P1–P3 to fail; a pass would be a lead, not a decipherment.
