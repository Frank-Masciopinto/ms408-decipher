# h38: family re-spelling (A) and native-shape copier (B)

Pre-registration: [PREREG.md](PREREG.md) (committed before computing). Results: [results/summary.md](results/summary.md).
Run: `run_h38.py measures`, `run_h38.py fingerprint`, `summarise.py`; test: `test_h38.py`.

**Verdict: negative for both variants.**
- **A (family re-spelling):** space predictability lands in the MS range (.72–.80) in 8/9 cells, the best so far, and
  word-final glyphs sit closer to MS than h37 in 6/9. But only .46–.56 of all edit-distance-1 pairs survive (target ≥ .9):
  the Naibbe streams form one giant edit component, and a BFS tree with a shared slot map cannot keep cross-branch links.
  Fingerprint 1–4/5, 0/9 at 5/5.
- **B (native-shape copier):** keeps the word-gap link and gap table (9/9) and final-glyph shape (≤ .05 bits in 5/9), but
  spaces are far too unpredictable (.32–.45), vocabulary is 1.7–2.4× MS and the fingerprint is 1/5 everywhere.
- Shuffled-shape control is further off (7/9). Italian and nonsense feeds behave the same.

No statement about meaning or an underlying language follows.
