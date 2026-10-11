# Controls: making the MS 408 statistics interpretable

> **MS 408 is undeciphered.** Nothing here decodes it. This stage only asks: *for each descriptive statistic already computed by the repo, what values do known kinds of text (natural language, simple ciphers, meaningless generators) give at about the same size?* No single metric is decisive.

Run: `python -m msdecipher controls-fetch && python -m msdecipher controls-run` (about 5 minutes with the Hebrew/Arabic controls; `controls-fetch --only ID ...` fetches a subset). Outputs are in `reports/controls/` (`comparison.md`, `comparison.csv`, `comparison_sd.csv`, `comparison_runs.csv`, `family_ranges.csv`, `verdicts.csv`, `verdict_summary.csv`, `verdict_shift_abjad.csv`, `size_sensitivity.csv`, `figures/`). Without the abjad files the run still works (they are skipped with a message).

## 1. Control texts (`controls_fetch.py`, `controls_text.py`)
Only fetch scripts and `data/controls/MANIFEST.json` (URL, SHA256, licence note) are committed; the texts are git-ignored (`python -m msdecipher controls-verify`).

| id | text | tokens used |
|---|---|---|
| `la_vulgate` | Vulgata Clementina (1598), Genesis + Exodus (la.wikisource.org) | 35,000 |
| `la_augustine` | Augustine, *Confessiones* (Gutenberg #33849) | 35,000 |
| `it_dante` | Dante, *Divina Commedia* (Gutenberg #1000), verse | 35,000 |
| `it_manzoni` | Manzoni, *I promessi sposi* (Gutenberg #45334) | 35,000 |
| `de_walther_mhg` | Walther von der Vogelweide, selected poems, Middle High German (Gutenberg #35795) | 9,183 (all there is: **smaller** than MS 408) |

Natural abjad controls (consonantal Hebrew and Arabic; added in the second pass):

| id | text | tokens used | licence / how it is stored |
|---|---|---|---|
| `he_tanakh` | Hebrew Bible, Genesis + Exodus, Sefaria version "Tanach with Text Only" (37,325 tokens available) | 35,000 | Sefaria lists it as Public Domain; git-ignored, manifest only |
| `he_mishneh_torah` | Maimonides, *Mishneh Torah* (12th c., medieval rabbinic Hebrew prose): Foundations of the Torah, Human Dispositions, Torah Study, Foreign Worship, Repentance, Sabbath, Sefaria "Torat Emet 363" (69,655 available) | 35,000 | Sefaria: Public Domain; git-ignored, manifest only |
| `ar_quran` | Quran, Tanzil "Simple Clean" v1.1, first 35k of 78,248 words (Classical Arabic, rhymed prose) | 35,000 | **CC BY 3.0 with "verbatim copies only, changing the text is not allowed"**, so only the fetch URL + SHA256 are committed; the downloaded file is kept unmodified in the git-ignored `data/controls/` and normalisation happens in memory only. Attribution: Tanzil Project, tanzil.net |
| `ar_muqaddimah` | Ibn Khaldun, *al-Muqaddimah* (14th c.), sub-pages linked from "الجزء الأول" on ar.wikisource.org, in book order (38,838 available) | 35,000 | Work in the public domain; Wikisource platform text CC BY-SA 4.0 |

Kalila wa Dimna (ar.wikisource) was looked at and not used: its Wikisource pages only transclude scans (185 words in total). Syriac / Ethiopic were **not** added (no quick clean open source and no honest way to normalise them in this pass).

MS 408 reference: ZL 3b running text ("P" lines), 34,977 readable tokens.

Normalisation (a tokenization choice that influences every number): lower case, diacritics folded, `æ→ae`, `ß→ss`, Latin `j→i`, `v→u`, apostrophes split words, only `a-z`, whitespace tokens, first *N* tokens after the front matter.

Abjad normalisation (`normalise_abjad_text`; a tokenization choice like any other): cantillation, niqqud, Arabic harakat/tatweel/Quranic marks, digits, Latin letters, brackets and HTML/wiki markup are removed; the Hebrew maqaf (־) splits words; only consonant letters are kept; Arabic alif-hamza variants (أ إ آ ٱ) fold to alif and Persian kaf/yeh to Arabic ones. Arabic clitics (و-, ال-, ب-) and Hebrew prefixes (ו-, ה-, ב-...) stay attached, as in the original orthography. **Each letter is one native Unicode code point = one unit**, which is what the single-character metrics already assume.
- *Native vs transliterated:* a 1-to-1 single-character Latin transliteration (`HEBREW_TRANSLIT`, Buckwalter for Arabic) is provided and a test checks that every label-free metric is identical on it, so no separate transliterated run is reported. A multi-character transliteration (sh, th ...) would amount to a different unit segmentation and was not tried.
- *Folded variant (`plain_folded:` rows, sensitivity only, excluded from the family verdicts):* Hebrew final forms (ך ם ן ף ץ) folded into the medial letters (27 → 22 letters); Arabic reduced alphabet (ى→ي, ة→ه, ؤ→و, ئ→ي, hamza deleted; 33 → 28 letters). Hebrew finals are a pure word-final spelling variant, so keeping them inflates positional skew; the folded rows show how much.

Not covered: Syriac, Ethiopic, Greek, Occitan, Old French, Czech, and a genuine medieval herbal/medical Latin text (no clean public-domain plain text found quickly). The abjad controls above are one language family in two scripts: they say what *Semitic consonantal text* looks like on these metrics, nothing more.

## 2. Transformations and generators (`controls_transforms.py`)
Applied to `la_vulgate` and `it_manzoni` (two bases per family, so each family band has just 2 points per variant), with 3 seeds for the stochastic ones (keys, codes, shuffles). The alphabet-independent subset (Vigenere over the text's own alphabet, verbose 2-symbol, Naibbe-inspired tiles, reversal, alphagram, letter shuffle, token shuffle) plus the Markov (order 1, 2) and iid-letter generators are also applied to the four Hebrew/Arabic texts, **in the same families**, so those bands now mix Latin/Italian and Hebrew/Arabic bases (and have 4 more members). Not applied to Hebrew/Arabic: monoalphabetic/Caesar (provably invisible), abjad vowel deletion (already vowelless) and the nomenclator (its syllabifier needs Latin vowels). `verdict_shift_abjad.csv` and section 2b of `comparison.md` show verdicts with and without them.

| family | implementation (simplified!) |
|---|---|
| abjad | delete a e i o u; drop emptied words |
| monoalphabetic substitution / Caesar | random bijection to Greek symbols; shift 3. Provably invisible to every metric here (tests check this) |
| polyalphabetic | Vigenere, key length 3 and 6, key advances over letters only |
| nomenclator-like | 60 most frequent words get a 2-symbol code; other words are split into crude syllables, each syllable gets a 2- (300 most frequent) or 3-symbol code |
| verbose 2-symbol | every letter -> one of 2 random homophone pairs |
| Naibbe-**inspired** | unigram/bigram tiles, up to 4 homophones for frequent letters, 2-3 symbol groups. **Not** Greshko's Naibbe cipher or its tables |
| reversal / alphagram / letter shuffle / token shuffle | reverse letters per word; sort letters per word; random permutation of letters in each occurrence; random permutation of tokens |
| Markov character gibberish | order 1 and 2 over letters of Latin/Italian words, with word-boundary symbols; no lexicon or word-order model |
| iid letters | letters and word lengths drawn independently |
| self-citation (Timm-Schinner **style**) | each word copies a word from the recent past with probability *p* ∈ {0.15, 0.3, 0.5} of one length-regulated edit; Zipf-weighted letters; **not fitted** and much cruder than the published generator |
| slot grammar | onset + head + vowel [+ head + vowel] + tail from small Zipf-weighted inventories. **Inventories were written with published descriptions of Voynichese in mind**, so resembling MS 408's positional statistics is expected and is not independent evidence |
| Markov o2 trained on MS 408 | reproduces MS 408's h2 by construction; kept as a sanity row and excluded from family bands |

## 3. Metrics (`controls_metrics.py`, reusing `stats.py`)
Zipf exponent (MLE, ranks 10-1000), Heaps beta (text order and shuffled), type/token ratio, hapax share, top-10 coverage, word entropy, mean/SD word length, unit H1, conditional entropies h2 and h3, h2 rise after shuffling letters inside words, Sukhotin vowel-like share (min count 20), positional skew (initial-vs-final JSD; share of units whose initial or final propensity is >3x over/under the baseline) and adjacent identical / edit-distance-1 token rates. Controls use single characters as units; MS 408 uses the collapsed EVA units (ch, sh, cth, ckh, cph, cfh) with a raw-EVA row beside it (`verdict_raw` columns).

## 4. Screening verdicts
For each family and metric the band is [min, max] of its members' means, widened by a round tolerance per metric; MS 408 is marked `≈` inside, `↑` above, `↓` below. This is a **screen**, not a test: families have 2-5 members from 1-2 base texts; tolerances are arbitrary; metrics are strongly correlated; counting `≈` cells is only used to order columns.

## 5. What the run shows (as of the committed reports; ZL 3b, collapsed units)
- **Lexicon-level statistics are not discriminating.** Zipf s (0.98), TTR (0.21) and Heaps beta (0.75) fall inside the bands of natural-language plaintext *and* of most substitution/transposition/code controls, and of the slot-grammar generator. Only iid letters, Markov gibberish, verbose/homophonic and shuffled-letter controls miss on TTR/Heaps (they create too many new word types).
- **Letter-level dependencies are the outlier.** MS 408 h2 = 2.22 and h3 = 1.95 bits are below *every* control family except (by construction) the Markov model trained on MS 408 itself; plaintext Latin/Italian/MHG give h2 ≈ 3.0-3.2 and h3 ≈ 2.3-2.6; the only family whose h2 band reaches MS 408 is the slot-grammar generator, and h3 is below all bands.
- **Shuffling letters inside words hurts MS 408 much more** (h2 rises by 1.35 bits) than natural text (0.7-1.0) or most ciphers; only alphagram (sorted letters) and the slot grammar are in the same range. Positional skew (92% of units strongly position-dependent) is likewise matched only by alphagram and slot grammar; Italian plaintext reaches 0.81 because of its vowel endings.
- **Hapax share of types** (0.69) is at the top of the plaintext range (0.59-0.68; Augustine 0.68) and above the substitution/code families' bands; it is a weak signal given the sample sizes.
- **Self-citation toy generators** (parameters not fitted) produce far more adjacent repeats and near-repeats (adjacent edit-distance-1 rate 0.10-0.17 and identical-token rate 0.05-0.15, vs MS 408's 0.034 and 0.008) and mismatch Zipf (0.55-0.70 vs 0.98) and h2 (3.4-3.6 vs 2.2); this does not rule out a better-tuned generator.
- **Verbose/homophonic controls** (2 symbols per letter; Naibbe-inspired tiles) have the wrong word length and type/token behaviour at single-symbol level, and h2 around 2.9-3.3, but their unit definition (symbol vs group) is a free choice; they should be re-run with group-level units before drawing any conclusion.
- No family reproduces all metrics. The families that come closest on the most metrics (slot grammar, alphagram) were either designed with Voynichese in mind or are degenerate (anagram collapses word types); read that as 'positional/word-internal regularity is the feature that must be explained', not as support for either.

### 5b. Effect of adding Hebrew and Arabic (second pass)
Four consonantal texts (Genesis+Exodus; Maimonides; Quran; Ibn Khaldun, 35k tokens each; `reports/controls/comparison.md` section 2b, `verdict_shift_abjad.csv`):
- **h2 / h3 (letter entropy): finding unchanged and, if anything, sharper.** Hebrew/Arabic give h2 = 3.63-3.87 bits (folded alphabets 3.52-3.72) and h3 = 2.61-3.04, i.e. *higher* than Latin/Italian/MHG (h2 ≈ 3.0-3.2) and far above MS 408 (2.22 / 1.95). A natural consonantal text does **not** bring h2 down toward MS 408; dropping vowels in Latin did not either (abjad transform: h2 ≈ 3.0). Caveat: absolute entropies depend on alphabet size and on how many letter types exist (22-33 letters here vs 27 collapsed EVA units; H1 is 4.2-4.3 for abjad vs 3.9 for MS 408), so a per-alphabet normalisation would be a fairer comparison and was not done.
- **Within-word shuffle effect: unchanged (MS 408 stays the outlier).** The h2 rise is 0.24-0.41 bits for Hebrew/Arabic, *smaller* than Latin/Italian (0.67-0.96) and much smaller than MS 408's 1.35, so the within-word letter order carries less weight in the (root-and-pattern, consonant-only) abjad texts than in MS 408. Only alphagram and the slot grammar still reach 1.35.
- **Positional skew: partly Hebrew final forms.** 0.48-0.58 of units skewed with Hebrew final letters kept, 0.14-0.23 (Hebrew) once they are folded; Arabic 0.58 (folded alphabet 0.50-0.54). All below MS 408 (0.92); word-initial vs final JSD 0.28-0.31 (0.11-0.26 folded) vs 0.66. The skewed share depends visibly on the orthographic convention (final forms, clitic letters like و and ال), a warning that this metric partly measures spelling conventions.
- **Zipf / Heaps / TTR / hapax: unchanged, non-discriminating.** Zipf s = 0.86-0.89 (MS 408 0.98), Heaps beta (shuffled) 0.76-0.82 (0.75), TTR 0.22-0.29 (0.21), hapax share 0.57-0.66 (0.69), so the abjad texts sit in the same loose zone as Latin/Italian; MS 408's TTR is close to the Hebrew ones; its Zipf s (0.98) is above every abjad text (0.86-0.89) and counts as "inside" the band only because of the 0.1 tolerance. Mean word length 3.8-4.5 units vs 4.47.
- **Verdict changes:** the new family "natural abjad text" contains MS 408 for 10 of 18 metrics, all lexicon/word-shape ones, and misses on unit H1/h2/h3, within-word shuffle gap, vowel-like share, positional JSD/skew and adjacent edit-distance-1 rate. Merging Hebrew/Arabic bases into the existing transformation families changes 13 of the existing 270 family-metric verdicts (only dispersion-type metrics: word length SD, hapax share and top-10 coverage for the shuffle/reversal/anagram families, vowel-like share for iid letters); **no verdict on h2, h3, within-word shuffle gap, positional skew, Zipf, Heaps or TTR changes.**
- **Caveats:** one language family, two scripts, four texts (Biblical, medieval rabbinic and Quranic/medieval Arabic prose; genres differ: the Quran is rhymed, the Muqaddimah and Maimonides expository); consonantal Hebrew/Arabic words are short and root-dense, orthographic choices (maqaf split, attached clitics, alif folding) are ours; the abjad texts are read left-to-right as codepoints, which is irrelevant for the statistics; and none of this says anything about what language MS 408 might encode. Absence of a Hebrew/Arabic match on these metrics is weak evidence against a plain abjad hypothesis *with these normalisations*; it does not exclude abjad + a transformation (e.g. verbose substitution), whose bands in the table are only crude simulations (`verbose_2sym`/`naibbe_like` on Hebrew/Arabic give h2 ≈ 2.9-3.3, Δh2 0.5-0.8).

## 6. Limits / TODO
- More and better controls (Syriac / Ethiopic abjad/abugida text, further Semitic genres, medieval herbal Latin, abbreviation-heavy Latin, Occitan/Old French/Czech); group-level units for verbose ciphers; the real Naibbe code (GitHub) and Timm-Schinner generator.
- Bootstrap confidence intervals per quire/bifolio for MS 408 and per chunk for controls; the verdict tolerances are placeholders until then.
- MHG control is only 9k tokens; see `size_sensitivity.csv` for how TTR, Zipf, Heaps and entropies shift when the sample shrinks.
- Currier A/B and sections are pooled; hands/sections are not modelled.
