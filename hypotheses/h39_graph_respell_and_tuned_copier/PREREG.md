# h39 pre-registration: graph-preserving re-spelling (A) and tuned native copier (B)

Written and committed before any computing. Final round (4 of 4) of the h35–h38 loop. Builds on h34 (gap rule),
h35 (whole-word re-spelling: S in range, near-copy network lost), h36 (positional glyph map: E .83–.95 but S .78–.95),
h37 (edit replay: tree kept, network lost), h38 (A family map: S in range 8/9, E .46–.56; B native copier with a-priori
rates: S .32–.45, inventory 1.7–2.4× MS, fingerprint 1/5). No translation or meaning claims.

**Split / generators.** Per hand (1A, 2B, 3B): train = even bifolia, test = odd bifolia (h34 split). Base streams:
C0, Naibbe-Italian (Boccaccio) + 5 % swap copy, Naibbe-nonsense (h34). h34 gap rule applied to every output, strength
s* chosen to match MS-train J (as h34/h38).

**Variant A `graph` (joint slot substitution).** One global glyph substitution per *slot* k ∈ {0, 1, 2, mid, −3, −2, −1}
(signed position from start/end; "mid" = everything else) applied to every word type. Because the same map is used for
every word, any substitution edge of the one-edit graph is preserved by construction, and insertion/deletion edges are
preserved whenever the shifted glyph lands in a slot with the same map. Maps are initialised as h36 rank maps and then
optimised **jointly over the whole graph** by simulated annealing (1 500 proposals; proposal = set one entry σ_k[g] to a
glyph from MS-train slot-k inventory; T 0.02→0.0005 geometric). Objective (lower better), all on train-derived targets:
`|S(x) − S_ms_train| + JS_final(x, MS_train) + 0.5·JS_slot(x, MS_train) + 2·max(0, 0.9 − E(x))`,
where x = first 4 000 re-spelled base tokens in 9-word lines (no gap rule), JS_slot = mean JS of per-slot glyph
distributions, E = h36 all-pairs near-copy preservation on top 800 types. Control `graphshuf`: same annealing but the
MS-train targets (final and slot distributions, S) taken from within-word glyph-shuffled MS-train words.

**Variant B `tuned` (native copier, tuned rates).** h38 native copier with grid
p_fresh ∈ {.03, .06, .10, .15, .25}, window ∈ {5, 10, 25, 50}, p(unchanged) ∈ {.1, .25, .4, .55} (remaining mass split
.8/.2 between one and two edits). Tuned **on even bifolia only**: loss = |V−V_ms|/V_ms + |C−C_ms|/C_ms + |S−S_ms|·4
where V = types per 5 k tokens, C = copy proxy (share of tokens with a token at edit distance ≤ 1 among the previous 5),
S = space predictability after gap rule (s = 1.0 during tuning), all vs MS-train. Best config per (hand, feed) is then
regenerated with a new seed and scored on odd bifolia. Feeds: `native` (h35 shape sample), `it` (Naibbe-Italian
re-spelled via h35), `non` (Naibbe-nonsense re-spelled via h35).

**Measures** (odd bifolia): S, J (h31 link), T (h34 table r), V (inventory ratio vs MS test), fingerprint n/5 (h20),
E (A only), F = JS of word-final glyph distribution to MS test. References: h35–h38 results.

**Predictions** (9 cells each):
- A1: E ≥ .9 in ≥ 7/9. A2: S in [.72, .80] in ≥ 6/9. A3: fingerprint 5/5 in ≥ 6/9. A4: F ≤ .05 in ≥ 7/9.
- A5: `graphshuf` S further from MS than `graph` in ≥ 6/9.
- B1: S in [.72, .80] in ≥ 6/9. B2: fingerprint 5/5 in ≥ 6/9. B3: J ≥ .6 × MS-train J and T ≥ .85 in ≥ 7/9.
- B4: V within ±25 % of MS in ≥ 7/9. B5: `it` vs `non` S within .03 in 3/3 hands (plaintext irrelevant).
- Headline H-A = A1 ∧ A2 ∧ A3; H-B = B1 ∧ B2 ∧ B3. Loop success = H-A ∨ H-B.
