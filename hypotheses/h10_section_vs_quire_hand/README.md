# h10: section vs quire, scribal hand and Currier language

**Verdict.** I found no section effect that survives the pre-registered rule: Holm p < 0.05 under both the stratified permutation null and the drift-aware rotation null. Holding quire, hand and language fixed:

1. **Section effects do exist inside a single quire and hand.** In Q15 (hand 1, Currier A), herbal and pharmaceutical pages differ: JS excess 0.072 bits, NB balanced accuracy 0.83 (chance 0.5), Holm p = 0.010 under the stratified permutation. The drift-aware null can't confirm it. That null has only 11 rotations (minimum p = 0.083), and the observed p is 0.17. The other within-stratum contrasts (S2–S4) are not significant (JS excess 0.007–0.081).
2. **Within one section, hand/language effects are 3–4× larger than within-stratum section effects.** Herbal hand 1 A vs hand 2 B in the same quires (Q4–Q7) gives JS excess 0.222 and balanced accuracy 0.99. Q6 hand 1 vs hand 5 gives 0.271, and Q17 hand 1 A vs hand 3 B gives 0.271. Within-section, within-hand **quire** differences are small: pharmaceutical Q15 vs Q19 gives 0.035 (balanced accuracy 0.48, i.e. at chance), and herbal Q1–Q7 in hand 1 A gives 0.021 (balanced accuracy 0.09 vs chance 0.14).
3. **Variance decomposition.** Pages are Hellinger-transformed vectors over the top 300 words (217 pages). The full model explains R² 0.323. Unique shares are: quire 0.068, **section 0.025**, hand 0.015, language 0.005 (all p ≤ 0.004), and page order 0.010 (p = 0.41). 0.200 is shared between section, quire, hand and language and can't be attributed to any one of them. Unique section is 8 % of the explained variance (P3 confirmed).
4. **h09 enrichments under a fixed hand.** The water, star and root/jar words stay enriched on their section's pages within one hand: water bio vs herbal in hand 2 B, log rate ratio 1.58; star words stars vs herbal in hand 3 B, 1.15; root/jar words pharma vs herbal in hand 1 A, 2.32; all Holm p = 0.004 under page-label permutation. Against frequency-matched random word sets, only the root/jar words in hand 1 A survive (Holm 0.004). The water and star sets are no more enriched than random words of the same frequency taken within the same hand (Holm 0.40). Inside Q15 alone, root/jar words give a log rate ratio of 1.06 (p = 0.033, Holm 0.099, only 33 tokens). The h09 **root-word transfer** to large-root herbal pages is weaker within hand 1 A (log rate ratio 0.44, p = 0.037, Holm 0.099) and absent in hand 2 B (0.05, p = 0.25).

So the "section signal" in earlier stages is mostly a mixture of hand/language and quire. A residual section difference is visible where quire and hand are fixed (Q15, and hand 1 herbal vs pharma: JS excess 0.117, BA 0.90, drift p = 0.018, Holm 0.072). It is about a quarter to a third the size of the hand effect. With so few non-confounded pages, no residual section effect passes both nulls after Holm correction.

## Pre-registration
`PREREG.md` and `inventory.py` / `results/inventory.csv` were committed before any vocabulary statistic (commit `a4bc34e`). Deviations: BA uses leave-one-bifolium-out with a fallback to leave-one-page-out where a bifolium holds a class's only other pages; the variance-decomposition permutation count is 499 instead of 999.

## Inventory (where section and quire/hand are not confounded; `results/inventory.csv`)
| stratum (quire × hand × lang) | classes (pages / running-text tokens) |
|---|---|
| Q15 h1 A | herbal 6p/461t · pharmaceutical 6p/896t |
| Q10 h4 | cosmological 4p/594t · zodiac 2p/153t |
| Q9 h4 | astronomical 8p/723t · cosmological 2p/214t |
| Q14 h2 B | cosmological 3p/611t · text-only 3p/1218t |
| Q8 (mixed hands) | herbal (h3/h5) · stars (h3 A) · cosmological (h1) · text-only: no class pair in one hand with text in both |

