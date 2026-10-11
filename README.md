# MS 408 Decipherment Framework

A research framework for studying the undeciphered **Beinecke MS 408** ("Cipher manuscript", also known as the Voynich manuscript), using the Yale digitization.

> **Status: MS 408 is undeciphered.** No claimed solution is accepted by scholars. This repo contains **no translation and makes no decipherment claim**. What exists so far is tooling that *describes* published transcriptions (frequencies, entropies, positional behaviour, Currier A/B differences). Those numbers are descriptive statistics, not decoding; see [docs/STATS_NOTE.md](docs/STATS_NOTE.md). No word is labelled a verb, name or any other category.

## Source
- Yale Library Digital Collections: https://collections.library.yale.edu/catalog/2002046
- PDF: https://collections.library.yale.edu/pdfs/2002046.pdf (214 pages, ~118 MB)
- GitHub rejects files over 100 MB, so the PDF is stored here as two halves in `source/`. Rebuild the full file with `./scripts/join_pdf.sh`.
- Check Yale's usage rights before redistributing page images (rendered images are git-ignored).

## Implementation status

| Workflow stage ([docs/WORKFLOW.md](docs/WORKFLOW.md)) | Status |
|---|---|
| 2 Transcription ingestion (download, IVTFF parser) | **Done** for IVTFF 2.0 EVA files (ZL 3b primary; IT 2a, RF 1b replication; GC 2a parse-only) |
| 3a Glyph catalogue from a transcription | **Done** (`glyphs/`) |
| 1 PDF page → folio index | **Done** ([`data/page_index.csv`](data/page_index.csv); 177 of 214 pages map 1:1, fold-outs/multi-folio scans are flagged, not resolved) |
| 3b Glyph catalogue from the page images | **Done, best effort** on 28 text-dominant pages ([docs/IMAGE_STAGE.md](docs/IMAGE_STAGE.md), [reports/image_stage/REPORT.md](reports/image_stage/REPORT.md)): lines found ±1 on 57% of pages, glyph candidates match the transcribed unit count for ~25% of words, image clusters agree only weakly with EVA units (NMI ≈ 0.16). Proxy metrics only, tuned on the same pages; no inventory size is supported by the images |
| 4 Unit segmentation (configurable `ch`, `sh`, …) | **Done** (4 presets or any custom list; not data-driven BPE yet) |
| 5 Basic statistics: Zipf, Heaps, H1/h2/h3, positional, Currier A/B | **Done**, no control corpora yet |
| 6 Sukhotin vowel/consonant test; intra-word structure | Sukhotin **done** (page-bootstrap stability); **learned slot grammar + prefix-core-suffix model with MDL and held-out folio CV, vs shuffled null and all controls, done** ([docs/WORD_STRUCTURE.md](docs/WORD_STRUCTURE.md), `reports/word_structure/`): position matters unusually much (null gap 2.9 bits/type vs ≤1.5 in natural text) but a 12-slot independent-emission grammar fits worse than a within-word bigram |
| 7 Word classes (behavioural clustering only) | **Done as behavioural tags, not grammar**: top-200 words clustered by neighbour/line/section/Currier/hand features with bootstrap / half-split ARI; MS 408 clusters are as stable as Latin/Italian/Hebrew/Arabic ones (ARI 0.42 vs 0.43), far above shuffled text (0.05); no category is named. Syntax induction **not done** |
| 10a Control corpora + transformations + null generators, same stats on all, comparison table | **Done (third pass, hardened)**: [docs/CONTROLS.md](docs/CONTROLS.md), `reports/controls/`. 17 base texts (Latin ×7 incl. Pliny/Celsus/Isidore/Macer herbal-medical-encyclopaedic, Italian ×4, German ×2, Hebrew ×2, Arabic ×2 consonantal), up to 3 size-matched 35k-token windows each, 12 transformations, 5 generators; jackknife (+bootstrap) CIs for MS 408 and per-control SEs, prediction-interval and z-score verdicts, alphabet-size-normalised metrics and regression; not done: Dioscorides/Pseudo-Apuleius, Syriac/Ethiopic, real Naibbe / Timm-Schinner code, folio→quire map |
| 10b Candidate generating mechanisms (Naibbe cipher, Timm & Schinner self-citation, Zattera/Stolfi grammars, slot-conditioned bigram) through the full metric suite | **Done**: [docs/MECHANISMS.md](docs/MECHANISMS.md), `reports/mechanisms/`. Naibbe (author's tables, card-draw, decryption round trip) and the authors' own self-citation Java code (parameter search inside documented bounds) reproduce 11–15 of 35 metrics at defaults (fitted self-citation 23/35); no hand-coded grammar beats the letter-pair baseline held out, the learned slot-conditioned bigram does (−0.6 bits/token). Nothing here decodes MS 408; Naibbe/self-citation papers only seen as excerpts (bot wall), Zattera probabilities unavailable |
| 1, 8–14 (cribs, nulls, candidate-plaintext attacks, validation gates) | **Not started** |

Honest limits: control texts and simulated families now exist (stage 10a) but are few, small and simplified, so the numbers still cannot say whether the text is language, cipher or neither (see [docs/CONTROLS.md](docs/CONTROLS.md)); the glyph catalogue was compared with the images only on 28 text pages with proxy metrics (stage 3b); samples are pooled over non-independent pages.

## Install and run

Python ≥ 3.10, `poppler-utils` for the image step.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,images]"     # [images] = opencv/scipy/scikit-image/scikit-learn for the image stage; or: pip install -r requirements-dev.txt  (then run from repo root with PYTHONPATH=src)
python -m pytest                   # real-data tests skip until the data is fetched; image-stage tests skip without the [images] extra

