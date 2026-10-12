# h15: line-initial robustness and stem-controlled Procrustes

Pre-registration: `PREREG.md` (0466079). Run with `python run_h15.py`; tests with `pytest test_h15.py` (4).
Outputs:
- `results/meta_summary.csv` and `results/units_{quire,bif}_*.csv`;
- `results/procrustes_rule_pairs_controlled.csv` and `results/procrustes_stem_calibration.csv`;
- `results/summary.json`;
- `figures/forest_quire.png`.

**Positional and distributional facts only. No meanings are claimed.**

## A. 2B/3B line-initial enrichment
Words: daiin, dain, saiin, sain, sar, sol, y. Expected counts come from the h14 S1 strata, computed within each unit. Units with expectation < 1 are pooled into "other".

**All 7 words combined:**
- **Per quire** (8 units): random-effects ratio 3.28 [2.48, 4.35]. 7/8 quires have ratio > 1 (sign p = 0.035; the exception is Q6, 1 observed vs 1.8 expected). I² = 0.10 (Q p = 0.35).
- **Leave-one-quire-out:** the minimum is 2.69 [1.98, …], with Q20 dropped. Q13 and Q20 hold most of the 2B/3B text.
- **Per bifolium** (18 units): 3.19 [2.52, …]. 17/18 have ratio > 1 (sign p = 7e-5). I² = 0. The leave-one-out minimum is 3.00.

**Single words:** pooled quire ratios are 2.5–4.4, and every CI excludes 1. Most single words have only 2–3 quire units, so their leave-one-out CIs sometimes touch 1 (dain 0.89, sar 0.99, sol 0.62).

**1A at its own sample size:**
- Combined: 102 observed vs 106.7 expected (ratio 0.96). Power to detect the 2B/3B ratio = 1.00. Difference z = 6.2.
- Per word, power is ≥ 0.8 for 5/7 words; sain (0.49) and sar (0.80) are borderline.
- The per-word difference z is > 3 only for daiin (4.1). For sol, 1A itself shows 2.8 (8 vs 2.5 expected).

## B. Stem-controlled Procrustes (h14 alignment, 20 directed rule pairs)
| Comparison set | Median percentile | Sign-flip p |
|---|---|---|
| All words (h14) | 0.76 | 0.0009 |
| Same onset (ch/sh/qok/…) | 0.60 | 0.097 |
| Same unit edit distance, non-rule | 0.73 | 0.013 |

- **Calibration** (non-rule same-onset pairs, n = 668): median 0.50.
- **Rule vs calibration:** Mann–Whitney p = 0.12.
- **Takeaway:** most of h14's advantage comes from the shared onset/stem. Against same-stem words the rule partners are only weakly and not significantly closer. A residual advantage remains over words at the same edit distance.

## Verdicts
| | Prediction | Result |
|---|---|---|
| A1 | pooled ratio > 1.5, CI excludes 1, ≥ 70 % of quires > 1 | **pass** (3.28; 7/8) |
| A2 | leave-one-quire-out never reaches 1 | **pass** (min lower bound 1.98) |
| A3 | I² < 75 % | **pass** (0.10) |
| A4 | 1A power ≥ 0.8 combined and for ≥ 4/7 words; combined difference z > 3 | **pass** (1.00; 5/7; z = 6.2) |
| B1 | rule partners beat same-onset words | **fail** (0.60, p = 0.097) |
| B2 | rule partners beat same-edit-distance words | **pass** (0.73, p = 0.013) |
| B3 | rule partners beat the stem calibration | **fail** (p = 0.12) |

## Limits
- **Few independent units:** 2B/3B text sits mostly in Q13 and Q20, so the quire meta-analysis has only 8 units. The bifolium analysis (18 units) shares the same strata definitions.
- **Rare words are pooled:** single-word analyses fold rare quires into "other".
- **Power is per HL, not per page.**
- **Procrustes is small:** 20 directed pairs on 10 words, sharing words (chedy/shedy appear several times), so the pairs are not independent. `ol` has no onset in the list, so its stem set is the other onset-less words.
