# h32: the shared spelling system between scribal hands, and "same content in different spelling"

No translation is attempted or claimed. Pre-registration: `PREREG.md` (commit `299b769`).

**Verdict.**
* **A context-dependent unit transducer maps herbal 2B toward herbal 1A better than h11's rules, but most of the gap is vocabulary.** With up to 30 learned rules it closes **29.3 % ± 1.3 %** of the section-matched held-out gap (5/5 splits above h11's 22.7 %; h11's own rules rerun on the same splits: 22.7 %). At the same budget of 10 rules it closes 23.2 %, i.e. no better than h11. The extra comes from more rules, not better rules. **70.7 % of the gap remains** (P1, P2, P3 pass).
* **The mapping is real and hand-specific.** It is far above permuted-hand controls (95th percentile 6.6 %, max 7.1 %, 20 permutations), split-half noise (−2.0 % to 0.8 %) and same-hand cross-section gaps (1A herbal ← 1A pharma 15.2 %, 2B herbal ← 2B biological 10.4 %, 3B herbal ← 3B stars 3.3 %). The reverse direction gives the same size (2B ← 1A 28.1 %). 1A ← 3B herbal: 16.4 % (3B has only 530 herbal tokens).
* **No evidence that the hands write the same content (S1 fails).** After mapping 2B herbal into 1A spelling:
  * Smith-Waterman on mapped tokens vs 200 within-page shuffles: 0 of 1900 page pairs pass BH q < 0.05; 0.47 % have p ≤ 0.01, against 0.64 % for 1A-vs-1A pages and 0.89 % for unmapped 2B. The longest local alignment scores 7 (8 within 1A), about three or four matching words.
  * Shared mapped bigrams/trigrams with 1A herbal: 236 and 5, against shuffle means 242 and 6.3 (ratio 0.98 and 0.79, p 0.71 / 0.79). Within 1A, the same test finds local phrase reuse beyond shuffles (ratio 1.22 and 2.57, p = 0.01). The mapping does not create it across hands.
  * Pages given the same plant family (h17 majority family): cross-hand same-family pairs are not more similar than different-family pairs (Δcosine −0.028, perm p = 0.90; 13 × 61 pages, 51 same-family pairs). Within 1A also not (Δ +0.022, p = 0.25).
* **Systematic, but not a tidy phonetic system (Q1 partly passes).** The first 5 rules carry 70 % of the 30-rule closure, and 85 % of chosen rules are context-conditioned (word start/end or a neighbouring unit). Context-free rules close only 12.3 % (see limits). But only four rules recur across splits: `#ai→#dai` (5/5 top-5), `-edy#→-ol#` (4/5), `#a→#cho` (3/5), `ch d→ch` (3/5). After those the rule lists differ from split to split, so ≥4 of 5 top-5 rules recurring fails (2–4 per split). It reads as a handful of word-edge spelling habits (B's `-edy`/`-dy`, `a-`/`ai-` onsets vs A's `-ol`/`-or`, `dai-`, `cho-`) plus a long tail of word-specific substitutions, not a letter-for-letter sound change.

## Results in detail
`results/closure.csv` (every run), `results/closure_summary.csv`, `results/summary.json`.

| pair | kind | closed, 10 rules | closed, 30 rules |
|---|---|---|---|
| 1A herbal ← 2B herbal | transducer | 23.2 % | **29.3 %** |
| 1A herbal ← 2B herbal | h11 rules (same splits) | 22.7 % | – |
| 1A herbal ← 2B herbal | context-free transducer | 11.7 % | 12.3 % |
| 2B herbal ← 1A herbal | transducer | 23.0 % | 28.1 % |
| 1A herbal ← 3B herbal | transducer / h11 | 12.8 % / 13.0 % | 16.4 % |
| 1A herbal ← 2B biological | hand + section | 27.4 % | 33.4 % |
| 1A herbal ← 1A pharmaceutical | same hand | 12.0 % | 15.2 % |
| 2B herbal ← 2B biological | same hand | 7.3 % | 10.4 % |
| 3B herbal ← 3B stars | same hand | 3.2 % | 3.3 % |
| split halves 1A / 2B herbal | noise | 1.3 % / −2.7 % | 0.8 % / −2.0 % |
| permuted hands (20) | control | mean 1.3 % | 95th pct 6.6 % |

Rules learned on all herbal pages (1A ← 2B), in order (`results/full_rules.txt`; `#` = word edge, `X[s→t]Y` = context): `[edy→ol]`, `ch[d→∅]`, `#[ai→dai]`, `#[a→cho]`, `[ek→∅]`, `#[oke→cth]`, `[f→t]`, `[yk→∅]a`, `[kar→ty]#`, `[ed→∅]`, … (30).

Same-content tests: `results/sw_pairs.csv`, `sw_summary.csv`, `ngram_share.csv`, `family_test.csv`.

## Deviations from PREREG
* Rule source/target length raised from ≤ 2 to ≤ 3 units, because `-edy → -ol` is a 3-unit block in unit alignment (found by the unit test before any data run).
* The candidate pool = alignment-derived rules (top 800 source types, distance ≤ 3, 600 kept) **plus** h11's positional n-gram rules, so the transducer's rule space contains h11's. The context-free arm uses only alignment-derived rules without context, so its lower closure partly reflects the smaller pool. Treat "context matters" as indicative.
* The 1A reference for the same-content tests is 20 random 1A herbal pages (seed 3) against all other 1A herbal pages.

## Limits
* Rules are chosen greedily on whole-vocabulary JSD; a weighted FST trained by EM on word-pair alignments might do better. 29 % is still a lower bound for spelling.
* Herbal 2B is only 20 pages / 2313 tokens and herbal 3B 6 pages, so 2B ← 1A and anything with 3B are noisy.
* Smith-Waterman only finds near-verbatim parallels in word order. Paraphrase, reordering or different content per page are not tested.
* Plant families come from modern proposals (h17) with weak agreement.
* Closure is in word-distribution JSD, which mixes spelling and frequency.

Reproduce: `python run_h32.py all` (~25 min on 5 cores; then the summary snippet in the commit is in `results/summary.json`); tests `pytest test_h32.py`.
