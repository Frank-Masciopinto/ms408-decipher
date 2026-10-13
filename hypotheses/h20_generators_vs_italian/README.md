# h20: generators and Italian-based encodings vs the MS 408 likelihood fingerprint

Pre-registration: `PREREG.md` (38ae92c). Pipeline: h19 unchanged (`run_split`, same folds, models and seeds), plus **PCLM**, a position-conditioned char LM (a slot-normalised, context-free word-grammar likelihood).

**Running it:**
- `python fetch_italian.py` (Italian texts → `data/controls/italian/`, git-ignored; URLs and SHA256 in `data/ITALIAN_MANIFEST.json`).
- `python run_h20.py` (≈ 11 min on 7 processes), then `python summarise.py`.
- Tests: `pytest test_h20.py` (4).
- `rapidfuzz` is now a project dependency (`pyproject.toml`, `requirements.txt`).

**Committed outputs:**
- `results/fingerprint_table.csv` (D1–D5, match flags and distance for 31 conditions × 2 fold schemes, plus all model bits);
- `results/cell_*.json` (fitted parameters per fold, cross-fitted λ at W = 5 and W = 100);
- `results/summary.json`;
- `results/encoding_info.json`;
- `figures/fingerprint.png`.

Per-token tables are local only: they contain transcription and control words.

**Positional and distributional facts only. No translation or meaning claims.**

## Conditions (10 500 tokens each; MS cells ≈ 10.3–10.8 k)
- **MS 408:** 1A, 2B, 3B.
- **Italian, 9 texts:**
  - Dante, *Commedia* and *Vita nuova*;
  - *Libro di Sidrach*;
  - Ariosto;
  - Boccaccio, *Decameron* I–II;
  - Cennini, *Libro dell'arte* (c. 1400 recipes);
  - *Fioretti*;
  - *Libro della cucina* (14th-c. ricettario);
  - M. Villani, *Cronica*.
- **h12 C0 copy-modify engine,** fitted per hand (fit distance 2.6–3.3, ≈ 12 s each).
- **Timm–Schinner self-citation:** authors' Java output; default and MS-fitted parameters, 2 seeds each, with their own line breaks.
- **Italian encodings** of Boccaccio, Cucina and Sidrach:
  - Naibbe;
  - a word-preserving syllabic cipher (501–957 syllable types → MS 2B unit 1–3-grams);
  - vowel removal;
  - scribal suspension.

## Fingerprint (bifolium folds; MS range in bold)
| condition (mean of group) | D1 n-gram gain | D2 cache gain | D3 λ(W = 5) | D4 char dominance | D5 char bits/glyph | stats matched (of 5) |
|---|---|---|---|---|---|---|
| **MS 408 (1A/2B/3B)** | **−0.18 … −0.13** | **0.23 … 0.27** | **0.032 … 0.043** | **+0.03 … +0.08** | **1.77 … 1.94** | 5 |
| Italian, 9 texts | +0.24 … +1.42 (mean 0.77) | 0.12 … 0.52 | 0.007 … 0.039 | −2.48 … −0.76 | 2.01 … 2.48 | 0–2 (none reproduces) |
| C0 engine per hand | −0.26 … −0.25 | 0.31 … 0.32 | 0.040 … 0.049 | +0.02 … +0.11 | 1.93 … 2.09 | 4, **5, 5** (2B, 3B reproduce) |
| self-citation (4 runs) | −0.23 … −0.08 | 0.34 … 0.55 | 0.037 … 0.069 | −0.45 … −0.25 | 1.77 … 1.87 | 2–4 |
| Naibbe(Italian) | −0.21 … −0.17 | 0.04 … 0.05 | 0.007 … 0.008 | −0.02 … +0.02 | 1.77 | 3 |
| syllabic cipher(Italian) | +0.46 … +1.42 | 0.14 … 0.41 | 0.010 … 0.037 | −3.06 … −1.87 | 2.20 … 2.52 | 1 |
| no vowels(Italian) | +0.25 … +1.25 | 0.30 … 0.61 | 0.063 … 0.152 | −1.55 … −0.52 | 2.31 … 2.68 | 0–1 |
| suspension(Italian) | +0.45 … +1.40 | 0.31 … 0.69 | 0.041 … 0.101 | −1.72 … −0.74 | 2.04 … 2.39 | 0–3 |

