# h11: modelling scribal hand and Currier language, then testing what is left

**Verdict.**
* **Hand × language is a large, real factor.**
  * It explains R² 0.164 of page word profiles alone (section alone: 0.157).
  * It gives the largest held-out gain of any factor: 0.109 bits/token over a global model with whole quires held out, 0.125 with bifolia held out.
  * Section adds only 0.015 bits/token beyond it (0.027 on bifolium folds) and R² 0.079.
* **After residualising on hand × language, a section signal remains and passes both pre-registered nulls**, for all sections together and for herbal vs pharmaceutical:
  * all sections: pseudo-F 2.32, nearest-centroid BA 0.34 vs chance 0.14 (null 0.04); Holm p = 0.005 within-hand permutation, 0.047 within-hand drift rotation;
  * herbal vs pharmaceutical: BA 0.86 vs 0.50, same Holm p (0.005 / 0.047);
  * herbal vs biological and herbal vs stars pass the permutation null but not the drift null (Holm 0.10).
* **After residualising also on quire, nothing remains.** Every residual section contrast has F ≈ 0 and p = 1. Within the hand residuals, section has no unique R² once quire is in the model (0.027, p = 0.56; quire 0.087, p = 0.002). With this manuscript's layout, section and quire **cannot** be separated; "section beyond hand" is equally well "quire beyond hand".
* **The image-linked word sets** (h09 water, star, root/jar) stay enriched on the hand residuals:
  * effects: water +0.26, star +0.05, root/jar +0.24 Hellinger units;
  * against within-hand label permutation and frequency-matched random words: Holm p = 0.01;
  * against the within-hand drift null: Holm p = 0.09 (root/jar), 0.22 (water), 0.26 (star), so none survives that;
  * the herbal root-word transfer gives +0.061 (perm p = 0.011, drift Holm 0.27);
  * on hand + quire residuals all of them vanish (perm Holm ≥ 0.33).
* **Hand differences look partly orthographic and partly lexical.** Up to 10 greedy rewrite rules (learned on half the pages, scored on the other half) close:
  * 22.7 % ± 1.7 % of the herbal hand 1 A vs hand 2 B gap;
  * 13.0 % of the herbal 1 A vs 3 B gap;
  * 11.0 %, 5.3 % and 1.3 % of three within-hand section gaps (1 A herbal vs pharma, 2 B herbal vs biological, 3 B herbal vs stars);
  * −1 % to −4 % for same-cell split halves (noise floor).

  The first rule learned for 1 A ← 2 B is `-edy → -ol` (*chedy → chol*), which is the classic Currier A/B marker. Most of the hand gap (≈ 77 %) is **not** closed by simple substitutions. So the hands look like **one system written with different spelling habits *and* different preferred vocabulary**, more than two independent generators. Rules close the hand gap about twice as well as section gaps, which supports P3 of the pre-registration.

## Results in detail

**1. Held-out models** (`results/heldout_models.csv`; hierarchical Dirichlet back-off unigrams; smoothing chosen on inner folds):

| model | bits/token, quire folds | gain | bits/token, bifolium folds | gain |
|---|---|---|---|---|
| M0 global | 10.879 | – | 10.748 | – |
| M1 +language | 10.797 | 0.082 | 10.678 | 0.070 |
| M2 +hand×lang | 10.770 | 0.109 | 10.623 | 0.125 |
| M3 +HL+quire | 10.770 (quire unseen) | 0.109 | 10.607 | 0.141 |
| M4 +HL+section | 10.755 | 0.123 | 10.596 | 0.152 |
| M6 section only | 10.843 | 0.036 | 10.651 | 0.097 |

Section alone is worth a third (quire folds) to three quarters (bifolium folds) of hand × language, and much of it is the same information.

**2. Residual section contrasts** (`results/residual_section_contrasts.csv`, 1000 within-HL permutations, 24–105 within-HL rotations): see the verdict. Raw profiles (reference) give the same "survives" pattern as hand residuals, but with larger BA for herbal vs biological / stars (0.87–0.88). Those contrasts are carried by hand: on hand residuals they fall to 0.82 and 0.56.

**3. Hand features** (`results/hand_discriminating_features.csv`; log-odds with informative Dirichlet prior, z, page-bootstrap 95 % CI). Herbal hand 2 B vs 1 A:
* 2 B words: `chedy` (δ = −3.47 [−3.72, −3.17]), `qokedy` (−3.46), `chdy` (−2.36), `ar` (−1.88), `aiin` (−1.45).
* 1 A words: `chol` (+1.07 [0.86, 1.26]), `chor` (+1.10), `sho` (+1.24), `cthy` (+1.04), `daiin` (+0.45).
* Units (collapsed EVA): 2 B prefers `e` (z −12.7), `d`, `a`, `k`, `y`; 1 A prefers `o` (z 14.3), `ch`, `cth`.
* Word-initial: 2 B `a-` (z −14.1), 1 A `cth-` (+7.2), `d-` (+6.3).
* Word-final: 2 B `-y` (z −11.8), 1 A `-l` (+9.2), `-o` (+6.8).

That is the -edy/-y vs -ol/-or contrast, plus the gallows `cth`, all with tight CIs.

**4. Rewrite-rule gap closure** (`results/rewrite_gap_closure.csv`, 5 random page splits each): numbers in the verdict. Rules learned for 1 A ← 2 B: `-edy→-ol`, `-hdy→-hor`, `ai-→dai-`, `a-→cho-`, `ed→∅`, `yk-→ch-`, `oke-→d-`, `he→h`, `-eey→-or`, `-am→-y`.

## Pre-registration and deviations
`PREREG.md` was committed first (`5bce8d2`). Deviations:
* **Generator not done.** The hand-conditioned copy-modify generator (h06 engine fitted per hand) was not run. Its fitting cost (h06/h07: tens of minutes per fit) times hands × folds was out of scope. The hierarchical unigram models are the only held-out models here.
* **Fewer permutations.** 1000 instead of 2000; the BA null uses the first 300 permutations.
* **Smoothing grid.** It was widened to 50 – 500,000, because the first grid's optimum hit its edge.

## Limitations
* Hand and Currier language are nearly the same variable, so "HL" has only a few well-populated cells (1 A, 2 B, 3 B, 4, 5 B).
* Quire-residualised tests can't test section, because sections almost never vary within a quire (h10). B-residual "nothing left" is therefore not evidence of no section effect.
* Rewrite rules are greedy string substitutions over frequent n-grams. A better orthographic model (unit-level alignment, context-dependent rules) could close more of the gap, so 22.7 % is a lower bound for "spelling". Vocabulary differences still look large relative to section gaps.
* The h09 image tags and word sets come from h09. This tests whether they survive, not whether they mean anything.

Reproduce: `python run_h11.py 1000 && python make_figures.py` (~9 min); tests `pytest test_h11.py`.
