# Research log — everything tried on MS 408, in order

This is the single running log of every stage in this repository: what was asked, what was done, what came out, and where it led. **Nothing here is a translation.** Detailed numbers are in [FINDINGS.md](FINDINGS.md) and in each linked report or hypothesis README. Dates and times are Europe/Warsaw, taken from `git log`.

Status key:
- **closed**: answered; nothing more is planned.
- **lead**: a result worth following up.
- **open**: unanswered or blocked.

## Dead ends (closed, negative)
- **The tone sheet:**
  - The "Codex Translation Sheet" is not a translation table (h01).
  - No tone or pitch map extends it to the whole script (h02, h03).
- **Zodiac cribs:** the circle-centre words are later Roman-script month names, and no label matches any sign or month name list (h05).
- **Drawing cribs:**
  - Word–drawing links are section and quire effects; none survives with quire held fixed (h09, h10, h13).
  - Pharmaceutical labels don't resemble their "same plant" herbal folio (h09, h17).
  - Same-genus or same-family folios don't share first words or vocabulary (h17).
  - Bax's `keerodal` / Apiaceae similarity fails out of sample (h18).
- **Section models:**
  - A topic-plaintext codebook doesn't predict an unseen section better than a setting switch or a global baseline (h07).
  - Section vocabulary is not above drift once quires are resampled (h08, h10).
- **Copy-modify:** the copy step is inert in per-hand copy-modify fits; the gain comes from the word grammar (h12).

## Open leads
- **Line structure (h13–h16):**
  - Line-start words are a 2B/3B habit, adding a d-/s- or gallows onset to common words.
  - `am`/`dam`/`dy` end lines in every hand.
  - Not yet modelled by any generator.
- **Hands (h11, h12, h14, h15):**
  - Hands look like one system with spelling habits (`-edy → -ol`) plus different vocabulary.
  - Word-level evidence for the mapping is weak (it is mostly shared stems).
- **Weak leads from h09:** root/jar words.
- **Section signal (h11):** survives on hand residuals but cannot be separated from quire with this data.
- **Not yet attempted:**
  - Likelihood-based comparison of language vs generator vs cipher models.
  - A pharma label ↔ grid layout from the scans, so h17 test A can be redone on individual labels.
  - The image-stage glyph check on higher-resolution scans.

## How to add an entry
1. **Where:** append at the bottom (newest last) and use the next `L` number. If the entry changes the summaries above, update them in the same PR.
2. **Fields:** date (Europe/Warsaw), ID + title + folder link, question, what was done, result + verdict (one or two lines), key commits, status (closed / lead / open), what it led to.
3. **Sources:** only report what the linked code or README shows. Put numbers in FINDINGS.md and link them; don't invent or round in a way that changes a verdict.
4. **Requirement:** every PR that adds or changes analysis must add or update an entry (see [CONTRIBUTING.md](CONTRIBUTING.md)).

---

## Entries

### L01 · 2026-10-11 15:33 · Setup: repo, source PDF, workflow
- **Folder:** [source/](source/), [docs/WORKFLOW.md](docs/WORKFLOW.md), [docs/PRIOR_WORK.md](docs/PRIOR_WORK.md), [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)
- **Question:** what is the source, and what should a decipherment workflow look like?
- **Done:**
  - Downloaded the Yale PDF (214 pp) and split it in two to stay under GitHub's 100 MB file limit (`scripts/join_pdf.sh` rejoins them).
  - Wrote a staged workflow (catalogue letters → word structure → word classes → …) and surveys of prior work and data sources.
- **Result:** infrastructure only.
- **Commits:** aeb98d1, 4196fbd
- **Status:** closed
- **Led to:** L02

### L02 · 2026-10-11 15:59 · Transcription data, IVTFF parser, glyph catalogue, descriptive statistics
- **Folder:** [src/msdecipher/](src/msdecipher/), [glyphs/REPORT.md](glyphs/REPORT.md), [reports/stats_report.md](reports/stats_report.md)
- **Question:** which letters are used, and what does the text look like statistically?
- **Done:**
  - Built a fetch script with a SHA256 manifest for voynich.nu transcriptions (ZL3b primary; IT2a, RF1b, GC2a). They are git-ignored because no licence is stated.
  - Wrote an IVTFF 2.0 parser, unit segmentation and the glyph catalogue.
  - Computed Zipf, Heaps, entropies, positional stats, Currier A/B and a Sukhotin test.
