# h09: image-context cribs (do the drawings tell us what words mean?)

**Verdict: no robust word-meaning pair.** The drawings let us build many candidate meanings, such as "water" words on
the bath pages and "root" words on the pharmaceutical pages. Almost all of them are section/quire effects: random tags that are
constant within a quire produce as many "enriched" words. After quire-aware nulls and Holm correction, two weak signals are left:

1. Labels on the same kind of object share **word-final bigrams** a bit more than labels on different objects, even within a quire (z = 2.7, Holm p = 0.03). The effect comes from the pharmaceutical pages, jar vs plant-part labels: p = 0.011 within quire, but Holm p = 0.09 in that subset.
2. "Root" candidate words picked on pharmaceutical pages are more frequent on herbal pages that I tagged as having large/tuberous roots (log rate ratio 0.34; p = 0.007 vs within-quire tag shuffles, p = 0.008 vs frequency-matched random words, k = 10). It is **fragile**: Holm over the 8 pre-registered transfers gives about 0.056, it fails at k = 5 (p = 0.17), it is weaker at k = 20–30 (p = 0.017–0.038), and with Currier A only it gives p = 0.04.

Treat these as candidate leads, not decipherment.

## What was done

| Step | File | Result |
|---|---|---|
| Pre-registered visual tags (225 folios, committed before any statistic: `7edbf90`) | `data/visual_tags.csv`, `PREREG.md` | nymphs, pools, pipes, stars, jars, roots, leaves, flowers, green/blue water, circles, animals; herbal: root size, blue/red flowers; confidence per row |
| T1 label-object sharing (699 labels, IVTFF subtypes Lc/Lf/Ln/Lt/Ls/Lz/La) | `results/t1_*.csv`, `figures/label_object_sharing.png` | global: same-type labels share prefix/first glyph/whole word (z 3.8–4.6), but **within quire** only suffix survives (z 2.7, Holm 0.03); prefix and word sharing are entirely quire effects |
| T2 herbal↔pharma "same plant" pairs (12 pairs from ZL3b header comments: Petersen, Stolfi, FSG, GL; 9 marked "?") | `results/t2_same_plant_pairs.csv` | mean rank of the true partner among all herbal pages 0.49 (p = 0.57). No signal. Only 3 pairs share any word (`okam`, `chody`, `oteol`); f102r1/r2 have only 4 labels each |
| T3 label word recurs in its own page's running text | summary.json `t3` | 64 hits vs 57.1 expected within quire (ratio 1.12, p = 0.09). Not significant. Jar labels: 0/36 |
| T4 context-word enrichment, 5 tags × 2 nulls | `results/t4_*.csv`, `results/candidate_word_meanings.csv`, `figures/enrichment_vs_quire_block_null.png` | page-shuffle null: water 71, star 31, root 12, jar 19, nymph 16 Holm-significant words. **Within-quire null: 0 for every tag.** Random quire-aligned tags beat the real tag in 7–27% of draws (water 17%, star 7%, root 27%, jar 23%, nymph 20%) |
| T5 transfer: select candidates in one section, test on herbal visual tags | summary.json `t5`, `t5_root_robustness`, `figures/root_transfer_robustness.png` | only root→large-root is positive (see above). water→large-root p = 0.058; star words and jar words: no transfer (jar→blue flower p = 0.024, not predicted, does not survive Holm) |
| T6 speculative: star words vs "star" in 8 languages (stella, stern, kokhav, najm, aster, estela, hvězda) | `results/t6_speculative_star_words.csv` | `olaiin`/`otaiin` have the same letter-repeat pattern as *stella* (ii ↔ ll), but 2% of all Voynich word types match that pattern, and neither word is star-enriched within quire. **Meaningless as evidence.** |

## Top candidate word-meaning pairs (from `results/candidate_word_meanings.csv`)

| candidate meaning | word | count | rate ratio tagged/untagged | Holm p, page shuffle | p within quire (raw) |
|---|---|---|---|---|---|
| water/bath | `qol` | 142 | 9.7 | 6e-26 | 0.13 |
| water/bath | `olkedy` | 26 | 8.5 | 3e-18 | 0.08 |
| water/bath | `qokain` | 279 | 4.9 | 5e-18 | 0.14 |
| woman/nymph | `otey` | 59 | 3.0 | 2e-14 | 0.004 (Holm 1.0) |
| star | `cheeo` | 19 | 14.6 | 3e-7 | 0.58 |
| star | `lkaiin` | 48 | 6.6 | 1e-6 | 0.08 |
| root | `ckhey` | 26 | 8.4 | 2e-8 | 0.008 (Holm 1.0) |
| root | `ctheol` | 10 | 11.0 | 6e-11 | 0.02 (Holm 1.0) |
| vessel/jar | `qokeody` | 33 | 14.5 | 5e-9 | 0.07 |

The page-shuffle p-values only say "this word belongs to the biological/stars/pharmaceutical section". Those sections coincide with
quires (and with Currier B for bio/stars), so they cannot separate "means water" from "is a word of quire 13". The pharma
candidates (`ckhey`, `chody`, `qokol`, `qockhey`, `oldy`, `sol`, ...) are the ones that partly transfer to herbal root pages.

## Limitations

* Tagging was done by one annotator from low-resolution montages: 300 px per herbal page and 700 px per 2×2 grid elsewhere. Foldout panels (f67–f70, f85/86, f89, f95, f101, f102) are coarse and marked `low`. Counts are approximate.
* Plant identities were not used as tags. The ZL3b header lists literature IDs, many marked disputed. Only the "same plant" pairs were used, and 9 of 12 are marked uncertain.
* The `[row,col]` references to pharma fragments were not resolved to individual labels, so whole-folio label sets were used. This dilutes T2.
* Every tag except herbal roots/flowers and star counts is near-constant within a section. The within-quire nulls are therefore conservative and have little power, and the global nulls are confounded. Nothing in between can fix this, because quires and sections coincide (see h08).
* The herbal large-root tag was assigned by eye. If I unconsciously preferred root-heavy pharma-like plants, the transfer could be biased, although the tags were committed before any statistic.

Reproduce: `python run_h09.py && python make_figures.py && python make_candidates.py`; tests: `pytest test_h09.py`.
