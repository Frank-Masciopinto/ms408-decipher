# h19 pre-registration: held-out likelihood comparison of mechanisms (GitHub issue #3, expert option 3)

Committed before any model is fitted or scored.

## Data
- **MS 408:** ZL3b P loci (h14 `table()`), readable tokens in page order. Cells: hand × Currier language 1A, 2B and 3B (≈ 10.3–10.8 k tokens each; the other cells are < 1 k tokens and are not scored).
- **Controls:** the first 10 500 normalised tokens of la_celsus, la_vulgate, it_sidrach and it_dante, cut into 150-token pseudo-pages. A pseudo-quire is 8 consecutive pages; pseudo-bifolia pair pages i and 7 − i within each pseudo-quire.
- **Cipher controls:** Naibbe ciphertext (`mech_naibbe`, 78-card deck, standard respacing) of la_pliny_herbal (Latin) and it_ariosto (Italian), 10 500 tokens each, same paging.
- **Synthetic positive control for copying:** 10 500 tokens drawn from the 2B unigram with a known copy rate λ = 0.2 under the copy model below (W = 20, edit parameters fixed). Used to check that λ is recovered.

## Folds
- Within each cell, GroupKFold(5) by bifolium (MS `bifolium_id`; controls: pseudo-bifolia).
- GroupKFold(min(5, n_quires)) by quire. The MS cell 3B has only 2 quires, so 2 folds.
- **Hyperparameters** (mixture weights, edit parameters, ε, θ, slot smoothing) are fitted on an inner split of the training fold (20 % of its groups), never on the test fold. Base models are then refitted on the full training fold.

## Models
Each model gives log2 P(w_t | history); history is the earlier tokens on the same page.
- **G (char LM):** interpolated Witten–Bell character 4-gram within words, with boundary symbols. A context-free spelling model, used as the shared OOV base.
- **SLOT:** the learned slot grammar (`mech_grammars.LearnedUnit("slot", K=12)`, collapsed units for MS, letters for controls), mixed 0.99 / 0.01 with G for robustness.
- **KN1, KN2, KN3:** interpolated Kneser–Ney word n-grams (discount 0.75), with the unigram level interpolated with G.
- **COPY(base):** P = (1 − λ) P_base(w | ctx) + λ · (1/k) Σ_{j ≤ k} P_edit(w | s_j), with s_j the last k = min(W, available) tokens on the page.
  - P_edit is a per-character edit channel on the optimal Levenshtein alignment (rapidfuzz editops): keep p_k, substitute p_s (character drawn from the training character unigram), delete p_d, with p_k + p_s + p_d = 1; geometric insertions p_i per gap.
  - Sources at edit distance > 3 get P_edit = 0, which is conservative.
  - λ, p_k, p_s, p_d and p_i are fitted by **EM** (closed-form M-step).
  - W ∈ {5, 20, 100} is chosen by inner-validation likelihood; all three are also reported.
  - Bases: KN1 ("COPY1") and KN3 ("COPY3").
- **NAIBBE(plain LM):** P = (1 − ε) P_N(w | letters so far) + ε G(w).
  - P_N sums over all decodings of w under the author's tables: a unigram (p = 17/36) or a bigram prefix + suffix, with table probabilities from the 78-card deck weights. Rejection sampling is ignored (deficient model).
  - The plaintext model is an interpolated letter trigram trained on la_isidore + la_augustine (Latin) or it_manzoni + it_sidrach (Italian); the Italian training includes it_sidrach, which is also a plain control.
  - The letter context is the most probable decoding of the preceding words, reset after an undecodable word.
  - Scored for MS cells and the cipher controls.
- **ONSET (MS only, optional feature):** at line-initial tokens, P' = (1 − θ) P(w | ctx) + θ Σ_o π_o 1[w = o + b, |b| ≥ 2] P(b | ctx), with o ∈ {d, s, t, p, k, f}. θ and π are fitted by EM on inner validation. Applied on top of KN3 and of the winning model.

## Metrics
- Mean bits/word on held-out tokens, pooled over folds, and bits/glyph = bits/word ÷ mean (characters + 1).
- **Context gain** = bits(KN1) − bits(best of KN2, KN3, COPY1, COPY3); also KN1 − KN3 and KN1 − COPY1 separately.
- **ML copy rate:** cross-fitted λ (EM on each held-out bifolium fold with the base fitted on the other folds; pooled), with a 95 % CI from 500 page bootstraps of the cross-fitted EM.
- **Model ranking** per cell: paired page-level differences in bits, with a sign test and a page-bootstrap CI.

## Predictions
- **P1 (context):** real-language controls gain more from context than MS cells. Mean control KN1 − best-context gain > 2× the mean MS gain (in bits/word).
- **P2 (copy rate):** MS λ is identified (CI width < 0.1) and lies in [0.01, 0.2]. MS λ > control λ. The synthetic λ = 0.2 is recovered within ±0.05.
- **P3 (cipher):** Naibbe beats SLOT on its own ciphertext controls, but not on any MS cell.
- **P4 (winner):** in each MS cell the winner (lowest held-out bits/word in both fold schemes) is a context-light model (KN1, COPY1 or SLOT), with the KN3 gain over KN1 < 0.3 bits/word.
- **P5 (onset):** ONSET reduces line-initial bits by > 0.3 bits/token in 2B and 3B, and by < 0.1 in 1A.

## Verdict rule (pre-stated)
- **"language-like":** MS context gain ≥ 50 % of the control mean.
- **"generated/copy-like":** COPY beats KN3 and λ's lower CI bound > 0.05.
- **"cipher-like":** NAIBBE beats SLOT and KN1 on MS.
- Otherwise: "none of the three clearly". More than one label can apply.

No translation or meaning claims.
