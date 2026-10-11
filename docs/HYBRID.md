# Hybrid generators: plaintext dependence + copy-and-modify reuse (Stage 9)

**MS 408 is undeciphered. Nothing here decodes it or identifies a plaintext.** The mechanisms stage ([MECHANISMS.md](MECHANISMS.md)) found the Naibbe cipher and the
self-citation generator complementary: the cipher gets word-frequency shape but over-structures words and under-produces rare types; self-citation gets letter-level
statistics and adjacent repeats but under-produces hapaxes (0.515 vs 0.687) and over-produces suffixes (0.52 vs 0.21). This stage builds hybrids of the two ingredients,
fits them on *training folios*, tests them on *held-out folios* and fresh seeds with the full 35-metric suite, and then asks whether MS 408's section-specific vocabulary needs
a topic-structured source. Reports: `reports/mechanisms/hybrid/REPORT.md` (step 1), `reports/mechanisms/hybrid/topics/REPORT.md` (step 2). Run: `python -m msdecipher hybrid-run`, `hybrid-topics`.

## Generators (`mech_hybrid.py`)

A simplified, documented Python copy-and-modify engine (**not** the Timm & Schinner rule set; that stays the Java parent). Per output word: with probability `p_copy` copy a recent
word (previous word with `p_prev`, else uniform over the last `window`), apply one operation (exact repeat `p_exact`, final-unit edit `p_suffix`, initial-unit edit `p_prefix`,
inner replacement = rest); otherwise take the next *innovation* from an encoder. ≤ 3 identical repeats, ≤ 10 units. **6 fitted parameters.**

