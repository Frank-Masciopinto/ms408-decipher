# h12 pre-registration: per-hand copy-and-modify generators (committed before any fit)

**Engine.** The repo's no-plaintext copy-modify control C0 (`mech_hybrid.generate` with `GrammarInnovator`; innovations from a slot-bigram grammar `mech_hybrid_run.Ctx`, 6 engine parameters fitted by `mech_hybrid_run.fit_variant`: random search + local perturbation, objective = z-distance on the 12 `FIT_SET` metrics, 2 fit seeds).
**Profiling (done before this commit, on hand 1A, 10,326 tokens):** grammar fit 0.53 s, one generation 0.16 s, metric vector 0.13 s, jackknife SE 0.8 s, so ~0.6 s per candidate and ~2 min per serial fit with the default 120 + 3×30 candidates. Speed-up used: fork-based multiprocessing (`controls_ci.pmap`, 8 cores) and a reduced search (60 random + 3×10 local). No change to the engine code is needed.

**Cells (hand × Currier language):** 1A, 2B, 3B, 4 (≥ 2,400 running-text tokens); 5B and singletons dropped.
**Folds:** within each cell, 3 bifolium folds (`msdecipher.quires.group_folds(level="bifolium")`), and 3 quire folds for cells with ≥ 3 quires (1A, 2B). Train on the cell's training pages (in page order), test on its held-out pages.
**Models generated for each held-out test set (n = test tokens, 3 generation seeds):**
* OWN: per-cell generator (grammar + engine fitted on that cell's training pages);
* POOLED: one generator fitted on the training pages of all cells of the same fold index together;
* SHUF: generator fitted on a random set of training pages from all cells with the same token count as the cell's training set (cell labels shuffled);
* CROSS: each other cell's OWN generator;
* MAPPED (1A ← 2B and 2B ← 1A only): CROSS output rewritten with up to 10 greedy rewrite rules (h11 `greedy_rules`) learned on the two cells' training pages.
**Scores against the held-out real text:** absolute z on unit h2, mean word length, Zipf s, Heaps β (z scale = jackknife SE of the test set with a 2 % floor); overall RMS z on the 12 FIT_SET metrics; top-word profile = JS (bits) between the generated and real distributions over the real test's top-100 words + "other".
**Predictions:**
* P1: OWN beats POOLED (lower RMS z and lower top-word JS) for each of 1A, 2B, 3B, averaged over folds.
* P2: OWN beats SHUF on the same scores.
* P3: CROSS is worse than OWN, and MAPPED closes ≥ 20 % but < 50 % of the top-word JS gap (CROSS − OWN) for 1A ← 2B and 2B ← 1A: one system plus a partial orthographic mapping (h11 closed 22.7 % of the real-text gap).
* P4: fitted engine parameters (p_copy, window, p_prev, op mix) overlap across hands (fold ranges overlap), i.e. the same copy-modify process with different vocabularies/spelling.
Decision: a prediction "holds" if it holds for every listed cell / pair in the fold mean, with the fold-wise sign test reported.
