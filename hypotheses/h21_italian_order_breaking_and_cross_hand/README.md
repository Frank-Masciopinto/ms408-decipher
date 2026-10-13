# h21 — order-breaking Italian encodings and cross-hand C0

Pre-registered in [PREREG.md](PREREG.md) (commit 2408d3e) before any computing. No translation claims.

**Question.** h20 found that Italian keeps a word n-gram gain (D1 > 0) and that Naibbe-Italian lacks local repetition, while only the C0 engine fitted to MS reproduces the h19 fingerprint. (A) Can an Italian encoding that breaks word order but keeps local repetition reproduce the fingerprint, and how contrived must it be? (B) Is C0's match only by construction? Here the engine is fitted on one hand and scored against the other hands.

**Method.**
- **Part A.** Italian (Boccaccio, Libro della cucina, Sidrach, Cennini; about 10.5k tokens each) goes through a base step, which is plain text, the h20 word-preserving syllabic cipher, or Naibbe. Optional layers can be added on top:
  - recency-biased homophone suffix variants (K);
  - within-line word shuffle (9-word pseudo-lines);
  - null words drawn from the MS 2B token distribution, with a geometric count of mean r per word.
- Each condition gets the h20 five statistics D1–D5, scored with the same h19/h20 pipeline, folds and match rule (MS range ± δ, distance).
- There are 24 base cells. An 18-cell grid on Boccaccio (syll × K∈{2,4,8} × shuffle × r∈{0,.3,.7}) picks the 2 best settings by distance, which are then transferred to the other three sources.
- **Part B.** C0 is fitted on a single hand (seeds 20 and 21) and point-matched against each other hand. It is also fitted on the pooled other two hands ("notX") and point-matched against X.

## Results (bifolium folds; quire in `results/*_quire.csv`)

| condition | best n/5 | distance |
|---|---|---|
| Naibbe-it + nulls r=.5 (2 layers, 33 % nulls) | 3 | 5.3–6.2 |
| Naibbe-it + shuffle | 2 | 10.0–10.6 |
| best grid: syll + K8 + nulls r=.7 (3 layers, 41 % nulls) | 1 | 36.9 |
| best grid with shuffle (4 layers) | 1 | 40.9 |
| plain / syll + shuffle | 1–3 | 81–332 |
| grid transfer to Cucina, Sidrach, Cennini | 1–3 | — |
| C0 single-hand / pooled (all 12 fits, scored vs MS range) | 4–5 | 2.2–6.0 |

- **Shuffling.** It does remove the n-gram gain: D1 becomes −0.15 to −0.24, as in MS. But word unigram/cache models still beat character models by a lot (D4 −0.76 to −1.75 vs MS +0.03 to +0.08), and bits/glyph stay too high (2.2–2.5 vs 1.77–1.94).
- **Nulls and homophones.** These move D4 toward MS, but even at 41 % nulls D4 is still about −0.42.
- **Naibbe.** Naibbe fixes D4 and D5, but its copy rate stays too low (λ5 ≤ 0.016 vs 0.032–0.043).
- **Bifolium vs quire.** No setting reaches 4/5 on bifolium folds. On quire folds the MS range is wider, and one transfer cell, Cennini syll+K8+r0.7 (3 layers, 41 % nulls), technically reaches 5/5, though its distance is still 26.5.

**Part B, point match to each hand's own MS values (n/5):**

| fit \ target | 1A | 2B | 3B |
|---|---|---|---|
| 1A s20/s21 | 4/5 | 3/3 | 4/3 |
| 2B s20/s21 | 5/5 | 3/4 | 4/3 |
| 3B s20/s21 | 5/4 | 3/3 | 5/5 |
| notX s20/s21 (vs X) | 4/5 | 3/3 | 3/1 |

- Against the pooled MS range (the h20 rule), all 12 C0 fits match at least 4/5, and 10 match 5/5.
- Against a single hand's point values, 2B is never matched at 4/5 by an engine that never saw 2B, and the not3B fits fail on 3B. C0 reproduces "an MS-like" fingerprint, but not reliably a specific unseen hand.

## Predictions

| | prediction | outcome |
|---|---|---|
| PA1 | shuffle: D1 ≤ 0.1 but D4 < −0.5; no base cell 5/5 | **pass** |
| PA2 | no single-mechanism cell ≥ 4/5 | **pass** (max 3) |
| PA3 | some grid setting ≥ 4/5; 5/5 needs ≥ 3 layers; best transfers ≥ 4/5 on ≥ 2/3 sources | **fail** (grid max 2/5; transfers 1–3/5) |
| PB1 | single-hand C0 ≥ 4/5 on other hand in ≥ 4/6 off-diagonal pairs | **fail** (seed 20: 4/6, seed 21: 2/6) |
| PB2 | pooled C0 ≥ 4/5 on its target, all 3 targets, both seeds | **fail** (1A yes; 2B 3, 3B 3 and 1) |
| PB3 | cross-hand C0 distance < best Italian encoding | **pass** (pooled 2.2–6.0, single 2.3–4.6 vs 5.3) |

**Verdict.**
- **Part A.** Within this family (shuffle, nulls, homophones, Naibbe, up to 4 layers and 41 % nulls), no Italian encoding reproduces the fingerprint on bifolium folds. The cheapest close setting is Naibbe plus one-third nulls, at 3/5. Breaking order is easy; what Italian encodings cannot get is the combination of high local copying with character-level dominance and low bits/glyph.
- **Part B.** C0's MS-range match survives fitting on other hands, so it is not purely circular. But hand-specific point matches are weaker, especially for 2B.

**Limits.**
- The grid is small (18 settings), on one source.
- Nulls are drawn from MS 2B tokens, which leaks MS statistics into the "Italian" encodings and flatters them.
- There is no Latin or other source.
- Point matching uses the same δ as the range rule.
- The quire 5/5 cell comes from the wider quire range.

**Files.**
- Code: `h21_lib.py`, `run_h21.py` (phase1/phase2), `summarise.py` and `test_h21.py`.
- Results: `results/partA_*.csv`, `partB_*.csv`, `partB_point_*.csv`, `summary.json`, `search_best.json`, `cell_*.json`, and `figures/fingerprint.png`. Per-token tables are not committed.
