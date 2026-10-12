# h19: held-out likelihood comparison of mechanisms (issue #3, expert option 3)

Pre-registration: `PREREG.md` (2726c9e).

**Running it:**
- `python run_h19.py` (≈ 90 s on 7 processes), then `python summarise.py`.
- Tests: `pytest test_h19.py` (5). They need `rapidfuzz` (`pip install rapidfuzz`) and are skipped without it.
- Per-token tables (`results/tokens_*.csv.gz`) hold transcription and control words. Those sources aren't committed (licences), so the tables are regenerated locally and not in git.

**Committed outputs:**
- `results/summary_table.csv` (bits per model, cell and fold scheme, winners, paired page tests, context gains);
- `results/copy_rate_crossfit.csv` (ML copy rate with bootstrap CI);
- `results/cell_*.json` (per-fold fitted parameters: copy λ for every W, edit channel, Naibbe ε, onset θ/π, slot smoothing);
- `results/summary.json` (predictions and verdict rules);
- `figures/bits_per_glyph.png`.

**Scored cells:**
- MS 408 hand×language cells 1A, 2B and 3B (≈ 10.3–10.8 k tokens each);
- 4 plain controls (Latin Celsus and Vulgate; Italian Sidrach and Dante; 10.5 k tokens each);
- 2 Naibbe ciphertexts (Latin Pliny, Italian Ariosto);
- a synthetic copy text with a known λ = 0.2.

Held-out data uses bifolium folds and quire folds; hyperparameters come from inner splits only. **No meaning or translation claims.**

## Key numbers (held-out bits/word, bifolium folds; quire folds in `summary_table.csv`)
| cell | G char-LM | SLOT | KN1 | KN2 | KN3 | COPY1 | COPY3 | NAIBBE (best plain LM) | bits/glyph of winner |
|---|---|---|---|---|---|---|---|---|---|
| MS 1A | 11.18 | 13.96 | 11.49 | 11.66 | 11.72 | 11.26 | 11.45 | 11.17 (ε = 0.99) | 1.94 |
| MS 2B | 10.49 | 13.80 | 10.78 | 10.92 | 10.98 | 10.54 | 10.68 | 10.47 (ε = 0.96) | 1.77 |
| MS 3B | 11.44 | 14.73 | 11.74 | 11.90 | 11.94 | 11.47 | 11.63 | 11.40 (ε = 0.94) | 1.84 |
| la_celsus | 14.98 | 20.04 | 13.93 | 13.82 | 13.85 | 13.75 | **13.64** | – | 2.05 |
| la_vulgate | 13.85 | 18.74 | 12.90 | 12.14 | 12.04 | 12.42 | **11.57** | – | 1.85 |
| it_sidrach | 12.27 | 16.22 | 11.70 | 10.64 | 10.58 | 11.18 | **10.08** | – | 1.96 |
| it_dante | 12.29 | 16.07 | 12.05 | 11.69 | 11.73 | 11.87 | **11.52** | – | 2.32 |
| Naibbe(la_pliny) | 11.08 | 14.57 | 11.16 | 11.36 | 11.41 | 11.09 | 11.33 | **9.67** (ε = 0.009) | 1.54 |
| Naibbe(it_ariosto) | 11.19 | 14.62 | 11.21 | 11.41 | 11.45 | 11.17 | 11.40 | **9.56** (ε = 0.003) | 1.53 |
| synthetic copy λ = 0.2 | 12.51 | 14.89 | 12.65 | 12.94 | 12.98 | **11.24** | 11.49 | 12.50 | 1.93 |

**Context (gain = KN1 − best of KN2/KN3/COPY1/COPY3):**
- MS: 0.23 / 0.25 / 0.27 bits/word (bifolium folds); 0.24 / 0.40 / 1.15 with quire folds. The 3B quire figure comes from a 2-quire split with a large vocabulary shift.
- Controls: 0.29–1.62, mean 0.94.
- In every MS cell the whole gain comes from the cache/copy component. Word n-gram context *hurts*: KN3 − KN1 = +0.20 to +0.23 bits/word. In the controls, KN2/KN3 help (up to −1.1 bits) and COPY3 (copy + trigram) wins all four.
- **The best MS model is context-free.** The character LM G, or G plus a 1–6 % Naibbe component, scores within 0.01–0.04 bits/word of the other leaders. Paired page tests vs the runner-up are tiny: 1A −0.001 bits [−0.005, 0.003].

**ML copy rate** (cross-fitted EM, COPY1, W = 100 chosen everywhere except synthetic W = 20; 500 page bootstraps):

