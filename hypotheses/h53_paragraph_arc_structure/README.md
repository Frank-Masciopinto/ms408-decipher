# h53 — paragraph interior arc

Pre-registered contrast of the words left in the middle of a paragraph's first line and the middle of its last line, after the first and last word of every line are removed. The null shuffles line order inside the paragraph. Nothing here is a translation.

**Reading: `paragraph_role`.** A1 passes in all three hands. C1 passes, so the same contrast does see a recipe paragraph.

Word-class excess is +0.044 / +0.022 / +0.029 bits in hands 1A, 2B and 3B, against −0.000 / +0.011 / +0.010 for the copier on the same folios. Cucina is +0.042. Hand 2B clears the pre-registered gap over its copier by 0.010 bits, which is the threshold. The onset of those same interior words, reported but not part of A1, separates the hands from the copier more cleanly (+0.074 / +0.020 / +0.039 against about 0). Shuffling lines inside a paragraph also removes top-to-bottom drift, and the copier already carries some of that drift; the comparison with the copier is what A1 uses.

## Word-class JS, opening interior vs closing interior

| stream | open / close tokens | word excess | onset excess | end excess |
|---|---|---|---|---|
| `MS_1A` | 1277 / 599 | +0.0442 (z +14.89, above p95) | +0.0737 (z +38.92, above p95) | +0.0016 (z +1.34, inside null) |
| `MS_2B` | 1018 / 582 | +0.0215 (z +6.18, above p95) | +0.0201 (z +11.51, above p95) | +0.0117 (z +7.97, above p95) |
| `MS_3B` | 1945 / 1032 | +0.0293 (z +14.66, above p95) | +0.0386 (z +31.76, above p95) | +0.0074 (z +9.08, above p95) |
| `page_line_copier_1A` | 1277 / 599 | -0.0001 (z -0.02, inside null) | -0.0002 (z -0.15, inside null) | +0.0019 (z +1.37, inside null) |
| `page_line_copier_2B` | 1018 / 582 | +0.0115 (z +3.66, above p95) | +0.0021 (z +1.57, inside null) | -0.0005 (z -0.35, inside null) |
| `page_line_copier_3B` | 1945 / 1032 | +0.0105 (z +6.22, above p95) | +0.0000 (z +0.05, inside null) | +0.0007 (z +1.08, inside null) |
| `it_cucina` | 1390 / 600 | +0.0421 (z +14.37, above p95) | +0.0355 (z +20.56, above p95) | +0.0218 (z +13.94, above p95) |

Only the word-class column enters A1 and C1. Onset and end are reported on the same line shuffles.

Figure: `figures/paragraph_arc.png`.
