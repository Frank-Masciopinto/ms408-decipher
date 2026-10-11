# Image stage status (WORKFLOW.md stages 1 and 3b)

| Piece | Status |
|---|---|
| Render PDF pages to PNG (`python -m msdecipher images`) | **Done (best effort).** `pdftoppm` at 100 dpi (the PDF scans are ≈220 ppi) into `data/images/page_NNN.png` (git-ignored). Numbers are *PDF page numbers* 1–214, taken from the `source/MS408_partN_pagesAAA-BBB.pdf` file names. |
| PDF page → folio index (`data/page_index.csv`) | **Not done.** The PDF has 214 pages incl. covers/binding/fold-outs; the map to folio ids (f1r, f67r1 …) has to be built and checked by hand. |
| Text line detection, ink/vellum separation, binarisation | **Not done.** |
| Word / glyph segmentation (`python -m msdecipher segment-glyphs`) | **Not implemented**: stub that exits with status 2. |
| Visual glyph clustering and comparison with the transcribed classes | **Not done.** |

Consequence: `glyphs/catalog.csv` is a catalogue of what a *transcriber* recorded. It has **not** been
checked against the page images, so it cannot yet correct the transcription alphabet.

Rights: check Yale's *Access and Usage Rights* statement for the item before redistributing images;
the rendered pages are not committed.

Planned next steps are in `docs/WORKFLOW.md` stage 3b (line detection → connected components →
alignment with the reference transliteration → HOG/embedding clustering → per-hand comparison).
