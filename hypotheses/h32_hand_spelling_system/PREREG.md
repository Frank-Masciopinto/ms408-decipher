# h32 pre-registration: the shared spelling system between scribal hands

Written 2026-10-13 before any h32 result was computed. Builds on h11 (10 greedy string rules close 22.7 % ± 1.7 % of the herbal 1A vs 2B gap; first rule `-edy → -ol`), h12, h13–h15 (rule pairs do not share contexts raw; the Procrustes advantage is mostly shared stems) and h23/h24 (2B's distinctness is largely a biological-section effect). No translation is attempted or claimed.

## Data
ZL3b running text (P/C/R loci, as h09–h11), collapsed EVA units (`ch sh cth ckh cph cfh` as single units). Hands/sections from `data/quires.csv` via h11's loader. **Section-matched pairs only** for hand comparisons: herbal 1A vs herbal 2B (primary), herbal 1A vs herbal 3B. Baselines: same-hand cross-section (1A herbal ← 1A pharma, 2B herbal ← 2B biological, 3B herbal ← 3B stars), same-cell split halves (noise floor), and permuted-hand controls (herbal 1A+2B pages pooled, hand labels permuted at page level, sizes kept).

## Method
1. **Transducer.** Context-dependent unit rewrite rules `L s R → t` (s, t = 0–2 units; L/R = word boundary, one unit, or nothing). Candidates come from aligning frequent source types to their nearest target types (unit Levenshtein ≤ 2) on the training pages only, and keeping the edit operations with their context. Rules are chosen greedily by word-distribution JSD on training pages (up to 30), applied in order, and scored on held-out pages (5 random page halvings, same seeds as h11's `gap_closure`). Gap closed = (JS before − JS after)/JS before on the held-out halves. h11's greedy string rules are rerun on the same splits for a direct comparison.
2. **Same content.** After mapping 2B herbal text into 1A spelling with the learned rules: (a) Smith-Waterman local alignment (match +2 if mapped tokens equal, +1 if unit edit distance 1, mismatch −1, gap −2) between every 2B-herbal and 1A-herbal page, against 200 within-page token shuffles per pair; (b) shared mapped bigrams/trigrams across hands vs shuffled; (c) same-plant-family cross-hand page pairs (h17 `plant_ids.csv`, majority family per folio) vs different-family pairs on mapped word profiles, by permutation. Reference: the same statistics within hand 1A (herbal vs herbal, different pages).
3. **Phonetic-like or arbitrary.** Systematic = few rules carry most closure, the top rules recur across splits, context conditioning adds closure, and real hand labels beat permuted labels.

## Predictions (pass/fail)
* **P1** Section-matched transducer closure of herbal 1A ← 2B exceeds h11's 22.7 % (mean over 5 splits, and above it in ≥4/5 splits).
* **P2** That closure is larger than every same-hand cross-section closure and than the 95th percentile of the permuted-hand control.
* **P3** Remaining gap: even the best transducer leaves > 50 % of the hand gap (hands differ mostly in vocabulary, as h11 suggested).
* **S1 (same content, expected to fail)** Cross-hand mapped page pairs show more significant SW alignments (BH q < 0.05 against the shuffle null) than the within-1A reference rate, and/or same-family pairs are more similar than different-family pairs (perm p < 0.05).
* **Q1 (systematic)** ≥ 4 of the 5 top-5 rules recur in ≥ 3/5 splits; the first 5 rules carry ≥ 60 % of the 30-rule closure; context-conditioned rules beat context-free ones on held-out closure.

## Deviations policy
Any change will be listed in README under "Deviations".
