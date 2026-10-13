# h26: Naibbe-structure cipher with tables from a neutral word-internal glyph grammar (pre-registration)

Written and committed before any h26 computing. No translation claims.

## Background
h25 tested Naibbe's structure with random, structureless tables. It got closer than other neutral ciphers (best distance 8.9) but never reached 5/5. Rendered in EVA-like units, it lost word-vs-char dominance (D4). The suspected missing ingredient is the internal glyph grammar of Naibbe's MS-derived tables. Here the cipher's code tables are drawn from a word-internal glyph grammar that is not MS-derived (neutral), with an MS-derived grammar as a positive control.

## Cipher
- **Engine:** the h25 NH engine: `NaibbeCipher` with 6 tables, Naibbe card weights, p_unigram 17/36, unambiguous-bigram rejection (≤ 50 retries).
- **Code tables:** generated from a grammar G:
  - unigram codes = whole words from G;
  - prefix codes = word *starts* from G (the first slots / first glyphs);
  - suffix codes = word *ends* from G (the last slots / last glyphs).
  
  So prefix + suffix follows G's order, as in Naibbe. Codes are distinct within each (state, table).
- **Building:** tables are built **serially** before any parallel scoring (this fixes the h25 race).

## Grammars
- **RS: random slot grammar.**
  - Made-up alphabet of 20 glyphs.
  - S ordered slots. Each slot has a random inventory of 2–6 glyphs, with probabilities drawn from Dirichlet(α).
  - Each slot is filled with probability p_fill. A unigram word uses all slots; a prefix uses slots 1..⌈S/2⌉; a suffix uses the rest. Empty results are resampled.
  - Base: S = 6, α = 0.5, p_fill = 0.7.
  - Property variants, one at a time:
    - entropy: `loEnt` α = 0.15, `hiEnt` α = 3;
    - rigidity: `loose` p_fill = 0.45, `rigid` p_fill = 0.9;
    - length: `short` S = 4, `long` S = 8.
- **LAT:** a glyph bigram chain from Latin spelling (`la_pliny` control text, word-internal letter bigrams, with start and end states). Letters are mapped to made-up glyphs through a random bijection. Prefix = sampled 2–3-glyph word starts; suffix = 2–4-glyph word ends; unigram = whole sampled words of 2–7 glyphs.
- **MS (positive control):** the same chain construction, trained on MS hand-2B words in EVA units and kept in EVA.
- **Rendering:** neutral grammars (RS, LAT) are rendered EVA-like with a random unit map (as in h25, not by MS frequency) and scored with EVA segmentation. This is the primary rendering. RS-base is also scored with char segmentation.

## Grid (Boccaccio unless stated; copy ∈ {none, swap c = .05})
- RS-base, LAT, MS: 5 grammar seeds each → 30 cells.
- RS property variants (6): 3 seeds → 36 cells.
- RS-base char segmentation: 5 seeds × none → 5 cells.
- **Transfer:** the best neutral (grammar, copy) setting and the MS control, each × Cucina, Sidrach, Cennini × 3 seeds → 18 cells.
- **Seeds:** reduced first if load is high, and reported.

## Measures
- **Statistics:** the h20 statistics D1–D5, match within MS range ± δ, distance. Bifolium is primary; quire is also reported.
- **Grammar properties,** measured on each cell's ciphertext in EVA units:
  - per-unit entropy H1;
  - positional rigidity = 1 − H(unit | position) / H1;
  - mean word length in units.
- **Plaintext survival:** uniquely-decodable share, as in h25.

## Predictions
- **G1 (positive control):** MS grammar, with or without swap, reaches ≥ 4/5 in ≥ 60 % of seeds, and its mean distance is ≤ 10. Otherwise the construction itself is suspect.
- **G2 (main question):** "any orderly grammar suffices" if RS-base or LAT, in its best copy condition, reaches ≥ 4/5 in ≥ 60 % of seeds **and** has a mean distance within 2× the MS-control mean. Otherwise "only an MS-like grammar".
- **G3:** every grammar beats h25's structureless NH under EVA rendering (h25 base mean 75.6 without copy and 67.5 with swap).
- **G4:** of the three properties, positional rigidity has the largest |Spearman ρ| with distance across all Boccaccio cells.
- **G5:** decodable share ≥ 0.8 at the best neutral setting.
