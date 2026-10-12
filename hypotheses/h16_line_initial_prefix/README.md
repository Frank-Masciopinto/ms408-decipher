# h16: is the 2B/3B line-start habit an added onset? Does 1A have its own line-edge words?

Pre-registration: `PREREG.md` (310f5af). Run with `python run_h16.py`; tests with `pytest test_h16.py` (3).
Outputs:
- `results/onset_tests.csv` and `results/onset_descriptives_2B3B.csv`;
- `results/open_search_{1A,2B,3B}.csv`;
- `results/summary.json`.

**Orthographic and positional facts only. No meanings are claimed.**

The statistic is an attribute summed over line-initial slots, compared with its exact within-stratum permutation mean and variance (h14 strata S1, and S1L = S1 + word length).

## A. Onset test (primary onsets d-, s-; 2B+3B pooled, HL kept in the strata)
- **a1, carries a d-/s- onset:** 727 initial tokens vs 424 expected (S1: ratio 1.71, z = 17.5). Under S1L: 1.88, z = 21.1. In 1A: 0.99 (z = −0.35), i.e. no onset excess.
- **a2, among d-/s- tokens, the stripped form is a common same-hand word** (top 200 non-initial types):
  - Shares: 69.2 % of initial vs 27.8 % of non-initial.
  - S1: ratio 1.82, z = 20.2. S1L: 1.62, z = 18.1.
  - 2B and 3B separately both have z ≥ 12.8.
- **a4, mid-line frequency of the stripped form:** mean log1p 3.20 for initial vs 1.21 for non-initial (S1: z = 21.4; S1L: z = 18.6).
- **Robustness check without the 7 h13 words** (I added this after the first run, so it is exploratory):
  - a2: 248 vs 113 expected (ratio 2.19, z = 16.4 under S1; z = 17.3 under S1L).
  - 472 initial tokens of 221 types; 60 types have a common stripped form.
  - Examples: dshedy (26), dar, sor, dair, dchedy (16), sal, sair, schedy, dol, dshey, dsheey, dcheey, dsheol.
- **a3, stripped form = right neighbour:** rare (9 vs 4.6 expected; S1 z = 2.5, S1L z = 2.9). This is not the pattern "word, then its stripped copy".
- **1A shows a weaker a2/a4 effect:** S1L a2 z = 4.4, a4 z = 5.9, with no excess of onsets. So the "stripped form is common" property is partly general to d-/s- words at line start, but only 2B/3B add the onsets.

## B. Open search (words with ≥ 20 tokens in the HL; Holm within each HL × null; must pass both S1 and S1L)
| HL | Line-initial enriched | Line-final enriched |
|---|---|---|
| 1A (83 words) | dchor 2.95, sor 2.78, sho 2.00 | dam 3.95, dy 2.96, dal 2.51, dar 2.29, daiin 1.46 |
| 2B (106) | dshedy 6.4, sor 5.2, tchedy 4.71, sol 4.39, pchedy 3.71, saiin 3.54, sain 3.29, sar 3.29, y 2.3 | am 6.34, oly 5.71, dam 4.41, lol 3.59, dy 2.87 |
| 3B (90) | saiin 6.49, sain 6.37, sar 5.65, daiin 4.12, dain 3.81, dair 3.32, y 3.3 | am 7.71 |

- **Depletions:**
  - 1A line-final: sho, chol, shol, chor.
  - 2B/3B line-initial: aiin, chedy.
  - 2B line-final: qokeedy.
- **In 2B, gallows-prefixed forms of chedy** (tchedy, pchedy) are line-initial, next to dshedy. The base chedy is depleted at line start, which fits a line-start onset added to common bases (descriptively).

## Verdicts
| | Prediction | Result |
|---|---|---|
| A1 | d-/s- onset excess at line start (z > 3, S1 and S1L) | **pass** (17.5 / 21.1) |
| A2 | stripped forms of initial d-/s- words are common words more often (a2, a4; z > 3) | **pass** (≥ 18) |
| A3 | stripped = right neighbour not enriched (\|z\| < 2) | **fail**, but tiny (9 vs 4.6 tokens; z = 2.5–2.9) |
| B1 | 1A has ≥ 3 initial and ≥ 3 final words | **pass** (3 / 5) |
| B2 | 1A initial set overlaps 2B/3B in ≤ 2 words | **pass** (only sor) |
| B3 | -am/-dy finals in all HLs | **pass** (1A dam, dy; 2B am, dam, dy; 3B am) |

## Limits
- **"Common word" is defined from the same hand's non-initial tokens.** The a2 contrast partly reflects d-/s- word types with short common remainders. The exploratory check without the 7 known words and the type counts address this, but they don't separate a productive prefix from a lexicalised set of line-start words.
- **Gallows onsets (t-, p-) were not in the pre-registered primary set;** tchedy and pchedy come only from the open search.
- **The normal approximation is coarse** for rare words. That is why words with expected count < 5 and fewer than 5 observed are excluded from Holm.
- **Line-start onsets could be scribal or layout conventions,** for example at the start of a ruled line. Nothing here indicates meaning.
