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
| 3b Glyph catalogue from the page images | **Not done.** Page rendering works; glyph segmentation is a stub ([docs/IMAGE_STAGE.md](docs/IMAGE_STAGE.md)) |
| 4 Unit segmentation (configurable `ch`, `sh`, …) | **Done** (4 presets or any custom list; not data-driven BPE yet) |
| 5 Basic statistics: Zipf, Heaps, H1/h2/h3, positional, Currier A/B | **Done**, no control corpora yet |
| 6 Sukhotin vowel/consonant test (after segmentation) | **Done** (page-bootstrap stability); HMMs/slot grammars **not done** |
| 1, 7–14 (folio index, word-class induction, cribs, nulls, candidate-plaintext attacks, validation gates) | **Not started** |

Honest limits: no Latin/Italian/cipher/gibberish controls have been run, so none of the numbers can say whether the text is language, cipher or neither; the glyph catalogue has not been checked against the images; samples are pooled over non-independent pages.

## Install and run

Python ≥ 3.10, `poppler-utils` for the image step.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"            # or: pip install -r requirements-dev.txt  (then run from repo root with PYTHONPATH=src)
python -m pytest                   # 47 tests; real-data tests skip until the data is fetched

python -m msdecipher fetch         # voynich.nu IVTFF files -> data/transcriptions/ + SHA256 manifest
python -m msdecipher verify        # check files against data/transcriptions/MANIFEST.json
python -m msdecipher parse         # inventory of ZL3b (5385 loci, tokens, flags)
python -m msdecipher catalog       # glyphs/catalog.csv, digraph_candidates.csv, REPORT.md
python -m msdecipher run-all       # catalogue + statistics + plots + replication -> glyphs/, reports/  (~15 s)
python -m msdecipher run-all --units ch,sh --uncertain-spaces join   # other segmentation / space policy
python -m msdecipher images --dpi 100   # render PDF pages -> data/images/ (git-ignored; PDF page numbers)
python -m msdecipher segment-glyphs     # NOT IMPLEMENTED (exits 2)
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
`fetch.py` download + manifest · `ivtff.py` IVTFF parser (folio, locus, hand, section, tokens, comments, alternative readings, uncertain spaces, ligatures, rare codes) · `segment.py` unit segmentation · `glyphs.py` catalogue · `stats.py` entropy / Zipf / Heaps / Sukhotin / JSD · `analysis.py` pipeline and Markdown · `plots.py` · `images.py` page rendering · `glyph_segmentation.py` stub · `cli.py`

## Layout
- `source/` the manuscript PDF (two halves)
- `glyphs/` glyph catalogue outputs
- `data/transcriptions/` manifest (+ git-ignored third-party files)
- `reports/` generated statistics, tables and figures
- `src/msdecipher/`, `tests/` code and tests
- `notebooks/` exploration (empty)
- `docs/` workflow, prior work, data sources, stats note, image-stage status

## Planned next
Control corpora and null models (Latin/Italian/Hebrew texts, shuffles, Markov and cipher generators), quire-level confidence intervals, BPE/data-driven units, the PDF-page→folio index and image glyph segmentation, then the later stages of [docs/WORKFLOW.md](docs/WORKFLOW.md). Background: [docs/PRIOR_WORK.md](docs/PRIOR_WORK.md), [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).
