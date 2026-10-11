# Controls: making the MS 408 statistics interpretable

> **MS 408 is undeciphered.** Nothing here decodes it. This stage only asks: *for each descriptive statistic already computed by the repo, what values do known kinds of text (natural language, simple ciphers, meaningless generators) give at about the same size?* No single metric is decisive.

Run: `python -m msdecipher controls-fetch && python -m msdecipher controls-run` (about 2 minutes). Outputs are in `reports/controls/` (`comparison.md`, `comparison.csv`, `comparison_sd.csv`, `comparison_runs.csv`, `family_ranges.csv`, `verdicts.csv`, `verdict_summary.csv`, `size_sensitivity.csv`, `figures/`).

## 1. Control texts (`controls_fetch.py`, `controls_text.py`)
Only fetch scripts and `data/controls/MANIFEST.json` (URL, SHA256, licence note) are committed; the texts are git-ignored (`python -m msdecipher controls-verify`).

| id | text | tokens used |
|---|---|---|
| `la_vulgate` | Vulgata Clementina (1598), Genesis + Exodus (la.wikisource.org) | 35,000 |
| `la_augustine` | Augustine, *Confessiones* (Gutenberg #33849) | 35,000 |
| `it_dante` | Dante, *Divina Commedia* (Gutenberg #1000), verse | 35,000 |
| `it_manzoni` | Manzoni, *I promessi sposi* (Gutenberg #45334) | 35,000 |
| `de_walther_mhg` | Walther von der Vogelweide, selected poems, Middle High German (Gutenberg #35795) | 9,183 (all there is: **smaller** than MS 408) |

MS 408 reference: ZL 3b running text ("P" lines), 34,977 readable tokens.

Normalisation (a tokenization choice that influences every number): lower case, diacritics folded, `æ→ae`, `ß→ss`, Latin `j→i`, `v→u`, apostrophes split words, only `a-z`, whitespace tokens, first *N* tokens after the front matter.

Not covered: natural Hebrew/Arabic (a real abjad text), Greek, Occitan, Old French, Czech, and a genuine medieval herbal/medical Latin text (no clean public-domain plain text found quickly). These are the most important missing controls.

## 2. Transformations and generators (`controls_transforms.py`)
Applied to `la_vulgate` and `it_manzoni` (two bases per family, so each family band has just 2 points per variant), with 3 seeds for the stochastic ones (keys, codes, shuffles).

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

## 6. Limits / TODO
- More and better controls (abjad natural texts, medieval herbal Latin, abbreviation-heavy Latin, Occitan/Old French/Czech); group-level units for verbose ciphers; the real Naibbe code (GitHub) and Timm-Schinner generator.
- Bootstrap confidence intervals per quire/bifolio for MS 408 and per chunk for controls; the verdict tolerances are placeholders until then.
- MHG control is only 9k tokens; see `size_sensitivity.csv` for how TTR, Zipf, Heaps and entropies shift when the sample shrinks.
- Currier A/B and sections are pooled; hands/sections are not modelled.
