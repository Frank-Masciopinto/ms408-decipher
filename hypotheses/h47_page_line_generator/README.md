# h47: Page-and-Line-Aware Non-Semantic Generator (`page_line_copier`)

Pre-registration: `PREREG.md`. This experiment tests whether adding explicit line-edge
slot conditioning (`h30`/`h34`) and partial lookback-buffer reset at folio boundaries
(`rho_keep = 0.15`, `W_buf = 90`) to the `h39` non-semantic copier architecture allows a
single mechanical generator (`page_line_copier`) to simultaneously pass all six manuscript
structural benchmarks (`B1`–`B6`) across hands `1A`, `2B`, and `3B` without semantic content.

## Verdict and Predictions (`U1`–`U3`)

- Overall verdict: **supported**
- **U1** (`page_line_copier` on Hand `2B` passes at least `5/6` benchmarks `B1`–`B6`): **pass** (`6/6` passed on `2B`).
- **U2** (`page_line_copier` passes at least `5/6` benchmarks on at least two of `1A`, `2B`, `3B`): **pass** (`1A`: `6/6`, `2B`: `6/6`, `3B`: `6/6` [`5/6` if `d=80` unscored is counted strictly on `3B`]).
- **U3** (Previous `h39` best generators pass `<= 3/6` when evaluated on all six simultaneously): **pass** (`h39_native_tuned_2B` passes `1/6`; `h39_C0_graph_2B` passes `2/6`).

## Summary Table (`B1`–`B6` Pass/Fail)

| Stream | Hand | Tokens | Lines | Folios | B1 (h20 5/5) | B2 (S & J) | B3 (Line Edge) | B4 (Page Drop) | B5 (Page Burst) | B6 (Page Decay) | Total Passed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `page_line_copier_1A` | `1A` | 10326 | 1477 | 112 | **pass** (5/5) | **pass** | **pass** | **pass** | **pass** | **pass** (`page`) | **6/6** |
| `page_line_copier_2B` | `2B` | 10494 | 1197 | 46 | **pass** (5/5) | **pass** | **pass** | **pass** | **pass** | **pass** (`page`) | **6/6** |
| `page_line_copier_3B` | `3B` | 10493 | 1069 | 28 | **pass** (5/5) | **pass** | **pass** | **pass (d160; d80 unscored)** | **pass** | **pass** (`page`) | **6/6** |
| `h39_native_tuned_2B` | `2B` | 10494 | 1197 | 46 | **fail** (1/5) | **fail** | **fail** | **fail** | **fail** | **pass** (`page`) | **1/6** |
| `h39_C0_graph_2B` | `2B` | 10494 | 1197 | 46 | **pass** (5/5) | **pass** | **fail** | **fail** | **fail** | **fail** (`none`) | **2/6** |

## Detailed Benchmark Metrics

### B1: `h20` Bifolium 5-Metric Fingerprint (`D1`–`D5`)

| Stream | Match | D1 (KN2-KN1) | D2 (alpha2) | D3 (lam5) | D4 (line delta) | D5 (char H) |
|---|---|---|---|---|---|---|
| `page_line_copier_1A` | 5/5 (**pass**) | -0.2682 | 0.2491 | 0.0389 | -0.0692 | 2.0155 |
| `page_line_copier_2B` | 5/5 (**pass**) | -0.2587 | 0.2239 | 0.0313 | 0.0552 | 1.8678 |
| `page_line_copier_3B` | 5/5 (**pass**) | -0.2624 | 0.2386 | 0.0246 | -0.0609 | 1.8633 |
| `h39_native_tuned_2B` | 1/5 (**fail**) | -0.1879 | 5.4273 | 0.2296 | -5.0753 | 2.7045 |
| `h39_C0_graph_2B` | 5/5 (**pass**) | -0.2605 | 0.2656 | 0.0376 | 0.1107 | 1.9099 |

### B2: `h40` Interior Space Predictability $S$ and Cross-Word Junction MI $J$

| Stream | $S_{\text{interior}}$ | Target $S_{\text{MS}} \pm 0.02$ | $S$ in band | $J$ (bits) | $J \ge 0.060$ | B2 Pass |
|---|---|---|---|---|---|---|
| `page_line_copier_1A` | 0.7419 | [0.7300, 0.7900] | pass | 0.0673 | pass | **pass** |
| `page_line_copier_2B` | 0.8152 | [0.7910, 0.8470] | pass | 0.1157 | pass | **pass** |
| `page_line_copier_3B` | 0.8300 | [0.7950, 0.8670] | pass | 0.2064 | pass | **pass** |
| `h39_native_tuned_2B` | 0.5896 | [0.7910, 0.8470] | fail | 0.1330 | pass | **fail** |
| `h39_C0_graph_2B` | 0.8152 | [0.7910, 0.8470] | pass | 0.1778 | pass | **pass** |

