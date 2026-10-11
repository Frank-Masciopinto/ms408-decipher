"""Image-based glyph segmentation (docs/WORKFLOW.md stage 3b).

*** NOT IMPLEMENTED. This is a stub. ***

What exists: :mod:`msdecipher.images` renders page images. What does NOT exist: text-line
detection, ink/vellum separation, word and glyph segmentation, the PDF-page -> folio index,
alignment to the transcription, or clustering of glyph crops. Consequently the glyph catalogue
in ``glyphs/catalog.csv`` comes from a transcription only and has NOT been checked against the
page images.

Planned approach (see docs/IMAGE_STAGE.md): build ``data/page_index.csv`` (PDF page <-> folio),
binarise (e.g. Sauvola), find text lines, split connected components / strokes, align with the
reference transliteration, then cluster crops (HOG or learned embeddings) and compare the
clusters with the transcribed glyph classes per scribal hand.
"""
from __future__ import annotations

STATUS = "not implemented"


def segment_page(image_path, *args, **kwargs):
    raise NotImplementedError(
        "Glyph segmentation from images is not implemented yet (stub). "
        "See docs/IMAGE_STAGE.md and docs/WORKFLOW.md stage 3b.")
