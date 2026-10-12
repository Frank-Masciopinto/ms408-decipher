# h13 — the 100 most common words in context and images

Pre-registration: `PREREG.md` (commit c80e2f7). Run: `python run_h13.py`; tests: `pytest test_h13.py` (5).
Outputs: `cards/CARDS.md` plus `results/cards.{csv,json}` (one card per word), `results/positions.csv`, `results/clusters.csv`, `results/cluster_membership.csv`, `results/edit_pairs_context.csv`, `results/rule_pairs_cross_hand.csv`, `results/image_links.csv` and `results/image_links_surviving.csv` (the latter is empty), `results/summary.json`, `figures/clusters_svd.png`.
**These are distributional profiles only. No meanings are claimed.**

## Results (from `results/summary.json`)
- **Positions** (P loci, within hand×language, Holm over 400 tests):
  - Line-initial enriched: 7 words (daiin, dain, saiin, sain, sar, sol, y).
  - Line-final enriched: 3 words (am, dam, dy).
  - Paragraph-initial enriched: 0 words. Paragraph-initial depleted: aiin, daiin, ol.
  - Strong line-initial depletion: 24 words, for example ch-/sh- -edy/-ey/-ol words, ol, ar, aiin.
  - Line-final depletion: 15 words, mostly qok- words and ch-/sh- -ol/-or words.
  - Labels: no word is label-enriched; aiin and daiin are label-depleted.
- **Neighbour classes** (PPMI L|R, k = 8):
  - Silhouette is 0.0155. Under the within-HL neighbour shuffle the null mean is 0.0065 and the max 0.0227, giving p = 0.095. The classes are weak and do not beat the null at 0.05.
  - Kruskal–Wallis test of log frequency across classes: p = 0.066.
  - Three large classes:
    - class 1 (41 words): e-rich -edy/-ey/-eey words plus qok-/ot-, dominant HL 2B;
    - class 3 (23 words): short -l/-r/-ar/-ain words such as ol, ar, or, al, aiin, dominant HL 3B;
    - class 5 (27 words): daiin, chol, chor, dar, dy, sho, chy, dominant HL 1A.
  - These classes largely track hand×language rather than syntax.
- **Spelling variants:**
  - Pre-registered rule pairs (-edy/-ol, -edy/-or, -dy/-ol) inside the unit-edit ≤ 2 set: 5 pairs. Their mean cosine is 0.187, against 0.155 for the 880 other pairs (p = 0.135).
  - Cross-hand test (X in 2B vs Y in 1A, 24 directed pairs): mean cosine 0.056 vs 0.054 for random partners. Wilcoxon one-sided p = 0.59, sign-flip p = 0.42, median partner rank 48th percentile.
- **Image links:**
  - 868 tests: 700 page-level (100 words × 7 tags, 223 pages) and 168 label-level (object types, words with ≥ 3 label tokens).
  - The null permutes tags within quire×HL (2000 permutations).
  - 46 tests have raw p < 0.05, about what chance predicts (≈ 43). **None survive Holm.**
  - Smallest: odaiin × jar page rate, p = 0.0005, Holm 0.43.

## Verdicts
| | prediction | result |
|---|---|---|
| P1 | ≥10 initial-enriched, ≥5 final-enriched | **fail** (7 initial, 3 final; many significant *depletions*) |
| P2 | clusters beat shuffle, ≥3 non-band classes | **fail** (p = 0.095; 3 classes span wide rank ranges but track HL) |
| P3 | rule pairs share cross-hand contexts | **fail** (p = 0.59): h11/h12's -edy→-ol mapping is distributional, not a word-for-word correspondence |
| P4 | ≤5 image links survive | **pass** (0) |

## Limits
- Line-position effects partly reflect line length and the right-justification of the layout.
- Context vectors for words outside 2B/1A are sparse, and the cross-hand test covers only 2B→1A.
- Image tags are hand-coded at page level and are nearly constant within quire, so the stratified null has little power. That is a design choice, not evidence of absence.
- Edit distance is over collapsed units, so -edy↔-ol (3 units) mostly falls outside the ≤ 2 set. The cross-hand test uses all rule pairs.
- One page-level p-value bug was found and fixed before the final run: floating-point ties in degenerate nulls had given p = 0.0005. A tolerance now handles it.
