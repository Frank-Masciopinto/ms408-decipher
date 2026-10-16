# h56 — identifiability after the copying routine

Pre-registered programme. No reading is proposed unless a detector that can recover a planted topic also finds a manuscript association that survives held-out quires. Multispectral images were not available, so erasures could not be recovered.

**Stage 7: `unidentifiable`.** Grounded associations: none.

The detector recovers a planted topic (accuracy 0.575 against 0.000 when no topic is present), so the null results are not a failure of the detector. No tested residual predicts jars, roots, nymphs, or stars. Labels are less surprising under their folio's paragraph vocabulary than length-matched paragraph words (contrast −0.494 bits, p 0.82), so they do not sit outside the page routine. About 76% of paragraph tokens fall in an edit-distance-1 family of at least three tokens. The composite lattice rule U1 fails on two of twelve hand–reading cells, both because the edit-1 rate is 0.027 and 0.030 against a floor of 0.030; bigram gain stays negative and the line-initial onset excess stays positive in every cell. Alternative readings touch 1.85% of paragraph tokens, and 98.5% of those alternatives are at most three characters. Erased strokes were not recoverable: there are no multispectral images.

## Stages

- U1 reading lattice: `0`. Alternative groups cover 1.853% of paragraph tokens.
- R1 labels vs folio routine: contrast -0.4940, p 0.8231, pass `0`.
- R2 illustrated-page surprise: pass `0`.
- M1 folio roots vs drawings: pass `0` (0 of 25 roots tested; component coverage 0.758).
- L labels vs drawings: pass `0`.
- C1 glyph-scale alternatives: `1` (short-option fraction 0.985). Multispectral: `unavailable`.
- S6 synthetic recovery: `1` (planted 0.575, null 0.000).

## Reading lattice

| reading | hand | bigram gain | edit-1 rate | onset excess | pass |
|---|---|---|---|---|---|
| `primary` | 1A | -0.7982 | +0.0390 | +0.1346 | `1` |
| `primary` | 2B | -0.9101 | +0.0337 | +0.3418 | `1` |
| `primary` | 3B | -0.8073 | +0.0308 | +0.4492 | `1` |
| `alternate` | 1A | -0.7893 | +0.0387 | +0.1351 | `1` |
| `alternate` | 2B | -0.9080 | +0.0337 | +0.3409 | `1` |
| `alternate` | 3B | -0.7965 | +0.0307 | +0.4480 | `1` |
| `joined` | 1A | -0.6087 | +0.0335 | +0.1478 | `1` |
| `joined` | 2B | -0.7762 | +0.0302 | +0.3517 | `1` |
| `joined` | 3B | -0.6299 | +0.0271 | +0.4643 | `0` |
| `it2a` | 1A | -0.7757 | +0.0371 | +0.1353 | `1` |
| `it2a` | 2B | -0.8821 | +0.0310 | +0.3427 | `1` |
| `it2a` | 3B | -0.7585 | +0.0300 | +0.4522 | `0` |

## Drawing tests

| test | tag | statistic | p | Holm p | pass |
|---|---|---|---|---|---|
| R2 surprise | jars | +0.1354 | 0.5767 | 1.0000 | `0` |
| R2 surprise | roots | +1.8722 | 0.3888 | 1.0000 | `0` |
| R2 surprise | nymphs | -0.3954 | 0.3593 | 1.0000 | `0` |
| R2 surprise | stars | -3.4174 | 0.3358 | 1.0000 | `0` |
| L1 count | jars | +0.4161 | 0.1744 | 0.6037 | `0` |
| L1 count | roots | +0.3167 | 0.3123 | 0.6247 | `0` |
| L1 count | nymphs | -0.1821 | 0.1509 | 0.6037 | `0` |
| L1 count | stars | — | 1.0000 | 1.0000 | `0` |
| L2 onset | jars | +0.0823 | 1.0000 | 1.0000 | `0` |
| L2 onset | roots | +0.0882 | 1.0000 | 1.0000 | `0` |
| L2 onset | nymphs | +0.0882 | 0.4208 | 1.0000 | `0` |
| L2 onset | stars | — | 1.0000 | 1.0000 | `0` |

Figure: `figures/identifiability.png`.
