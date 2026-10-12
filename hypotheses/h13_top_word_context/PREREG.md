# h13 pre-registration: the 100 most common words in context (committed before computing)

**Data.** ZL3b (h09 parser plus raw IVTFF markers), running text = P loci (lines), labels = L loci. Top 100 = most frequent word types in P + C + R + L loci.
Hand × language (HL) from `data/quires.csv`. Image tags from `hypotheses/h09_image_context_cribs/data/visual_tags.csv` (pre-registered in h09).

## Metrics per word
1. **Position** (P loci only): line-initial, line-final, paragraph-initial (line opened by `<%>`), and label share (L tokens / all tokens). Expected counts are within-HL: each token contributes its HL cell's base rate. Enrichment = observed/expected, two-sided Poisson p. Holm over 100 words × 4 positions.
2. **Neighbours.** Left and right neighbour counts within P lines over the top 300 context words, PPMI-weighted, concatenated (L|R). Cosine similarity; average-linkage clustering into k = 8 classes; 2-D SVD plot. Cluster quality = silhouette vs the same procedure on context vectors with the neighbour tokens shuffled within HL (20 shuffles).
   **Spelling variants**: pairs of top-100 words at unit edit distance ≤ 2, and specifically the h11/h12 rule pairs X-edy ↔ X-ol (and -edy ↔ -or, -dy ↔ -ol). Test: context cosine of rule pairs vs all other top-100 pairs at the same edit distance (permutation of pair labels, 5000), and **cross-hand** cosine (X's contexts in 2B vs Y's contexts in 1A) vs the mean cross-hand cosine of X with random other top-100 words.
3. **Image links.** *Page level*: per-page rate (per 1000 tokens) vs h09 tag scores water, star, root, jar, nymph, large_root, blue_flower (Pearson r of log1p rate). *Label level*: the word's label tokens by IVTFF object type (jar, plant part, nymph, tube, star, zodiac) vs expectation. Null: tags / object types permuted **within quire × HL strata** (2000). Holm over all word × tag (page) and word × object type (label) tests.

## Predictions
* P1: at least 10 words are significantly line-initial or paragraph-initial enriched within HL (gallows-initial words such as p-/t- words, and `daiin`-like words at line start), and at least 5 line-final (`-am`, `-y` words).
* P2: neighbour clusters beat the shuffled-context silhouette; at least 3 classes are not just frequency bands.
* P3: rule pairs (-edy/-ol etc.) have higher cross-hand context similarity than random pairs (one-sided p < 0.05). If not, the h11/h12 mapping is a distributional, not a word-level, correspondence.
* P4: few image links survive the quire × HL null after Holm (≤ 5 word–tag pairs), because tags are nearly constant within quire.
No translation or meaning claims are made from any result.