python -m msdecipher fetch         # voynich.nu IVTFF files -> data/transcriptions/ + SHA256 manifest
python -m msdecipher verify        # check files against data/transcriptions/MANIFEST.json
python -m msdecipher parse         # inventory of ZL3b (5385 loci, tokens, flags)
python -m msdecipher catalog       # glyphs/catalog.csv, digraph_candidates.csv, REPORT.md
python -m msdecipher run-all       # catalogue + statistics + plots + replication -> glyphs/, reports/  (~15 s)
python -m msdecipher run-all --units ch,sh --uncertain-spaces join   # other segmentation / space policy
python -m msdecipher images --dpi 100   # render PDF pages -> data/images/ (git-ignored; PDF page numbers)
python -m msdecipher images --native    # native-resolution scans (pdfimages) -> data/images/native/ (git-ignored)
python -m msdecipher page-index         # PDF page -> folio index -> data/page_index.csv
python -m msdecipher segment-glyphs     # lines/words/glyph candidates + clustering + QA -> reports/image_stage/ (~1 min; needs  pip install -e ".[images]")
python -m msdecipher controls-fetch     # Latin/Italian/MHG/Hebrew/Arabic control texts -> data/controls/ (git-ignored) + MANIFEST.json (--only ID ... for a subset)
python -m msdecipher controls-verify    # SHA256 check
python -m msdecipher controls-run       # stats + CIs on MS 408 + all controls/nulls -> reports/controls/ (~10-15 min; --tokens, --seeds, --boot, --workers)
python -m msdecipher mechanisms-run # candidate mechanisms vs MS 408 -> reports/mechanisms/ (~25 min incl. self-citation search; needs a JDK for the Java reference generator, else uses cached texts; --reuse, --no-sweep)
python -m msdecipher word-structure # Stage 6+7: slot grammar / affixes / behavioural clusters on MS 408 + all controls -> reports/word_structure/ (~10-15 min; --reuse rebuilds the report from the CSVs)
```

`--units` accepts a preset (`raw`, `basic` = ch/sh, `collapsed` = ch, sh, cth, ckh, cph, cfh (default), `extended` = + ee, ii, iin, in) or a comma list such as `ch,sh,qo`.

### Outputs
- `glyphs/catalog.csv` – every EVA symbol and rare `@nnn;` code with counts and word/line positional shares; `digraph_candidates.csv`, `top_pmi_bigrams.csv`; `glyphs/REPORT.md`
- `reports/stats_report.md` – the main report (tables, Currier A vs B, Sukhotin, replication, limits)
- `reports/*.csv` – `summary_stats`, `unit_frequencies`, `word_frequencies_top1000`, `word_length_distribution`, `positional_units`, `currier_ab_units`, `currier_ab_words`, `sukhotin`, `replication`
- `reports/figures/*.png` – Zipf, Heaps, unit shares A vs B, positional heatmap, entropies

### Data licence caveat
The voynich.nu transliteration files state no open licence, so they are **not committed**; only `data/transcriptions/MANIFEST.json` (URLs + SHA256) and the fetch script are. See [data/transcriptions/README.md](data/transcriptions/README.md).

## Package layout (`src/msdecipher/`)
`fetch.py` download + manifest · `ivtff.py` IVTFF parser (folio, locus, hand, section, tokens, comments, alternative readings, uncertain spaces, ligatures, rare codes) · `segment.py` unit segmentation · `glyphs.py` catalogue · `stats.py` entropy / Zipf / Heaps / Sukhotin / JSD · `analysis.py` pipeline and Markdown · `plots.py` · `images.py` page rendering / native scan extraction · `pageindex.py` PDF page→folio index · `imgproc.py` / `glyph_stage.py` / `image_report.py` image glyph stage · `controls_fetch.py` / `controls_text.py` / `controls_transforms.py` / `controls_metrics.py` / `controls_run.py` / `controls_plots.py` / `controls_ci.py` control stage · `slot_grammar.py` / `word_structure.py` / `word_classes.py` / `word_structure_run.py` / `word_structure_plots.py` word-structure stage · `mech_naibbe.py` / `mech_selfcitation.py` / `mech_grammars.py` / `mechanisms_run.py` / `mechanisms_report.py` mechanisms stage · `cli.py`

## Layout
- `source/` the manuscript PDF (two halves)
- `glyphs/` glyph catalogue outputs
- `data/transcriptions/` manifest (+ git-ignored third-party files)
- `reports/` generated statistics, tables and figures
- `src/msdecipher/`, `tests/` code and tests
- `hypotheses/` tests of outside claims about the script, one folder each (`h01_tone_sheet/`: the "Codex Translation Sheet" tone/glyph/meaning table; `h02_full_tone_map/`: 39 candidate Hz maps for every unit, tested against nulls and controls; `h03_slotgrammar_map/`: pitch tied to slot index in the learned / Zattera slot grammars, slot patterns as word "chords", held-out predictive gain vs letters and vs Naibbe/self-citation outputs, and a slot = syllable-position test: rising contours are tautological, slot patterns add no information beyond letters except a tiny Zattera edge on hand/section; `h05_zodiac_cribs/`: the 12 zodiac pages (10 signs; Aquarius/Capricorn lost) — the central words are Roman-script *month* names, not Voynichese sign names; 299 nymph labels and ring text tested against 19 sign/month name lists (length, isomorph, crib-drag with transfer): nothing beyond the nulls after correction; label pitches under the sheet and `a_slotgrammar_ext` given as illustration)
- `notebooks/` exploration (empty)
- `docs/` workflow, prior work, data sources, stats note, image-stage status

## Planned next
More controls (Dioscorides/Pseudo-Apuleius, Syriac/Ethiopic, Occitan/Old French/Czech), a hybrid cipher + self-citation mechanism, group-level units for verbose ciphers, quire-level confidence intervals, BPE/data-driven units, Brown/syntax induction, and higher-resolution scans for the image stage (herbal pages, per-hand comparison), then the later stages of [docs/WORKFLOW.md](docs/WORKFLOW.md). Background: [docs/PRIOR_WORK.md](docs/PRIOR_WORK.md), [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).
