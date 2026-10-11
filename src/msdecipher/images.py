"""Best-effort page-image extraction from the Yale PDF halves in ``source/``.

Renders each PDF page to a modest-resolution PNG (default 100 dpi; the embedded scans are
~220 ppi, so this is roughly half size) into ``data/images/`` which is git-ignored. Uses
poppler's ``pdftoppm``. Page numbers are *PDF page numbers* (1..214), NOT folio ids:
the PDF-page -> folio map (stage 1 of docs/WORKFLOW.md) is NOT built yet.

Rights: check the Yale item's usage statement before redistributing any image.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .paths import images_dir, source_dir

PART_RE = re.compile(r"pages(\d+)-(\d+)")


def find_parts(directory: Path | None = None) -> list[tuple[Path, int]]:
    """[(pdf path, first global page number)] for ``MS408_part*_pagesAAA-BBB.pdf`` files."""
    parts = []
    for p in sorted((directory or source_dir()).glob("MS408_part*_pages*.pdf")):
        m = PART_RE.search(p.name)
        if m:
            parts.append((p, int(m.group(1))))
    return parts


def extract_pages(dpi: int = 100, outdir: Path | None = None, first: int | None = None,
                  last: int | None = None, source: Path | None = None) -> list[Path]:
    """Render pages to ``page_NNN.png`` (NNN = global PDF page number). Returns written paths."""
    if shutil.which("pdftoppm") is None:
        raise RuntimeError("pdftoppm (poppler-utils) is required")
    outdir = outdir or images_dir()
    outdir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for pdf, start in find_parts(source):
        # determine page count of this part
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
        n = int(re.search(r"Pages:\s+(\d+)", info).group(1))
        lo = max(1, (first - start + 1) if first else 1)
        hi = min(n, (last - start + 1) if last else n)
        if lo > hi:
            continue
        tmp = outdir / f".tmp_{pdf.stem}"
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", "-f", str(lo), "-l", str(hi), str(pdf), str(tmp)],
                       check=True)
        for f in sorted(outdir.glob(f".tmp_{pdf.stem}-*.png")):
            local = int(f.stem.rsplit("-", 1)[1])
            dest = outdir / f"page_{start + local - 1:03d}.png"
            f.replace(dest)
            written.append(dest)
    return written


def extract_native(outdir: Path | None = None, first: int | None = None, last: int | None = None,
                   source: Path | None = None) -> list[Path]:
    """Extract the embedded scans at native resolution (JPEG, ~1500x2000 px, 220 ppi) with ``pdfimages``.

    Written to ``data/images/native/page_NNN.jpg`` (git-ignored). The first PDF page (Yale info sheet) has no
    scan. Each other PDF page holds exactly one JPEG, so no re-encoding takes place.
    This is the input of the glyph stage (the 100 dpi renders are too small: x-height ~ 5 px)."""
    if shutil.which("pdfimages") is None:
        raise RuntimeError("pdfimages (poppler-utils) is required")
    outdir = outdir or (images_dir() / "native")
    outdir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for pdf, start in find_parts(source):
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
        n = int(re.search(r"Pages:\s+(\d+)", info).group(1))
        for local in range(1, n + 1):
            g = start + local - 1
            if (first and g < first) or (last and g > last):
                continue
            dest = outdir / f"page_{g:03d}.jpg"
            if dest.exists():
                written.append(dest)
                continue
            tmp = outdir / f".tmp_{g:03d}"
            subprocess.run(["pdfimages", "-j", "-f", str(local), "-l", str(local), str(pdf), str(tmp)],
                           check=True, capture_output=True)
            files = sorted(outdir.glob(f".tmp_{g:03d}-*.jpg"))
            if files:
                files[0].replace(dest)
                written.append(dest)
            for f in outdir.glob(f".tmp_{g:03d}-*"):
                f.unlink()
    return written
