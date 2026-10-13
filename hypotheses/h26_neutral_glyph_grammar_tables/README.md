# h26: Naibbe-structure cipher with tables from a word-internal glyph grammar

This stage was pre-registered in [PREREG.md](PREREG.md) (commit b66763a) before any computing. It makes no translation claims.

## Question
h25 showed that Naibbe's structure with random, structureless tables does not reach the MS fingerprint. This stage asks:
- Is any orderly word-internal glyph grammar in the tables enough, or only an MS-like one?
- Which grammar property matters?

## Method
- **Engine:** the h25 NH engine (6 homophone tables, Naibbe card weights, respacing, prefix + suffix words). Tables are built serially from a grammar; scoring runs in parallel.
- **Grammars:**
  - **RS:** random slot grammars (base S = 6, α = 0.5, p_fill = 0.7), with variants for entropy (`loEnt`/`hiEnt`), rigidity (`loose`/`rigid`) and length (`short`/`long`).
  - **LAT:** a glyph-bigram chain from Latin spelling. The text is Pliny, *Naturalis Historia* XX–XXVII (`la_pliny_herbal`; the pre-registration's `la_pliny` id does not exist). Letters map to made-up glyphs.
  - **MS:** positive control. The same chain construction trained on MS-2B words in EVA units.
- **Rendering:** neutral grammars were rendered EVA-like with a random unit map. RS-base was also scored with char segmentation.
- **Copying:** none, or `swap` at c = .05.
- **Seeds:** 5 for RS/LAT/MS and 3 for the variants. The machine load was lower this time, so the seed counts were not reduced.
- **Added after the main runs (diagnostic anchor, not pre-registered):** the author's **real Naibbe tables** in the same engine, 5 seeds. This checks whether the engine or the tables are at fault.
- **Transfer:** RS-base + swap (the best of the pre-registered RS-base/LAT) and the MS control (no copying) went to Cucina, Sidrach and Cennini × 3 seeds. `loose` + swap, the best neutral variant overall, was not transferred.

## Results (bifolium folds, Boccaccio unless stated, EVA-rendered)

| tables | copy | n | ≥ 4/5 | 5/5 | distance, mean [95 % CI] | D2 | λ5 | D4 | D5 | decodable |
|---|---|---|---|---|---|---|---|---|---|---|
| **real Naibbe tables (anchor)** | swap | 5 | **100 %** | **20 %** | **3.43 [3.01, 3.86]** | 0.21 | 0.022 | −0.08 | 1.83 | |
| real Naibbe tables (anchor) | none | 5 | 0 | 0 | 8.59 [7.74, 9.43] | 0.05 | 0.008 | +0.02 | 1.78 | |
| MS-trained chain (positive control) | none | 5 | 0 | 0 | 94.0 [69.3, 118.6] | 0.02 | 0.002 | −0.83 | 1.56 | 0.72 |
| MS-trained chain | swap | 5 | 20 % | 0 | 103.0 [71.4, 134.6] | 0.23 | 0.016 | −0.93 | 1.62 | 0.72 |
| RS base | swap | 5 | 0 | 0 | 123.8 | 0.04 | 0.006 | −0.88 | 1.28 | 0.48 |
| RS `loose` (best neutral) | swap | 3 | 0 | 0 | 24.8 | 0.06 | 0.010 | −0.29 | 1.54 | 0.40 |
| RS `short` | swap | 3 | 0 | 0 | 37.0 | 0.02 | 0.004 | −0.10 | 1.17 | 0.19 |
| RS `loEnt` / `hiEnt` / `rigid` | swap | 3 | 0 | 0 | 108 / 125 / 158 | | | −0.6 … −1.0 | | |
| RS `long` | swap | 3 | 0 | 0 | 678 | | | −2.4 | | |
| LAT chain | swap | 5 | 0 | 0 | 1005 | 0.17 | 0.010 | −3.0 | 1.65 | 0.93 |
| RS base, char segmentation | none | 5 | 0 | 0 | 17.7 | 0.04 | 0.012 | −0.24 | 1.70 | 0.48 |

- **Overall:**
  - Only the real Naibbe tables give ≥ 4/5 or 5/5 (5/5 in 1 of 5 seeds on bifolium folds, 5 of 5 on quire folds).
  - Apart from them, a single MS-chain seed reaches 4/5.
  - No grammar-generated table reaches 5/5 on either fold scheme.
- **Transfer** (3 seeds each): MS chain 90–93 and RS-base + swap 108–113 on Cucina, Sidrach and Cennini, all 0 % at ≥ 4/5.
- **The engine is not the problem:** with the author's tables it reproduces the h24 result (3.43 vs 3.61).
- **The positive control fails too.** Tables sampled from an MS-trained glyph chain are as far off as neutral grammars. The usual failure is word-vs-char dominance: D4 ≈ −0.8 against MS +0.03 … +0.08. MS-like *glyph statistics* in the codes are therefore not enough. What Naibbe's hand-built tables add is *how* their codes are chosen:
  - short, highly regular unigram words, and prefix/suffix pieces that make recurring word-shaped combinations;
  - few, unrelated-looking homophones per letter.
  
  This keeps character models good *per word*.
- **Which grammar property matters:** Spearman ρ with distance, over the 66 Boccaccio EVA cells (real-Naibbe anchor excluded):

| property | ρ |
|---|---|
| mean word length | **+0.85** |
| positional rigidity | −0.37 |
| per-unit entropy | +0.22 |

  Shorter rendered words, as in `loose` and `short`, come closest. Rigidity helps only weakly.
- **Plaintext survival:** the closest neutral settings are also the least decodable. `loose` gives 0.40 and `short` 0.19, because short codes collide. LAT is 0.93 decodable but very far off. There is a trade-off: closeness bought with short codes costs decodability.

## Predictions

| | prediction | outcome |
|---|---|---|
| G1 | MS-grammar control ≥ 4/5 in ≥ 60 % of seeds, distance ≤ 10 | **fail** (20 %, 94–103), so the chain construction cannot rebuild Naibbe-like tables |
| G2 | RS-base or LAT ≥ 4/5 in ≥ 60 %, within 2× of the MS control | **fail** (0 %; 124 vs 94): no orderly grammar suffices, and the sampled MS-like one does not either |
| G3 | every grammar beats h25's structureless NH under EVA rendering (75.6 / 67.5) | **fail** (`loose`, `short` yes; RS base, `rigid`, `long`, LAT no) |
| G4 | rigidity has the largest \|ρ\| | **fail** (mean word length, ρ +0.85) |
| G5 | best neutral decodable ≥ 0.8 | **fail** (RS-base 0.48; `loose` 0.40) |

## Verdict
- **No word-internal glyph grammar sampled at random reproduces the fingerprint**: neither a neutral one (RS, Latin-spelling chain) nor an MS-trained chain. All of them miss mainly on word-vs-char dominance.
- **Only the author's hand-designed Naibbe tables do**, under the same engine (3.43, ≥ 4/5 in 5/5 seeds).
- So "Naibbe-like design plus some orderly grammar" is not enough. The match depends on specific, hand-tuned table choices that were made with MS 408's word shapes in view. That weakens the h23 result as evidence that *a natural-language cipher* would naturally look like MS 408.
- The strongest single property is rendered word length.

## Limits
- Grammar families are simple (slot grammars and bigram chains). Prefix and suffix pieces are sampled independently, which is unlike Naibbe's complementary pieces.
- The EVA rendering uses one random unit map per seed; LAT words come out long once rendered.
- Variants have 3 seeds.
- The real-Naibbe anchor was added after the pre-registration as a diagnostic.
- Only RS-base + swap and the MS control were transferred.

## Files
- Code and tests: `h26_lib.py`, `run_h26.py` (phase1 / anchor / phase2), `summarise.py`, `test_h26.py`.
- `tables/`: the generated cipher tables.
- Results: `results/fingerprints_*.csv`, `groups_*.csv`, `summary.json`, `transfer_settings.json`, `cell_*.json`.
- Figure: `figures/grammar_tables.png`.