Biological (Q13 only, hand 2 B) and stars/recipes (Q20, hand 3 B) have **no** within-quire contrast. Hand 2 B also writes herbal (Q4–Q7) and cosmological (Q14) pages; hand 3 B also writes herbal pages (Q17). Those across-quire, within-hand contrasts are the H block.

## All contrasts (`results/contrasts.csv`, 2000 permutations; "t" = tokens of words occurring ≥ 2 times)
| contrast | BA | JS excess (perm) | p perm / drift | Holm perm / drift |
|---|---|---|---|---|
| S1 Q15 h1A herbal vs pharma | 0.83 | 0.072 | 0.0025 / 0.17 | 0.010 / 0.67 |
| S2 Q10 h4 cosmo vs zodiac | 0.50 | 0.081 | 0.065 / 0.17 | 0.19 / 0.67 |
| S3 Q9 h4 astro vs cosmo | 0.63 | 0.007 | 0.39 / 0.40 | 0.39 / 0.67 |
| S4 Q14 h2B cosmo vs text-only | 0.67 | 0.067 | 0.093 / 0.17 | 0.19 / 0.67 |
| S5 pooled S1–S4 | 0.68 | 0.055 | 0.006 / 0.17 | – |
| H1 hand1A herbal vs pharma | 0.90 | 0.117 | 0.0005 / 0.018 | 0.002 / 0.072 |
| H2 hand2B herbal/bio/cosmo | 1.00 | 0.169 | 0.0005 / 0.048 | 0.002 / 0.11 |
| H3 hand3B herbal vs stars | 0.83 | 0.242 | 0.0005 / 0.036 | 0.002 / 0.11 |
| H4 hand4 astro/cosmo/zodiac | 0.63 | 0.041 | 0.013 / 0.27 | 0.013 / 0.27 |
| R1 herbal Q4–7 1A vs 2B | 0.99 | 0.222 | 0.0005 / 0.063 | 0.0025 / 0.25 |
| R2 herbal Q6 h1 vs h5 | 1.00 | 0.271 | 0.0045 / 0.083 | 0.014 / 0.25 |
| R3 herbal Q17 1A vs 3B | 1.00 | 0.271 | 0.005 / 0.10 | 0.014 / 0.25 |
| R4 pharma Q15 vs Q19 (h1A) | 0.48 | 0.035 | 0.018 / 0.063 | 0.018 / 0.25 |
| R5 herbal h1A Q1–Q7 | 0.09 | 0.021 | 0.0005 / 0.047 | 0.0025 / 0.24 |

Jackknife CIs (by bifolium) are in the CSV where at least 3 deletions keep every class: H1 BA 0.59–1.21, H3 0.70–0.97, H4 0.46–0.79, R1 0.97–1.01. They are wide and partly beyond [0, 1], because there are few bifolia.

## Limitations
* The non-confounded section contrasts are tiny: 6–12 pages and 400–1,300 tokens. The drift-aware null has only 5–11 distinct rotations, so p < 0.05 is **impossible** for S1–S4 under it. The pre-registered "both nulls" rule can't be met there, and a null result is not evidence of no section effect.
* Hand and Currier language are almost the same variable (hand 1 = A; hands 2, 3, 5 = B), so "hand" here means hand + language.
* The section labels come from illustration type, so "section" and "picture type" are the same factor.
* JS is size-dependent. Excess over a permutation null with the same page sizes corrects for that within a contrast. Comparing across contrasts of very different sizes is only approximate.
* The variance decomposition is linear on Hellinger vectors of the top 300 words, and factors with many levels (quire, 17 df) absorb more by chance. The unique-R² p-values account for that, but the R² sizes don't.

Reproduce: `python inventory.py && python run_h10.py 2000 && python make_figures.py`; tests `pytest test_h10.py`.
