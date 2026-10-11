# Candidate generating mechanisms vs MS 408 (Stage 8)

**MS 408 is undeciphered. Nothing here decodes it.** This stage implements published *candidate generating mechanisms* and asks, metric by
metric, whether their output is statistically distinguishable from MS 408 under the measurement suite already built (Stages 3, 6, 7). A
mechanism that reproduces a metric only shows that the metric does not discriminate; a miss is evidence against *that implementation on that
metric*. Full numbers: `reports/mechanisms/REPORT.md` (auto-generated; CSVs and figures next to it). Run: `python -m msdecipher mechanisms-run`.

## What was built

| module | content |
|---|---|
| `mech_naibbe.py` | Naibbe cipher (Greshko 2025): the author's six tables (23 letters x unigram/prefix/suffix, `data/mechanisms/naibbe_tables.csv`), random unigram/bigram respacing (17/36 standard, 18/36 balanced), per-letter card draw from a shuffled 78- or 52-card deck (28/14/11/11/7/7 and 20/8/8/8/4/4), unambiguity rule for bigrams, and **decryption** (round trip tested) |
| `mech_selfcitation.py` | Timm & Schinner (2020) self-citation generator, **driven through the authors' own Java reference implementation** (compiled from their repo at `a6ede22`), with the documented parameter bounds, cached output texts (`data/mechanisms/selfcitation/`) and a sweep API |
| `mech_grammars.py` | Zattera 12-slot table; Stolfi (2000) crust-mantle-core PCFG with his counts (unambiguous, parse-based probability, verified against the exact inside algorithm); `SlotModel` (skip-HMM slots with optional hand-coded mask, order 0 or **order 1 = slot-conditioned bigram** with hidden slots and hierarchical smoothing); `compare_grammars` (held-out CV by folio, coverage, MDL) |
| `mechanisms_run.py`, `mechanisms_report.py` | every mechanism through `controls_metrics.metrics` + `word_structure_run.row_metrics`, MS 408 jackknife SEs, prediction-interval verdicts, scorecards, self-citation search, report, figures |

Tests: `tests/test_mech_naibbe.py`, `test_mech_selfcitation.py` (Java tests skip without a JDK; cached-text fallback is tested), `test_mech_grammars.py`, `test_mechanisms_run.py`.

## Method

* Each run is 35,000 tokens (MS 408: 34,977), collapsed-EVA units, 500-token chunks as blocks. Verdict `≈` = MS 408 inside the 95 % prediction
  interval of the mechanism's runs widened by MS 408's block-jackknife SE (`controls_ci.interval_verdict`); `↑`/`↓` = MS 408 above / below.
* 35 suite metrics in 10 groups: letter entropy (H1, h2, h3, h2/H1), within-word shuffle (h2 rise), positional skew, slot-grammar shuffle penalty
  and gain, suffix/prefix rate, Zipf/Heaps/hapax/top-10, word shape, adjacent repeats (identical, edit distance 1), cluster stability (bootstrap/half-split ARI,
  silhouette, class MI, NMI), and coverage by the Zattera table / Stolfi grammar.
* Seeds: Naibbe 5 seeds x 11 plaintexts (7 Latin incl. herbal/medical, 4 Italian) for the 78-card deck = 55 runs; 52-card deck 11; 50:50 respacing 6.
  Self-citation 5 seeds each for the authors' defaults and for the fitted parameters; grammar generators 5 samples each. 108 + 6 runs, 5 reference rows.

## Findings (numbers from `reports/mechanisms/`)

Scorecard (metrics reproduced `≈` out of 35):

| mechanism | ≈ | MS 408 above (↑) | MS 408 below (↓) |
|---|---|---|---|
| Naibbe, 78-card (55 runs) | 11 | 13 | 11 |
| Naibbe, 52-card | 12 | 12 | 11 |
| Naibbe, 50:50 respacing | 14 | 10 | 11 |
| Self-citation, authors' defaults | 15 | 14 | 6 |
| **Self-citation, fitted within documented bounds** | **23** | 7 | 5 |
| Learned slot grammar (in-sample, i.i.d. sampler) | 14 | 10 | 11 |
| **Learned slot-conditioned bigram (in-sample)** | **22** | 7 | 6 |
| Zattera slots (EM probs) | 9 | 13 | 13 |
| Zattera slots + conditioned bigram | 11 | 13 | 11 |
| Stolfi (refit / published probs) | 8 / 8 | 11 | 16 |

