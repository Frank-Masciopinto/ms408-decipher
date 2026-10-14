# Prior work on Beinecke MS 408 (Voynich manuscript) — survey

Surveyed 11 Oct 2026 (Europe/Warsaw) from web sources. Links were fetched or confirmed reachable during the survey unless marked *(not re-verified)*. This is a working bibliography for a **research framework**, not a claim of translation.

## 0. Bottom line

- **The manuscript is undeciphered.** Yale: "Cryptographic approaches have failed to decipher the text, if it is indeed encoded" — https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript. Bowern & Lindemann (2021): "There is at present no consensus on the language underlying the manuscript" [BL21].
- **No claimed solution is accepted.** The 2019 "proto-Romance" claim was criticised by linguists and the university withdrew its press promotion [Ke19][Ch19]. Search results for 2025–26 also show new claims (some self-withdrawn after out-of-sample failure); these were *not vetted* here and are not endorsed.
- **What *is* known** (consensus-ish): 15th-century material (parchment, ink, pigments); non-random text with language-like word-frequency behaviour but very peculiar word internal structure; at least two statistically distinct "dialects" (Currier A/B) and five scribal hands (Fagin Davis); section-dependent vocabulary.
- **What is disputed:** natural language vs. cipher vs. meaningless/"gibberish" generation vs. constructed language; what the units (glyph/letter/word/space) are; what A/B represent.

---

## 1. Transcription alphabets and corpora