- **Result:** descriptive only.
  - 27 EVA symbols plus 85 rare codes.
  - Zipf s 0.985, h2 2.22, h3 1.95.
  - Currier A/B differ (this checks consistency with Currier's own classification).
- **Commits:** b40125e, 4582c0c, f31792d, 4eaffb9
- **Status:** closed
- **Led to:** L03, L04

### L03 · 2026-10-11 16:01–16:34 · Image stage (scans → folio index → glyph candidates)
- **Folder:** [docs/IMAGE_STAGE.md](docs/IMAGE_STAGE.md), [reports/image_stage/REPORT.md](reports/image_stage/REPORT.md), `data/page_index.csv`
- **Question:** do the scans support the transcriber's glyph classes?
- **Done:** built a PDF page → folio index, then binarisation, line/word/glyph segmentation, EVA alignment and clustering.
- **Result:** weak and inconclusive (28 pages, proxy metrics). kNN recovers the EVA unit 36% of the time vs 6% chance; no inventory size is supported.
- **Commits:** 0341dff, 07cb118, 57d20f5
- **Status:** open (needs higher-resolution scans)
- **Led to:** —

### L04 · 2026-10-11 16:13–16:49 · Controls: Latin/Italian/German, ciphers, generators, then Hebrew and Arabic
- **Folder:** [docs/CONTROLS.md](docs/CONTROLS.md), [reports/controls/](reports/controls/)
- **Question:** is MS 408 like natural language, simple ciphers or generated text?
- **Done:**
  - Collected public-domain control texts.
  - Applied 12 transformations (abjad, substitution, Vigenère, nomenclator, verbose, anagram…) and 5 generators, then ran a metric suite with verdict screening.
  - Added Hebrew (Sefaria) and Arabic (Tanzil, Muqaddimah) with abjad normalisation.
- **Result:** lexicon metrics don't discriminate. Letter-level entropy is far below every family except anagram and the slot-grammar generator.
- **Commits:** bae9274, d9beb7a, 128306e, 237959d, 037e8f8, d90fa4c
- **Status:** closed
- **Led to:** L05

### L05 · 2026-10-11 17:23 · Hardening: topical Latin controls, jackknife/bootstrap CIs, prediction-interval verdicts
- **Folder:** [docs/CONTROLS.md](docs/CONTROLS.md), [docs/STATS_NOTE.md](docs/STATS_NOTE.md)
- **Question:** do the verdicts survive uncertainty and topic-matched controls?
- **Done:**
  - Added herbal/medical Latin (Pliny, Celsus, Macer, Isidore), Sidrach, Ariosto and Faust.
  - Added size-matched windows, block-jackknife CIs, z and prediction-interval verdicts, and alphabet-size normalisation.
- **Result:** the letter-level outlier result holds (h2 z −6.8 vs natural plaintext).
- **Commits:** 3e47bac, 73de1ed
- **Status:** closed
- **Led to:** L06

### L06 · 2026-10-11 17:45 · Word structure and word classes (stages 6–7)
- **Folder:** [docs/WORD_STRUCTURE.md](docs/WORD_STRUCTURE.md), [reports/word_structure/REPORT.md](reports/word_structure/REPORT.md)
- **Question:** do words have internal slot structure, and are there behavioural word classes?
- **Done:** fitted a learned skip-HMM slot grammar, a prefix-core-suffix model, MDL and a within-word shuffle null; clustered frequent words with stability tests.
- **Result:** position matters unusually much (2.93 bits/type shuffle gap vs natural maximum 1.47), but independent slots aren't enough. Words are suffix-light (21% vs 67–73%).
- **Commits:** 69ec3f5, bec5bb7, 2e33eea
- **Status:** closed
- **Led to:** L07

### L07 · 2026-10-11 18:08–19:02 · Mechanisms: Naibbe, Timm–Schinner, Zattera, Stolfi
- **Folder:** [docs/MECHANISMS.md](docs/MECHANISMS.md), [reports/mechanisms/REPORT.md](reports/mechanisms/REPORT.md)
- **Question:** does any published generating mechanism reproduce the text?
- **Done:**
  - Naibbe cipher with the author's tables.
  - Timm & Schinner self-citation via the authors' Java.
  - Zattera slot alphabet, Stolfi PCFG and a slot-conditioned bigram, all run through the full metric suite.
- **Result:** no mechanism matches everything. Out of 35 metrics: fitted self-citation 23, Naibbe 11–14, Zattera 9, Stolfi 8.
- **Commits:** 44609e1, 24a180e, 992ef96, 990a683, 6d45e3a, 4320b19
- **Status:** closed
- **Led to:** L11

### L08 · 2026-10-11 18:28 · h01 "Codex Translation Sheet" (user-supplied tone/glyph image)
- **Folder:** [hypotheses/h01_tone_sheet/](hypotheses/h01_tone_sheet/)
- **Question:** is the sheet a valid glyph → tone/meaning table?
- **Done:** coverage, unit existence, tone-scale fit vs random, section permutation and predictive tests.
- **Result:** not a translation table. It covers 1% of word types, and its tones fit no better than random (p = 0.39).
- **Commits:** ddab805
- **Status:** closed
- **Led to:** L09

### L09 · 2026-10-11 19:09 · h02 full tone map for every unit
- **Folder:** [hypotheses/h02_full_tone_map/](hypotheses/h02_full_tone_map/)
- **Question:** can the sheet be extended to all letters, by frequency or other orderings?
- **Done:** 39 candidate Hz maps, tested against random-map and shuffle nulls and 13 controls.
- **Result:** hypothesis generation only; nothing is both beyond the nulls and non-circular.
- **Commits:** 247f42a
- **Status:** closed
- **Led to:** L10

### L10 · 2026-10-11 20:25 · h03 slot-grammar tone map
- **Folder:** [hypotheses/h03_slotgrammar_map/](hypotheses/h03_slotgrammar_map/)
- **Question:** does pitch tied to slot position (or slot = syllable) carry information?
- **Done:** slot-tied pitch maps, slot-pattern "chords", held-out gain vs letters and mechanisms.
- **Result:** rising melodies are tautological, slot patterns add nothing beyond letters, and the syllable reading is non-diagnostic.
- **Commits:** d60079d
- **Status:** closed
- **Led to:** —

### L11 · 2026-10-11 20:40–21:26 · Hybrid copy-and-modify model and plaintext-signal test
- **Folder:** [docs/HYBRID.md](docs/HYBRID.md), [reports/mechanisms/hybrid/](reports/mechanisms/hybrid/)
- **Question:** does a cipher-plus-copy hybrid fit, and does a plaintext topic help?
- **Done:** a copy-modify engine with Naibbe / codebook / plaintext-edit encoders, folio-fold fits, held-out suite, and a section-vocabulary test with a drift-aware null.
- **Result:** a 6-parameter hybrid fits 21.7/35 held-out metrics, but the plaintext is not what helps. The no-plaintext C0 reaches 25.3/35.
- **Commits:** 1e904b5, f53d473, b1a28cb
- **Status:** closed
- **Led to:** L13

### L12 · 2026-10-11 20:47 · h05 zodiac pages as cribs
- **Folder:** [hypotheses/h05_zodiac_cribs/](hypotheses/h05_zodiac_cribs/)
- **Question:** are the circle-centre and nymph labels the names of zodiac signs?
- **Done:** 12 pages / 10 signs; affix, length, isomorph and crib-drag tests against 19 name lists.
- **Result:** no cribs. The centre words are later Roman-script month names, and no label matches a name list beyond chance.
- **Commits:** af3cc08
- **Status:** closed
- **Led to:** L13

### L13 · 2026-10-11 22:47–22:56 · h06 section-varying no-plaintext generator; hybrid on the zodiac pages
- **Folder:** [hypotheses/h06_section_null_and_zodiac/](hypotheses/h06_section_null_and_zodiac/)
- **Question:** can a generator without plaintext produce the section signal, and do generators match the zodiac pages?
- **Done:** section-varying pools, units and parameters, plus a random-block null; generators fitted elsewhere were scored on the zodiac pages.
- **Result:**
  - Section-aligned parameters reproduce the section classification accuracy without plaintext (0.68–0.72), but not its JS magnitude.
  - No generator reproduces the zodiac pages.
- **Commits:** 37905ef, 03ade37
- **Status:** closed
- **Led to:** L14

### L14 · 2026-10-11 23:26 · FINDINGS.md master summary
- **Folder:** [FINDINGS.md](FINDINGS.md)
- **Question:** what is established so far?
- **Done:** wrote the summary, hypotheses table, caveats and next steps.
- **Result:** documentation.
- **Commits:** 5a9e9e7
- **Status:** closed
- **Led to:** L15, L16

### L15 · 2026-10-12 17:12 · h08 quire map and quire-level CIs
- **Folder:** [hypotheses/h08_quires/](hypotheses/h08_quires/)
- **Question:** do the results survive resampling by quire instead of 8-page blocks?
- **Done:** built `data/quires.csv`, quire/bifolium resampling and leak-free group folds.
- **Result:** the letter-level findings hold. The section signal weakens: NB 0.723 with quire CI 0.523–0.924 is no longer above drift.
- **Commits:** 79e12aa
- **Status:** closed
- **Led to:** L17, L18

### L16 · 2026-10-12 17:47 · h07 leave-one-section-out
- **Folder:** [hypotheses/h07_leave_one_section_out/](hypotheses/h07_leave_one_section_out/)
- **Question:** does a setting-switch generator or a topic-plaintext hybrid better predict an unseen section?
- **Done:** pre-registered falsification test; fitted on four sections and predicted the fifth.
- **Result:** weak and negative-leaning. Setting-switch beats the topic codebook, but neither beats a global baseline.
- **Commits:** 397a5cb
- **Status:** closed
- **Led to:** —

### L17 · 2026-10-12 17:48–17:55 · h09 image-context cribs from the drawings
- **Folder:** [hypotheses/h09_image_context_cribs/](hypotheses/h09_image_context_cribs/)
- **Question:** can drawings (plants, stars, jars, water, nymphs) tie words to meanings?
- **Done:**
  - Pre-registered visual tags for 224 folios.
  - Tested label–object sharing, same-plant pairs, label-in-text, enrichment with quire nulls, and transfer.
- **Result:** no robust word–meaning pair; enrichment is a section/quire effect. Root/jar words are a weak lead.
- **Commits:** 7edbf90, c807ba0, 11bda08
- **Status:** closed (root/jar words remain a weak lead)
- **Led to:** L18

### L18 · 2026-10-12 18:28–18:33 · h10 section vs quire and hand
- **Folder:** [hypotheses/h10_section_vs_quire_hand/](hypotheses/h10_section_vs_quire_hand/)
- **Question:** is the "section" effect really a quire or scribe effect?
- **Done:** within-stratum and reverse contrasts, variance decomposition and h09 rechecks (pre-registered).
- **Result:** no section effect passes both nulls after Holm; hand/language effects dominate.
- **Commits:** a4bc34e, 828ccf5, 40bbaa0
- **Status:** closed
- **Led to:** L19

### L19 · 2026-10-12 18:44–19:04 · h11 hand × language models
- **Folder:** [hypotheses/h11_hand_language_model/](hypotheses/h11_hand_language_model/)
- **Question:** how much do scribe and language explain, and what remains?
- **Done:** hierarchical models, residual section/image tests, hand features and a rewrite-rule orthography test.
- **Result:**
  - Hand × language is the largest factor.
  - A section signal survives on hand residuals but not once quire is also removed.
  - Rules close 22.7% of the 1A–2B gap (first rule `-edy → -ol`).
- **Commits:** 5bce8d2, 528412f, b7a6026
- **Status:** lead (spelling mapping)
- **Led to:** L20

### L20 · 2026-10-12 19:40–20:06 · h12 per-hand copy-modify generators
- **Folder:** [hypotheses/h12_per_hand_copy_modify/](hypotheses/h12_per_hand_copy_modify/)
- **Question:** is each hand one system plus a spelling mapping, and does copying matter?
- **Done:** C0 engine fitted per hand × language, with pooled, shuffled, cross-hand and rule-mapped baselines.
- **Result:**
  - Per-hand beats pooled in 14/15 folds.
  - The copy step is inert (p_copy ≈ 0.02–0.04).
  - The mapping closes 45–69% of the top-word gap.
- **Commits:** a1366f0, e7a5a05, 60de6ad
- **Status:** closed
- **Led to:** L21

### L21 · 2026-10-12 20:10–20:13 · h13 top-100 words in context and images
- **Folder:** [hypotheses/h13_top_word_context/](hypotheses/h13_top_word_context/)
- **Question:** what do position, neighbours and images say about the 100 most common words?
- **Done:** per-word cards (position, PPMI classes, spelling variants, image links) with quire×HL nulls.
- **Result:**
  - Real line-position preferences: 7 line-start words, 3 line-end words.
  - Neighbour classes track hand.
  - 0/868 image tests survive.
- **Commits:** c80e2f7, f2e3d97, 7b437bb
- **Status:** lead (line position)
- **Led to:** L22

### L22 · 2026-10-12 20:15–20:17 · h14 line-position controls
- **Folder:** [hypotheses/h14_line_position_controls/](hypotheses/h14_line_position_controls/)
- **Question:** are the line-start/end effects artefacts of line length or layout?
- **Done:** stratified, within-line and length-matched nulls; 2B → 1A Procrustes alignment.
- **Result:**
  - The effects are real.
  - Line-start words are mostly a 2B/3B habit; `am`/`dam`/`dy` end lines in every hand.
  - Rule partners are aligned closer than random (p = 0.0005).
- **Commits:** be999f9, 3c697fe, 596bf2f
- **Status:** lead
- **Led to:** L23

### L23 · 2026-10-12 20:30–20:32 · h15 line-start robustness and stem control
- **Folder:** [hypotheses/h15_line_initial_robustness_and_stem_control/](hypotheses/h15_line_initial_robustness_and_stem_control/)
- **Question:** is the 2B/3B line-start habit consistent across quires, and is the `-edy`/`-ol` pairing just shared stems?
- **Done:** per-quire/bifolium meta-analysis, leave-one-out, 1A power check, stem-controlled Procrustes.
- **Result:**
  - Line starts: ratio 3.28 [2.48, 4.35]; 7/8 quires; absent in 1A at full power.
  - The rule-pair advantage is mostly shared stems (p = 0.097).
- **Commits:** 0466079, 5616426, 6068136
- **Status:** lead (line structure); closed (word-level mapping)
- **Led to:** L24

### L24 · 2026-10-12 20:36–20:39 · h16 line-start onsets and an open line-edge search
- **Folder:** [hypotheses/h16_line_initial_prefix/](hypotheses/h16_line_initial_prefix/)
- **Question:** are 2B/3B line-start words ordinary words with a d-/s- added at the front, and does 1A have its own line-edge words?
- **Done:** onset and stripped-form tests; open search per hand × language.
- **Result:**
  - Yes: onset ratio 1.71 (z = 17.5); the stripped form is a common word in 69% vs 28% of cases.
  - 1A has its own small set (dchor, sor, sho).
- **Commits:** 310f5af, 243fb2e, 0dd63bf
- **Status:** lead (not yet modelled)
- **Led to:** L26

### L25 · 2026-10-12 20:39–20:43 · Public release: SEO README, licence, contributing guides, CI
- **Folder:** [README.md](README.md), [CONTRIBUTING.md](CONTRIBUTING.md), [.github/](.github/), [CITATION.cff](CITATION.cff)
- **Question:** make the repository public and usable by contributors.
- **Done:**
  - SEO README, MIT licence, contributing guide, code of conduct, issue/PR templates, citation file, social preview.
  - CI test workflow (with the images extra and poppler); Naibbe round-trip test skipped when the control corpus isn't fetched.
- **Result:** CI green.
- **Commits:** 7f0eff0, ed3669f, 9c23d8d
- **Status:** closed
- **Led to:** L28

### L26 · 2026-10-12 20:41–20:55 · h17 published plant IDs and pharmaceutical labels as cribs
- **Folder:** [hypotheses/h17_herbal_label_cribs/](hypotheses/h17_herbal_label_cribs/)
- **Question:** do labels and texts of plants that the literature identifies, or matches between herbal and pharma pages, share words?
- **Done:**
  - Built a table of 239 ID proposals for 107 folios from 8 source groups.
  - Tests: pharma ↔ herbal labels, same genus/family folios, Bax crib consistency; nulls held quire × hand × language fixed.
- **Result:**
  - Labels and same-plant folios: no link (p ≥ 0.16).
  - Bax cribs at family level: Holm 0.004, but the pass rests on one crib (`keerodal` ~ `ksheodal`).
- **Commits:** e499f8c, ae54722, 4830bba
- **Status:** closed (the lead was tested in L27)
- **Led to:** L27

### L27 · 2026-10-12 21:00–21:03 · h18 out-of-sample Apiaceae crib test
- **Folder:** [hypotheses/h18_apiaceae_crib/](hypotheses/h18_apiaceae_crib/)
- **Question:** does the `keerodal` shape recur on Apiaceae folios that weren't used to find it?
- **Done:** pre-registered non-Bax Apiaceae set (with a no-Vatne sensitivity set), a k…dal/k…dy shape, a quire×HL null and random-shape calibration.
- **Result:** fails. The target pages open with 0 such words (null 0.08–0.17); token share p = 0.23–0.26; all Holm p = 1. The pharma grid → label map isn't available.
- **Commits:** 0220892, ff46f11, 48ad021
- **Status:** closed
- **Led to:** —

### L28 · 2026-10-12 · This research log
- **Folder:** [RESEARCH_LOG.md](RESEARCH_LOG.md)
- **Question:** keep everyone on the same page.
- **Done:** chronological log of L01–L27; linked from README and CONTRIBUTING; added a PR checkbox.
- **Result:** documentation.
- **Commits:** (this commit)
- **Status:** closed
- **Led to:** future entries

### L29 · 2026-10-12 21:09–21:40 · h19 held-out likelihood comparison of mechanisms (issue #3, option 3)
- **Folder:** [hypotheses/h19_heldout_likelihood/](hypotheses/h19_heldout_likelihood/)
- **Question:** scored on held-out pages, does MS 408 behave like language, generated (copy-and-modify) text, or a Naibbe cipher?
- **Done:**
  - Per hand × language (1A, 2B, 3B) with bifolium and quire folds; hyperparameters fitted on inner splits.
  - Models: char LM, slot grammar, Kneser–Ney 1–3, copy-and-modify as a probabilistic model (EM copy rate and edit channel), Naibbe likelihood with Latin/Italian plaintext LMs, and a line-start onset feature.
  - Calibration: 4 plain controls, 2 Naibbe ciphertexts and a synthetic copy text.
- **Result:**
  - Context gain is 0.25 bits/word in MS vs 0.94 in the controls, and n-grams hurt. The best MS model is context-free.
  - Not Naibbe-like: escape weight 0.94–0.99 on MS vs ≤ 0.009 on real ciphertext.
  - ML copy rate 0.10–0.13 (CIs ±0.02), inside the controls' range of 0.07–0.17. The synthetic rate of 0.2 is recovered.
  - The onset feature saves 0.25–0.59 bits on line-initial tokens.
  - P1 passes; P2–P5 fail.
- **Commits:** 2726c9e, a71ad8b, 44b3838, (FINDINGS/README/log commit)
- **Status:** closed
- **Led to:** —

### L30 · 2026-10-13 08:32–09:20 · h20 generators and Italian encodings vs the MS likelihood fingerprint
- **Folder:** [hypotheses/h20_generators_vs_italian/](hypotheses/h20_generators_vs_italian/)
- **Question:** which condition reproduces MS 408's held-out fingerprint from h19 (no n-gram gain, cache gain of real-text size, a 5-word copy rate, char-level dominance)? Italian is the primary real-language reference.
- **Done:**
  - 9 Italian texts, with a new download script and manifest (texts git-ignored).
  - h12 C0 engine per hand; Timm–Schinner self-citation (authors' Java).
  - Italian through Naibbe, a syllabic cipher, vowel removal and suspension.
  - Added a position-conditioned char LM (PCLM); `rapidfuzz` became a project dependency.
- **Result:**
  - Only C0 (2B, 3B) reproduces all five statistics; self-citation reaches up to 4/5.
  - No Italian text or Italian encoding reproduces. Italian keeps an n-gram gain of +0.24 to +1.42 bits/word; Naibbe-Italian lacks local repetition.
  - P1–P4 and P6 pass; P5 fails on its threshold.
- **Commits:** 38ae92c, ba444aa, (FINDINGS/README/log commit)
- **Status:** closed
- **Led to:** —

### L31 · 2026-10-13 09:30–10:10 · h21 order-breaking Italian encodings and cross-hand C0
- **Folder:** [hypotheses/h21_italian_order_breaking_and_cross_hand/](hypotheses/h21_italian_order_breaking_and_cross_hand/)
- **Question:** can Italian that is encoded to break word order but keep local repetition reproduce the h20 fingerprint, and how contrived must it be? Does C0's match survive fitting on other hands?
- **Done:**
  - Within-line shuffle, nulls drawn from MS 2B tokens, recency homophones and Naibbe, applied to Boccaccio, Cucina, Sidrach and Cennini: 24 base cells.
  - An 18-setting grid on Boccaccio, with the top 2 settings transferred to the other sources.
  - C0 fitted per hand (seeds 20 and 21) and on pooled other hands, point-matched across hands.
- **Result:**
  - Shuffling removes the n-gram gain, but char dominance and bits/glyph stay non-MS. The best encoding, Naibbe plus 33 % nulls, reaches 3/5; the best grid setting reaches 1–2/5 on bifolium folds.
  - Cross-hand C0 stays inside the MS range but point-matches unseen hands unevenly.
  - PA1, PA2 and PB3 pass; PA3, PB1 and PB2 fail.
- **Commits:** 2408d3e, 5d2852a, (FINDINGS/README/log commit)
- **Status:** closed
- **Led to:** —

### L32 · 2026-10-13 10:12–10:35 · h22 Italian cipher plus a generic copy-and-modify layer
- **Folder:** [hypotheses/h22_italian_cipher_plus_copy/](hypotheses/h22_italian_cipher_plus_copy/)
- **Question:** is local copying the one ingredient missing from Italian encodings? How much plaintext signal survives it? Is hand 2B genuinely distinct?
- **Done:**
  - Copy layer (c × W grid, edits not fitted to MS) on Naibbe, Naibbe+nulls, syllabic+nulls and Naibbe+shuffle, with clean vs leaky nulls.
  - Top-2 transfer to Cucina, Sidrach and Cennini; plaintext recovery (signal share, oracle decoding, MI).
  - Cross-hand C0 with 5 seeds.
- **Result:**
  - Naibbe + 5 % copying (W = 20) reaches 4/5 on all four sources, at distance 5.4–7.9; it fails only D4, and nothing reaches 5/5 on bifolium folds.
  - The h21 null benefit was mostly the MS leak.
  - The plaintext signal largely survives.
  - Blind C0 fits never match 2B (but match 1A every time).
  - QA1–QA3, QA6 and QB1 pass; QA4 and QA5 fail.
- **Commits:** b37c88b, da1c19d, (FINDINGS/README/log commit)
- **Status:** closed
- **Led to:** —