(Coverage-by-Zattera / by-Stolfi metrics are tautological for the generators that *are* those grammars.)

**1. Naibbe cipher.** Reproduces the *lexicon-shape* metrics: Zipf exponent 1.027 (MS 408 0.985), Heaps beta 0.728 (0.745), word entropy, h2/H1 (0.546 vs 0.568), affix
suffix-type share 0.254 (0.207) — and, notably, **cluster stability** (half-split ARI 0.207 vs MS 0.207; every i.i.d. grammar sampler gives ≈ 0.00-0.02), which none of the other
mechanisms except the plaintext-derived Naibbe reproduces at the point-estimate level (the verdict is weak, see caveat). It misses the within-word structure by a wide margin: the
slot-grammar shuffle penalty is **5.6 bits** vs MS 408's **2.9** (z ≈ -18: Naibbe words are *far more* positionally structured than MS 408 words, because every affix is built from the
author's slot-grammar glyph strings), within-word shuffle h2 rise 1.47 vs 1.35, positional skew share 0.86 vs 0.92, hapax share of types 0.38 vs 0.69 (type/token 0.158 vs 0.205: the
cipher produces too few rare types), adjacent edit-1 rate 0.012 vs 0.034, adjacent identical rate 0.002 vs 0.008 (no line/paragraph/copy structure). Results are insensitive to
plaintext language (Latin vs Italian differ by ≤ 0.05 bits in h2) and to the deck (52 vs 78 cards). Decryption round trip: exact (15,674 letters, 10,329 words). Conclusion: the
cipher does what Greshko claims at word level (frequency-rank shape) but, with this implementation and these metrics, it is not a match for MS 408's internal word structure or its local repetition.

**2. Self-citation.** With the authors' defaults at 35k tokens: type/token 0.130 vs 0.205, hapax share 0.52 vs 0.69, top-10 coverage too high, adjacent edit-1 rate 0.053 vs 0.034;
positional JSD too high (0.76 vs 0.66); suffix rate 0.42 vs 0.21. A size-matched check at the authors' own text size (10,900 tokens) shows the same gap (TTR 0.185 vs MS 408 windows 0.280),
so it is not a length artefact. **Parameter search** (60 random vectors + 72 local refinements, all inside the documented ranges; fit on 9 lexicon metrics only): fit distance (RMS z) 8.08 at
defaults -> **4.33** at best; 17/60 random vectors beat the defaults; most sensitive parameters: `suggestions.dyType_min_percentage`, `suggestions.iType_min_percentage`, `combine_split`, `add_remove`
(`morph.replace.probability` and `suggestions.olType_min_percentage` had no effect on the fit). The fitted generator, evaluated on **fresh seeds on the whole suite**, reproduces 23/35: all three
letter entropies (h2 2.239 vs 2.217), the within-word shuffle effect (1.257 vs 1.348), slot shuffle penalty (2.49 vs 2.88), adjacent identical (0.008 vs 0.008) and edit-1 rates (0.038 vs 0.034), Heaps beta. Still missed:
**hapax share (0.515 vs 0.687, z ≈ 16)**, type/token (0.139 vs 0.205), suffix rate (0.52 vs 0.21), word-length SD, positional JSD (0.86 vs 0.66). Caveat: the generator embeds MS-408-derived design
(glyph classes, curve-line follow rule, f103v seed line, `daiin/ol/chedy` suggestion types), so matching local statistics is not independent evidence.

**3. Hand-coded grammars vs learned (held-out, MS 408, bits per word; `grammar_comparison_ms408.csv`).**

| model | bits/token | bits/type | bits/new type | token coverage | type coverage | MDL/type (params) |
|---|---|---|---|---|---|---|
| letter-pair baseline | 12.37 | 17.15 | 20.21 | 0.995 | 0.984 | 18.98 (644) |
| learned slot grammar K=12 | 15.50 | 19.72 | 22.77 | 0.990 | 0.983 | 21.24 (178) |
| **learned slot-conditioned bigram** | **11.74** | **16.12** | **19.04** | 0.990 | 0.983 | 18.45 (1617) |
| Zattera slots (EM probs) | 13.84 | 17.46 | 20.50 | 0.819 | 0.538 | 18.85 (46) |
| Zattera slots + conditioned bigram | 13.41 | 17.25 | 20.40 | 0.819 | 0.538 | 18.96 (359) |
| Stolfi (probs refit on train folds) | 13.61 | 17.61 | 20.65 | 0.943 | 0.824 | 19.03 (65) |
| Stolfi (published probs, not held out) | 13.61 | 17.69 | 20.98 | 0.943 | 0.824 | 19.18 (0) |

