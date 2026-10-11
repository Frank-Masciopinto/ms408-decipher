"""Repository-relative paths (overridable with the MSDECIPHER_ROOT environment variable)."""
from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    env = os.environ.get("MSDECIPHER_ROOT")
    if env:
        return Path(env).resolve()
    # src/msdecipher/paths.py -> repo root is three levels up
    return Path(__file__).resolve().parents[2]


def transcription_dir() -> Path:
    return repo_root() / "data" / "transcriptions"


def reports_dir() -> Path:
    return repo_root() / "reports"


def glyphs_dir() -> Path:
    return repo_root() / "glyphs"


def images_dir() -> Path:
    return repo_root() / "data" / "images"


def source_dir() -> Path:
    return repo_root() / "source"
