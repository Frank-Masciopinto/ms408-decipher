# MS 408 Decipherment Framework

A research framework for studying the undeciphered **Beinecke MS 408** ("Cipher manuscript", also known as the Voynich manuscript), using the Yale digitization.

> **Status:** MS 408 is undeciphered. No claimed solution is accepted by scholars. This repo is a reproducible pipeline for testing hypotheses. It does not contain or claim a translation.

## Source
- Yale Library Digital Collections: https://collections.library.yale.edu/catalog/2002046
- PDF: https://collections.library.yale.edu/pdfs/2002046.pdf (214 pages, ~118 MB)
- GitHub rejects files over 100 MB, so the PDF is stored here as two halves in `source/`. Rebuild the full file with `./scripts/join_pdf.sh`.

## Planned pipeline
1. **Glyph inventory.** Segment and catalog every distinct character form, then map to a transcription alphabet (EVA).
2. **Transcription and word segmentation.** Align with published transcriptions and check them against the page images.
3. **Statistics.** Frequency, entropy, Zipf and Heaps tests, and comparison with known languages and ciphers.
4. **Structure.** Positional and morphological analysis, word grammar, and unsupervised word-class clustering (candidate verbs, names, nouns, function words).
5. **Sentence and section structure.** Line and paragraph behaviour, topic per section, and links to illustrations and labels.
6. **Hypothesis testing.** Candidate languages and cipher families, cribs from plant and star labels, and falsification criteria.
7. **Validation and reproducibility.**

Detailed write-ups from the research pass will land in `docs/`.

## Layout
- `source/` the manuscript PDF (two halves)
- `glyphs/` extracted glyph images and catalog
- `data/transcriptions/` third-party transcription files (check licenses)
- `src/msdecipher/` analysis code
- `notebooks/` exploration
- `docs/` workflow, prior work, data sources