| id | innovation / edit source | extra fitted parameters |
|---|---|---|
| A1 | Naibbe-cipher tokens made on the fly from Latin/Italian plaintext (author's tables, card draws, respacing, unambiguity); edits use the innovated words' own unit pools | 0 |
| A2 | whole-word codebook: each plaintext word type → a fixed codeword from a slot-conditioned-bigram grammar fitted on the training types | ~1.4–1.6k (counted) |
| B (reverse) | copy-modify base (`p_copy ≥ 0.6`); each edit inserts the Naibbe glyph string of the *next plaintext letter*; innovations are Naibbe tokens | 0 |
| C0 (control) | same engine, innovations i.i.d. from the MS-fitted grammar: **no plaintext** | ~1.4–1.6k |

## Step 1: fit on training folios, test on held-out folios

3 folds by folio (folio *i* → fold *i* mod 3; every fold spans all sections and both Currier languages). Fit objective: RMS z over 9 lexicon metrics + H1/h2/h3 (12 metrics);
random search (120) + local refinement; **the 23 structure metrics (within-word shuffle, positional skew, slot grammar, suffix, cluster stability, word-length SD, coverage) are never fitted.**
Evaluation: 5 fresh-seed runs per model per fold on different plaintexts (7 Latin, 4 Italian), generated at the held-out fold's size (~11k tokens), prediction-interval verdicts vs the
held-out fold's jackknife SE. Parents run identically (Timm-Schinner fitted parameters came from all of MS 408 → in-sample, a head start).

| model | fitted k | ≈ of 35 (held-out, mean of folds) | ≈ of the 23 unfitted | χ² on the 12 fit metrics: train / held-out | AIC_train = χ² + 2k |
|---|---|---|---|---|---|
| **A1** Naibbe + copy-modify | 6 | 21.7 | 14.0 | 102 / **62** | **114** |
| A2 codebook + copy-modify | ~1,390 | 21.7 | 13.0 | 279 / 238 | 3,123 |
| B reverse | 6 | 17.3 | 14.0 | 519 / 422 | 531 |
| C0 no-plaintext control | ~1,390 | 25.3 | 17.0 | 72 / 72 | 2,916 |
| Naibbe cipher (parent) | 0 | 17.7 | 10.0 | 456 / 208 | 456 |
| Self-citation defaults (parent) | 0 | 22.7 | 16.7 | 434 / 399 | 434 |
| Self-citation fitted (parent, in-sample) | 15 | 26.0 | 17.0 | 222 / 216 | 252 |
| Slot-conditioned bigram (trained on training folios) | ~1,380 | 25.0 | 18.0 | 154 / 129 | 2,985 |

Findings:

1. **A1 repairs part of what each parent misses with 6 parameters.** Against the Naibbe parent it gains +4.0 reproduced metrics (14.0 vs 10.0 of the 23 unfitted ones): adjacent identical rate 0.008 vs MS 0.008 (parent 0.002),
   adjacent edit-1 rate 0.036 vs 0.034 (parent 0.011), within-word shuffle effect 1.32 vs 1.34 (parent 1.48), hapax share 0.640 vs 0.700 (parent 0.561, still below). Against the self-citation parents its hapax share is closer to MS 408 (0.640 vs 0.52–0.53; MS 0.700). Its held-out χ² on the fit metrics (62) is the lowest of all models, with the smallest AIC (114).
2. **What it does not repair:** slot-grammar shuffle penalty 4.78 vs 3.32 (words still over-structured: the tables' glyph strings are strongly position-bound), suffix rate 0.32 vs 0.16, positional JSD 0.545 vs 0.660,
   hapax share still ↑ in 3/3 folds. **No model of any kind matches the suffix rate** (0/3 or 1/3 folds in every column).
3. **Plaintext adds no measurable improvement over a no-plaintext copy-modify control on these metrics.** C0 (no plaintext, but ~1.4k parameters of MS-fitted grammar) reproduces 25.3/35 and 17/23 unfitted, A1 14/23. The
   parameter-penalised comparison favours A1 only because C0/A2 spend ~1.4k parameters; per parameter A1 is efficient, per outcome the grammar-driven control is better. The honest summary: **a hybrid fits the lexicon/letter metrics it was fitted on
   with 6 parameters and generalises to held-out folios, but the plaintext ingredient is not what produces the improvement over the parents — the copy-modify layer is** (A1 vs the pure cipher; C0 vs A1).
4. **A2 (codebook)** fixes hapax share/type-token (3/3 folds) but loses the within-word shuffle effect (1.09 vs 1.34) and positional structure; **B (reverse)** fits worst (the plaintext glyph strings make words too long: word-length SD 2.10 vs 1.65).
5. Cluster-stability metrics are matched by every model (MS 408's jackknife SE is large); read the point estimates in the report.

## Step 2: plaintext-signal (section vocabulary) test

Folio-level bags of words; five classes (herbal 128 folios, recipes 25, biological 19, pharmaceutical 16, cosmological+astronomical 13). Statistics: between-section JS, held-out-folio classification (NB, TF-IDF+LR; 5-fold CV by folio, 3 repeats),
section-keyword split-half overlap. Nulls: exchangeable-folio label permutation (1,000), and a **drift-aware null** (labels circularly shifted along the folio order, 181 shifts). Generated corpora are laid out on the same folio sequence;
topic-matched plaintexts (herbal ← Pliny XX–XXVII, pharmaceutical ← Celsus, biological ← Pliny VII–XI, recipes ← Macer, cosmo/astro ← Isidore) vs topic-mixed (work drawn per folio), a single-work control, C0, pure Naibbe and the Java generator.

Results are in `reports/mechanisms/hybrid/topics/REPORT.md`; the headline numbers are reproduced below from it.

| quantity | MS 408 | notes |
|---|---|---|
| between-section JS | 0.406 bits (permutation null 0.246, p = 0.001) | drift-aware (shifted-label) null 0.332, p = 0.0055 (smallest attainable) |
| NB balanced accuracy, held-out folios | 0.723 (95 % folio-bootstrap CI 0.676–0.766; chance 0.20) | shifted-label null mean 0.406, max 0.611 |
| TF-IDF + LR balanced accuracy | 0.662 (CI 0.613–0.718) | |
| within Currier A (herbal vs pharmaceutical) / within B (herbal, biological, recipes) | 0.944 / 0.976 | label-permutation nulls 0.49 / 0.33 |

Generators on the same folio layout (NB balanced accuracy, mean of 10 seeds; within-A / within-B in brackets):

| generator | NB acc. | JS excess | within-A / within-B |
|---|---|---|---|
| C0 no plaintext | 0.204 | 0.004 | 0.49 / 0.37 |
| Naibbe cipher, topic-matched / topic-mixed | 0.324 / 0.213 | 0.002 / −0.004 | 0.55 / 0.50 vs 0.49 / 0.37 |
| A1 hybrid, topic-matched / topic-mixed | 0.328 / 0.240 | 0.001 / −0.003 | 0.51 / 0.53 vs 0.50 / 0.42 |
| B reverse hybrid, matched / mixed | 0.463 / 0.426 | 0.004 / 0.004 | 0.70 / 0.57 vs 0.66 / 0.47 |
| self-citation (Java), defaults / fitted | 0.554 / 0.542 | 0.029 / 0.029 | 0.83 / 0.65 and 0.77 / 0.66 |
| A2 codebook hybrid, topic-matched / topic-mixed | **1.000** / 0.262 | **0.434** / −0.016 | 1.00 / 1.00 vs 0.61 / 0.41 |

Reading: (i) MS 408's section signal is far above what exchangeable-folio noise gives *and* above what contiguous drift gives (shifted-label null max 0.611; best drifting generator, the Java self-citation text, 0.55).
(ii) It does not reduce to Currier A/B: inside each language MS 408 classifies sections at 0.94–0.98 whereas every generator without topic-linked content stays ≤ 0.83 / 0.66.
(iii) Feeding topic-structured plaintext through the Naibbe tokens (A1, pure cipher) leaves almost no section signal at folio level (0.33 vs 0.24 mixed; JS excess ≈ 0) because the cipher randomises word boundaries and homophones; only a
whole-word codebook preserves it, and then it **overshoots** (accuracy 1.00, JS excess 0.43 vs MS 0.16). (iv) So MS 408's section vocabulary is *consistent with* section-dependent content reaching the text through a word-level mapping at partial strength,
but it is equally what a generator whose parameters or seed change by section would give; the data neither demand nor exclude a topic-structured plaintext.

## Limitations

* The engine is simplified; differences from the Java parent mix 'rules' and 'plaintext'. Plaintexts are Latin/Italian controls; the topic assignment of works to sections is arbitrary (maximising contrast).
* 6 engine parameters vs 12 fitted metrics (A1, B); A2/C0 add ~1.4k grammar parameters, so their letter-level agreement is partly circular. The penalised comparison (AIC with k) is descriptive: with 12 data points any k ≳ 12 can fit them all.
* 3-fold interleaved-folio CV tests generalisation across folios within sections and hands, not across sections; held-out folds are ~11k tokens with wide jackknife SEs.
* Section signal: Currier language/scribe is confounded with section (a within-language test is included for herbal-vs-pharmaceutical in A and herbal/biological/recipes in B); bifolio/quire structure is ignored; generators that change parameters or seed text by section (a plaintext-free source of section vocabulary) were not tested.
* Parameters are weakly identified (see `fit_trace_*.csv`); a fitting hybrid is an existence result, not evidence about how MS 408 was made.

## Follow-up (h06): section-varying generators without plaintext, and the zodiac pages

Full write-up and tables: [hypotheses/h06_section_null_and_zodiac/README.md](../hypotheses/h06_section_null_and_zodiac/README.md).

* **Section signal without plaintext.** Copy-and-modify generators whose seed pool (S most frequent types per section), favoured units or engine parameters depend on the section, cross-fitted on training folios and tested on held-out folios with the step-2 statistics: pools of 10 / 50 types per section (66 / 306 section-specific parameters) give NB accuracy 0.676 / 0.724 (MS 408: 0.723, CI 0.676–0.766; drift-null max 0.611); full unit preferences (498) 0.684; richer variants overshoot (0.82–0.83). Matched random folio-block groups stay at 0.28–0.35 and Currier-language-only groups at 0.360, so the signal needs section-aligned vocabulary but not a plaintext. No no-plaintext variant reaches the JS magnitude (best 0.357 vs 0.406). Verdict: section-varying generation can explain the classification signal; the topic-driven plaintext hybrid is sufficient, not necessary.
* **Zodiac pages.** Generators fitted on non-zodiac text (A1 cipher + copy-modify, SV, parents, controls) reproduce 7–13 of 22 zodiac statistics and none reproduces the label o-initial share (0.673 vs 0.17–0.33), the near-absence of q (0.3–1.5 % vs 4–17 %) or the zodiac's distinctiveness; a zodiac group fitted on half the pages recovers q and part of the JS but not o-initial. Ring text is less page-local than ordinary folios (local − other-page hit rate 0.017 vs 0.119); a global zodiac pool fits no better than a page-local one on held-out pages. Adjacent-month pages are more alike, but exactly as much as folio-order drift (label bigram cosine ρ 0.68 vs 0.66); the circular component is not significant after Holm.
