# h17 — published plant identifications and pharmaceutical labels as cribs

Pre-registered in [PREREG.md](PREREG.md) (commit e499f8c, before any statistic was computed). **No translation claims.** Plant identifications for MS 408 are contested: almost none is accepted by everyone, and different authors propose plants from different continents. Here they are only used as *independent labels* that a meaning-bearing text might track.

## 1. Plant-ID table
`data/plant_ids.csv` has 239 proposals for 107 herbal folios from 8 source groups: Petersen (with O'Neill and Holm), ELV Grolier, ELV Beinecke, Zandbergen comments in ZL3b, Tucker & Talbert / Janick, Vatne 2022, and Sherwood/Bax. Sources are listed in `sources/SOURCES.md`. `results/plant_id_consensus.csv` gives the most-named genus per folio and how many sources name it:

- 46 folios have a genus named by ≥ 2 sources, and 13 by ≥ 3. Many of those agreements are Petersen + ELV, who are not independent.
- **Strongest consensus**: f9v *Viola* (6 sources). Then, with 3–4 sources each: f2r *Centaurea*, f1v *Atropa*, f25v *Plantago*, f29r *Arctium*, f2v *Nymphoides/Nymphaea*, f31r *Hyoscyamus*, f32r *Mentha*, f4r *Hypericum*, f51v *Lycopsis*, f56r *Borago*, f65v *Anthemis*, f6v *Ricinus*.
- Tucker & Talbert disagree with the European IDs on most of the folios they cover. They propose New World genera, sometimes in the same family (f6v Euphorbiaceae, f32r Lamiaceae).
- Pharmaceutical ↔ herbal "same plant" correspondences: 12 come from ZL3b comments (Petersen, Stolfi, FSG, GL; 9 are marked `?`), 4 from Petersen's marginal cross-references and 2 from Tucker & Talbert. 16 of these pairs could be used. The rest have no labels on the pharmaceutical side or point to the wrong section.

## 2. Results (10,000 draws each; Holm over the 11 primary p-values)

| Test | Statistic | Observed | Null mean | p | Holm |
|---|---|---|---|---|---|
| A: pharma labels ↔ matched herbal folio (16 pairs), null = same quire × hand × language | S1 edit similarity to paragraph-initial words | 0.221 | 0.209 | 0.21 | 1 |
| | S2 vocabulary Jaccard | 0.0049 | 0.0049 | 0.50 | 1 |
| | S3 shared 3-letter start | 0 | 0.005 | 1 | 1 |
| B: same genus (59 pairs), null = HL permutation | F1 first-word similarity / F2 paragraph-initial / F3 vocabulary | 0.205 / 0.399 / 0.065 | 0.242 / 0.416 / 0.061 | 0.94 / 0.75 / 0.16 | 1 |
| B: same family (406 pairs) | F1 / F2 / F3 | 0.220 / 0.393 / 0.060 | 0.232 / 0.403 / 0.060 | 0.83 / 0.70 / 0.50 | 1 |
| C: Bax crib words vs other folios of the same genus (k = 1) | max edit similarity | 0.405 | 0.279 | 0.23 | 1 |
| C: Bax crib words vs other folios of the same family (k = 4) | max edit similarity | 0.323 | 0.225 | **0.0004** | **0.004** |

Secondary results:
- A gives the same answer under the hand × language null (p 0.46 / 0.78 / 1) and the unrestricted null (0.42 / 0.67 / 1).
- B also fails with consensus ≥ 2 (only 3 genus pairs), with ELV merged, and under the quire × HL null (genus F3 p = 0.07, the lowest).
- No pharmaceutical label equals a word on its matched herbal folio more often than chance. The few shared words (in `results/A_pairs.csv`) are common short words.

**The one pass (C, family level) is fragile and should not be read as a crib:**
- **One crib drives most of it.** `keerodal`, the word above f41v that Bax read as coriander, resembles the paragraph-initial words of two other Apiaceae folios: `ksheodal` (f90v1) and `ke'chdy` (f34v). Its own p is 0.008. Without it, the combined p is 0.08 (after the crib folios are also dropped).
- **Ranunculaceae part:** f29v `kooiin` matches f3v `koaiin`. Both are folios that Bax himself put in Ranunculaceae. `kooiin` also opens f2v (water lily), so the word is not specific to one family.
- **Dropping Bax's own IDs, or the four crib folios as targets, leaves p at 0.003–0.005.** These are secondary results with no correction.
- **Calibration:** I treated the paragraph-initial word of each of the 120 identified folio × family cases as a pseudo-crib. 5 % of them reach p < 0.05, and 7.7 % of the k-initial ones (Bax's words all start with k-). So one crib at p < 0.01 among four is unusual, but not remarkable.
- **The cribs were not chosen blind.** Bax picked them after studying the pages, and family-level sharing of a k-…-dal shape is a long way from reading a name.

## 3. Predictions
- P1 (labels track the matched herbal folio): **fails**.
- P2 (same-plant folios have more similar first words or vocabulary): **fails**. Same-genus pairs are, if anything, *less* similar than chance.
- P3 (Bax cribs consistent beyond chance): **nominally passes at family level, fails at genus level**. The pass rests on one crib, so it is a weak lead and not a confirmation.

## 4. Limits
- The IDs are contested, partly dependent (Petersen and ELV) and partly transcribed from search snippets. Tucker & Talbert and Vatne coverage is incomplete, and the genus/family normalisation is mine.
- Pharma "same plant" positions (`f102r1[3,2]`) cannot be mapped to single labels, so whole-page labels are used. That dilutes test A, and pharma pages have only 4–33 labels.
- Quires and hands barely vary within a plant group (h09/h10), so the stratified nulls have low power. A null result is absence of evidence.
- Bax crib spellings were taken from the transcription at the loci he describes; his paper was not re-checked letter by letter.
- n is small everywhere: 16 pharma pairs, 3 high-consensus genus pairs, 4 cribs.

## 5. Next step
Test the one lead out of sample. Pre-register a list of Apiaceae folios whose identification does **not** come from Bax: a new botanical pass, or Tucker & Janick's full list once it is obtained. Then check whether `k…dal/k…dy`-shaped paragraph-initial words are enriched there against the same hand × language null. Also digitise the pharma row/column label layout so that test A can use individual labels.

## Files
`h17_lib.py`, `run_h17.py`, `test_h17.py`, `data/` (plant IDs, extra pairs, Bax cribs), `sources/SOURCES.md`, `results/` (`summary.json`, `A_pairs.csv`, `C_bax_cribs*.csv`, `plant_id_consensus.csv`, `run_log.txt`).
