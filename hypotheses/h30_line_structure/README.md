# h30 · The line as a unit (per hand × language)

Pre-registration: [PREREG.md](PREREG.md) (committed f137ec3 before any run). No translation claim is made here.

**Question.** Is a Voynich line a verse line, a list/table entry, or prose broken at the margin? Each hand is compared with 7 controls: 3 verse (Dante, Ariosto, Macer Floridus), 3 hard-wrapped prose (Augustine, Manzoni, Sidrach) and 1 recipe text (Cucina).

**Measures.**
- **M1:** line length.
- **M2:** position(first / second / mid / penult / last) ↔ word-class MI against a word-permutation null within each stratum (MS stratum = hand|quire; control stratum = 50-line block); 200 permutations.
- **M3:** within-line vs across-line END→ONSET and TYPE→TYPE MI, with a null that shuffles line order within a page.
- **M4:** rhyme-like END repetition.
- **M5:** paragraph-first-line onsets (JS divergence).
- **M6:** held-out bits/token for bag, positional, bigram and a 4-state HMM. MS folds are quires; for 3A, which has fewer than 5 quires, and for the controls, the folds are contiguous fifths.

Run: `python run_h30.py && python summarise.py` (about 50 s). Test: `pytest test_h30.py`. Full table: [results/summary.md](results/summary.md).

## Key numbers

| | wpl | CV | pos. TYPE excess (z) | first+last share | END→ONSET within / across excess | para-onset JS (z) | gain pos / HMM (bits/tok) |
|---|---|---|---|---|---|---|---|
| 1A | 6.99 | .435 | .055 (46) | .74 | .104 / −.011 | .571 (126) | .039 / .018 |
| 2B | 8.74 | .310 | .039 (38) | .78 | .246 / −.010 | .501 (78) | .030 / .001 |
| 3B | 9.85 | .259 | .046 (43) | .73 | .234 / .022 | .407 (97) | .030 / .020 |
| 3A (80 lines) | 9.28 | .200 | .030 (2.3) | .74 | .135 / .047 | .668 (4.1) | −.015 / −.046 |
| verse (3) | 6.1–7.2 | .15–.20 | .125–.148 | .59–.80 | .10–.20 / ≤.016 | ≤.06 | .116–.139 / .05–.12 |
| prose (3) | 10.0–11.4 | .22–.37 | .004–.028 | .71–.84 | .02–.11 / .003–.131 | ≤.09 | −.013–.023 / .01–.10 |
| Cucina | 9.90 | .406 | .038 (33) | .79 | .081 / .051 | .328 (78) | .039 / .131 |

Rhyme-like END repetition is at null for every hand (z ≤ 0.5). For comparison, Ariosto has z 5.3 and Macer 4.1.

## Verdicts (pre-registered rules)

| hand | L1 not verse | L2 positional ≥3× prose | L3 line-bounded | L4 para onset | L5 model gain | class |
|---|---|---|---|---|---|---|
| 1A | pass | pass | pass | pass | **fail** | structured line, not classified |
| 2B | pass | **fail** (0.039 vs threshold 0.040) | pass | pass | fail | margin-broken prose (borderline) |
| 3B | pass | pass | pass | pass | **fail** | structured line, not classified |
| 3A | fail (CV .20) | fail | pass | fail | fail | "verse-like" by rule, but **underpowered (80 lines)** |

## Reading

- **Not verse.** Line length varies far more than in the verse controls, and no line-end rhyme exists for 1A, 2B or 3B.
- **Line-bounded.** The line is a closed unit, like a list entry, a rubric or a paragraph line: END→ONSET dependency is strong within a line and absent across the line break in 1A and 2B (3B shows only a weak +0.022, z 2.8). In the hard-wrapped prose controls, Sidrach and Cucina carry dependency across the break (z 10.8 and 4.9).
- **Position is a property of the word.** Positional MI is 3–4× that of hard-wrapped prose, and about 75 % of it sits at the first and last position. It is still only ~⅓ of the verse level, which comes from verse capitals and rhyme.
- **Paragraph-first lines are a separate regime.** Their onsets are gallows-heavy (JS .41–.57), more strongly so than Cucina's recipe headings. First lines are also longer (1A 7.97 vs 6.83; 3B 10.5 vs 9.6).
- **Prediction is not helped.** Position and an HMM line grammar barely improve held-out prediction, by 0.03–0.04 bits/token, short of the 0.05 pre-registered bar. So the line edges are marked, but the line has no strong internal grammar.
- **Overall shape.** The pattern is closest to Cucina (recipe/list prose with headed entries), with stronger edge marking. However, L5 fails, so the pre-registered "list/table" label is **not** granted.

## Limits

- The controls are printed editions whose line breaks come from the modern typesetter, and Cucina's are partly editorial.
- 3A has 80 lines.
- Word classes are top-30 types and top-10 onsets/ends, so MI depends on the vocabulary.
- MS folds are quires but control folds are fifths, so M6 is not exactly comparable between them.
- The HMM is small (4 states, 25 EM iterations).
- The 2B L2 failure is within rounding of the threshold.

## Next

Build an entry-level model: paragraph-first line → body lines → last-word marker. Test whether line-final words (am/dy class) close an entry, comparing against the Cucina recipe structure with matched vocabulary size.
