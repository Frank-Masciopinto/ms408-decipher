# h55 — word order and neighbouring paragraph steps

Pre-registered tests. The order null shuffles whole words inside a line. Paragraph steps are compared with other pairs of neighbouring lines, using only words two places in from either edge. A result is interpreted only when the copier stays quiet and a planted copier is detected. Nothing here is a translation.

**Slots: `no_adjacency`.** The check is valid: the copier passes on no hand, and sorting the copier's words by core is detected on all three (excess +0.80 to +0.91). In the manuscript the real order sits below a random order of the same words, by 0.042 / 0.048 / 0.052 bits (z −5.6 / −7.9 / −8.6). The copier sits below its own shuffle too, by less in hands 1A and 2B (−0.016, −0.024) and by about as much in 3B (−0.042).

**Bits: `invalid`.** Sorting by core is detected, but the copier itself passes the absolute gain rule on hands 2B and 3B (+0.032 and +0.033). The manuscript values on those hands are +0.037 and +0.047. This gain does not separate the two.

**Paragraphs: `role`, from the opening step only.** The first line against the second line exceeds a random neighbouring pair by +0.021 / +0.024 / +0.021 bits (z +4.1 / +4.9 / +6.5). The copier is inside its null on every hand, and marking the planted first line is detected. The last step passes on no hand. Hand 2B's closing excess (+0.024) is smaller than its copier's (+0.034). The onset ranking is not shared at the pre-registered bar (r +0.02, +0.39, +0.32; none above its null). The largest onset change on that opening step is `ch` more common on the second line, by 0.06 / 0.04 / 0.08, with `sh` less common.

## S. Order

| stream | S1 word shuffle | S2 folio-held-out gain |
|---|---|---|
| `MS_1A` | -0.0423 (z -5.62, n 8115) | -0.0475 (z -4.27, n 6563) |
| `MS_2B` | -0.0475 (z -7.94, n 8838) | +0.0373 (z +3.53, n 8534) |
| `MS_3B` | -0.0519 (z -8.61, n 8912) | +0.0474 (z +4.36, n 8880) |
| `page_line_copier_1A` | -0.0158 (z -2.61, n 8410) | -0.0157 (z -1.48, n 7358) |
| `page_line_copier_2B` | -0.0241 (z -4.62, n 9083) | +0.0317 (z +3.03, n 8840) |
| `page_line_copier_3B` | -0.0419 (z -8.35, n 9136) | +0.0329 (z +3.21, n 9041) |

| plant | S1 | S2 |
|---|---|---|
| `plant_1A` | +0.7962 (z +125.29, n 8370) | +0.2509 (z +20.64, n 7154) |
| `plant_2B` | +0.9104 (z +150.84, n 9111) | +0.5981 (z +57.98, n 8715) |
| `plant_3B` | +0.9106 (z +162.32, n 9173) | +0.6747 (z +66.19, n 8978) |

## P. One-line steps

| stream | opening | closing |
|---|---|---|
| `MS_1A` | +0.0210 (z +4.05, above p95, n 662/743) | -0.0044 (z -0.34, inside null, n 334/228) |
| `MS_2B` | +0.0244 (z +4.87, above p95, n 665/760) | +0.0240 (z +2.06, above p95, n 362/246) |
| `MS_3B` | +0.0208 (z +6.49, above p95, n 1126/1288) | -0.0007 (z -0.12, inside null, n 802/475) |
| `page_line_copier_1A` | -0.0005 (z -0.10, inside null, n 662/743) | -0.0254 (z -2.15, inside null, n 334/228) |
| `page_line_copier_2B` | -0.0092 (z -2.30, inside null, n 665/760) | +0.0337 (z +3.46, above p95, n 362/246) |
| `page_line_copier_3B` | +0.0008 (z +0.28, inside null, n 1126/1288) | +0.0029 (z +0.58, inside null, n 802/475) |

| plant | opening | closing |
|---|---|---|
| `plant_1A` | +0.7568 (z +32.33, above p95, n 662/743) | +0.6725 (z +18.07, above p95, n 334/228) |
| `plant_2B` | +0.8341 (z +40.36, above p95, n 665/760) | +0.7884 (z +30.49, above p95, n 362/246) |
| `plant_3B` | +0.7076 (z +41.09, above p95, n 1126/1288) | +0.6422 (z +40.82, above p95, n 802/475) |

## Shared onset shift

Side `opening`. `not_shared`. 1A-2B r +0.018 (n 10, pass `False`); 1A-3B r +0.394 (n 10, pass `False`); 2B-3B r +0.315 (n 12, pass `False`).

Figure: `figures/step_and_order.png`.
