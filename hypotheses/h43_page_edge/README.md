# h43: vocabulary at the page edge

Pre-registration: [PREREG.md](PREREG.md). Paragraph words in reading order. A window is 80 tokens lying on one folio. Pairs have start-distance 80 or 160. Same means both windows are on one folio. Cross means a folio boundary falls between them. Similarity is the cosine of the two word-count vectors. The effect is the mean same cosine minus the mean cross cosine. A distance is scored only when both sides have at least 30 pairs. Inside each quire the token stream is rotated circularly against that quire's folio lengths, 100 times, one numpy Generator seeded with 43, consumed in the order 1A, 2B, 3B, Boccaccio, cucina, Pliny. Each quire draws an independent shift on 0..n-1. Folio sizes stay fixed and local order stays fixed. A scored distance passes when the observed effect is above the null 95th percentile (`numpy.percentile`, linear).

Manuscript words are the h14 paragraph table for hands 1A, 2B and 3B, transcription ZL3b-n.txt, comma treated as a word space. Folios and quires are the real ones.

Control boundaries are read from the raw files before tokenisation. Each stretch is tokenised on its own with the same normaliser as the existing loader, so a token cannot cross a boundary. Boccaccio: a boundary at each Novella heading (Introduzione is not a boundary). Cucina: a Zambrini recipe heading, a line that is entirely `=...=` or `_..._`, inside the loader's span from INCOMINCIASI to the line before TAVOLA. Pliny: a TEI `div` with `subtype="chapter"` in books 20-27. Blank lines are not boundaries. Each control is one fake quire, one rotation group, because the source has no quires. A control is available only with at least 20 boundaries.

## Predictions

- E1. At distance 80, at least two of the three hands pass: **pass**.
  - 1A: effect 0.082466, null 95th 0.058580, same 184, cross 45, scored True, pass True.
  - 2B: effect 0.099770, null 95th 0.074346, same 4440, cross 41, scored True, pass True.
  - 3B: effect 0.019649, null 95th 0.029282, same 6807, cross 23, scored False, pass False.
- E2. At distance 80, at least two available controls pass. **fail**. Passing controls: la_pliny_herbal. Available controls: 3.

## Pair effects

| series | distance | n_same | n_cross | effect | null_p95 | scored | pass |
|---|---|---|---|---|---|---|---|
| 1A | 80 | 184 | 45 | 0.082466 | 0.058580 | True | True |
| 1A | 160 | 0 | 586 | null | null | False | False |
| 2B | 80 | 4440 | 41 | 0.099770 | 0.074346 | True | True |
| 2B | 160 | 2549 | 2164 | 0.056482 | 0.049907 | True | True |
| 3B | 80 | 6807 | 23 | 0.019649 | 0.029282 | False | False |
| 3B | 160 | 5047 | 1738 | 0.013226 | 0.024407 | True | False |
| Boccaccio | 80 | 58284 | 20 | 0.093670 | 0.037746 | False | False |
| Boccaccio | 160 | 56604 | 1620 | 0.034809 | 0.022513 | True | True |
| Cucina | 80 | 1511 | 12 | -0.175300 | 0.156329 | False | False |
| Cucina | 160 | 1199 | 153 | -0.257629 | 0.150996 | True | False |
| Pliny | 80 | 55014 | 127 | 0.047271 | 0.013664 | True | True |
| Pliny | 160 | 46348 | 8961 | 0.031201 | 0.013675 | True | True |

## Sizes

| series | tokens | folios | quires | boundaries | available |
|---|---|---|---|---|---|
| 1A | 10326 | 112 | 10 |  |  |
| 2B | 10722 | 46 | 6 |  |  |
| 3B | 10835 | 28 | 2 |  |  |
| Boccaccio | 61623 | 21 | 1 | 20 | True |
| Cucina | 12627 | 181 | 1 | 180 | True |
| Pliny | 76765 | 156 | 1 | 155 | True |

## Run

```
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python -m pytest hypotheses/h43_page_edge/test_h43.py -p no:cacheprovider
python hypotheses/h43_page_edge/run_h43.py
python hypotheses/h43_page_edge/summarise.py
```

numpy 2.5.4, python 3.12.3, runtime 4.3s.
