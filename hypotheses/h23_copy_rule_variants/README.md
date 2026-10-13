# h23: copy-rule variants, and what makes hand 2B distinct

This stage was pre-registered in [PREREG.md](PREREG.md) (commit 1d5d29c) before any computing. It makes no translation claims.

## Question
In h22, Naibbe-Italian with 5 % generic copying got 4 of the 5 statistics (4/5) but missed D4, the word-vs-character dominance: about −0.17, where the MS range is −0.07 … +0.18. This stage asks two things:
- Can a different copy rule raise the 5-word copy rate λ5 without pushing D4 down?
- What makes hand 2B distinct?

## Method
- **Text and cipher:** Naibbe-Italian on Boccaccio, with no nulls or shuffle.
- **Copy rules:** seven variants (see PREREG), none fitted to MS. Edit units come from the cell's own output.
  - `ref`: the h22 rule.
  - `heavy`: two edits per copy.
  - `slot`: prefix/suffix edits only.
  - `swap`: replace the final unit with a different final unit.
  - `inline`: copy only from the same line.
  - `prevline`: copy only from the previous line.
  - `unit`: splice in one unit from a recent token.
- **Copy rates:** c ∈ {0.03, 0.05, 0.10}.
- **Secondary:** syllabic cipher plus own-ciphertext nulls, every variant at c = 0.05.
- **Transfer:** the best 2 settings go to Cucina, Sidrach and Cennini.
- **Scoring:** the h20 five statistics. The primary scheme is bifolium folds.

## Results (bifolium folds)

| Naibbe-Boccaccio | n/5 | distance | λ5 | D4 | signal share |
|---|---|---|---|---|---|
| no copying | 3 | 9.0 | 0.007 | +0.02 | 1.00 |
| h22 rule (`ref`), c = .05 | 4 | 6.2 | 0.023 | −0.16 | 0.95 |
| **`swap`, c = .05** (best) | **5** | **3.0** | 0.023 | −0.06 | 0.95 |
| `swap`, c = .03 | 5 | 3.7 | 0.020 | −0.05 | 0.97 |
| `inline`, c = .03 (2nd) | 4 | 3.2 | 0.028 | −0.08 | 0.98 |
| `unit`, c = .03 / .05 / .10 | 4 | 3.4–3.6 | 0.016–0.029 | −0.03 … −0.10 | 0.90–0.97 |
| `heavy`, any c | 3–4 | 7.0–41.8 | | −0.18 … −0.44 | |

- **How the rules change D4:**
  - At each c, `swap` and `unit` keep D4 highest.
  - `heavy`, `slot` and `prevline` are no better than `ref`, or worse.
  - All rules collapse at c = 0.10, except `unit` and `swap` at c = .10 (4/5).
  - What hurts D4 is copying whole words, not copying as such. A suffix swap gives local repetition at the level of the word stem while keeping word models from gaining much.
- **Transfer, bifolium folds:**

| setting | Cennini | Cucina | Sidrach |
|---|---|---|---|
| `swap` c = .05 | 4/5 (2.96) | 4/5 (3.65) | 4/5 (3.69) |
| `inline` c = .03 | **5/5** (2.29) | 4/5 (2.42) | 4/5 (3.64) |

  - Every 4/5 transfer misses only D4, and only just: −0.071 … −0.127 against the bound of −0.07.
  - On quire folds, all 8 best and transferred cells reach 5/5.
- **Comparison with C0:** these distances, 2.3–3.7, lie inside the C0 cross-hand range of 1.9–6.0 (h21/h22). A cipher of Italian with a light suffix-swap copy layer is now about as close to MS as the MS-fitted engine.
- **Plaintext survival:** in the best settings, 95–98 % of tokens are untouched Naibbe ciphertext, so the plaintext would remain fully decodable for anyone holding the key. This shows only that such a text could carry a plaintext, not that MS 408 does.
- **Secondary, syllabic cipher:** it stays far away (distance ≥ 300, D4 ≤ −1.6) under every variant. Oracle decoding accuracy is 0.59 and MI is 0.90 of H. The syllabic cipher's problem is word-level predictability, and copying cannot fix that.

