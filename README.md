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
| 6 Sukhotin vowel/consonant test (after segmentation) | **Done** (page-bootstrap stability); HMMs/slot grammars **not done** |
| 10a Control corpora + transformations + null generators, same stats on all, comparison table | **Done (second pass)**: [docs/CONTROLS.md](docs/CONTROLS.md), `reports/controls/`. 9 control texts (Latin ×2, Italian ×2, MHG ×1, **Hebrew ×2, Arabic ×2** consonantal abjad), 12 transformations (8 also applied to the Hebrew/Arabic texts), 5 generators; not done: herbal Latin, Syriac/Ethiopic, real Naibbe / Timm-Schinner code, CIs |
| 1, 7–14 (folio index, word-class induction, cribs, nulls, candidate-plaintext attacks, validation gates) | **Not started** |

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
python -m msdecipher controls-run       # stats on MS 408 + all controls/nulls -> reports/controls/ (~5 min; --tokens, --seeds)
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
`fetch.py` download + manifest · `ivtff.py` IVTFF parser (folio, locus, hand, section, tokens, comments, alternative readings, uncertain spaces, ligatures, rare codes) · `segment.py` unit segmentation · `glyphs.py` catalogue · `stats.py` entropy / Zipf / Heaps / Sukhotin / JSD · `analysis.py` pipeline and Markdown · `plots.py` · `images.py` page rendering / native scan extraction · `pageindex.py` PDF page→folio index · `imgproc.py` / `glyph_stage.py` / `image_report.py` image glyph stage · `controls_fetch.py` / `controls_text.py` / `controls_transforms.py` / `controls_metrics.py` / `controls_run.py` / `controls_plots.py` control stage · `cli.py`

## Layout
- `source/` the manuscript PDF (two halves)
- `glyphs/` glyph catalogue outputs
- `data/transcriptions/` manifest (+ git-ignored third-party files)
- `reports/` generated statistics, tables and figures
- `src/msdecipher/`, `tests/` code and tests
- `notebooks/` exploration (empty)
- `docs/` workflow, prior work, data sources, stats note, image-stage status

## Planned next
More controls (herbal Latin, Syriac/Ethiopic, Occitan/Old French/Czech; the real Naibbe and Timm-Schinner generators), group-level units for verbose ciphers, quire-level confidence intervals, BPE/data-driven units, a held-out evaluation and higher-resolution scans for the image stage (herbal pages, per-hand comparison), then the later stages of [docs/WORKFLOW.md](docs/WORKFLOW.md). Background: [docs/PRIOR_WORK.md](docs/PRIOR_WORK.md), [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).
