# h11 pre-registration (committed before any statistic is computed)

Data: ZL3b running text (P, C, R loci; h09 parser); page metadata `data/quires.csv` via h10 `inventory.pages()`. Hand = LFD hand, language = Currier language; "HL" = hand×language cell.

## 1 Word-production models (held-out fit)
Hierarchical Dirichlet-smoothed unigram models with back-off: global → language → HL → (quire) → (section). p(w|g) = (n_gw + a·p(w|parent))/(n_g + a), a chosen on training folds from a grid. Folds: `msdecipher.quires.group_folds(level="quire")` (5 folds) and bifolium folds. Score: held-out bits/token (lower is better) per model: M0 global, M1 +language, M2 +HL, M3 +HL+quire, M4 +HL+section, M5 +HL+quire+section. "Variance explained" by hand+language: R² of Hellinger page vectors (top 300 words) on HL dummies, alone and relative to the full h10 model.
Hand-conditioned copy-modify generator: if feasible, the h06 engine fitted per hand; otherwise documented as not done.

## 2 Residual tests
Residualise Hellinger page vectors on (A) HL dummies and (B) HL + quire dummies. On residuals:
* section classification: nearest-centroid (cosine), leave-one-bifolium-out, balanced accuracy; between-section pseudo-F. Nulls: labels permuted within HL (2000) and cyclic rotation along page order within HL (drift-aware).
* variance decomposition (unique R² of section, quire, page order on residuals A).
* h09 word sets (water qol olkedy qokain qoteedy qokedy; star cheeo lkaiin oteey al oteedy; root/jar ctheol ckhey qoor qokeody qockhey qokeol okeol) and the k=10 root transfer set (chody ckhey oldy qockhey okeeey qokey sol aiin qokol okal): mean residual score (sum of residual Hellinger coordinates of the set) on target vs other pages; nulls: within-HL label permutation, within-HL drift rotation, frequency-matched random word sets. Holm over the family.
Prediction R1: after (A), section remains detectable (BA above within-HL null) for herbal vs pharma and stars vs others; after (B), only contrasts with within-quire variation can remain and none survives the drift null. R2: root/jar words survive (A) vs random words; water/star do not; root transfer does not survive.

## 3 Hand effects
* Discriminating words/units/prefixes/suffixes between HL cells (main: herbal 1A vs herbal 2B, Q4–Q7 and all herbal; also all 1A vs all 2B): log-odds ratio with informative Dirichlet prior (Monroe et al. 2008), z, page-bootstrap 95 % CI.
* Orthography vs vocabulary: greedy rewrite-rule model (up to 10 string substitutions over word-initial / word-final / any-position unit n-grams, learned on half the pages, scored on the other half) mapping one cell's tokens toward another's; statistic = fraction of held-out word-distribution JS removed. Compare: hand gap (herbal 1A vs herbal 2B) vs section gap within one hand (1A herbal vs 1A pharma; 2B herbal vs 2B biological) vs same-cell split halves (noise floor).
Prediction R3: rewrite rules close a larger fraction of the hand gap than of the section gap (orthography-like hands), but less than half of it (hands also differ in vocabulary).
