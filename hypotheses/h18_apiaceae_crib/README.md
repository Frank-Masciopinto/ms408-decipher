# h18 — out-of-sample test of the h17 `keerodal` / Apiaceae lead

Pre-registered in [PREREG.md](PREREG.md) (commit 0220892, before computing). **No translation claims.**

## Setup
- **Lead under test:** in h17, Bax's coriander crib `keerodal` (f41v) resembled `ksheodal` (f90v1) and `ke'chdy` (f34v). Those discovery folios and all of Bax's folios are excluded here.
- **Targets:** Apiaceae folios proposed by non-Bax sources.
  - Primary set: f16v (Ethel Voynich *Eryngium?*, Tucker & Janick *Eryngium* cf. *heterophyllum*), f31v (Petersen *Heracleum*), f50v (O'Neill "Umbellifera?"), plus Vatne 2022's Apiaceae f33v, f39v and f96r.
  - f65r (Petersen's *Oenanthe* note) has only a label and no running text, so it drops out.
  - Vatne grouped plants partly by word similarity, so the decisive set is **noVatne = f16v, f31v, f50v**.
- **Shape:** `^k[a-z]*dal$`, or `^k[a-z]*dy$`, or a k-initial word with edit similarity ≥ 0.5 to `keerodal`.
  - These words make up 1.0 % of herbal tokens.
  - 5.0 % of folios start with such a word, and 2.6 % of paragraph-initial words are such words.
- **Comparison pool:** 121 herbal folios. The null permutes the Apiaceae flag within quire × hand × language strata (10,000 times). A hand × language-only null is secondary.

## Results

| Set | O1 first word in shape | O2 paragraph-initial share | O3 page-token share | p (quire×HL) | Holm |
|---|---|---|---|---|---|
| primary (6) | 0 / 6 (null 0.084) | 0 (null 0.035) | 0.0158 (null 0.0139) | 1 / 1 / 0.26 | 1 / 1 / 1 |
| noVatne (3) | 0 / 3 (null 0.168) | 0 (null 0.070) | 0.0193 (null 0.0165) | 1 / 1 / 0.23 | 1 / 1 / 1 |

- **First and paragraph-initial words** on the targets: f16v `pchroiin`/`pchocthy`, f31v `podair`/`pcheeody`, f50v `tchy`, f33v `tar`/`tshdy`, f39v `pdair`/`pardy`, f96r `tor`. All are ordinary gallows-initial words; none is k-initial.
- **In-page hits** (O3) are the common forms `keedy`, `keody` and `kchdy`. They occur at roughly the pool rate.
- **Hand × language null:** O3 p = 0.50 (primary) and 0.30 (noVatne).
- **Calibration:** I tested 66 random `^X…Y$` shapes of similar frequency. Only 3 % of them reach p < 0.05 on O3. SHAPE's O3 p sits at the 20th–27th percentile (O1 and O2 are tied at p = 1).

**Verdict:**
- **P1 fails.** The `keerodal` resemblance does not replicate on Apiaceae folios that were not used to find it. The h17 family-level pass is best explained as a post-hoc coincidence among three folios.
- **h17 test A (individual pharma labels) was not redone.** I found no published table that maps ZL3b's `[row,col]` pharma positions to the Petersen-numbered labels. Building one needs image-based layout work.

## Limits
- There are only 3–6 target folios. Each is a contested ID, and Vatne's IDs depend on word shape.
- The shape definition is one pre-registered choice. Other k-shapes were not tried as primary tests, though calibration covers random shapes.
- The quire × hand × language strata leave little freedom for the shuffles.
- A null result is absence of evidence. It rules out only a strong, consistent plant-name word on these pages.

## Next step
Plant-name cribs based on published IDs now look exhausted at this resolution (h09, h17, h18). Two options:
- Build the pharma label ↔ grid layout from the scans, then retest individual labels against their same-plant herbal folios.
- Turn to the likelihood-based model comparison (expert option 3).

## Files
`h18_lib.py`, `run_h18.py`, `test_h18.py`, `data/apiaceae_folios.csv`, `results/summary.json`, `results/run_log.txt`.
