# h52 — non-touching slot agreement

Pre-registered test of whether the opening of a word still predicts the ending of the next word, or the interior of a word predicts the next interior, after the touching pair `(end of word t, onset of word t+1)` is held fixed. The null shuffles the right-hand slot inside each touching pair. Nothing here is a translation.

**Verdict: `supported`.** The validity check passes (`synthetic_bind_2B` excess +2.056, z +702). G1 passes on F2 in all three hands. G2 fails. F1 passes only in hand 3B.

The F2 excess is about +0.02 bits in each hand (z +4.3 to +5.0). The same statistic on Cucina and Sidrach is +0.17 to +0.20 bits. The copier sits between −0.001 and +0.007. So adjacent interiors are coupled beyond the junction rule, and `page_line_copier` does not produce that coupling, at roughly one tenth the size of the same coupling in the two Italian prose texts.

## Lag 1 excess over the stratum shuffle

| stream | F1 onset(t) → end(t+1) | F2 core(t) → core(t+1) | F3 end(t) → end(t+1) |
|---|---|---|---|
| `MS_1A` | +0.0075 (z +1.31, n 8115) | +0.0229 (z +4.30, n 8115) | +0.0248 (z +7.19, n 8830) |
| `MS_2B` | +0.0090 (z +2.15, n 8838) | +0.0202 (z +4.30, n 8838) | +0.0151 (z +6.36, n 9297) |
| `MS_3B` | +0.0124 (z +2.62, n 8912) | +0.0225 (z +4.99, n 8912) | +0.0186 (z +7.50, n 9424) |
| `page_line_copier_1A` | +0.0039 (z +0.97, n 8410) | +0.0075 (z +1.77, n 8410) | -0.0015 (z -0.55, n 8849) |
| `page_line_copier_2B` | -0.0014 (z -0.46, n 9083) | -0.0011 (z -0.28, n 9083) | +0.0028 (z +1.51, n 9293) |
| `page_line_copier_3B` | -0.0067 (z -1.69, n 9136) | +0.0018 (z +0.43, n 9136) | +0.0062 (z +3.19, n 9409) |
| `it_cucina` | +0.2224 (z +41.10, n 8199) | +0.1990 (z +40.59, n 8199) | +0.2017 (z +68.46, n 9002) |
| `it_sidrach` | +0.2181 (z +34.24, n 7692) | +0.1674 (z +26.75, n 7692) | +0.3175 (z +72.00, n 9135) |

## Lag 2, reported only

| stream | F1 | F2 |
|---|---|---|
| `MS_1A` | -0.0057 (z -0.87, n 6652) | +0.0282 (z +4.38, n 6652) |
| `MS_2B` | +0.0059 (z +1.12, n 7656) | +0.0184 (z +3.33, n 7656) |
| `MS_3B` | +0.0004 (z +0.07, n 7927) | +0.0078 (z +1.44, n 7927) |
| `page_line_copier_1A` | -0.0020 (z -0.39, n 6971) | -0.0079 (z -1.26, n 6971) |
| `page_line_copier_2B` | +0.0012 (z +0.36, n 7899) | -0.0066 (z -1.26, n 7899) |
| `page_line_copier_3B` | +0.0057 (z +1.24, n 8061) | -0.0005 (z -0.09, n 8061) |
| `it_cucina` | +0.0974 (z +15.44, n 7244) | +0.0894 (z +14.72, n 7244) |
| `it_sidrach` | +0.1084 (z +14.74, n 6839) | +0.0786 (z +13.36, n 6839) |

F3 conditions only on the next word's onset, so it is a suffix-to-suffix reference and is not part of G1 or G2. Prose rows are references and do not change the verdict.

Figure: `figures/slot_agreement.png`.
