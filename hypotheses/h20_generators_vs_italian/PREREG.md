# h20 pre-registration: which generator or Italian-based encoding reproduces the MS 408 likelihood fingerprint?

Committed before any text is generated or scored.

## Pipeline
This is h19's held-out pipeline, unchanged (`hypotheses/h19_heldout_likelihood/run_h19.py`, `run_split`, same seed):
- **Folds:** bifolium and quire folds; inner-split hyperparameters.
- **Models:** G (char 4-gram), SLOT, KN1–3, COPY1/COPY3 (EM copy-and-modify, W ∈ {5, 20, 100}), NAIBBE (la/it plaintext LMs, EVA cells only), and the line-start ONSET feature where lines exist.
- **Added: PCLM** (slot-normalised word-grammar likelihood). A Witten–Bell char 3-gram whose context also includes the position in the word (min(i, 8)) and whether the word length is short (≤ 4) or long. It is a properly normalised, context-free word model, like G.
- Every text is cut to 10 500 tokens (MS cells: their full ≈ 10.3–10.8 k). Non-MS texts use 150-token pseudo-pages, 8-page pseudo-quires and nested pseudo-bifolia.

## Conditions
- **(c) MS 408:** cells 1A, 2B, 3B (the target fingerprint).
- **Italian (primary real-language reference),** 9 texts. A download script lives in this folder (`fetch_italian.py`). Texts are git-ignored under `data/controls/italian/`; URLs and SHA256 are committed in `data/ITALIAN_MANIFEST.json`.
  - Already fetched: it_dante (Commedia), it_sidrach (14th-c. prose), it_ariosto (16th-c. verse).
  - New: Boccaccio *Decameron* (Giornate I–II, it.wikisource); Cennino Cennini *Il libro dell'arte* (c. 1400, workshop recipes, it.wikisource); *Fioretti di San Francesco* (14th c., it.wikisource); *Il libro della cucina del sec. XIV* (14th-c. ricettario, PG #33954); Dante *Vita nuova* (PG #71218); Matteo Villani *Cronica* vol. 1 (14th c., PG #69898).
  - All are public domain (PG: US public domain; Wikisource platform text CC BY-SA 4.0). Nothing is redistributed.
- **(a) h12 copy-modify engine (C0),** fitted per hand (1A, 2B, 3B) on all pages of that hand (`run_h12.fit`), 10 500 generated tokens each.
- **(b) Timm–Schinner self-citation, authors' Java code:**
  - authors' default parameters, seeds 1 and 2;
  - parameters fitted to MS 408 in the mechanisms stage (`data/mechanisms/selfcitation/fitted_s1/2`), regenerated with the Java code when a JDK is present;
  - the generator's own line breaks are kept, which enables ONSET.
- **Italian-based encodings,** applied to three plaintexts (Boccaccio, Cucina, Sidrach):
  - **(i) Naibbe** homophonic cipher (`mech_naibbe`, 78-card deck, standard respacing).
  - **(ii) Verbose syllabic cipher:** a rough syllabification (onset consonants + vowel nucleus; final consonants join the last syllable). Each syllable type maps to one fixed EVA string. Codes are the most frequent MS 408 2B within-word glyph 1–3-grams, assigned by frequency rank (frequent syllables get frequent/short codes). Word = the concatenation of its syllable codes; word boundaries are kept.
  - **(iii-a) Vowel removal:** word-internal vowels are dropped (an initial vowel is kept; a word that would be empty keeps its first letter).
  - **(iii-b) Scribal suspension:** words longer than 5 letters become their first 3 letters + last letter.

## Pre-registered discriminating statistics (bifolium folds; quire folds reported alongside)
- **D1, n-gram gain** = bits(KN1) − min(bits(KN2), bits(KN3)) (bits/word; negative means n-grams hurt).
- **D2, cache gain** = bits(KN1) − bits(COPY1).
- **D3, 5-word copy rate** = cross-fitted ML λ of COPY1 with W fixed at 5, with a 95 % page-bootstrap CI (500 draws).
- **D4, char-level dominance** = min over word models (KN1–3, COPY1, COPY3) − min(G, PCLM) (bits/word; positive means a context-free char model wins).
- **D5, char-model bits/glyph** = min(G, PCLM) bits/word ÷ mean (characters + 1).

**MS fingerprint:** the range [min, max] of each D over the three MS cells. A condition **matches on Dk** if its value lies within the MS range widened by δ: δ = 0.10 bits for D1, D2 and D4; 0.015 for D3; 0.15 for D5. It **reproduces the fingerprint** if it matches all five. Also reported: the standardised distance Σ_k ((x_k − MS mean_k)/δ_k)².

## Predictions
- **P1:** no plain Italian text reproduces the fingerprint. All 9 have D1 > 0 and D4 < 0.
- **P2:** at least one generator, (a) or (b), matches ≥ 4 of 5 stats.
- **P3:** Naibbe-Italian has D1 ≤ 0.1, but D2 and D3 fall below the MS range, so it does not reproduce.
- **P4:** the word-preserving syllabic cipher keeps D1 > 0.3, so it fails D1.
- **P5:** both abbreviation schemes keep D1 > 0.3 and fail D1.
- **P6:** the condition with the smallest distance is a generator, not an Italian encoding.

No translation or meaning claims.
