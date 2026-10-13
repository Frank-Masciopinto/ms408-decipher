# h33 · Are MS 408's spaces the real word boundaries?

**Question.** h31 showed that a word's last glyph strongly predicts the next word's first glyph. Could the "real" units straddle the spaces, so that re-cutting the text gives more language-like units?

**Pre-registration:** [PREREG.md](PREREG.md) (commit 533f9e8, made before any number was computed). **Code:** `h33_lib.py`, `run_h33.py`, `summarise.py`, `test_h33.py`. **Numbers:** [results/summary.md](results/summary.md).

## Setup
- **Corpora:** hands 1A, 2B and 3B (ZL3b); 5 natural texts (Augustine and Macer in Latin; Sidrach, Manzoni and Cucina in Italian); 3 generators (Naibbe on Pliny, Naibbe on Ariosto, C0 fitted on 2B). Each is capped at 10,326 tokens.
- **Transforms,** always within a line: join pairs; move 1–2 glyphs across each space in either direction; Morfessor on space-stripped lines.
- **Variants:** `full`, and `interior`, which drops the first and last word of each line (the line-edge control).
- **Metrics:** TTR, Zipf slope, morphs per type, held-out unigram→trigram gain (h19 KN over CharLM), junction MI, and how well spaces can be predicted from the 2 glyphs on each side.

## Results (interior variant; full is the same picture)
| | orig TTR | shift+1 TTR | orig n-gram gain | shift+2 gain | space entropy removed |
|---|---|---|---|---|---|
| MS 1A / 2B / 3B | .29 / .25 / .30 | .45 / .39 / .45 | −.25 / −.20 / −.23 | +.18 / +.23 / +.09 | .75 / .81 / .82 |
| Natural (5) | .22–.44 | .36–.66 | −.09 … +.89 | +.03 … +.82 | .60–.76 |
| Generators (3) | .36–.39 | .54–.60 | −.34 … −.29 | +.04 … +.08 | .82–.88 |

- **Re-cutting never helps.** Every shift and every pair-join makes MS units *less* word-like. TTR rises 35–60 %, the Zipf slope flattens (−1.0 → −0.7) and Morfessor finds no smaller piece inventory. Real text behaves the same way.
- **The n-gram "gain" after shifting is an artifact.** Moving a glyph across a space splits each old word over two units, so neighbouring units now predict each other. The same rise appears in the generators, whose spaces are true boundaries by construction, and in Augustine and Macer. For the same reason the junction-MI criterion (M5) cannot be met by any shift. That is a flaw in the pre-registration, recorded here rather than patched.
- **Morfessor on stripped lines** fails on every corpus, including natural ones: it stores whole lines (TTR ≈ 1). It gives no alternative segmentation.
- **Spaces are very predictable from the surrounding glyphs.** Two glyphs on each side remove 75–82 % of the uncertainty about where a space goes (F1 .89–.92). That is above all natural texts in 2B and 3B (max: Cucina, .757). 1A (.750) is level with Cucina. All three hands sit below the generators (.82–.88).

## Pre-registered verdicts
- **P1 (natural-text sanity) fails as written.** Shifts raise TTR everywhere, but n-gram gain rose for Augustine and Macer under shift+1. The M4 criterion is therefore not a clean discriminator (see the artifact above).
- **H-straddle: not supported** (0/3 hands).
- **H-true-space: not supported as worded,** for the same artifact reason. On TTR, Zipf and morph inventory, though, MS reacts to re-cutting like texts whose spaces are real.
- **S1: passes** (2/3 hands).

## Plain reading
There is no sign that the true units straddle the spaces. Wherever the cut is moved, MS words get worse in the same way real words and cipher code-groups do. So the end→start link from h31 is a dependency *between* units, not the inside of a hidden longer word. The spaces themselves are placed by a strong local glyph rule, tighter than in natural spelling and close to a generator's. That fits word-final and word-initial glyph classes, the h31 "gap rule".

## Limits
- EVA characters are treated as glyphs (e.g. `ch` counts as 2), and controls use Latin letters. Alphabet size differs, which affects the space-prediction comparison.
- One transcription (ZL3b). Generator lines are fixed 9-word chunks.
- n-gram gain is negative for MS at this size (trigram worse than unigram held out), as in h19.
- Morfessor-on-lines was degenerate, so the unsupervised re-segmentation arm is effectively untested. A proper Bayesian segmenter (e.g. Goldwater-style DP) is still to do.
- No translation or meaning claims.

## Next
A junction-rule generator: take C0 or Naibbe and add a per-hand rule linking a word's final glyph to the next word's initial glyph. Then check whether it reproduces both h31's junction MI and this space predictability (.75–.82) without breaking the h20 fingerprint.
