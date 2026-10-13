# h31 pre-registration: MS 408's word-construction system

Committed before any h31 statistic was computed. **No translation or meaning claims.**

## Question
Are MS 408 words built from a small inventory of combinable pieces that behave like morphemes (language-like), or are the pieces combined freely the way a generator or table cipher combines them?

## Corpora (about 10,500 tokens each; built as in h19 `all_cells()`)
| Group | Corpora | Notes |
|---|---|---|
| MS | hands 1A, 2B, 3B | ZL3b, EVA characters as written; h19 tokenisation |
| Natural (NAT) | la_celsus, la_vulgate, it_sidrach, it_dante, he_tanakh, ar_quran | Hebrew and Arabic use the repository's 1:1 transliteration |
| Generators (GEN) | Naibbe(la_pliny), Naibbe(it_ariosto), C0 | Naibbe: real tables, h19 seeds. C0: the h12 no-plaintext copy-modify generator, fitted on MS 2B with seed 0 |

Generator caveat: C0 is fitted on MS, so similarity to MS is partly circular.

## Segmenters (type-level, on characters)
- **M1 Morfessor Baseline 2.0.6.** MDL, trained on types, default corpus weight; Viterbi segmentation.
- **M2 Bayesian stem + suffix.** Collapsed Gibbs over the split point of each type. DP priors on stems and suffixes, α = 1. Base = geometric length (p = 0.5) × character unigram. The suffix may be empty. 300 sweeps, seed 0.
- **M3 slot/affix baseline.** `msdecipher.slot_grammar.AffixModel` (the project's prefix + core + suffix word-structure model). stem = prefix + core.

For M1, suffix = last morph if the word has ≥ 2 morphs, otherwise empty; stem = the rest.

## Metrics (per corpus × segmenter)
- **I1 inventory:** distinct morph types per word type (M1), and distinct suffixes (all M).
- **P1 productivity:** observed distinct (stem, suffix) type pairs ÷ the number expected if stems and suffixes were drawn independently from their token marginals, Σ 1 − (1 − p_s p_x)^N.
- **C1 constraint:** token-level MI(stem; suffix) minus its mean under 200 suffix shuffles across tokens, divided by H(suffix). This is the normalised excess dependence.
- **R1 paradigm reuse:** among stems with ≥ 2 distinct suffixes (type level), the share whose exact suffix set is shared with ≥ 1 other stem. Reported as a ratio to 200 nulls that keep each stem's number of suffixes and draw suffixes by type frequency.
- **A1 agreement:** MI(suffix of word i; first character of word i+1) over adjacent tokens within a page, minus its mean under 200 within-page order shuffles, in bits. To separate morphology from plain letter adjacency, A1' is the same quantity with the last character of word i in place of the suffix (reported alongside).
- **L1 held-out likelihood:** bits/word on held-out page groups, using MS bifolium folds and 5 contiguous block folds for the others. Compared:
  - the h19 `CharLM(4)`;
  - M1 and M2 morph models: P(w) = Σ over segmentations Π q(m) × stop terms, with CRP-smoothed morph unigrams and a character base;
  - M3 `AffixModel.logprob2`.
  - Statistic: the gap = best morph model − CharLM (bits/word).

## Verdict rules (per metric, M1 primary; M2 and M3 as robustness)
- MS (each hand) is **language-like** on a metric if all three hands fall inside the NAT range [min, max] and outside the GEN range.
- **Generator-like** is the reverse. Otherwise **neither / overlapping**.
- **H-morph** (words are morpheme-like) is supported if MS is language-like on ≥ 3 of P1, C1, R1, A1 under M1, and the same holds under at least one of M2/M3.
- **H-decor** (independent combination, generator-like) is supported if MS is generator-like on ≥ 3 of the 4.
- **Expectation (prior work: L06, h19, h26–h29):** MS has fewer suffixes, stronger within-word constraints, little cross-word dependence, and a CharLM that beats morph models by more than in natural text. Overall verdict expected: neither / generator-leaning.
- No multiple-testing correction applies, because these are descriptive range comparisons. The A1 and C1 null z-scores are reported.
