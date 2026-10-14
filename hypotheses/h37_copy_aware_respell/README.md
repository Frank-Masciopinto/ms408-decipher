# h37: copy-aware re-spelling

Pre-registration: [PREREG.md](PREREG.md) (committed before computing). Results: [results/summary.md](results/summary.md).
Run: `run_h37.py measures`, `run_h37.py fingerprint`, `summarise.py`; test: `test_h37.py`.

**Verdict: negative.** Re-spelling only source words (h35 shape model) and replaying each near-copy's one-glyph edit
keeps 96–98 % of parent→child links, but only .45–.51 of all edit-distance-1 pairs (target ≥ .9), because siblings
and cross-family neighbours are rebuilt independently. Space predictability lands at .69–.74 (3/9 inside .72–.80) and
the fingerprint at 2–4/5 (0/9 at 5/5). Link, gap table and inventory are kept; the shuffled-shape control is far off;
Italian and nonsense plaintext behave the same. No statement about meaning or an underlying language follows.
