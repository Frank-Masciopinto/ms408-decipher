# h10 pre-registration (committed before any vocabulary statistic; only `inventory.py` metadata/token counts were computed)

Data: ZL3b running text (P, C, R loci; h09 parser), page metadata from `data/quires.csv`.
Stratum = quire × LFD hand × Currier language. Unit = page (folio side). Words with ≥2 occurrences in the contrast set.

## Statistics (same for every contrast)
* **NB**: multinomial naive Bayes (alpha 0.5), leave-one-bifolium-out CV, balanced accuracy (BA).
* **JS**: Jensen–Shannon divergence (bits) between the classes' pooled word distributions (mean over class pairs); **JS excess** = JS − mean of null JS.
* **Nulls**: (a) *stratified permutation*: page labels shuffled only within the contrast's strata (2000 perms; for single-stratum contrasts this is a page shuffle inside that quire×hand); (b) *drift-aware*: labels cyclically rotated along page order within each stratum (all non-identity rotations), which keeps contiguous blocks contiguous.
* **CI**: delete-one-bifolium jackknife of BA and JS excess.
* **Holm** across all pre-registered contrasts of a block (S, H, R), separately for each null; a contrast "survives" only if Holm p < 0.05 under **both** nulls.

## Contrasts
**S — section within the same quire × hand × language** (the only fully non-confounded section contrasts):
S1 Q15|h1|A herbal vs pharmaceutical; S2 Q10|h4 cosmological vs zodiac; S3 Q9|h4 astronomical vs cosmological; S4 Q14|h2|B cosmological vs text-only;
S5 pooled S1–S4 (stratified statistic = token-weighted mean of per-stratum values).
**H — section within the same hand × language, across quires**: H1 hand1 A herbal vs pharmaceutical; H2 hand2 B herbal vs biological vs cosmological; H3 hand3 herbal (Q17) vs stars (Q20; B pages only); H4 hand4 astronomical vs cosmological vs zodiac.
**R — the reverse: hand / language / quire within one section**: R1 herbal, hand 1 A vs hand 2 B, within Q4–Q7 (stratified by quire); R2 herbal Q6 hand 1 vs hand 5; R3 herbal Q17 hand 1 A vs hand 3 B; R4 pharmaceutical Q15 vs Q19 (same hand 1 A: pure quire effect); R5 herbal hand 1 A across quires Q1–Q7 (quire effect within section and hand).
**V — variance decomposition**: Hellinger-transformed page vectors (top 300 words, pages ≥ 50 tokens), linear partitioning (RDA R²) into section, quire, hand, Currier language, page order (cubic). Unique R² = full − drop-one; Freedman–Lane permutation p (999).
**I — h09 rechecks under fixed hand**: (I1) h09 "water" words (qol, olkedy, qokain, qoteedy, qokedy) biological vs herbal within hand 2 B; (I2) h09 "root/jar" words (ctheol, ckhey, qoor, qokeody, qockhey, qokeol, okeol) pharmaceutical vs herbal within Q15|h1|A and within hand 1 A; (I3) h09 "star" words (cheeo, lkaiin, oteey, al, oteedy) stars vs herbal within hand 3 B; (I4) h09 root-word transfer (k = 10 pharma root candidates) restricted to hand 1 A herbal pages, tag shuffled within quire. Statistic: log rate ratio; null: page-label permutation within stratum + frequency-matched random word sets.

## Predictions (stated in advance)
* P1: S1 (herbal vs pharma in one quire and hand) shows a section effect beyond both nulls; S2–S4 are too small to show one (power is low; a null result there is not evidence of absence).
* P2: Within herbal, hand/language effects (R1, R3) are of comparable or larger size (BA, JS excess) than the within-stratum section effects S1–S4.
* P3: In V, quire and section share most of the explained variance; the unique section share is small (< 25 % of the total explained).
* P4: h09 water and star words remain enriched within hand (I1, I3: they are known Currier-B / section words), root/jar words weaken within Q15 (I2), and the root transfer (I4) does not survive.