| Cell | λ | 95 % CI |
|---|---|---|
| MS 1A | 0.103 | [0.093, 0.115] |
| MS 2B | 0.131 | [0.114, 0.151] |
| MS 3B | 0.122 | [0.108, 0.137] |
| la_celsus | 0.068 | [0.060, 0.077] |
| la_vulgate | 0.152 | [0.129, 0.179] |
| it_sidrach | 0.166 | [0.147, 0.187] |
| it_dante | 0.072 | [0.063, 0.080] |
| Naibbe ciphertexts | 0.022–0.026 | |
| synthetic (true 0.200) | 0.205 | [0.196, 0.214], recovered |

- **The copy rate is identified, but it isn't distinctive.** MS λ falls inside the range of real texts, where the copy component models word repetition and burstiness.
- *Exploratory* (inner-validation λ for each window): at W = 5, MS λ ≈ 0.042–0.048 vs controls 0.015–0.044 and ciphers 0.008. Local copying in MS 408 is slightly above most controls, but similar to Sidrach.

**Naibbe:**
- On its own ciphertexts, the right-language Naibbe model wins by 0.85–1.05 bits/word, with escape ε ≤ 0.009.
- On MS, 76–85 % of tokens are decodable under the Naibbe tables, but the fitted escape weight is ε = 0.94–0.99. The cipher component explains only ≈ 1–6 % of the probability mass and improves on G by just 0.01–0.04 bits/word (vs ≈ 1.5 bits on real ciphertext).

**Line-start onset feature** (gain on line-initial tokens, KN3 base):
- 1A 0.25, 2B 0.39, 3B 0.59 bits/token; fitted θ ≈ 0.15 (1A), 0.23 (2B), 0.29 (3B).
- On the COPY1 base: 0.22 / 0.34 / 0.46.

**Slot grammar:** worst everywhere (13.8–14.7 bits on MS). This is a smoothing/coverage weakness of the learned K = 12 grammar as a full probability model, not evidence against slot structure.

## Verdicts
| | Prediction | Result |
|---|---|---|
| P1 | control context gain > 2× MS | **pass** (0.94 vs 0.25 bifolium; 0.96 vs 0.60 quire fails 2×) |
| P2 | MS λ identified, in [0.01, 0.2], above controls; synthetic recovered | **fail**: identified (CI width ≤ 0.04) and in range, synthetic recovered, but MS λ is not above controls (Vulgate and Sidrach are higher) |
| P3 | Naibbe beats SLOT on ciphertexts but not on MS | **fail**: wins on ciphertexts, but also "beats" SLOT on MS because SLOT is weak and NAIBBE contains G as escape |
| P4 | MS winner context-light (KN1/COPY1/SLOT); KN3 gain < 0.3 | **fail** on the winner list: the winner is NAIBBE≈G (5/6), COPY1 in 3B quire. Context-light in substance, and KN3 is worse than KN1 |
| P5 | onset gain > 0.3 in 2B/3B, < 0.1 in 1A | **fail** (2B 0.39, 3B 0.59, but 1A 0.25: 1A also has onset-like line-start words, cf. h16 dchor/sor) |

**Pre-stated verdict rule:**
- "language-like": **no** (MS context gain 26 % of the controls').
- "copy-like": formally **yes** in all three cells (COPY1 < KN3 and λ lower bound > 0.05). But 1 of 4 real-language controls (Celsus) also meets it, so it doesn't discriminate.
- "cipher-like": formally **yes**, but degenerate. NAIBBE beats SLOT and KN1 only through its G escape (ε ≥ 0.94); it is not a Naibbe-like fit.

**Reading:**
- Under the same token budget, MS 408 cells behave unlike both real-language controls and Naibbe ciphertext.
- Previous words help only as a cache of similar recent words (copy/burstiness of real-text size). n-gram word context does not help.
- Most of the information sits in within-word spelling, and a context-free character model is best.
- This fits "generated/self-similar text with a word grammar" better than the other two options. But the copy rate itself isn't distinctive, so the result rules out more than it confirms.

## Limits
- **Small cells:** ≈ 10 k tokens per cell, so higher-order n-grams are sparse. The controls share the same budget, but MS has a higher type/token ratio, which handicaps every word-level model.
- **Copy model approximations:**
  - The edit channel uses one optimal alignment (a lower bound on the sum over alignments).
  - Sources farther than edit distance 3 are ignored.
  - The window covers the same page only.
  - The copy component also captures topic repetition, so λ is a "recent-similar-word" rate, not proof of mechanical copying.
- **Naibbe model approximations:** it ignores the rejection rule (deficient). Its letter context is the argmax decoding, and the plaintext LMs are trigram letter models from other texts. A better plaintext LM, or other cipher tables, could do better. This tests the published Naibbe scheme, not ciphers in general.
- **Controls:** modern editions, normalised spelling, pseudo-pages of 150 tokens.
- **No class-based model** (optional in the brief; not done).
- **Not pre-registered:** the W = 5 comparison and the G-vs-NAIBBE reading are exploratory.