**Ranking and quire folds:**
- **Closest to MS** (standardised distance): C0-2B 2.3, C0-3B 2.4, C0-1A 4.3, Naibbe-Sidrach 8.7, Naibbe-Boccaccio 9.0. Self-citation is next at 10.3–39.
- **Quire folds:** the MS range is wider because 3B has only 2 quires (D2 up to 1.12, D4 down to −0.58). There, C0 1A/2B/3B and three of the four self-citation runs (default s2, fitted s1, fitted s2) reproduce. No Italian text or Italian encoding does.

**What each condition misses:**
- **Plain Italian:** word n-grams always help (D1 > 0) and word models always beat char models (D4 ≤ −0.76). It misses on D1, D4 and usually D5. The ricettario *Cucina* is the most formulaic (D1 = 1.42); a recipe genre makes Italian *more* n-gram-predictable, not less.
- **Naibbe:** respacing removes word context, so D1 < 0 and D4 ≈ 0, as in MS. But the cache gain (0.04) and the 5-word copy rate (0.007) are far below MS.
- **Syllabic cipher, vowel removal, suspension:** they keep the Italian word sequence, so the n-gram gain survives (D1 0.25–1.42), and they move bits/glyph *away* from MS (2.0–2.7).
- **Self-citation:** matches D1 and D3 but has too much cache (D2 0.34–0.55) and is word-model-dominated (D4 < 0).
- **C0 copy-modify engine:** comes closest. Its slight excesses are D1 (−0.26 vs MS −0.18, inside δ) and D2 (0.32, inside δ).

## Verdicts
| | Prediction | Result |
|---|---|---|
| P1 | no Italian text reproduces; all D1 > 0 and D4 < 0 | **pass** |
| P2 | a generator matches ≥ 4/5 | **pass** (C0 2B and 3B 5/5; self-citation fitted s1 4/5) |
| P3 | Naibbe-Italian: D1 ≤ 0.1, but D2 and D3 below MS, so no reproduction | **pass** |
| P4 | syllabic cipher keeps D1 > 0.3 and fails D1 | **pass** (0.46–1.42) |
| P5 | abbreviations keep D1 > 0.3 and fail D1 | **fail** on the threshold (no-vowel Boccaccio D1 = 0.25), though all six still fail the D1 match |
| P6 | the closest condition is a generator | **pass** (C0-2B) |

**Answer to the question:**
- Of the conditions tested, only **text generated from a per-hand word grammar with copy-and-modify** reproduces MS 408's held-out likelihood fingerprint. That fingerprint is: no n-gram gain, a cache gain of real-text size, a 5-word copy rate of 0.03–0.04, and a context-free char model at least as good as any word model.
- Plain Italian of every genre tried, and the three word-preserving Italian encodings, all keep a strong word-sequence signal that MS lacks.
- Naibbe-Italian loses that signal but also loses the local repetition MS has.

This does not show that MS 408 *is* generated text. It shows that these Italian-based hypotheses, in these forms, do not produce its likelihood profile.

## Limits
- **Circularity:** the C0 engine and the fitted self-citation parameters were fitted to MS 408 (on other statistics), so their closeness is partly by construction. The Italian conditions were not tuned to MS at all.
- **Simple encodings:** one syllabification, one codebook, two abbreviation rules. Homophonic, null-padded or reordered encodings of Italian, which would break word n-grams, were not tried. Neither were real medieval abbreviation systems (tittles, sigla), only their effect on word forms.
- **Text sizes and editions:** 10.5 k tokens per condition with the h19 smoothing choices. The Italian texts are modern editions with normalised spelling and accents folded by the normaliser. Wikisource chapter order is alphabetical for *Fioretti*, which slightly perturbs cross-chapter context only.
- **Tolerances:** the δ tolerances were pre-registered but are judgement calls. The distance column is given so other tolerances can be applied.
- **Self-citation runs:** reused from the cached authors'-Java outputs, which are deterministic per seed.
