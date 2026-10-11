# h05 — the zodiac pages as a crib source (and the label pitches under the earlier tone maps)

Request: *"notice zodiac signs toward the end of the pdf, those are the names of zodiac signs depicted in the middle of the circle, and work from there."*
Everything here is reproducible: `python run_h05.py && python make_figures.py && pytest test_h05.py` (~75 s; `--quick` ≈ 12 s). Data: `data/transcriptions/ZL3b-n.txt`, `data/images/native`.

## 0. Verdict in five lines

1. **The words in the middle of the circles are not Voynichese and are not sign names.** They are short *Roman-script month names* (Mars, Abril, May, … Octembre, Novembre, Decembre) in a later(-looking) hand, next to the emblem of the sign (fish, ram, bull …). They do not occur in the transcription (only in its comments). So they give **no Voynichese letter-for-letter crib at all**: the one thing the pages *do* provide for free is the sign↔month pairing in Roman letters. The only Voynichese in the centre of any diagram is one star label (`otolal`, f70v2).
2. What *is* Voynichese on these pages: 935 words of circular ring text and **299 labels (336 words) – one short label per nymph/star**, 15 or ~30 per page. These are not sign names: they differ nymph by nymph (86–100 % of the label words on a page occur once on that page), no label is shared by all pages, and the two pages of Aries (and of Taurus) are not more alike than neighbouring pages of different signs.
3. Nothing about the labels' **length, letter pattern, prefixes/suffixes or repeat structure matches any of 19 candidate sign-/month-name lists (Latin, Italian, French, Spanish, Catalan, Occitan, German, Hebrew, Arabic) beyond chance** after multiple-testing correction (72 length tests, 36 isomorph tests, 22 crib-drag transfer tests: smallest Holm-adjusted p = 1.0, 0.61, 0.12).
4. Labels **do** differ from page to page (held-out classification of a label's page: 24.7 % vs 8.2 % for shuffled pages), but that difference tracks *position in the section* (e.g. `ot-` falls from 45 % to 3–27 % of labels, rho = −0.75 over the 12 pages in order) rather than the sign — the same drift and Currier-A/B-like split seen across the whole manuscript. Neighbouring pages resemble each other whatever sign they show.
5. The tone/frequency work is carried over only as an **illustration** (label-pitch table, `a_slotgrammar_ext` and the sheet's 8 digraphs): the pitches are a hypothesis-generation device with no evidential link to the pages.

## 1. The zodiac folios (task 1)

Twelve pages (`$I=Z`), ten signs. **Aquarius and Capricorn are missing**: f74 (the other half of the bifolio f73+f74) was cut out of the book (cut stubs visible at f75), so those two signs are lost or were never drawn. Aries and Taurus are each drawn twice (two halves of 15 nymphs: 5 inner + 10 outer), every other sign once with ~30 nymphs. The cycle starts with Pisces. Page→sign mapping follows Stolfi's zodiac notes and voynich.nu; **I checked every page against the scans** (`data/images/native/page_128…135.jpg`; the pdf pages in the table): the emblems are fish, ram ×2, bull ×2, twins, crab, lion, standing woman, balance, a four-legged animal with curly tail (Scorpio, "looks more like a lizard"), crossbowman. I could confirm a short Roman word under/next to every emblem I looked at but cannot read all of them at this resolution (`abril` on f70v1/f71r is clear; the rest of the readings below come from the literature).

| folio | sign (verified in image) | Roman month word near centre | pdf page | ring texts (Cc) | labels (Lz) by band | ring words |
|---|---|---|---|---|---|---|
| f70v2 | Pisces (two fish, 2 stars) | Mars | 128 | 3 | 30 (19 outer, 10 inner, **1 central star `otolal`**) | 93 |
| f70v1 | Aries (ram, "dark") | Abril/Aberil | 129 | 2 | 15 (10 outer, 5 inner) | 60 |
| f71r | Aries (ram, "light") | Abril/Aberil | 130 | 3 | 15 (10, 5) | 72 |
| f71v | Taurus ("light") | May | 131 | 3 | 15 (10, 5) | 76 |
| f72r1 | Taurus ("dark", hole in vellum) | May | 131 | 3 | 15 (10, 5) | 81 |
| f72r2 | Gemini | Yuny/Yony/Jong | 131 | 3 | 29 (5 top, 15 outer, 9 inner; one nymph unlabelled) | 78 |
| f72r3 | Cancer (crab) | Jollet? | 131 | 4 | 30 (12 outer, 11 middle, 7 inner) | 118 |
| f72v3 | Leo | Augst | 132 | 3 | 30 (18, 12) | 81 |
| f72v2 | Virgo | Septembr(e)? | 132 | 3 | 30 (18, 12) | 74 |
| f72v1 | Libra (scales) | Octembre | 133 | 3 | 30 (20, 10) | 71 |
| f73r | Scorpio | Novembre | 134 | 3 | 30 (16 outer, 10 inner, 4 top) | 63 |
| f73v | Sagittarius | Decembre? | 135 | 3 | 30 (16, 10, 4 top) | 68 |

Full per-locus table (`results/zodiac_loci.csv`: type Cc/Lz, ring/band, clock position of the nymph, raw text), every label token (`results/label_tokens.csv`), page table (`results/zodiac_folios.csv`). The transcription has no radial (R) loci on these pages: only ring text (Cc) and nymph/star labels (Lz). Band names come from the transcriber's comment lines; "top" = the 4–5 overflow nymphs drawn above the circle. Fig. 1: `figures/fig1_zodiac_pages_labels.png`.

## 2. Crib table and literature (task 2)

Per sign (`results/crib_table_by_sign.csv`; pages pooled for Aries/Taurus): number of label words / types / hapax share / most frequent and most sign-specific labels.

| sign | label words | types | hapax share | most frequent labels (count) |
|---|---|---|---|---|
| Pisces | 33 | 31 | 0.88 | oty 2, otar 2 |
| Aries | 42 | 41 | 0.95 | otal 2 |
| Taurus | 44 | 38 | 0.75 | ar 3, char 2, otaiin 2, otar 2, ary 2 |
| Gemini | 30 | 28 | 0.87 | okal 2, okaly 2 |
| Cancer | 38 | 38 | 1.00 | – (all once) |
| Leo | 31 | 29 | 0.87 | okaly 2, otaly 2 |
| Virgo | 31 | 30 | 0.94 | cheoldy 2 |
| Libra | 27 | 27 | 1.00 | – (all once) |
| Scorpio | 30 | 29 | 0.93 | otaly 2 |
| Sagittarius | 30 | 28 | 0.87 | oteody 2, ykey 2 |

* **Are the label sets distinct?** Yes in the weak sense: the 272 label word types overlap *less* between pages than under a token shuffle (mean pairwise Jaccard 0.0197 vs 0.0233, shuffle max 0.030; only 37 types occur on ≥2 pages, 35 on ≥2 signs). So there is **no common pool of label words** and no recurring "sign word". (This contradicts the usual remark that labels are a small recycled inventory; at the whole-label-word level on these pages they are almost all unique — recurrence is at the *affix* level, below.)
* **Same sign, similar labels?** The test that would support "labels contain the sign's name": the two Aries pages and the two Taurus pages should resemble each other more than other page pairs *and more than neighbouring pages* do. Unit-bigram cosine of label sets: same-sign pairs 0.770 / 0.789 (ranks 20 and 14 of 66 pairs), mean 0.780 vs 0.772 for the nine adjacent different-sign pairs and 0.715 for all pairs; random pair-of-pairs p = 0.12. On label word types the Aries pair shares *no* word (the least similar of all 66 pairs), the Taurus pair ranks 2nd (p = 0.15). Ring text: p = 0.10. **No support.** (`fig2_page_similarity.png`.)
* **Do labels identify the page?** Leave-one-label-out naive Bayes on unit bigrams: 24.7 % (12 pages) vs 8.2 % shuffled (max of 200 shuffles 13.1 %, p = 0.005); at sign level 27.1 % vs 10.0 %. χ² of page vs first unit, first two units, last unit, last two units, length: all p ≤ 0.008. Page-specific style is real; the next two bullets say what it follows.
* **Affixes** (`results/label_affix_shares_by_page.csv`, `shared_affixes_all_pages.csv`, `fig3`). The only prefix/suffix present on all 12 pages at a high rate is `o-` (label-initial `o` 67 % vs 21 % of running-text words; minimum page 48 %, median 68 %) and `-y` (46 % vs 41 %, min page 26 %); `ok-`/`ot-` are on all pages but at very different rates (`ot-` 3–71 %, `ok-` 5–53 %). **There is no `-ar`/`-or` ending shared by all pages**: share of labels ending in `ar`/`or` ranges 0.0 (Leo, Libra) – 0.43 (Taurus f71v). **There is no one ending shared by Sep–Dec** (the four "-bre" months, f72v2, f72v1, f73r, f73v): their labels are more alike than random 4-sets of pages (p = 0.002 on 495 sets) but not more than 4 *consecutive* pages (p = 0.11 over the 9 windows), and not at all in ring text (p = 0.64) — that is the page-order drift, not a month name.
* **Drift with page order** (12 pages, permutation, uncorrected): `ot-` share rho = −0.75 (p = 0.007), `-ar/-or` rho = −0.75 (p = 0.009), `-y` rho = +0.69 (p = 0.018), `ok-` rho = +0.35 (p = 0.28), mean length rho = −0.08 (p = 0.81). Holm over these five: 0.034, 0.036, 0.054, 0.55, 0.81. Labels shift gradually along the section (and with the language/hand difference of the pages), they do not carry sign-specific stems.

### Literature (cite / dispute marks)

| claim | source | status |
|---|---|---|
| 12 pages = 10 signs; Aries and Taurus split in two halves of 15; Aquarius/Capricorn lost with f74; sequence starts at Pisces | Stolfi, zodiac section notes (`ic.unicamp.br/~stolfi/voynich/Notes/040/data-sections/zod`); voynich.nu quire 11/12 pages | **accepted**; whether Aquarius/Capricorn were ever drawn is undecided (f74 was cut out, cut marks on f75) |
| Roman month names next to the emblems: Mars, Aberil/Abril, May, Yony/Jong, Jollet?, Augst, Septembr(e)?, Octembre, Novembre, Decembre? | Stolfi/Zandbergen e-mails in the notes above; inamidst.com/voynich/months; Schwerdtfeger list via S. Bax (`stephenbax.net/?p=1226`); voynichanalysis.wordpress.com 2012 | readings of *Mars, May, Augst, Octembre, Novembre* agreed; **Abril vs Aberil, Yony vs Jong/Jolliz, Septembr(e), Decembre/Decebre disputed** (Stolfi: some letters only readable by assuming a month name) |
| the month names are in a different, French-looking late-15th-c. hand | Reeds, quoted in Stolfi's notes; voynich.nu | **disputed**: Stolfi proposes the same hand as the f116v "michiton" lines; language called Occitan (inamidst), northern French/Anglo-Norman (voynichanalysis, Bax), with *Augst*/*Aberil* closer to Swiss/Bavarian (voynichanalysis); Bax/King: "we do not know enough about medieval French month-names to associate them with a specific region" |
| "septembr + abbreviation" = Latin genitive | Voynich Ninja "month names" thread | **disputed, unverified** |
| nymphs/stars = degrees (30 per sign); labels = descriptions of the rising decan-degree image (Angelus, Astrolabium Planum 1488; Peter of Abano) | Zandbergen quoted in Stolfi's notes | **speculative**; Zandbergen himself notes the repetition in Engel/Angelus lists is much higher than in the Voynich labels — our result of nearly all-unique labels agrees |
| the label by the seven-star cluster (Pleiades) on f68r3, EVA `doary`/`doaro`, may be "Taurus" | Bax 2014 (partial decoding); Zandbergen/Stolfi note "Pleiades"; Voynich Ninja thread "Bax' label readings" | **disputed**; Bax calls it speculative and "not necessarily Latin Taurus". My check: `doary`/`doaro` occur **0 times** on any zodiac page and 0 times in running text, so if it were "Taurus" it is not on the Taurus pages |
| E. Sherwood proposals | – | I found no specific Sherwood claim about the zodiac month names in my searches; **not cited, not verified** |
| Arabic-West month names (ynyr, fbryr, mrs, 'bryl, m'yh, … 'ktwbr, nwnbr, dgnbr) as a possible reading | Kunitsch via Zandbergen, in Stolfi's notes | **suggestive only**; "octembre" does not fit; I include it as a candidate list |

## 3. Frequency work (task 3)

**Units** (`results/label_unit_enrichment.csv`, `label_unit_position_vs_ms.csv`, `length_structure_profile.csv`). 12 units differ from running text after Holm (Fisher, 28 units with ≥15 occurrences tested): more `f` (0.93 % vs 0.23 %, ×4.1), `m` (×2.7), `a` (×1.7), `t` (×1.6), `l` (×1.4), `o` (×1.25); fewer `d`, `i`, `n`, `sh` (×0.46), `ch` (×0.33) and essentially **no `q`** (0.05 % vs 3.4 %, ×0.016 — `qo-` is absent from the labels, and `qo` is the sheet's 174 Hz unit). Label words are short: mean 5.63 letters (sd 1.7, max 12; 12.5 % ≥ 8 letters, one ≥ 11) vs 4.99 for running text; 62 % have a repeated unit (running text 37 %).
Name lists (one per sign, letters): Latin signs mean 6.0 letters, Latin months 7.1, Italian 6.7, German 6.3, Hebrew 4.3, Arabic 3.9 … Latin *Sagittarius* (11 letters) is longer than any label but one.

**Length ordering vs sign/month names** (`length_order_tests.csv`, `fig4`): Spearman between the mean length of a sign's labels (or ring words; letters or units) and the length of its name, one permutation null per test (20 000 permutations of the names over the 10 signs; Aries and Taurus pages pooled). 18 name lists × 4 metrics = **72 tests; 5 have p < .05 (3.6 expected by chance)**, smallest p = 0.015 (French sign names, rho = −0.75, i.e. the *wrong* sign for a name-length effect), **smallest Holm p = 1.0**. Latin sign names: rho = −0.41, p = 0.24. Latin months: label length rho = 0.07 (p = 0.86); the second-smallest p of all is Latin months vs ring-word length (rho = +0.73, p = 0.021, Holm 1.0) — the expected-sized fluke among 72. The p-value histogram is flat.

**Name-in-page isomorph test** (`isomorph_name_in_page_tests.csv`, fig. 5 left). If a sign's name occurred as a label word or ring word on its page (one letter = one unit), some token on that page would have the same length and repeat pattern as the name (e.g. *taurus* = 0 1 2 3 2 4, *novembre* = 0 1 2 3 4 5 6 3), more often than elsewhere in the MS. Statistic: sum over 10 signs of a binomial-style z against the MS-wide rate of that pattern; null = permuting names over signs (20 000), exact whole-token and contiguous-window versions. **36 tests; 3 with p < .05 (1.8 expected); smallest p = 0.017 (Arabic sign names, window mode; those names have no repeated letters, so it is only a length-profile effect), smallest Holm p = 0.61.** For the Latin sign names (exact): observed 54 matching tokens vs 61.7 expected from the MS rate.

## 4. Crib-drag with transfer test (task 4)

For each of 11 name lists that has a lexicon in the repo's controls (Latin, Italian, German, Hebrew, Arabic; French/Spanish/Catalan/Occitan have no control corpus, so they are in the length and isomorph tests only):
1. for each sign, take the most frequent token on its pages that is isomorphic to its name (unit-level) as the candidate;
2. read off a partial unit→letter map from the candidates (`crib_drag_candidates.csv`, `mapping` column of `crib_drag_summary.csv`) and count **conflicts** (units that would need two letters);
3. **transfer**: apply the map to all fully-mapped words (≥3 units) of the *rest of the manuscript* and count distinct word types landing in the language's lexicon (Latin 10 215 types, Italian 13 001, German 2 283, Hebrew 3 402, Arabic 6 125; types seen ≥2 times in the control text);
4. null A = same pipeline with the names *permuted over the signs* (400 runs); null B = random lexicon words with the same length as each name (400 runs); p is computed among null runs whose mapping covers the same number of units (±1), because hits grow with coverage. Holm over 22 tests.

Result (`crib_drag_summary.csv`, fig. 5 right, null runs in `crib_null_store.json`):

| names | signs with a candidate | units mapped | conflicts (null A min) | lexicon types hit in rest of MS | null A mean / null B mean | p vs A (matched) | p vs B (matched) | Holm A / B |
|---|---|---|---|---|---|---|---|---|
| sign:latin | 7 | 13 | 8 (4) | 78 | 24.5 / 34.3 | 0.006 | 0.048 | 0.12 / 0.91 |
| sign:italian | 3 | 9 | 3 (1) | 32 | 13.1 / 29.3 | 0.031 | 0.158 | 0.61 / 1.0 |
| sign:german | 6 | 16 | 4 (5) | 29 | 10.3 / 9.6 | 0.024 | 0.115 | 0.50 / 1.0 |
| sign:hebrew | 9 | 13 | 9 (7) | 38 | 41.4 / 39.9 | 0.46 | 0.50 | 1 / 1 |
| sign:arabic | 10 | 14 | 8 (7) | 19 | 20.7 / 30.0 | 0.65 | 0.86 | 1 / 1 |
| month:latin | 3 | 11 | 3 (0) | 9 | 26.5 / 19.8 | 0.97 | 0.87 | 1 / 1 |
| month:italian | 5 | 11 | 8 (4) | 22 | 28.5 / 26.0 | 0.72 | 0.59 | 1 / 1 |
| month:german | 5 | 11 | 5 (2) | 1 | 3.2 / 12.2 | 0.81 | 1.0 | 1 / 1 |
| month:roman words on the pages | 6 | 9 | 7 (3) | 18 | 14.1 / 25.5 | 0.16 | 0.61 | 1 / 1 |
| month:Schwerdtfeger/Bax reading | 7 | 10 | 10 (3) | 5 | 16.5 / 24.9 | 0.86 | 0.97 | 1 / 1 |
| month:Arabic-West (Kunitsch) | 9 | 12 | 9 (6) | 45 | 32.4 / 34.3 | 0.11 | 0.32 | 1 / 1 |

**Reading it.** The nominal best list is Latin sign names (p = 0.006 vs permuted pairings, 0.048 vs random words), but (a) it does not survive correction (Holm 0.12 / 0.91 over the 22 tests), (b) the map is not a coherent substitution — 8 of 13 mapped units would need two different letters (the best of 400 permuted-pairing runs still had 4 conflicts, so conflicts of this size are normal for this procedure), (c) the "candidates" are mostly tokens occurring once on the page and each isomorphic to dozens-to-hundreds of other word types (up to 929 for names without repeated letters, e.g. *aries* → `cheody`), so almost any word could be chosen, (d) a post-hoc "joint" p (hits ≥ observed *and* conflicts ≤ observed, null A) is 0.002 for Latin signs, 0.002 German, 0.012 Italian — I defined it *after* seeing the table, it is not in the Holm family and should be read as a pointer for a pre-registered replication, not as evidence. **Overfitting statement:** with 3–10 usable candidates and 9–16 mapped units, the map has about as many free parameters as constraints; "plausible words elsewhere" are then expected from any map that covers the frequent units `o a l y d`, which is why nulls B/A are needed. German is the one list whose 4 conflicts are below every null-A run (min 5) but only 41 matched null runs exist for it and its lexicon is the smallest. **Verdict: no label set is shown to encode any candidate sign- or month-name list.**

## 5. Label pitches (task 5, illustration only)

`results/label_pitch_table.csv`: every one of the 272 label word types with its units (T2 segmentation, the sheet's 8 digraphs `ae dy ka ly ny qo ri ya` as single units), the Hz sequence under **`a_slotgrammar_ext`** (h02's slot-grammar order extended from the sheet's own values; the sheet's 8 digraphs keep their sheet Hz: qo 174, ka 233, ri 261, dy 294, ae 322, ya 365, ny 400, ly 433), mean/first/last Hz, range and contour, and the alternative `c_pos` mean. `results/unit_hz_a_slotgrammar_ext.csv` is the full unit→Hz table.

* 92 of 272 label types contain at least one sheet digraph (so a sheet-value pitch is defined for them directly); `ly` (433 Hz) and `dy` (294) are the most frequent. Example: `otaly` = o t a ly → 274, 246, 303, 433 Hz.
* Only 28 of the 272 label types (10 %) have a monotone pitch contour (26 rising, 2 falling) – no better than the whole text under h02/h03; there is no tonal "name" contour shared by labels.
* Mean label pitch by sign: 289.5 Hz (Scorpio) – 305.5 Hz (Cancer), overall 298.2 Hz; η² of sign = 0.062, label-shuffle permutation p = 0.015 (`fig6`). That page effect is just the affix drift of §2 (more `ot-/ar` → different mean Hz), not a pitch signature of a sign.
* As in h02/h03: a frequency assignment is a hypothesis-generation device with no evidential link to the manuscript unless it beats a null, and `a_slotgrammar_ext` is partly circular (anchored on the sheet and fitted to the MS's slot statistics). Here it beats nothing; no audio was rendered.

## 6. What I would and would not conclude

* The user-visible premise needs correcting: the **centre words are Roman month names**, not sign names and not Voynichese. The sign is shown by the *emblem*. The pairing (emblem ↔ month ↔ sign) is therefore a solid piece of context (and dating/provenance evidence for the *added* words), but it does not constrain the Voynichese alphabet.
* The Voynichese on these pages (ring text + nymph labels) shows no detectable encoding of sign or month names under any of the tests above; it does show strong page/position structure (affix drift, `o-` initial dominance, absent `qo-`).
* A cleaner future test would need *independent* anchors: e.g. a held-out replication of the Latin-signs crib-drag with a pre-registered conflict criterion, and label–star identification (which nymph/star is which degree) rather than sign names.

## Limitations

* Power: 10 signs, ≤ 10 usable candidate tokens. A true single name would have to appear verbatim as a short label *and* be isomorphic to its plaintext under a one-letter-one-unit cipher; verbose or syllabic encodings, multi-label phrases, or labels naming nymphs/degrees instead are invisible to these tests.
* Transcription ZL3b with first readings of `[a:b]` alternatives; words with `?`/ligature placeholders were dropped from word-level tests (336 label words kept out of ~350). Segmentation is the repo's "collapsed" EVA units.
* Name lists: Latin/Italian/German/French/Hebrew/Arabic from standard names; **Occitan, Catalan, Spanish lists are from memory and unchecked against a dictionary**; Hebrew/Arabic names are consonantal and compared to an alphabetic text; the Roman month readings are the disputed ones in §2. French/Spanish/Catalan/Occitan lacked lexicons, so they enter only the length/isomorph tests. German lexicon is small (2 283 types, Faust) → low power.
* Pages are not independent (adjacent pages, same quire/hand/language state; Currier A/B split not modelled), so page-level p-values (drift, classification) are optimistic.
* Holm families: length 72, isomorph 36, crib-drag 22; the joint-conflict p and the drift tests are uncorrected/post hoc and labelled so.

## Files

`h05_lib.py` (extraction, name lists, tests, crib-drag), `run_h05.py`, `make_figures.py`, `test_h05.py` (13 tests: extraction counts, name lists, permutation tests on planted data, planted-cipher crib-drag recovery, no Roman words in the transcription), `results/*.csv|json`, `figures/fig1…fig6`.
