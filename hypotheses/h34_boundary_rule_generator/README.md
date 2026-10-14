# h34 — per-hand word-gap rule generator

Pre-registered in [PREREG.md](PREREG.md) (commit 46d318e) before computing. Statistics only; **no translation or meaning claims**.

## Question
h31: in MS 408 a word's last glyph predicts the next word's first glyph far more than in any natural text, and generators show none of it. h33: spaces are predictable from ±2 glyphs (.75–.82). Can a simple per-hand **gap rule** added to existing generators reproduce this, without breaking their inventory or the h20 fingerprint (D1–D5)?

## Method
- MS lines per hand split by bifolium (even index = train, odd = test). The rule table r(f|l) = P(first | prev last)/P(first) and the strength s* are fitted on train pages only; targets come from test pages.
- Base generators: (a) C0 copy-modify fitted on the hand's train pages, (b) Naibbe-Italian (Boccaccio) + swap copy c=.05, (c) the same Naibbe pipeline on nonsense (Zipf pseudo-word) plaintext.
- Rule: at each within-line gap, choose the next word among the next 10 queued base tokens with weight r^s (local reordering; no new word types). s ∈ {0, .5, 1, 1.5, 2, 3}; s* = 1 for all 9 cells.
- Controls: s = 0, shuffled rule table (rows permuted), all-gaps variant, edge-excluded measurement.

## Results (test pages; [results/summary.md](results/summary.md))

| | MS test J | gen J (s*) | s = 0 | shuffled J | table r (real / shuffled) | space S (MS / s=0 / s*) | fingerprint s=0 → s* |
|---|---|---|---|---|---|---|---|
| 1A | .142 | .082 / .107 / .116 | ≤ .004 | .07–.11 | .90–.96 / −.47 | .724 / .75–.87 / .72–.84 | 4,4,5 → 4,5,5 |
| 2B | .269 | .178 / .204 / .199 | ≤ .004 | .10–.12 | .95 / .27–.31 | .798 / .82–.87 / .80–.84 | 5,4,5 → 5,5,5 |
| 3B | .219 | .191 / .182 / .186 | ≤ .004 | .08–.09 | .96 / −.01–.06 | .792 / .84–.87 / .81–.85 | 5,4,5 → 5,5,5 |

(gen J listed as C0 / Naibbe-Italian / Naibbe-nonsense.)

| Prediction | Result | Pass |
|---|---|---|
| P1 J within ±35 % of MS test, ≥7/9 | 8/9 (1A C0 .082 too low) | ✔ |
| P2 last glyph beats ending (J > J_end), ≥7/9 | 9/9 (J_end .007–.031) | ✔ |
| P3 table r ≥ .6 real, ≤ .3 shuffled, ≥7/9 | 8/9 (2B nonsense shuffled .307) | ✔ |
| P4 space S in [.75, .82], ≥6/9 | 2/9 | ✘ |
| P5 inventory kept (types/5k ±5 %) | 9/9 (identical by construction) | ✔ |
| P6 Naibbe-It s* 5/5 for ≥2 hands; no cell loses >1 stat | 3/3 at 5/5; max loss 0 | ✔ |
| P7 MS edge-excluded J ≥ 50 % of J; gen edge J matches ≥6/9 | MS .95–.98 of J; 8/9 | ✔ |

**H-gap supported (P1, P2, P3, P6 pass).**

## Reading
- A one-parameter-per-hand rule ("pick a next word whose first glyph suits the previous last glyph") added to any of the three generators reproduces the MS end→start link: size (~75–90 % of the target at s = 1), its hand-specific table (r ≈ .9–.97 with held-out MS pages), and the last-glyph-beats-ending pattern. The fingerprint is kept or improved (all Naibbe-Italian cells move from 4/5 to 5/5).
- The link is not a line-edge artifact: removing first and last words keeps 95–98 % of it in MS.
- It works equally with nonsense plaintext, so like h24–h29 it says nothing about an underlying language.
- **Spaces are not explained.** Reordering words lowers space predictability by only .015–.03, and the Naibbe streams stay at .83–.85 against MS .72–.80. Space placement depends on word-internal glyph structure (word starts/ends), which a word-choice rule cannot change.
- The shuffled table still creates a link of about half the size (any non-uniform table does). It is the table *pattern* (T) that singles out the real rule.

## Limits
- Coarse s grid (s* = 1 everywhere) leaves generators ~10–40 % under target J; a finer fit would close it but was not pre-registered.
- One seed per cell; one transcription (ZL3b); bifolium split only; lookahead K = 10 fixed.
- Reordering slightly perturbs copy adjacency; fingerprint checked only in the bifolium scheme.

## Files
`h34_lib.py` (rule, measures), `run_h34.py` (`measures`, `fingerprint`), `summarise.py`, `test_h34.py`, `results/` (bulky token/line files git-ignored).