Hand-coded grammars have an escape to the letter-pair model for uncovered words, so misses are priced in. Findings: (i) no grammar written down in the literature beats the letter-pair bigram on
held-out bits per token or per type; Zattera's table (46 parameters) has a *better* MDL per type (18.85) than the letter-pair model (18.98, 644 parameters) and the learned slot grammar (21.24), but loses on held-out bits and covers only 82 % of tokens / 54 % of types in this transcription
(paper: 86.6 % tokens on its own alphabet), Stolfi covers 94.3 % of tokens (his note: 96.3 % in 1998 data) at the price of a much more permissive grammar; (ii) the learned 12-slot grammar *with the
previous unit as extra context* is the best model on every held-out measure (-0.63 bits/token, -1.03 bits/type against the letter-pair), i.e. the slot positions carry information beyond adjacent-letter
dependence, but the plain slot grammar loses to letter pairs on bits (it wins on parameters: 178 vs 644);  (iii) re-fitting Stolfi's rule probabilities on the training folios changes held-out bits per type by only 0.09 (17.69 -> 17.61), i.e. his published probabilities were not badly over-fitted to the 1998 text.

**4. Grammars as generators (i.i.d. samples, fitted in-sample to MS 408).** The slot-conditioned bigram sampler reproduces 22/35 metrics (h2 2.287 vs 2.217, shuffle gap 1.308 vs 1.348, slot shuffle penalty
2.91 vs 2.88, positional skew 0.923 vs 0.923) but, having no memory between words, misses adjacent repeats (identical 0.002 vs 0.008; edit-1 0.015 vs 0.034) and word-length SD. The plain slot grammar,
Zattera and Stolfi samplers over-generate types (TTR 0.36-0.52 vs 0.205), overshoot h2 and undershoot the within-word shuffle effect. So a *within-word* conditional model explains the letter-level
statistics; what it cannot supply is the *between-word* (copy/repetition) layer, which is exactly what the self-citation generator supplies and the cipher lacks.

**5. Combined reading (descriptive, not a decipherment).** No single mechanism reproduces everything. Letter-level structure is matched by a within-word conditional grammar or by the fitted self-citation
generator; the cipher matches the rank-frequency shape and cluster stability but over-structures words; self-citation matches repetition but under-produces rare types and over-produces suffixes. A
hybrid (cipher-like plaintext dependence + self-citation-like local copying) is not tested here.

## Caveats / what could not be done faithfully

* **Naibbe**: the Cryptologia paper sits behind a bot wall and could not be fetched; details come from the author's MIT-licensed code/tables (commit `f2675ec`, citation clause honoured) and paper excerpts seen in
  search results. Not used: *Voynichesque*, the Excel implementations, any nulls/line/paragraph machinery (the paper lists none). One fresh deck per ~60 plaintext letters (author: per plaintext line).
* **Self-citation**: not re-implemented (the behaviour is defined by ~5,000 lines of rules); the authors' Java was compiled (JDK 17, log4j 1.2.17) and driven via `conf.properties`. The paper itself was only seen as snippets. The
  circular follow rules (`voynich`, `statistic`, `percent`) were excluded from the sweep. Without a JDK the cached texts are used (`MSDECIPHER_JAVA_HOME`, `mech_selfcitation.build()` to rebuild).
* **Zattera**: the 12-slot table is taken from Zandbergen's reproduction of the paper; the paper's probabilities and transliteration alphabet were unavailable, so only the structure is hand-coded.
* **Stolfi**: only the normal-word PCFG (abnormal-word lists excluded); published probabilities were fitted on the whole 1998 text (not held out).
* Cluster-stability verdicts have little power (MS 408 jackknife SE 0.12-0.16 on ARI); read the point estimates. Many metrics are correlated, no metric is decisive, in-sample generators are an upper bound.
* The self-citation fit selects among ~130 vectors on 9 metrics with 2 seeds; the evaluation uses fresh seeds, but the fit distance is itself a model choice (2 % relative floor on the metric scale).