## Part B: hand 2B

|  | tokens | types | top-50 share | -edy | qo- | main section |
|---|---|---|---|---|---|---|
| 1A | 10.3k | 2864 | 0.37 | 0.002 | 0.09 | herbal 76 % |
| 2B | 10.7k | 2376 | **0.43** | **0.21** | **0.19** | biological 58 % |
| 3B | 10.8k | 3008 | 0.36 | 0.14 | 0.16 | stars 95 % |

- **Line-initial onsets:** 2B starts lines with q (19 %) and s (18 %); 1A with o, d and y; 3B with y, d, s and p.
- **Fingerprints of subsets** (D5 = bits per glyph; the full hands are 1A 1.94, 2B 1.77, 3B 1.84):
  - Size-matched, about 4.5k tokens: 2B biological 1.68, 2B non-biological 1.95, 2B first pages 1.86, 1A 1.97, 3B 1.94.
  - With -edy removed: 2B rises 1.77 → 1.89 (+0.12) and 3B by +0.07. 2B's D1 moves −0.13 → −0.18.
- **RB1 fails:** 2B's low bits/glyph sits in its biological pages. Its non-biological pages look like 1A and 3B. So 2B's distinctness is at least partly a section (biological) effect.
- **RB2 passes:** the -edy family carries much of it. Removing it raises 2B's D5 by 0.12 and makes D1 MS-typical (−0.18).
- Hand and section are confounded, so none of this is causal.

## Predictions

| | prediction | outcome |
|---|---|---|
| RA1 | some variant: D4 ≥ −0.07 with λ5 ≥ 0.022 | **pass** (`swap` c = .05) |
| RA2 | some Naibbe setting 5/5 on bifolium folds | **pass** (`swap` c = .03 and .05) |
| RA3 | best transfers ≥ 4/5 to all 3, 5/5 on ≥ 2 | **fail** (4/5 on all 3; 5/5 on 0, D4 just out) |
| RA4 | signal share ≥ 0.9 | **pass** (0.95) |
| RA5 | `unit` and `swap` have higher D4 than `ref` at every c | **pass** |
| RB1 | both 2B halves have lower D5 than 1A/3B | **fail** (only biological) |
| RB2 | no -edy: D5 +≥ 0.05 and D1 more negative | **pass** (+0.12; −0.05) |

## Verdict
- A Naibbe-type cipher of Italian, with a light suffix-swap copy layer (5 % of tokens) and no MS-fitted parameters, reproduces all five statistics on Boccaccio. It comes within the D4 boundary on three other Italian sources, at distances that match the MS-fitted C0 engine.
- So the h19/h20 likelihood fingerprint does **not** separate "a cipher of a natural language plus scribal copying" from a process generator. This weakens the fingerprint as evidence against meaningful text. It does not show that MS 408 is Italian or enciphered.
- Hand 2B's distinctness tracks the biological section and the -edy family.

## Limits
- Naibbe was designed with MS 408 in mind, and its glyph tables are MS-like, so it is not a neutral cipher.
- The grid is small (7 variants × 3 c values), on one source; the bifolium 5/5 sits near the D4 boundary.
- There is one seed per cell.
- The Part B subsets are small (about 4.5k tokens), and hand and section are confounded.
- Quire folds for the 2B-biological and 2B-sub subsets fall back to bifolium groups, because those subsets span fewer than 5 quires.

## Files
- Code and tests: `h23_lib.py`, `run_h23.py` (phase1/phase2), `summarise.py`, `test_h23.py`.
- Results: `results/fingerprints_*.csv`, `summary.json`, `search_best.json` and `cell_*.json`.
- Figure: `figures/copy_variants.png`.
- Per-token tables are git-ignored.
