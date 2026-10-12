# h18 pre-registration: out-of-sample test of the h17 `keerodal` (Apiaceae) lead

Committed before any h18 statistic was computed. No translation claims.

## Lead being tested
h17: Bax's coriander crib `keerodal` (f41v) resembled paragraph-initial words of the other Apiaceae folios f90v1 `ksheodal` and f34v `ke'chdy`. Those three folios were used to find the lead, so they are **excluded** from both the target set and the comparison pool. The other Bax folios (f2r, f3v, f29v, f16r) are also excluded.

## Target set (data/apiaceae_folios.csv), from non-Bax sources
- **Primary:** f16v (ELV, Tucker & Janick *Eryngium*), f31v (Petersen *Heracleum*; Vatne), f50v (O'Neill "Umbellifera?"), f65r (Petersen marginal *Oenanthe*), f33v, f39v, f96r (Vatne 2022 Apiaceae "kor/kar" group).
- **Caveat:** Vatne grouped her plants partly by **word** similarity (k-initial "kor/kar" names). Her IDs are therefore not independent of word shape, which biases the test toward a pass. Pre-registered sensitivity: **S-noVatne** = {f16v, f31v, f50v, f65r}. **A pass counts only if it holds in S-noVatne.**
- **Comparison pool:** all other herbal folios (ZL3b section = herbal) minus the excluded folios.

## Shape definitions (EVA from ZL3b, h13 tokenisation, `'` removed)
- `KDAL`: regex `^k[a-z]*dal$`
- `KDY`: regex `^k[a-z]*dy$`
- **Primary shape** `SHAPE` = KDAL ∪ KDY ∪ {w : 1 − lev(w, "keerodal")/max(len) ≥ 0.5 and w starts with k}

## Outcomes (per folio, averaged over targets)
- O1: first word of the folio's text is in SHAPE (0/1).
- O2: share of paragraph-initial words in SHAPE.
- O3: share of all running-text and label tokens in SHAPE.

## Nulls
Permute the Apiaceae flag among herbal folios **within quire × hand × language strata**, 10,000 times. Folios in single-member strata are uninformative. As a secondary null, permute within hand × language only. One-sided p (target > null).

## Calibration
Random word-shape cribs of the form `^X[a-z]*Y$`, where:
- X is a single initial EVA glyph;
- Y is a word ending of 2–3 characters;
- the shape's overall token rate in the herbal pool is within a factor of 2 of SHAPE's.

Run up to 200 such shapes through the same O1–O3 × quire×HL procedure, and report the percentile of SHAPE's p among them.

## Correction and verdict
- Holm over the 6 primary tests: O1–O3 × {primary set, S-noVatne}.
- **P1 (lead replicates):** at least one outcome passes Holm < 0.05 in S-noVatne **and** SHAPE's p is in the lowest 5 % of the calibration shapes.
- Expectation stated in advance: P1 fails. There are 4–7 target folios and low power.

## Pharma label layout (redo of h17 test A)
ZL3b gives pharma "same plant" positions as `[row,col]`. The labels in the transcription carry Petersen numbers (`<!68a>`), not grid positions. Mapping these needs image-based layout work, which is out of scope unless a published row/column ↔ label table is found. If no such table is found, h17 test A is **not** redone, and that is reported.
