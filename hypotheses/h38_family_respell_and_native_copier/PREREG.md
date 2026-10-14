# h38 pre-registration: family re-spelling (A) and native-shape copier (B)

Written and committed before any computing. Builds on h34 (gap rule), h35 (whole-word re-spelling: S in range,
fingerprint 2–3/5), h36 (glyph-wise map: fingerprint 5/5 in 6/9, S .78–.95), h37 (edit replay: parent→child kept
96–98 %, all-pairs E .45–.51, S .69–.74, fingerprint 2–4/5; siblings drift; y/l/n too rarely final). No translation or
meaning claims.

**Split / generators.** Per hand (1A, 2B, 3B): train = even bifolia, test = odd bifolia (h34 split). Base streams:
C0, Naibbe-Italian (Boccaccio) + 5 % swap copy, Naibbe-nonsense (h34).

**Variant A `fam` (network-aware re-spelling).** Base word types are linked by edit distance 1; connected components
are families. Each family's most frequent type (root) gets a fresh h35 shape-model spelling (length ±1, distinct).
Other members are reached by BFS from the root; every edit is replayed at the position-relative index, but the new
glyph is taken from a *family-shared* map keyed by (edit kind, relative slot, original glyph): drawn once per family
and reused by every member, so siblings that vary the same slot vary it the same way. Drawn glyphs follow the per-hand
shape 3-gram; if the slot is word-final they are drawn from the per-hand MS-train word-final glyph distribution.
Collisions: 50 redraws, then fresh sample. Control `famshuf`: same with shape model fitted on within-word
glyph-shuffled MS words.

**Variant B `nat` (native-shape copier).** Timm–Schinner/C0-style self-citation directly in MS word shapes: each token
is with p = .15 a fresh word, else a copy of a uniformly chosen token among the previous 50, unchanged with p = .25,
one edit with p = .60, two edits with p = .15 (substitution / insertion / deletion equally likely; new glyphs from the
per-hand shape 3-gram on even-bifolium words, word-final slots from the final-glyph distribution). Fresh-word source
(the "feed"): `nat` = h35 shape-model sample; `nat_it` / `nat_non` = the Naibbe-Italian / Naibbe-nonsense base stream
re-spelled with the h35 whole-word map. h34 gap rule applied to all outputs (s* matched to train J).

**Measures** (odd bifolia): S (space predictability), J (h31 link), T (h34 table r), V (inventory ratio vs `off`;
for B vs MS-test types per 5k), fingerprint n/5 (h20), E (h36 all-pairs near-copy preservation; A only), F = Jensen–
Shannon divergence (bits) of the word-final glyph distribution to MS test. References: h35, h36pos, h37 results.

**Predictions** (9 cells each):
- A1: E ≥ .9 in ≥ 7/9. A2: S in [.72, .80] in ≥ 6/9. A3: fingerprint 5/5 in ≥ 6/9.
- A4: F lower than h37 `copy` in ≥ 7/9. A5: `famshuf` S further from MS than `fam` in ≥ 6/9.
- B1: S in [.72, .80] in ≥ 6/9. B2: fingerprint 5/5 in ≥ 6/9. B3: J ≥ .6 × MS-train J and T ≥ .85 in ≥ 7/9.
- B4: F ≤ .05 bits in ≥ 7/9. B5: `nat_it` vs `nat_non` S within .03 in 3/3 hands (plaintext irrelevant).
- Headline H-A = A1 ∧ A2 ∧ A3; H-B = B1 ∧ B2 ∧ B3.
