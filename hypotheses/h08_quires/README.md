# h08 — Quire map of MS 408 and quire-level confidence intervals

**Question.** The repo's MS 408 CIs used an 8-page-block jackknife as a *stand-in* for the codicological unit.
Quires (and the scribes' bifolia) are the real units of production. Do the CIs change if whole quires are resampled
instead, and do any earlier verdicts flip?

## 1. Quire map — `data/quires.csv` (+ `quire_summary.csv` here)

Built by `msdecipher.quires.write_quire_map()` from the ZL3b page headers, with the literature's collation added.
There is one row per transcription page (226 rows). Columns:

| column | meaning | source |
|---|---|---|
| `page`, `leaf` | page id, folio number | ZL3b |
| `quire_letter`, `quire` | `$Q` A–T → 1–20 (P = 16 and R = 18 are lost) | ZL3b / IVTFF [1] |
| `lfd2020_quire` | same quire in Fagin Davis' 18-quire article numbering | [3] |
| `page_in_quire`, `folio_in_quire`, `bifolio` | `$P`, `$F` (a–f first half, u–z second half), `$B` (counted from the outside) | ZL3b / IVTFF [1] |
| `bifolium_id`, `conjugate_leaf` | `Q08-B1`; the conjugate leaf (same `$Q`/`$B`, mirror `$F`: a↔z, b↔y …). `missing` = conjugate is lost | derived |
| `position_in_quire`, `leaves_in_original_quire` | leaf position in the *original* gathering (B for the first half, 2n+1−B for the second half; n = original bifolia) | derived + [2][3] |
| `foldout` | panel-numbered pages (f67r1 …) or `$P` letters spanning more than 2 page slots (f101) | ZL3b |
| `currier_language`, `lfd_hand`, `currier_hand`, `illustration`, `section` | `$L`, `$H` (Fagin Davis' 5 hands, `@` = unassigned), `$C`, `$I` | ZL3b [1][3] |
| `quire_missing_leaves` | leaves lost from that quire | [2][3] |

Summary (20-quire numbering): 18 of the 20 conventional quires survive. Q16 (f91–92) and Q18 (f97–98) are wholly lost.
Missing leaves: **f12** (Q2, conjugate of f13), **f59–f64** (three central bifolia of Q8), **f74** (Q12, conjugate of f73),
**f91–92** (Q16), **f97–98** (Q18), **f109–110** (central bifolium of Q20).
Foldouts: f67, f68, f70, f72, f85, f86, f89, f90, f95, f101, f102.
Hands: Q1–3, Q15 and Q19 are hand 1; Q9–12 are hand 4 (astronomical/zodiac); Q13 and Q14 are hand 2; Q20 is hand 3. Hand 5 is on the f41/f48 bifolium (Q6) and on f57r/f66 (Q8).
Hands 1/2 alternate by bifolium in Q4–Q7.

### Sources
1. R. Zandbergen, *IVTFF format description*, voynich.nu/software/ivtt/IVTFF_format.pdf. Definitions of `$Q $P $F $B $L $H $C $I`; ZL3b transcription, voynich.nu. The `$H` hands are Fagin Davis'.
2. R. Zandbergen, voynich.nu quire pages, e.g. https://www.voynich.nu/q08/index.html ("Quire 8 probably used to contain 5 normal-sized bifolia. The three central bifolia are lost."). Per-page Currier language and LFD hand are also given there.
3. L. Fagin Davis, "How Many Glyphs and How Many Scribes? Digital Paleography and the Voynich Manuscript", *Manuscript Studies* 5(1) (2020) 164–180. Collation 1–7⁸ (2⁸⁻¹ lacking f12), 8¹⁰⁻⁶, 9–11², 12²⁻¹, 13¹⁰, 14¹, 15⁴, 16⁸⁻⁴ (lacking 91–92, 97–98), 17⁴, 18¹⁴⁻². Five scribes; 1/2 alternate by bifolium. 78v/81r was originally the innermost bifolium.
4. L. Fagin Davis, *Manuscript Road Trip* blog (Voynich posts): the same collation in the conventional 20-quire numbering (16 lacking 91–92, 18 lacking 97–98).

### Disagreements (marked, none resolved by us)
* **Quire numbering.** The 2020 article has 18 quires and treats 20-quire Q16 + Q17 + Q18 as one gathering, 16⁸⁻⁴. Its 17 = Q19 and its 18 = Q20. The IVTFF `$Q`, voynich.nu and LFD's blog use 20 quires. We key on the 20-quire numbering and carry `lfd2020_quire`. *Consequence for resampling:* Q17 (f93–96) is one unit in both schemes, because the lost Q16 and Q18 contribute no text.
* **Q8 original size.** Zandbergen ("probably 5 bifolia") and LFD (8¹⁰⁻⁶) agree. Our `position_in_quire` uses 5.
* **Q20.** 14⁻² (LFD) = 7 bifolia, with the central one (f109/110) lost. ZL3b `$B` runs 1–6 for the survivors, consistent with this.
* **Present order vs original order.** LFD argues Q13 was re-folded (78v/81r originally innermost). `bifolio`/`position_in_quire` follow the *present* binding as encoded in ZL3b, not the reconstruction.
* **Hands.** We take `$H` verbatim from ZL3b, which is LFD's assignment as transcribed by Zandbergen. A few pages have `$H` but no `$L` (e.g. f57v, Q9–12 labels).

## 2. Quire-level resampling (code)

The existing APIs and defaults are unchanged. Additions:
* `controls_ci.make_group_blocks(pages, keys)` groups pages by any key (quire, bifolium). It plugs into `resample_blocks` / `leave_out` / `jackknife_se`.
* `controls_run.ms_pages_named()`, `resample_ms_groups(pages, keys, segs, B, …, name)`, `group_ci_table(point, reps, name)`. These give a group bootstrap and a delete-one-group jackknife for every controls metric.
* `mech_hybrid_topics.ms_uncertainty(docs, n_boot, seed, group_of=None)`. When `group_of` maps folio → group, it runs a cluster bootstrap over groups and adds `*_jack_se`.
* `quires.group_folds(units, df, k, level, seed, labels)` gives k folds in which no quire (`level="quire"`) or no bifolium (`"bifolium"`, so conjugate leaves are never split) occurs in both train and test. `quires.leakage()` checks this. `quires.group_units()` maps page/leaf names to group keys.

Run: `python hypotheses/h08_quires/run_h08.py --boot 100` (~5 min on 8 cores). Tests: `python -m pytest hypotheses/h08_quires`.

## 3. Results

Only 17 quires carry running text (Q12 f73 has labels only). The quire jackknife therefore has 17 unequal groups (Q20 = 23 pages, Q13 = 20 pages). The CIs are est ± 1.96 · jackknife SE, the same convention as `reports/controls/ms408_ci.csv`.

| metric (collapsed) | estimate | SE page | SE 8-page block | **SE quire** | SE bifolium | old CI | **quire CI** |
|---|---|---|---|---|---|---|---|
| h2 (unit cond. entropy) | 2.217 | 0.020 | 0.047 | **0.079** | 0.037 | 2.125–2.309 | **2.062–2.372** |
| within-word shuffle gap in h2 (shuffled 3.56 − 2.22) | 1.348 | 0.024 | 0.035 | **0.059** | 0.030 | 1.280–1.416 | **1.232–1.463** |
| Zipf s (MLE, ranks 10–1000) | 0.985 | 0.013 | 0.025 | **0.044** | 0.023 | 0.936–1.034 | **0.898–1.071** |
| Heaps β (in order) | 0.745 | 0.020 | 0.017 | **0.021** | 0.014 | 0.706–0.784 | **0.703–0.786** |

* Across all 23 metrics, the quire SE is a median **1.67×** the 8-page-block SE (range 0.71–2.25×). For h2, the shuffle gap and Zipf it is about 1.7×; for Heaps it is 1.06× against the SE used before.
* The **bifolium** jackknife is *smaller* than the 8-page block (median 0.85×). Conjugate leaves are not the dependence unit; whole quires (section + scribe + language runs) are.
* The shuffle gap stays far from 0 (lower bound 1.23). The within-word-order effect is untouched.

**Verdicts against the control families** (`verdict_flips.csv`). We recomputed the prediction-interval verdict with SE = max(old SE, quire SE). **8 of the 828 MS-vs-family cells flip, all from outside to inside (≈).** None reverses direction:
* the abjad family on unit_h3 (collapsed)
* Vigenère on type-token ratio (collapsed and raw)
* the slot-grammar generator on 5 cells: shuffle gap h2 (raw), h2/H1 (raw), shuffle gap/H1 (raw), and the adjacent identical-word rate (collapsed and raw)

The slot-grammar generator moves from 15/23 to 17/23 within (collapsed) and becomes closer to MS 408 than the anagram family (17/23). The family ranking otherwise holds.

**Section signal** (`section_ci_quire.csv`):

| stat | estimate | folio bootstrap (old) | quire cluster (SE = max(boot, jack)) | bifolium cluster |
|---|---|---|---|---|
| NB balanced accuracy | 0.723 | 0.677–0.770 (SE 0.024) | **0.523–0.924** (SE 0.102; percentile 0.514–0.771) | 0.649–0.798 (SE 0.038) |
| JS between sections (bits) | 0.406 | 0.373–0.440 (SE 0.017) | **0.276–0.537** (SE 0.067) | 0.323–0.489 (SE 0.042) |

Flips:
* **NB 0.723 vs drift-null max 0.611.** With folio and bifolium resampling it is above the drift null. With **quire** resampling the lower bound, 0.52, falls below 0.611. "Beyond drift" is **no longer significant at the quire level**.
* **JS 0.406 vs best no-plaintext generator 0.357 (h06).** It was already inside the folio CI's reach (lower 0.373, just above). With quire resampling the CI is 0.276–0.537, so **the "JS gap" is not significant**. "JS above the shifted-label null 0.246" survives barely (lower bound 0.276).
* The JS bootstrap percentile intervals lie *above* the estimate (resampling with duplicate folios inflates JS). Use the jackknife-based CI.

**Leak-free held-out classification** (utility demo, 5 seeds × 5 folds, label-balanced). Bifolium folds give NB **0.670** (vs 0.723 with stratified folio CV, which puts conjugate leaves on both sides). Quire folds give **0.321**. The quire result is not a fair test of section vocabulary: biological = Q13 only and pharmaceutical = Q15/Q19, so holding out a quire often removes most of a class from training. Sections and quires are nearly confounded, so section and quire effects cannot be separated by resampling alone. This is the main caveat on every section-level claim.

## Files
`run_h08.py`, `test_h08.py` (10 tests), `quire_summary.csv`, `ms408_ci_quire.csv` (all metrics, page / block8 / quire / bifolium SEs and ratios), `verdict_flips.csv`, `section_ci_quire.csv`, `results.json`; `data/quires.csv`; `src/msdecipher/quires.py`.
