# h06 — (1) can a section-varying generator *without plaintext* produce MS 408's section signal? (2) the zodiac pages against fitted generators

Everything is reproducible: `python run_h06_section.py` (~11 min) → `python make_section_tables.py`; `python run_h06_zodiac.py` (~3 min) → `python make_zodiac_tables.py`; `pytest test_h06.py` (9 tests, ~10 s).
Library: `h06_lib.py` (section-varying generator SV, fitting), `h06_zodiac.py` (zodiac data from h05's CSVs, statistics, copy-scope fits, locality and calendar tests). `hypotheses/h05_zodiac_cribs/` is only read (`zodiac_loci.csv`, `label_tokens.csv`).
Nothing here decodes MS 408; generators are descriptive models, and a generator that fits is an existence result.

## Part 1 — section-varying NO-PLAINTEXT generators

**Generator (SV)**: the copy-and-modify engine of the hybrid stage plus three section-dependent components, each switchable, *no plaintext anywhere*. Innovations come from one global slot-bigram grammar fitted on the training folios (shared by every variant, 1 608 parameters; the C0 control of step 1).
* **E** engine parameters per group (p_copy, window, p_prev, p_exact, p_suffix, p_prefix [+ p_pool]); fitted per group by random + local search on lexicon + letter metrics of the group's training text (6–7 parameters per group).
* **U** favoured units per group: innovations are importance-resampled from a 60 000-word grammar sample with weight ∏ r_g[u] (r_g = smoothed group/global unit-frequency ratio; estimated, not searched; 25–26 units → ~25 parameters per group; "U3/U8" keep only the 3/8 most deviant units).
* **P** vocabulary seed pool per group: the S most frequent types of the group's training text; with probability p_pool (fitted) an innovation is drawn from the pool. Each pooled word counts as one parameter (memorisation is the cost being measured).

Groups: 6 sections (herbal, recipes, biological, pharmaceutical, cosmo-astro, other); Currier language only (A/B/other); section × language (with fall-back to section); **random folio blocks** (blocks of 8 consecutive folios assigned at random to 5 groups: a null with the same machinery and parameter budget but no link to the true sections).
**Protocol — cross-fitted step-2 test**: 3 interleaved folio folds; for each fold every generator is fitted on the other two folds and generates text for the *held-out* folios (same layout, tokens per folio, section/language labels as the real folios). The three held-out texts are assembled in manuscript order (201 folios) and put through exactly the step-2 statistics (NB balanced accuracy over the 5 section classes with 5-fold CV by folio, JS between sections, within-language NB, drift-aware shifted-label null). 8 fresh seeds per variant; 95 % t-intervals across seeds; verdicts = prediction-interval verdicts of `controls_ci.interval_verdict` using MS 408's folio-bootstrap SE (0.024 for accuracies, 0.017 for JS; the within-language accuracies reuse the overall SE).

MS 408 on the same statistics: NB accuracy **0.723** (CI 0.676–0.766), JS **0.406** bits (excess over the label-permutation null 0.160), LR 0.662, within-A 0.944, within-B 0.976; drift-null (shifted labels) max 0.611.

| variant (no plaintext unless stated) | section-specific params | NB accuracy [95 % CI] | JS (bits) | JS excess | within-A / B | reproduced of 6 |
|---|---|---|---|---|---|---|
| C0g global, no section dependence | 0 | 0.198 [0.157, 0.239] | 0.279 | 0.003 | 0.47 / 0.35 | 0 |
| E per-section engine params | 36 | 0.192 [0.176, 0.208] | 0.275 | 0.003 | 0.49 / 0.35 | 0 |
| U3 / U8 favoured units (3 / 8 units per section) | 18 / 48 | 0.235 / 0.203 | 0.279 / 0.277 | 0.004 / 0.002 | 0.48 / 0.42, 0.49 / 0.35 | 0 / 0 |
| U favoured units, all units | 498 | 0.684 [0.665, 0.704] | 0.332 | 0.050 | 0.87 / 0.89 | 3 |
| **P10** pool of 10 types per section | **66** | **0.676 [0.654, 0.697]** | 0.304 | 0.055 | 0.77 / 0.88 | 1 |
| **P50** pool of 50 types | 306 | **0.724 [0.705, 0.744]** | 0.294 | 0.069 | 0.89 / 0.87 | 3 |
| P200 pool of 200 types | 1 206 | 0.768 [0.741, 0.796] | 0.299 | 0.089 | 0.93 / 0.90 | 4 |
| EUP10 engine+units+pool 10 | 600 | 0.782 [0.772, 0.793] | 0.350 | 0.090 | 0.96 / 0.95 | 4 |
| EUP25 / EUP50 / EUP100 / EUP200 | 690 / 840 / 1 140 / 1 740 | 0.834 / 0.828 / 0.820 / 0.831 (overshoot, MS below the interval) | 0.357 / 0.345 / 0.335 / 0.335 | 0.120 / 0.115 / 0.110 / 0.114 | 1.00 / 0.99 | 3–4 |
| **by Currier language only** (EUP50) | 420 | 0.360 [0.344, 0.376] | 0.274 | 0.042 | 0.49 / 0.38 | 0 |
| by section × language (EUP50) | 1 913 | 0.821 [0.801, 0.842] | 0.344 | 0.114 | 1.00 / 0.95 | 3 |
| **random folio blocks (null)** EUP50 / EUP200 | 700 / 1 450 | 0.339 [0.316, 0.361] / 0.354 [0.331, 0.377] | 0.245 / 0.232 | 0.013 / 0.011 | 0.50 / 0.48 | 0 |
| random blocks U (all units) / P200 | 415 / 1 005 | 0.276 / 0.310 | 0.285 / 0.226 | 0.007 / 0.011 | 0.51 / 0.37, 0.50 / 0.47 | 0 |
| *plaintext-driven (step 2)*: A1 Naibbe+copy, topic-matched | 6 | 0.328 | 0.341 | 0.001 | 0.51 / 0.53 | 0 |
| *A2 whole-word codebook, topic-matched* | 6 + 1 608 grammar (codebook table random, not fitted) | 1.000 | 0.904 | 0.434 | 1.00 / 1.00 | 1 (overshoots) |
| *A2 codebook, topic-mixed* | same | 0.262 | 0.500 | −0.016 | 0.61 / 0.41 | 0 |
| *self-citation (Java), fitted* | 15 | 0.542 | 0.275 | 0.029 | 0.77 / 0.66 | 0 |

(`results/section_summary_vs_ms408.csv` has every variant × metric with CI, z and verdict; `section_param_sweep.csv`, `section_alignment_vs_random_blocks.csv`, `section_variant_parameter_counts.csv`, `figures/fig1_section_signal_vs_parameters.png`.)

**Findings.**
1. **Section-varying generation without plaintext reaches MS 408's classification accuracy.** A seed pool of just 10 word types per section (66 parameters incl. pool rates) gives 0.676 (≈ MS 408's 0.723, z = 1.3); 50 types give 0.724 (z = 0.0); full per-section unit preferences (498 parameters, no pool) give 0.684; the richer variants overshoot (0.78–0.83). All exceed the drift-null maximum of MS 408 (0.611) in every seed. Within-language accuracies come within range (0.87–0.93 vs 0.94/0.98) or overshoot (0.99+).
2. **The signal needs section-*aligned* parameters, not merely any parameters.** The same recipes with *random* folio-block groups with the same or larger budget stay at 0.28–0.35 (aligned − random = +0.41…+0.49 NB accuracy, Welch t = 34–44, all four paired recipes), and **Currier language alone** gives 0.360 [0.344, 0.376] (within-A 0.49, within-B 0.38) — the section signal is not a Currier A/B effect, in line with step 2's within-language result. Engine parameters alone (36 params) and favoured units restricted to 3 or 8 units add nothing (0.19–0.24 ≈ C0g 0.20): the information is the vocabulary/units themselves.
3. **Cost.** Accuracy per parameter is best for small pools (P10: 66 parameters → 0.68); 10 pooled words per section is a very small memorised vocabulary, but it *is* section-specific memorised vocabulary. By the descriptive AIC-like criterion (χ² of the 6 section metrics + 2·k, k = all parameters fitted to MS 408 incl. the shared 1 608-parameter grammar and 6 engine parameters) the best section-varying variant is P10 (3 457), vs 3 819 for the no-section C0g; low-parameter parents win the raw AIC (A1 495, Naibbe 462, self-citation 300) only because they fit no grammar *and* they do not reproduce the section signal (χ² 170–480 on 6 metrics vs 33–97 for section-varying SV). The criterion is a ranking aid, not a likelihood.
4. **What no section-varying no-plaintext variant reaches: the JS magnitude.** MS 408's between-section JS is 0.406 bits (excess 0.160); the best SV variants give 0.35–0.357 (excess 0.12, matched at EUP25 only), P-only variants 0.29–0.30. The topic-matched codebook (A2) overshoots (0.904). So MS 408's section difference is carried by a heavier tail of section-specific word types than a 10–200-word seed pool plus tilted grammar produces; with accuracy the generators match, with JS they fall short in every setting tried.
5. **Verdict.** *Section-varying generation without any plaintext explains the section-classification signal* (NB accuracy 0.68–0.83 vs 0.723, drift-null max 0.611) *at a cost of ≈66–500 section-specific parameters; it does not need a plaintext or topic-driven content.* It does require **section-aligned** vocabulary preferences (random-block and language-only nulls fail), and none of the no-plaintext variants reproduces the JS magnitude (≤ 0.357 vs 0.406). A topic-driven plaintext is therefore sufficient (A2) but not necessary; the data cannot tell a topic-structured plaintext from a scribe/process whose vocabulary seed changes by section. The earlier statement "consistent with section-dependent content, but equally what a generator whose parameters/seed change by section would give" is now an *explicit demonstration*, with its price tag.

