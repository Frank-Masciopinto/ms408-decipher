# h12: per-hand copy-and-modify generators

**Verdict.**
* **Generators fitted per hand predict held-out text of that hand better than a pooled generator or a shuffled-cell generator** (P1, P2 hold):
  * top-100-word JS lower in 14 of 15 folds against both baselines;
  * RMS z over the 12 fit metrics lower in 12/15 (pooled) and 13/15 (shuffled).
  * Example, hand 1 A with bifolia held out: top-word JS 0.059 (OWN) vs 0.101 (POOLED) vs 0.100 (SHUF).
* **The "copy-and-modify" part is not what does it.** In every per-hand fit the copy probability is tiny (p_copy 0.017–0.043). The other engine parameters are not identified: the same random candidate often wins for all hands in a fold. So these are effectively **per-hand word-grammar generators**. P4 (same engine parameters across hands) "holds" only trivially and tells us nothing.
* **One system plus a spelling mapping fits the hand 1 A / 2 B relation better than predicted.** A generator for the wrong hand (CROSS) is always worse than the right one. Rewriting its output with ≤ 10 rules learned from the two hands' training text closes, on average:
  * 1 A ← 2 B: 49 % (bifolium folds) / 45 % (quire folds) of the top-word JS gap (fold range 19–67 %);
  * 2 B ← 1 A: 59 % / 69 % (range 47–88 %).

  P3 predicted 20–50 %, so its upper bound fails for 2 B ← 1 A: the mapping explains *more* than expected. The first rule learned in every fold is `-edy → -ol` (1 A ← 2 B) or `-ol/-eol/-or → -edy` (2 B ← 1 A).

  This is a top-100-word statistic on generated text. It is not comparable to the 22.7 % that h11 measured on the full real-text word distribution, and much of the remaining vocabulary gap is in rarer words.

## Design (pre-registered: `PREREG.md`, commit `a1366f0`)
* **Engine.** The repo's no-plaintext copy-modify control C0: `mech_hybrid.generate` with slot-bigram grammar innovations (`mech_hybrid_run.Ctx`), 6 engine parameters fitted by `fit_variant`.
* **Speed.** Profiling showed the engine is cheap: on 10k tokens, grammar 0.53 s, one generation 0.16 s, metrics 0.13 s. So no engine change was needed. With fork-parallel candidate evaluation (8 cores) and a reduced search (60 random + 3×10 local), one fit takes a median 8.5 s. The whole run is 17 min for 42 fits.
* **Cells.** 1 A, 2 B and 3 B, each with 3 bifolium folds; 1 A and 2 B also with 3 quire folds. Hand 4 had no fold with ≥ 200 held-out tokens and was dropped.
* **Scoring.** Each held-out set is scored against OWN, POOLED, SHUF, CROSS (other hands' OWN) and MAPPED, with 3 generation seeds each.

## Results (`results/scores_mean.csv`; fold means)
| level | cell | model | RMS z | top-word JS | \|z\| h2 | \|z\| length | \|z\| Zipf | \|z\| Heaps |
|---|---|---|---|---|---|---|---|---|
| bifolium | 1A | OWN | 2.42 | 0.059 | 2.06 | 0.78 | 1.37 | 1.26 |
| | | POOLED | 2.92 | 0.101 | 0.68 | 3.03 | 1.70 | 1.32 |
| | | SHUF | 3.06 | 0.100 | 0.88 | 2.81 | 1.81 | 1.30 |
| | | CROSS 2B | 1.88 | 0.141 | 2.69 | 2.98 | 0.87 | 1.00 |
| | | MAPPED 2B | 2.13 | 0.101 | 1.07 | 1.29 | 3.36 | 0.78 |
| bifolium | 2B | OWN | 2.68 | 0.087 | 1.99 | 1.31 | 2.03 | 1.10 |
| | | POOLED | 4.33 | 0.106 | 4.48 | 0.93 | 4.34 | 1.50 |
| | | CROSS 1A | 4.29 | 0.195 | 5.87 | 3.06 | 3.95 | 1.33 |
| | | MAPPED 1A | 2.90 | 0.132 | 4.78 | 2.83 | 1.87 | 0.98 |
| bifolium | 3B | OWN | 3.21 | 0.070 | 2.68 | 0.23 | 2.29 | 1.73 |
| | | POOLED | 3.97 | 0.080 | 4.83 | 2.66 | 2.21 | 1.42 |
| quire | 1A | OWN | 2.79 | 0.065 | 2.18 | 1.51 | 1.30 | 1.48 |
| | | POOLED | 2.91 | 0.088 | 1.44 | 1.84 | 1.21 | 1.43 |
| quire | 2B | OWN | 4.93 | 0.127 | 5.35 | 1.35 | 3.50 | 1.60 |
| | | POOLED | 6.41 | 0.136 | 7.30 | 2.07 | 3.96 | 1.96 |

* **Per-metric results are mixed.** OWN is clearly better on word length and the top-word profile, and better on h2 for 2 B and 3 B. For hand 1 A, the **pooled** generator matches h2 better (|z| 0.68 vs 2.06). For 1 A, a pooled or even 2 B generator gets letter entropy right while getting the vocabulary wrong.
* **Overall fit is still poor:** no model gets RMS z under ~1.9, and hand 2 B with whole quires held out is fitted badly by everything (RMS z ≥ 4.2).

## Verdicts vs predictions
| prediction | verdict |
|---|---|
| P1 OWN beats POOLED for 1A, 2B, 3B | **holds** on fold means for top-word JS and RMS z (14/15 and 12/15 folds); not for h2 in 1A |
| P2 OWN beats SHUF | **holds** (14/15, 13/15 folds) |
| P3 CROSS worse; MAPPED closes 20–50 % | CROSS worse in every fold; closure 45–49 % (1A←2B) holds; 59–69 % (2B←1A) **exceeds** the upper bound |
| P4 engine parameters overlap across hands | trivially true and **uninformative**: p_copy ≈ 0.02–0.04 everywhere; parameters not identified |

## Limitations
* The generator's per-hand advantage comes from refitting a ~1.6k-parameter word grammar on each hand's text. "Per-hand generator beats pooled" is therefore close to "per-hand vocabulary beats pooled vocabulary", which h11 already showed. The copy layer adds nothing measurable here. The objective (12 metrics, 2 seeds) gives the copy parameters no traction at hand-sized samples (2.4k–10k tokens).
* The search is reduced (60 + 30 candidates instead of 120 + 90), and the parameter estimates differ between folds.
* The mapping rules are learned on real training text and applied to generated text. Closure is measured only on the top-100-word profile.
* Only 3 folds per level and only 3 usable cells; hand 4 and hand 5 are too small.

Reproduce: `python run_h12.py` (~17 min, 8 cores), then `python summarise.py`; tests `pytest test_h12.py`.
