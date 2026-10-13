# h33 pre-registration: are MS 408 spaces true word boundaries?

Written and committed **before any h33 number was computed**.

## Question
h31 found that a word's last glyph predicts the next word's first glyph more than in any natural text and in no generator.
One reading: the "real" units straddle the spaces. Does re-cutting the text at other places give units that look **more** language-like than the scribes' words?

## Data
- MS: ZL3b lines for hands 1A, 2B, 3B (h30 loader `load_ms`, line order kept).
- Natural controls (h30 loader, same cleaning): augustine (Latin prose), macer (Latin verse herbal), sidrach and manzoni (Italian prose), cucina (Italian recipes).
- Generators (h31 cached streams): Naibbe on Pliny (Latin), Naibbe on Ariosto (Italian), C0 fitted on 2B. Lines are cut every 9 words (close to the MS mean).
- Every corpus is capped at the same token count (the smallest MS hand), from the start.

## Transforms (all inside a line; line breaks never crossed)
- `orig`: the given words.
- `join2`: join adjacent words in pairs.
- `shift+1`, `shift+2`: the last 1 or 2 glyphs of each word move onto the start of the next word.
- `shift-1`, `shift-2`: the first 1 or 2 glyphs of the next word move onto the end of the previous word.
- `morf`: Morfessor Baseline trained on space-stripped lines; its segments are the units.
- Empty units are dropped.

## Metrics per unit stream
- M1 type/token ratio on the first 5000 units; M2 Zipf slope (ranks 1–500).
- M3 morph inventory: Morfessor morphs per unit type.
- M4 held-out word n-gram gain: bits/unit of a unigram model minus a Kneser-Ney trigram (h19 `KN` over a `CharLM(4)` base), 5 contiguous line-block folds.
- M5 junction dependence: MI(last glyph of unit, first glyph of next unit) within lines, minus the mean of 50 within-line order shuffles.
- Space prediction S: on space-stripped lines, predict "boundary here?" from 2 glyphs left + 2 right (backed-off counts, held-out folds). Report the share of boundary entropy removed (1 − H(cond)/H(base)) and F1.

## Controls
- Everything is run in a `full` variant and an `interior` variant that drops the first and last word of every line before transforming. This rules out the h13–h16/h30 line-edge effects.

## Predictions
- **P1 (sanity, natural text):** in every natural control, `shift±1` lowers M4 relative to `orig` and raises M1. If this fails, the test can't tell anything apart.
- **H-straddle (spaces are not the real boundaries)** is supported only if, in ≥ 2 of 3 hands and in the `interior` variant, some shift or `morf` gives M4 ≥ `orig` M4 **and** M5 drops by ≥ 50 % with no M1 rise beyond the smallest natural-control rise for that transform.
- **H-true-space** is supported if MS behaves like P1: every shift lowers M4 in ≥ 2 of 3 hands.
- **S1:** the MS space-entropy share removed exceeds every natural control in ≥ 2 of 3 hands. This would mean spaces are largely fixed by the glyphs around them, i.e. rule-placed rather than free.
- Generators are the reference for "spaces placed by a rule over code groups".

No translation or meaning claims will be made.
