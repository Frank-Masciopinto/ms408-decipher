import hashlib
import json
import shutil
import subprocess
import sys

import pytest

from msdecipher import fetch, images
from msdecipher.cli import main


class FakeResp:
    def __init__(self, content, status=200):
        self.content, self.status_code = content, status


class FakeSession:
    def __init__(self, bodies, status=200):
        self.bodies, self.status, self.headers, self.calls = bodies, status, {}, []

    def get(self, url, timeout=0):
        self.calls.append(url)
        return FakeResp(self.bodies[url.rsplit("/", 1)[1]], self.status)


SRC = [{"file": "a.txt", "alphabet": "Eva-", "role": "x", "description": "d"},
       {"file": "b.txt", "alphabet": None, "role": "y", "description": "e"}]


def test_fetch_writes_files_and_manifest(tmp_path):
    sess = FakeSession({"a.txt": b"hello", "b.txt": b"world"})
    m = fetch.fetch_all(tmp_path, session=sess, sources=SRC)
    assert sess.headers["User-Agent"].startswith("msdecipher/")        # honest UA, not a browser
    assert "Mozilla" not in sess.headers["User-Agent"]
    assert (tmp_path / "a.txt").read_bytes() == b"hello"
    assert m["files"][0]["sha256"] == hashlib.sha256(b"hello").hexdigest()
    assert "licence" in m["license_note"] and "NOT redistributed" in m["license_note"]
    on_disk = json.loads((tmp_path / "MANIFEST.json").read_text())
    assert on_disk == m
    assert fetch.verify(tmp_path) == [("a.txt", "ok"), ("b.txt", "ok")]
    (tmp_path / "a.txt").write_bytes(b"changed")
    (tmp_path / "b.txt").unlink()
    assert fetch.verify(tmp_path) == [("a.txt", "MISMATCH"), ("b.txt", "missing")]


def test_fetch_keeps_timestamp_when_unchanged(tmp_path):
    sess = FakeSession({"a.txt": b"x", "b.txt": b"y"})
    m1 = fetch.fetch_all(tmp_path, session=sess, sources=SRC)
    m1["files"][0]["retrieved_at"] = "2000-01-01T00:00:00Z"
    (tmp_path / "MANIFEST.json").write_text(json.dumps(m1))
    m2 = fetch.fetch_all(tmp_path, session=sess, sources=SRC)
    assert m2["files"][0]["retrieved_at"] == "2000-01-01T00:00:00Z"


def test_fetch_http_error(tmp_path):
    with pytest.raises(RuntimeError, match="406"):
        fetch.fetch_all(tmp_path, session=FakeSession({"a.txt": b"", "b.txt": b""}, status=406), sources=SRC)


def test_committed_manifest_is_consistent():
    m = fetch.load_manifest()
    names = {e["file"] for e in m["files"]}
    assert {"ZL3b-n.txt", "IT2a-n.txt", "RF1b-e.txt"} <= names
    for e in m["files"]:
        assert len(e["sha256"]) == 64 and e["url"].startswith("https://www.voynich.nu/data/")


def test_gitignore_excludes_third_party_data():
    from msdecipher.paths import repo_root
    gi = (repo_root() / ".gitignore").read_text()
    assert "data/transcriptions/*" in gi and "!data/transcriptions/MANIFEST.json" in gi


def test_images_find_parts(tmp_path):
    for n in ("MS408_part1_pages001-107.pdf", "MS408_part2_pages108-214.pdf", "other.pdf"):
        (tmp_path / n).write_bytes(b"")
    parts = images.find_parts(tmp_path)
    assert [(p.name, s) for p, s in parts] == [("MS408_part1_pages001-107.pdf", 1), ("MS408_part2_pages108-214.pdf", 108)]


@pytest.mark.skipif(shutil.which("pdftoppm") is None or shutil.which("pdfinfo") is None, reason="poppler missing")
def test_extract_pages_with_tiny_pdf(tmp_path):
    # build a 2-page PDF with only stdlib: minimal hand-written PDF
    pdf = tmp_path / "src" / "MS408_part1_pages001-002.pdf"
    pdf.parent.mkdir()
    objs = ["<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] >>"]
    body, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(body))
        body += f"{i} 0 obj\n{o}\nendobj\n".encode()
    x = len(body)
    body += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    for o in offs:
        body += f"{o:010d} 00000 n \n".encode()
    body += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n".encode()
    pdf.write_bytes(body)
    out = images.extract_pages(dpi=30, outdir=tmp_path / "img", source=pdf.parent)
    assert [p.name for p in out] == ["page_001.png", "page_002.png"]
    assert all(p.stat().st_size > 0 for p in out)


def test_cli_stub_and_help(capsys):
    assert main(["segment-glyphs"]) == 2
    assert "NOT IMPLEMENTED" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        main(["--help"])


def test_glyph_segmentation_stub_raises():
    from msdecipher import glyph_segmentation as gs
    assert gs.STATUS == "not implemented"
    with pytest.raises(NotImplementedError):
        gs.segment_page("x.png")


def test_python_dash_m_runs():
    r = subprocess.run([sys.executable, "-m", "msdecipher", "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "undeciphered" in r.stdout