## Part 2 — the zodiac pages (f70v2–f73v: 934 readable ring tokens, 336 readable label tokens, 12 pages)

Ring text: loci type Cc; labels: Lz (h05's `label_tokens.csv`, readable tokens only, a–z). Generators are **fitted on the non-zodiac folios only** (global grammar, global engine, per-section EUP50 models, a *label-mode* group fitted on 808 non-zodiac label tokens, the hybrid A1/A2 parameters from the all-MS fit, Java self-citation fitted, Naibbe pure, i.i.d. cosmo-astro words) and laid out on the zodiac pages (ring tokens then labels per page, page by page). 10 seeds each; statistics = 22 zodiac-specific numbers; verdicts with the **page-jackknife SE** of the real value (12 pages).

Zodiac facts (real, ± page-jackknife SE): word-JS from the rest of MS 408 0.578 ± 0.012 bits (page-sized windows of running text: 0.344 ± 0.014), unit-JS 0.033 ± 0.003 (windows 0.004); 28.3 % of zodiac tokens are types absent from the non-zodiac text; **label o-initial share 0.673 ± 0.032** (ring text 0.407, non-zodiac labels 0.481, running text 0.205); **q in 0.3 % of labels and 1.5 % of ring tokens** (running text 15.3 %); label hapax share of types 0.849; 91.6 % of label words occur once on their page; label length 5.41 ± 0.12 units (SD 1.64); ring within-page repeated share 0.230, labels 0.084; page-to-page type Jaccard 0.088 (ring) / 0.020 (labels).

| generator (fitted on non-zodiac text only) | reproduced of 22 | above / below | RMS z (clipped 20) |
|---|---|---|---|
| SV + label mode (labels group from non-zodiac labels) | 13 | 6 / 3 | 4.35 |
| **A1 cipher + copy-modify** (Isidore plaintext) | 12 | 6 / 4 | 4.42 |
| SV per-section EUP50 (group cosmo-astro) | 11 | 8 / 3 | 4.76 |
| A2 codebook + copy-modify | 10 | 5 / 7 | 5.45 |
| Naibbe cipher (no copying) | 10 | 7 / 5 | 4.88 |
| C0g no plaintext, global | 9 | 10 / 3 | 4.98 |
| i.i.d. non-zodiac cosmo-astro words | 8 | 10 / 4 | 6.75 |
| self-citation (Java, fitted) | 7 | 9 / 6 | 4.72 |

(`results/zodiac_generator_table.csv`: every statistic × generator; `figures/fig2_zodiac_stats_vs_generators.png`.) The ranking among the top five is within what 12 pages can resolve (counts move by ±2 with seeds and SE choices); **no generator reproduces the zodiac's specific character**:
* **Fails for every generator**: label o-initial share (generators 0.17–0.33 vs 0.673), q absence (generators 3.7–17 % of labels/ring tokens contain q vs 0.3 % / 1.5 %; only the label-mode group, learned from non-zodiac labels, gets labels to 3.7 %), ring/label o-initial and mean label length (all but A2 are 4.1–4.8 vs 5.41). The zodiac text is more distinct from the rest of MS 408 (word JS 0.578) than any non-zodiac-fitted *no-plaintext* generator (0.455–0.507).
* **Reproduced by most** (generic, so uninformative): label hapax share (0.82–0.84 vs 0.849), label words occurring once per page, label length SD, page overlap of unit bigrams, ring adjacent edit-1 rate, ring repetition (A1, label-mode SV, Naibbe).
* **Zodiac as one more section** (leave-pages-out, odd/even pages): SV groups fitted on 6 zodiac pages and tested on the other 6 reproduce 14.5 (pooled group, 258 zodiac parameters) / 15.0 (separate ring and label groups, 416 parameters) of 22 vs 12.5 (C0g) and 11.5 (SV from non-zodiac) for the non-zodiac-fitted ones, RMS z 2.3–2.5 vs 3.7–3.9 (`zodiac_cv_summary.csv`): that fixes most of q absence (generated q share 1.4–4 % vs real 0.3–2.3 %; inside the prediction interval in 6 of the 8 half × group × ring/label comparisons) and part of word JS, but o-initial stays far off (0.33–0.47 vs 0.67) because the tilt is position-agnostic: label-initial `o-` is positional structure the SV generator cannot express. Parameters ≈ half the number of tokens fitted: memorisation caveat as in part 1.

**Copy-and-modify scope: zodiac-local pool vs global pool.** Real-data test (`zodiac_copy_locality.csv`): hit rate = share of tokens with an identical/edit-1 token among the preceding ≤ W tokens of the *same page* vs a same-size random sample from the other pages vs from non-zodiac text.
* Ring text: 0.337 local vs 0.319 other pages vs 0.254 non-zodiac (W = 30; difference 0.017 ± 0.016 jackknife; permutation p = 0.050; W = 10: 0.188 vs 0.168, p = 0.020). Ordinary MS folios (12 random folios, first 90 tokens, same procedure): 0.434 vs 0.314, difference 0.119 ± 0.011. **The ring text is much *less* page-local than ordinary running text**: the page-local pool is barely better than other pages' text.
* Labels in locus order: local 0.259 vs other pages 0.146 (W = 30; difference 0.115 ± 0.032, p = 0.003; W = 10: 0.188 vs 0.098, 0.093 ± 0.032, p = 0.003), i.e. as local as ordinary text — consistent with the shared `o-`/`ot-` prefixes by page found in h05 (it is a fact about similar-looking labels on one page, not a demonstration of copying).
* Model fits (`zodiac_copy_scope_fits.csv`, `zodiac_copy_scope_summary.csv`, fig. 4): the 6 engine parameters re-fitted to the ring text for each copy scope, 4 independent searches, 2-fold held-out pages (RMS z over 8 ring statistics, lower is better): page-local 1.92 ± 0.13, recent window 1.92 ± 0.19, **global zodiac pool 1.74 ± 0.20** (in-sample 0.97 ± 0.17 with p_copy ≈ 0.90 — copying from anywhere earlier in the zodiac text), global + non-zodiac pool 1.65 ± 0.28. The in-sample advantage of the global zodiac pool (0.97 vs 1.7) mostly vanishes on held-out pages (differences ≤ 0.27 ≈ 1 SD of search noise). **No support for "copy within the page/ring from a zodiac-local pool"; if anything, copying from the whole zodiac text fits better, and ring text is less locally copied than ordinary folios.**

**Calendar structure.** Pages in month order (Mar, Apr, Apr, May, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec — month names as read in h05; Aquarius/Capricorn absent); statistic = Spearman(similarity, −circular month distance) over the 66 page pairs; null: the 10 month values permuted among the sign groups (the two Aries pages and the two Taurus pages stay together), 20 000 permutations; also the folio-order drift correlation (random page orders), and the partial correlation with circular month distance given folio-order distance (the only part that separates calendar from book order; essentially the wrap-around Dec↔Mar). Holm over the 15 p-values.

| similarity | ρ(circular) [p; Holm] | ρ(folio-order drift) [p] | partial circular | given folio order [p; Holm] | adjacent − distant [p; Holm] |
|---|---|---|---|---|---|
| ring, type Jaccard | 0.259 [0.009; 0.12] | 0.264 [0.023] | 0.106 [0.11; 0.46] | 0.017 [0.015; 0.18] |
| labels, type Jaccard | 0.198 [0.055; 0.27] | 0.193 [0.071] | 0.022 [0.40; 0.80] | 0.013 [0.024; 0.20] |
| ring, unit-bigram cosine | 0.334 [0.022; 0.20] | 0.294 [0.019] | 0.141 [0.15; 0.46] | 0.030 [0.037; 0.22] |
| **labels, unit-bigram cosine** | **0.677 [0.0003; 0.004]** | 0.657 [0.0006] | 0.301 [0.016; 0.18] | **0.151 [0.0007; 0.010]** |
| ring + labels, unit-bigram cosine | 0.341 [0.024; 0.20] | 0.375 [0.006] | 0.026 [0.46; 0.80] | 0.028 [0.016; 0.18] |

Adjacent-month pages do share more vocabulary than distant ones, and for label unit-bigrams strongly and surviving Holm (ρ = 0.68). But this is **the same ordering as the book's page order** (folio-order drift ρ = 0.66, p = 0.0006; the pages are bound in month order), i.e. the drift h05 found (`ot-` share falling along the section, Currier-A/B-like change) — the calendar test cannot separate "adjacent months" from "adjacent pages". The only component specific to the calendar (partial given folio order, essentially a Dec→Mar wrap) is 0.30 for label bigrams, p = 0.016 uncorrected, **0.18 after Holm: not established**; the ring text and label type-overlap show nothing beyond drift. Same-sign pages (Aries ×2, Taurus ×2) are not more alike than neighbours (h05). Verdict: calendar structure is not supported beyond page-order drift.

## Limitations
* Section-varying generators are fitted on the same manuscript they are tested against (cross-fitted by interleaved folio folds, so neighbouring folios of the same section sit in training); a per-section pool memorises vocabulary by construction — the parameter counts are the honest price, and "reproduces the signal" is an existence result. They do not reproduce JS magnitude.
* The random-block null uses one random assignment (blocks of 8 folios, 5 groups); more assignments would tighten the null band.
* MS 408's within-language accuracies reuse the overall SE; JS excess reuses the JS SE.
* Zodiac: 12 pages / 934 + 336 tokens: wide SEs (page-jackknife); verdict counts move by ±2 with seeds; the "zodiac fitted on half the pages" models fit 258–416 parameters to ~600 tokens. Labels share the ring-text generator unless label-mode is used; label order = locus order (not a verified reading order). The OOV reference (a window null of 0) is trivial; compare the generators' 0.21–0.35 instead.
* The month order is read from Roman words in the centres (several readings are disputed in h05); permutation nulls respect the missing months only through circular distance with gaps.
