# h37 pre-registration: copy-aware re-spelling

Written and committed before any computing. Builds on h35 (whole-word per-hand glyph 3-gram re-spelling: S in MS
range .72–.80 but fingerprint 2–3/5, edit-neighbour preservation E ≈ .01) and h36 (glyph-wise rank map: fingerprint 5/5
in 6/9, E .83–.96, but S .78–.95, 1/9 in range). No translation or meaning claims.

**Hypothesis H-copy.** If only *source* word types are re-spelled with the h35 whole-word shape model and every near-copy
is rebuilt by replaying its one-glyph edit on the re-spelled source, space placement (S), the copy structure (E) and the
5/5 fingerprint can hold at the same time.

**Method.** Per hand, train = even bifolia, test = odd bifolia (h34 split). Generators: C0, Naibbe-Italian Boccaccio +
5 % swap copy, Naibbe-nonsense (h34 base streams). Generator copy provenance is not exposed by the h34 streams, so sources
are found with an edit-neighbour graph: types are visited by descending frequency; a type is *derived* if some more
frequent type is at edit distance 1 (parent = most frequent such type), else it is a *root*. Roots: fresh h35 sample
(length ±1, distinct). Derived: the parent→child edit (substitution / insertion / deletion at position i) is replayed on
the re-spelled parent at the position-relative index (counted from the nearer word end, clipped); the new glyph is drawn
from the per-hand shape 3-gram given the re-spelled left context (substitution excludes the current glyph). On collision
with an already used spelling: up to 50 redraws, then a fresh h35 sample. h34 gap rule applied afterwards (s* matched to
train J). Primary variant `copy`. Controls: `off` (h34), `h35`, `h36pos`, `shuf` (same procedure with a shape model fitted on
within-word glyph-shuffled MS words), nonsense plaintext.

**Measures.** S, J (h31 link), T (h34 table r), inventory ratio V, fingerprint n/5 (h20), E (h36 definition).

**Predictions** (9 cells = 3 hands × 3 generators, `copy`):
- P1: S in [.72, .80] in ≥ 6/9.
- P2: J ≥ .6 × MS-train J in ≥ 7/9. P3: T ≥ .85 in ≥ 7/9. P4: |V−1| ≤ .3 in ≥ 7/9.
- P5: fingerprint 5/5 in ≥ 6/9.
- P6: E ≥ .9 in ≥ 7/9.
- P7: `shuf` moves S further from MS than `copy` in ≥ 6/9.
- P8: Italian vs nonsense S within .03 in 3/3 hands.
H-copy supported if P1, P5, P6 all pass. Partial outcomes are reported as the trade-off they show.