| Key | Reference | Link | Notes |
|---|---|---|---|
| [Za-transcr] | R. Zandbergen, *Voynich MS – Text Analysis – Transliteration of the Text* (updated 2025–26) | https://www.voynich.nu/transcr.html | History of FSG, Currier/D'Imperio, Takahashi, EVA, v101, ZL, Reference transliteration; stats table; stresses that transcription = subjective decisions on glyph identity and spaces. |
| [Za-sp] | R. Zandbergen, *Special Topics: Transliteration of the text* | https://www.voynich.nu/extra/sp_transcr.html | IVTFF format, ivtt/bitrans tools, STA/"aaa" alphabets, assisted-OCR programme, list of badly legible text. |
| [IVTFF] | IVTFF format definition (v2.0.x) | https://www.voynich.nu/software/ivtt/IVTFF_format.pdf | Loci types P/L/C/R; page variables ($Q quire, $P, $I illustration, $L Currier language, $H hand). |
| [Re95] | J. Reeds (1995), "William F. Friedman's transcription of the Voynich manuscript", *Cryptologia* 19(1) *(not re-verified)* | — | Origin of the FSG machine-readable transcription. |
| [LSI] | Landini–Stolfi Interlinear file (EVA) | https://ic.unicamp.br/~stolfi/EXPORT/voynich/ | Historic de-facto standard; superseded by IVTFF files for new work. |
| EVA | Landini & Zandbergen — Extensible Voynich Alphabet, designed to be reversible and "almost pronounceable" — *a transliteration, not a transcription (no claim about sounds)* | see [Za-transcr] | Capitalisation rule for ligatures; Extended EVA via high-ASCII codes. |
| v101 | G. Claston's Voynich 101 alphabet and transcription | see [Za-transcr] | Keeps stroke combinations that appear to be single signs; widely regarded as accurate. |
| [DI78] | M. D'Imperio (1978), *The Voynich Manuscript: An Elegant Enigma*, NSA/CSS *(not re-verified; PDF widely mirrored)* | — | Standard monograph; surveys history, script, comparisons (Latin abbreviations, alchemical symbols, 14th–15th c. ciphers). |
| [Cu76] | P. Currier (1976), "Some important new statistical findings" in *Papers of the 1976 Voynich Manuscript Seminar* (ed. D'Imperio) | HTML conversion linked from https://www.voynich.nu/a1_intro.html | Discovery of Languages A/B, Hands 1/2, word/character-level criteria (e.g. final `-y`, `-edy`, `qo-` strongly B). |
| [Be76] | W. R. Bennett (1976), *Scientific and Engineering Problem-Solving with the Computer* | see [Za-intro] | First entropy estimates showing anomalous character-level values. |
| Voynichese.com | Browser with per-token boxes over Beinecke images (Takahashi–Stolfi EVA) | https://www.voynichese.com | Useful for token coordinates (coarse; construction protocol not published per [RT26-preprint]). |

## 2. Surveys and statistical/linguistic analyses

| Key | Reference | Link | Findings (as reported) and caveats |
|---|---|---|---|
| [BL21] | C. L. Bowern & L. Lindemann (2021), "The Linguistics of the Voynich Manuscript", *Annual Review of Linguistics* 7:285–308. doi:10.1146/annurev-linguistics-011619-030613 | https://www.annualreviews.org/content/journals/10.1146/annurev-linguistics-011619-030613 ; preprint https://alumniacademy.yale.edu/sites/default/files/2021-07/The%20Linguistics%20of%20the%20Voynich%20Manuscript.pdf | Review of phonology/morphology/syntax-like evidence; argues for treating the text as natural language rather than medieval hoax; states no consensus on the underlying language. *The same group later showed that gibberish and some ciphers can mimic many of these metrics [GB22][BG22], so "language-like" statistics remain non-decisive.* |
| [LB20] | L. Lindemann & C. Bowern (2020), "Character Entropy in Modern and Historical Texts: Comparison Metrics for an Undeciphered Manuscript", arXiv:2010.14697 | https://arxiv.org/abs/2010.14697 ; data/code https://github.com/chirila/Voynich-public | Second-order conditional character entropy for Voynichese is unusually low (≈1.9–2.6 bits) vs. comparison texts in many languages. |
| [RK11] | S. Reddy & K. Knight (2011), "What We Know About The Voynich Manuscript", ACL-HLT LaTeCH workshop | https://aclanthology.org/W11-1511.pdf | Currier/D'Imperio transcription; two vocabularies A/B; HMM suggests final glyphs cluster separately (abjad-like hint); topic-like bursts; strong adjacent-page similarity ("ordered narrative") especially in B; characters resemble Arabic/Hebrew/pinyin-style statistics more than English. |
| [MZ13] | M. A. Montemurro & D. H. Zanette (2013), "Keywords and Co-Occurrence Patterns in the Voynich Manuscript: An Information-Theoretic Analysis", *PLoS ONE* 8(6):e66344 | https://doi.org/10.1371/journal.pone.0066344 (PMC3689824) | Long-range word-distribution organisation "compatible with real language"; keyword co-occurrence networks; Herbal–Pharmacological strongest section link. *Shown later to be reproducible by non-linguistic generators in part — treat as non-discriminating.* |
| [Am13] | D. R. Amancio et al. (2013), "Probing the Statistical Properties of Unknown Texts: Application to the Voynich Manuscript", *PLoS ONE* 8(7):e67310 | https://doi.org/10.1371/journal.pone.0067310 ; arXiv:1303.0347 | Word-statistics, network and intermittency measures: incompatible with random/shuffled text, mostly compatible with natural language; candidate keywords; no decipherment. |
| [Za-ent] | R. Zandbergen, "From bigram entropy to word entropy in the Voynich MS" | https://www.voynich.nu/extra/wordent.html | Word entropy not anomalous (stars section ≈9.9 bits/word, between Dante and Pliny) despite unusual character-level entropy and low initial-character entropy. |
| [Za-intro] | R. Zandbergen, *Analysis – Intro* (entropy, Zipf, HMM, Sukhotin, clustering primers; Currier languages; 2024 "RZ languages A/B/C" reclassification) | https://www.voynich.nu/a1_intro.html ; also https://www.voynich.nu/extra/curabcd.html | A and B are statistically distinct at character, bigram and word levels; may be dialects/topics/encodings rather than different languages; RZ-C is intermediate (most astronomical pages). |
| [Za-writing] | R. Zandbergen, *the Writing System* | https://www.voynich.nu/writing.html | Character set (Latin-like, numeral-like, abbreviation-like, gallows), labels/titles/circles, extraneous writing (month names in northern-French-like hand on zodiac pages, colour annotations, f116v), "no corrections" remark and exceptions, Currier hands vs. Fagin Davis hands. |
| [GB22] | D. E. Gaskell & C. L. Bowern (2022), "Gibberish after all? Voynichese is statistically similar to human-produced samples of meaningless text", CEUR-WS Vol-3313 (VOY2022) | https://ceur-ws.org/Vol-3313/paper4.pdf ; code/data https://github.com/danielgaskell/voynich | 42 volunteers wrote "gibberish"; it replicates many Voynichese properties (Zipf-like, low information, repeats, positive word-length autocorrelation); classifier labels VMS samples closer to gibberish, with low confidence. Authors argue common "language-likeness" criteria can't distinguish. |
| [BG22] | C. L. Bowern & D. E. Gaskell (2022), "Enciphered after all? Word-level text metrics are compatible with some types of encipherment", CEUR-WS Vol-3313 | https://ceur-ws.org/Vol-3313/paper6.pdf | 22 text transformations; bigraph merging and null insertion lower conditional entropy and can match word-level metrics; does *not* prove encipherment. |
| [RT26-preprint] | L. Rozanova & A. Temerev (Aug 2026), "A Glyph Is Not a Letter, a Token Is Not a Word, a Space Is Not a Space: What the Units of Voynichese Are Not", arXiv:2608.17096 | https://arxiv.org/abs/2608.17096 ; code https://github.com/lrozanova/voynich-units | **Preprint; not peer-reviewed as far as verified; authors disclose LLM assistance.** On ZL 3b: h₂≈2.69 bits vs ≈3.5 for Latin/Italian/English controls; adjacent-token identity order ≈0.8% of token entropy vs 2–10% in prose; edge-glyph coupling ≈0.2 bits; "uncertain" spaces physically narrower; Naibbe cipher and self-citation generator reproduce several metrics but not edge coupling or hapax-rich vocabulary. Treat quantitative claims as hypotheses to reproduce. |

## 3. Word structure / grammar of "Voynichese"

| Key | Reference | Link | Findings |
|---|---|---|---|
| [St97] | J. Stolfi, prefix–midfix–suffix paradigm ("soft"/"hard" letters), 1997 | https://ic.unicamp.br/~stolfi/EXPORT/voynich/ (index) | Almost every word = all-soft string, or soft prefix + hard midfix + soft suffix. |
| [St00] | J. Stolfi (2000), "A Grammar for Voynichese Words" (crust–mantle–core paradigm) | https://ic.unicamp.br/~stolfi/EXPORT/voynich/00-06-07-word-grammar/ | Word ≈ crust-prefix · mantle-prefix · core (gallows) · mantle-suffix · crust-suffix; ~75% whole-crust words. |
| [St-AxB] | J. Stolfi, prefix-midfix-suffix: A versus B | https://ic.unicamp.br/~stolfi/EXPORT/voynich/ (index; "Comparing languages A and B at the sub-word level") | Sub-word differences between Currier languages. |
| [St-sw] | J. Stolfi, "Special words" (page-level colourised over-represented words) | https://ic.unicamp.br/~stolfi/EXPORT/voynich/ | Page-specific frequent words — candidate topical/content words/names. |
| [St-labels] | J. Stolfi, label lists, label occurrence maps, "The Name of the Sunflower", f77v label references | https://ic.unicamp.br/~stolfi/EXPORT/voynich/ | Label tokens do recur in running text but rarely adjacent to the label. |
| [St-Chinese] | J. Stolfi, "Chinese Theory redux" / word-length distribution similar to Vietnamese/East-Asian languages | https://ic.unicamp.br/~stolfi/EXPORT/voynich/ | Hypothesis of monosyllabic/isolating language; tested against pinyin controls in [RT26-preprint], which finds token-level order and closure differ. |
| [Ze22] | M. Zattera (2022), "A new transcription system for the Voynich manuscript" / slot-alphabet word grammar, VOY2022 | https://ceur-ws.org/Vol-3313/ (abstract bundle: https://www.um.edu.mt/__data/assets/pdf_file/0019/503335/Conferencebookofabstracts.pdf) | 12-slot template; 86.6% of tokens fit; per-section grammars classify pages; argues for multiple "languages" with A/B as major divisions. *(Title as listed in the conference; details via abstract only.)* |
| [Su-Gu91] | B. V. Sukhotin's vowel/consonant algorithm (transl. by J. Guy, 1991) | explained at https://www.voynich.nu/a1_intro.html | Graph-based; **smoke test on raw EVA labels `h` as vowel because of `ch/sh` — shows need for unit segmentation first.** |
| [CN80] | Cave & Neuwirth (1980), Hidden Markov models for English *(not re-verified)* | — | HMM character classes in English. |

## 4. Paleography and scribes

| Key | Reference | Link | Findings |
|---|---|---|---|
| [FD20] | L. Fagin Davis (2020), "How Many Glyphs and How Many Scribes? Digital Paleography and the Voynich Manuscript", *Manuscript Studies* 5(1):164–180 | https://repository.upenn.edu/mss_sims/vol5/iss1/6 | Five hands: Currier's Scribes 1 and 2 plus 3, 4, 5, identified by glyph traits ([k], [n]-finial, gallows loops); scribe output aligns with sections and codicological structure; hands 3–5 write Currier-B-type text. |
| [FD22] | L. Fagin Davis, keynote at VOY2022 | https://ceur-ws.org/Vol-3313/keynote2.pdf | Refinements (e.g. re-attribution of f66r; tests with [n] finials, gallows). |
| IVTFF `$H` | Fagin Davis hand IDs incorporated into IVTFF page variable `$H` (Currier's in `$C`) | https://www.voynich.nu/data/000_README.txt | Directly usable metadata. |

## 5. Generative / "it is gibberish / hoax" accounts (use as null models)

| Key | Reference | Link | Notes |
|---|---|---|---|
| [Ru04] | G. Rugg (2004), "An elegant hoax? A possible solution to the Voynich manuscript", *Cryptologia* 28(1) *(not re-verified)* | — | Cardan-grille/table method generating Voynich-like text. |
| [Sc07] | A. Schinner (2007), "The Voynich Manuscript: Evidence of the Hoax Hypothesis", *Cryptologia* (2007) | https://www.researchgate.net/publication/220615584 | Stochastic/"random-walk" evidence argued to support hoax. |
| [TS20] | T. Timm & A. Schinner (2020), "A possible generating algorithm of the Voynich manuscript", *Cryptologia* 44(1):1–19. doi:10.1080/01611194.2019.1596999 | https://www.academia.edu/39257842/A_possible_generating_algorithm_of_the_Voynich_manuscript ; reference implementation (MIT, Zenodo 10.5281/zenodo.2531632 per [RT26-preprint]) | "Self-citation": new words made by copying/modifying earlier ones; reproduces Zipf-like statistics. |
| [Gr25] | M. A. Greshko (2025), "The Naibbe cipher: a substitution cipher that encrypts Latin and Italian as Voynich Manuscript-like ciphertext", *Cryptologia* | https://www.tandfonline.com/doi/full/10.1080/01611194.2025.2566408 ; https://www.michaelgreshko.com/naibbe-cipher ; code https://github.com/greshko/naibbe-cipher (MIT) | Verbose homophonic substitution, hand-operable with 15th-century materials (card deck); reproduces many Voynich-like properties; **demonstrates a cipher hypothesis is not excluded by statistics, not that it is true**. |

## 6. Decipherment methodology (how to attack unknown scripts/ciphers)

| Key | Reference | Link | Use here |
|---|---|---|---|
| [HK16] | B. Hauer & G. Kondrak (2016), "Decoding Anagrammed Texts Written in an Unknown Language and Script", *TACL* 4 | https://aclanthology.org/Q16-1006.pdf | 3-stage pipeline: language ID (97% on 380 languages) → substitution → anagram decoding (93% word accuracy on 50 test ciphers). Voynich: Hebrew ranked first, but outputs **not syntactically/semantically consistent** (authors' own caveat). |
| [KNRY06] | K. Knight, A. Nair, N. Rathod, K. Yamada (2006), "Unsupervised Analysis for Decipherment Problems", COLING/ACL | https://aclanthology.org/P06-2065/ | EM/Bayesian decipherment framing; includes vowel/consonant-type analyses. |
| [RK11b] | S. Ravi & K. Knight (2011), "Bayesian Inference for Zodiac and Other Homophonic Ciphers", ACL | https://aclanthology.org/P11-1025/ | Homophonic cipher solving with n-gram LMs (e.g. Zodiac 340/408). |
| [SBK10] | B. Snyder, R. Barzilay, K. Knight (2010), "A Statistical Model for Lost Language Decipherment", ACL | https://aclanthology.org/P10-1107.pdf | Ugaritic→Hebrew; needs a known related language; recovered 29/30 letters. |
| [LCB19] | J. Luo, Y. Cao, R. Barzilay (2019), "Neural Decipherment via Minimum-Cost Flow: From Ugaritic to Linear B", ACL | https://aclanthology.org/P19-1303.pdf | Neural + min-cost flow; first automatic Linear B–Greek result. Requires cognate overlap; use for method validation. |
| [Se16] | R. Sennrich et al. (2016), BPE subword units | https://aclanthology.org/P16-1162/ | Unit discovery (Stage 4). |
| [Br92] | P. Brown et al. (1992), "Class-Based n-gram Models of Natural Language" | https://aclanthology.org/J92-4003/ | Distributional word clustering (Stage 7). |

## 7. Refuted / criticised proposals (cautionary examples)

| Key | Reference | Link | Why it matters |
|---|---|---|---|
| [Ch19] | G. Cheshire (2019), proto-Romance proposal, *Romance Studies* | (journal; see criticism) | High-degree-of-freedom glyph→sound mapping, selective matching. |
| [Ke19] | A. Keidan (2019), "No, the Voynich manuscript has not been deciphered" | https://keidan.it/RESOURCES/PRODUCTS/Keidan-vs.-Cheshire.pdf | Argues the claim lacks a defined testable language, misuses Romance-linguistics terminology, uses arbitrary mappings. Related coverage: Ars Technica (https://arstechnica.com/science/2019/05/no-someone-hasnt-cracked-the-code-of-the-mysterious-voynich-manuscript/), Language Log (https://languagelog.ldc.upenn.edu/nll/?p=42749), Voynich Portal (https://voynichportal.com/2019/05/16/cheshire-reprised/). |
| — | 2025–26 claims surfaced in search (e.g. thevoynichproject.org/downloads/PAPER.md; SSRN abstract 7367158; "partial solve" withdrawn after out-of-sample failure) | *not vetted — listed only as examples of why Stage 12 gates exist* | Do not cite as evidence. |

## 8. Community resources

- Voynich Ninja forum (active discussion; "vord" terminology for blank-delimited strings): https://www.voynich.ninja *(not re-verified)*
- 1st International Conference on the Voynich Manuscript (Malta, 2022) proceedings: https://ceur-ws.org/Vol-3313/
- Yale Beinecke digital library record and images: https://brbl-dl.library.yale.edu/vufind/Record/3519597 ; the PDF used here: https://collections.library.yale.edu/pdfs/2002046.pdf

## 9. Established vs. disputed — short table

See Appendix B in `WORKFLOW.md`.
