# h39: graph-preserving re-spelling (A) and tuned native copier (B)

Final round (4 of 4) of the h35–h39 re-spelling loop. Pre-registration: [PREREG.md](PREREG.md) (committed before
computing). Results: [results/summary.md](results/summary.md). Run: `run_h39.py measures`, `run_h39.py fingerprint`,
`summarise.py`; test: `test_h39.py`.

**Verdict: negative for both headline hypotheses (H-A, H-B); the loop's success criterion is not met.**

- **A (one glyph map per slot, annealed jointly over the whole one-edit graph):** best near-copy network of the loop
  (E .74–.83 vs .46–.56 in h38; target ≥ .9 missed in 9/9), word-final glyphs ≤ .04 bits from MS in 9/9, fingerprint
  5/5 in 4/9 (C0 in all hands, Naibbe-nonsense 2B), 3–4/5 otherwise. Spaces .74–.84: in range in only 3/9 (all 1A or
  3B-Italian); 2B/3B land .02–.05 above. Shuffled-target control is far off (S .31–.54, 9/9). Side effect: merging
  glyphs collapses 340–1 330 types, and the h34 gap table agreement drops (r .16–.60) because the map moves the
  glyphs the gap rule keys on.
- **B (copier with fresh rate, window and edit mix tuned on even bifolia):** matches MS's local near-repeat rate
  (copy proxy .16–.22 vs MS .16–.21) and keeps the word-gap link and table (9/9, r ≥ .91), but the tuner sat at the
  grid edge (25 % fresh, window 50, 55 % unchanged copies), spaces stay .48–.59 (0/9) and the fingerprint is 1/5 in
  9/9: its 5-word copy rate λ5 is .21–.23 vs MS .03–.04. Matching MS's near-repeat rate by literal copying
  overshoots MS's copy statistic about 5–7×.
- Italian and nonsense feeds behave the same (B5 3/3; A within noise).

What this round adds: (1) a global per-slot substitution is the best compromise found, so a fixed glyph-to-glyph
recoding of a copy-heavy base stream gets close on everything except a few hundredths of space predictability and
a tenth of the near-copy network; (2) MS's local similarity between nearby words is not produced by literal
copying at the rate the similarity suggests. No statement about meaning or an underlying language follows.