### B3: `h30` / `h34` Line-Edge Asymmetry and Line-Break Junction Reset

| Stream | Onset Excess ($z$) | End Excess ($z$) | Cross/Within Ratio | Para Initial $z$ | B3 Pass |
|---|---|---|---|---|---|
| `page_line_copier_1A` | 0.1994 (303.6) | 0.1367 (216.2) | -0.0276 | 72.2 | **pass** |
| `page_line_copier_2B` | 0.1642 (279.0) | 0.0300 (51.9) | -0.0337 | 77.4 | **pass** |
| `page_line_copier_3B` | 0.2067 (307.3) | 0.0908 (134.5) | -0.0195 | 184.4 | **pass** |
| `h39_native_tuned_2B` | 0.0001 (0.2) | -0.0001 (-0.1) | 0.7658 | -1.1 | **fail** |
| `h39_C0_graph_2B` | 0.0001 (0.1) | 0.0002 (0.3) | 1.0209 | -0.6 | **fail** |

### B4: `h43` Page-Boundary Drop at $d = 80$ and $d = 160$

| Stream | $d=80$ Scored ($n_{\text{cross}}$) | $d=80$ Effect vs Null p95 | $d=80$ Pass | $d=160$ Effect vs Null p95 | $d=160$ Pass | B4 Pass |
|---|---|---|---|---|---|---|
| `page_line_copier_1A` | True (45) | 0.1279 vs 0.0816 | pass | null vs null | fail | **pass** |
| `page_line_copier_2B` | True (40) | 0.1412 vs 0.0557 | pass | 0.1130 vs 0.0526 | pass | **pass** |
| `page_line_copier_3B` | False (23) | 0.1174 vs 0.0416 | fail | 0.1285 vs 0.0606 | pass | **pass** |
| `h39_native_tuned_2B` | True (40) | 0.0006 vs 0.0426 | fail | -0.0020 vs 0.0182 | fail | **fail** |
| `h39_C0_graph_2B` | True (40) | 0.0038 vs 0.0155 | fail | -0.0014 vs 0.0200 | fail | **fail** |

### B5: `h44` Page-Scale Burstiness (`h41_lib.burst`)

| Stream | Orig | In-Page | In-Quire | Full | Excess (`orig - full`) | `in_page - full` | `in_quire - full` | Quire Share | B5 Pass |
|---|---|---|---|---|---|---|---|---|---|
| `page_line_copier_1A` | 4.5277 | 4.6463 | 3.5762 | 3.5655 | 0.9622 | 1.0808 | 0.0107 | 0.0112 | **pass** |
| `page_line_copier_2B` | 5.4641 | 5.6505 | 3.5430 | 3.3977 | 2.0664 | 2.2529 | 0.1453 | 0.0703 | **pass** |
| `page_line_copier_3B` | 6.6170 | 7.0474 | 3.5700 | 3.6396 | 2.9774 | 3.4078 | -0.0696 | -0.0234 | **pass** |
| `h39_native_tuned_2B` | 9.2321 | 7.4816 | 5.1178 | 4.4701 | 4.7620 | 3.0115 | 0.6477 | 0.1360 | **fail** |
| `h39_C0_graph_2B` | 3.7373 | 3.7162 | 3.5957 | 3.5693 | 0.1680 | 0.1469 | 0.0264 | 0.1570 | **fail** |

### B6: `h42` Near-Repeat Page-Decay Profile

| Stream | Shape | Decay Point | Lag 1 | Lag 2–5 | Lag 6–20 | Lag 21–100 | Lag 101–500 | Lag 501–1000 | B6 Pass |
|---|---|---|---|---|---|---|---|---|---|
| `page_line_copier_1A` | `page` | `21-100` | 0.0583 | 0.0568 | 0.0515 | 0.0430 | 0.0505 | 0.0455 | **pass** |
| `page_line_copier_2B` | `page` | `21-100` | 0.0595 | 0.0622 | 0.0578 | 0.0418 | 0.0428 | 0.0430 | **pass** |
| `page_line_copier_3B` | `page` | `21-100` | 0.0408 | 0.0515 | 0.0457 | 0.0365 | 0.0335 | 0.0335 | **pass** |
| `h39_native_tuned_2B` | `page` | `101-500` | 0.0722 | 0.0660 | 0.0705 | 0.0585 | 0.0325 | 0.0312 | **pass** |
| `h39_C0_graph_2B` | `none` | `None` | 0.0355 | 0.0428 | 0.0408 | 0.0372 | 0.0428 | 0.0405 | **fail** |

## Reproduction

```bash
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python3 hypotheses/h47_page_line_generator/run_h47.py
python3 hypotheses/h47_page_line_generator/summarise.py
pytest hypotheses/h47_page_line_generator/test_h47.py
```

Environment: Python `3.12.3`, NumPy `2.5.4`, seed `47`.
