"""Download the voynich.nu IVTFF transcriptions and record a SHA256 manifest.

Plain ``requests`` with an honest, self-identifying User-Agent. voynich.nu answers HTTP 406 to
spoofed browser User-Agents *and* to the stock ``python-requests`` / ``Python-urllib`` ones
(observed 2026-10-11), but accepts curl's default and a descriptive custom one, so we send
``USER_AGENT`` below. We do not pretend to be a browser.

Licensing: the voynich.nu data README states no open licence. The downloaded files are
therefore git-ignored; only this script and ``data/transcriptions/MANIFEST.json`` are
committed. Anyone can re-create the data with ``python -m msdecipher fetch`` and check it
with ``python -m msdecipher verify``.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path

from .paths import transcription_dir

BASE = "https://www.voynich.nu/data/"
USER_AGENT = "msdecipher/0.1 (research tool; +https://github.com/Frank-Masciopinto/ms408-decipher)"

LICENSE_NOTE = (
    "voynich.nu publishes these files for research use but states no open licence in the "
    "000_README.txt that was read. They are NOT redistributed in this repository (git-ignored); "
    "only URLs and SHA256 checksums are recorded. Cite the transcribers (Zandbergen/Landini ZL, "
    "Claston GC, Takahashi IT, reference merge RF) and ask the maintainers before redistributing."
)

SOURCES = [
    {"file": "ZL3b-n.txt", "alphabet": "Eva-", "role": "primary",
     "description": "Zandbergen-Landini transliteration v3b (13 May 2025), Extended EVA, IVTFF 2.0"},
    {"file": "IT2a-n.txt", "alphabet": "EvaT", "role": "replication",
     "description": "Takahashi transliteration (as in Landini-Stolfi interlinear), basic EVA"},
    {"file": "RF1b-e.txt", "alphabet": "Eva-", "role": "replication",
     "description": "Reference transliteration 1b (automatic ZL+GC merge), extended EVA"},
    {"file": "GC2a-n.txt", "alphabet": "v101", "role": "parse-only",
     "description": "Claston v101 transliteration, v101 alphabet (not EVA; parser test only)"},
    {"file": "000_README.txt", "alphabet": None, "role": "documentation",
     "description": "voynich.nu data directory README"},
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_path(directory: Path | None = None) -> Path:
    return (directory or transcription_dir()) / "MANIFEST.json"


def load_manifest(directory: Path | None = None) -> dict:
    p = manifest_path(directory)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"license_note": LICENSE_NOTE, "files": []}


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch_all(directory: Path | None = None, session=None, sources=None) -> dict:
    """Download every source file; write/refresh the manifest; return it."""
    import requests

    directory = directory or transcription_dir()
    directory.mkdir(parents=True, exist_ok=True)
    session = session or requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    old = {e["file"]: e for e in load_manifest(directory).get("files", [])}
    entries = []
    for src in sources or SOURCES:
        url = BASE + src["file"]
        resp = session.get(url, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"{url}: HTTP {resp.status_code}")
        data = resp.content
        if not data:
            raise RuntimeError(f"{url}: empty body")
        dest = directory / src["file"]
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(dest)
        digest = hashlib.sha256(data).hexdigest()
        prev = old.get(src["file"])
        retrieved = prev["retrieved_at"] if prev and prev.get("sha256") == digest else _now()
        entries.append({**src, "url": url, "bytes": len(data), "sha256": digest,
                        "retrieved_at": retrieved})
    manifest = {"license_note": LICENSE_NOTE, "files": entries}
    manifest_path(directory).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify(directory: Path | None = None) -> list[tuple[str, str]]:
    """Compare local files with the manifest. Returns [(file, status)], status in
    ok / missing / MISMATCH."""
    directory = directory or transcription_dir()
    out = []
    for e in load_manifest(directory).get("files", []):
        p = directory / e["file"]
        if not p.exists():
            out.append((e["file"], "missing"))
        elif sha256_file(p) == e["sha256"]:
            out.append((e["file"], "ok"))
        else:
            out.append((e["file"], "MISMATCH"))
    return out
