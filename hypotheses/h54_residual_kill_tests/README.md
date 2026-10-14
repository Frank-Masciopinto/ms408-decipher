# h54 — kill tests for the slot and paragraph residuals

Pre-registered checks of whether the h52 interior coupling is adjacency rather than near-copy or a line palette, and whether the h53 paragraph contrast is a closing role rather than the folio's first line, a short last line, or drift. Nothing here is a translation.

**Overall: `paragraphs_only`.** Slots `partial` (A1 hands `2B`, `3B`; A2 hands none). Paragraphs `stands` (B3 hands `1A`, `2B`, `3B`). B1 hands `1A`, `3B`. B2 hands `1A`, `2B`, `3B`. C `not_run`. D `not_shared`.

The labels above are the pre-registered ones. Two design checks run after the results show that neither residual is settled by this run.

- **A2 does not test adjacency.** Moving second units around inside a line also detaches each one from its own word. Within-word mutual information between onset and second unit falls from 1.01 / 1.50 / 1.43 bits to 0.06 / 0.06 / 0.05, and the entropy of the next word's second unit given the junction rises from 1.96 / 1.71 / 1.79 to 2.96 / 3.20 / 3.23 bits. The copier, which links neighbouring words only through occasional one-edit copies, scores −0.097 / −0.075 / −0.131 under the same null. A null that fails on the copier cannot say whether the manuscript's coupling is adjacency or the line's inventory. A1 stands: removing near-copies does not remove the h52 excess.
- **B3 is not distance-matched.** `PREREG.md` uses that name, but the rule it states takes the earliest and latest long middle lines, and those are closer together than the opening and closing lines: mean line distance 1.96 / 4.78 / 2.02 against 3.96 / 6.80 / 4.02. Closing lines are also shorter (8.5 / 7.5 / 7.5 words against 9.6–11.2 for the other three roles). The shuffle null removes drift, so drift and line length both remain inside D. D is largest in hands 1A and 3B, where the middle pair is two adjacent lines in 56 % and 65 % of paragraphs, and smallest in 2B (8 %), which is the pattern drift alone would give.

The cross-hand word list does not get off the ground: after the count floor, the hands share 1, 1, and 5 types, under the floor of 15.

## A. Second-unit coupling

| stream | A1 near-copies removed | A2 within-line shuffle |
|---|---|---|
| `MS_1A` | +0.0177, z +3.39 (n 7507) | -0.2182, z -29.74 (n 8115) |
| `MS_2B` | +0.0219, z +4.71 (n 8320) | -0.2503, z -38.65 (n 8838) |
| `MS_3B` | +0.0248, z +5.43 (n 8486) | -0.2324, z -34.37 (n 8912) |
| `page_line_copier_1A` | +0.0099, z +1.94 (n 8020) | -0.0972, z -15.14 (n 8410) |
| `page_line_copier_2B` | +0.0023, z +0.53 (n 8710) | -0.0745, z -13.86 (n 9083) |
| `page_line_copier_3B` | -0.0001, z -0.03 (n 8823) | -0.1312, z -20.48 (n 9136) |

## B. Paragraph opening against closing

| stream | B1 no folio-first | B2 both lines ≥ 6 words | B3 D against matched middles |
|---|---|---|---|
| `MS_1A` | +0.0525, z +7.65 (n 595) | +0.0595, z +7.55 (n 486) | +0.0972, z +4.26 (n 206) |
| `MS_2B` | +0.0140, z +2.63 (n 701) | +0.0146, z +2.60 (n 613) | +0.0297, z +2.00 (n 372) |
| `MS_3B` | +0.0292, z +14.08 (n 1726) | +0.0266, z +10.18 (n 1290) | +0.0645, z +7.21 (n 553) |
| `page_line_copier_1A` | +0.0186, z +3.12 (n 595) | -0.0047, z -0.65 (n 486) | +0.0219, z +0.99 (n 206) |
| `page_line_copier_2B` | +0.0101, z +2.14 (n 701) | +0.0016, z +0.33 (n 613) | +0.0137, z +1.05 (n 372) |
| `page_line_copier_3B` | +0.0116, z +5.59 (n 1726) | +0.0090, z +3.86 (n 1290) | +0.0052, z +0.62 (n 553) |

## Conditional follow-ups

C was not run. A2 did not pass on two hands.
D `not_shared`. 1A-2B r +nan (n 1, pass `False`); 1A-3B r +nan (n 1, pass `False`); 2B-3B r +0.200 (n 5, pass `False`).

Figure: `figures/residual_kill_tests.png`.
