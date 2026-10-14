"""h40: paragraph lines under five transcription readings. No decipherment claims."""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _rel in (
    "src",
    "hypotheses/h09_image_context_cribs",
    "hypotheses/h13_top_word_context",
    "hypotheses/h14_line_position_controls",
    "hypotheses/h19_heldout_likelihood",
    "hypotheses/h30_line_structure",
    "hypotheses/h33_word_boundary_resegmentation",
):
    sys.path.insert(0, str(ROOT / _rel))

import h09_lib  # noqa: E402
import h13_lib  # noqa: E402
import h30_lib  # noqa: E402
import h33_lib  # noqa: E402

HANDS = ("1A", "2B", "3B")
# file name, delete commas before the h13 split
CONDITIONS = {
    "zl_split": ("ZL3b-n.txt", False),
    "zl_join": ("ZL3b-n.txt", True),
    "it2a": ("IT2a-n.txt", False),
    "rf_split": ("RF1b-e.txt", False),
    "rf_join": ("RF1b-e.txt", True),
}
CAP = 10326
_TOKENS_RAW = h13_lib.tokens_raw
_ORIGINAL_TR = h09_lib.TR
_TRANSCRIPTIONS = ROOT / "data" / "transcriptions"


def _comma_deleted(txt: str):
    """h13 splits on [.,\\s]; deleting the comma first glues the two sides."""
    return _TOKENS_RAW(txt.replace(",", ""))


def locus_tokens(txt: str, join: bool) -> list[str]:
    """Token strings for one locus line. join deletes commas before the h13 split."""
    raw = txt.replace(",", "") if join else txt
    toks, _para = _TOKENS_RAW(raw)
    return [w for w, _ok in toks]


def loader_restored() -> bool:
    return h09_lib.TR == _ORIGINAL_TR and h13_lib.H9.TR == _ORIGINAL_TR and h13_lib.tokens_raw is _TOKENS_RAW


@contextmanager
def applied_transcription(condition: str):
    """Point h09/h13 at one transcription. Join conditions delete commas. Always restored."""
    fname, join = CONDITIONS[condition]
    saved_tr = h09_lib.TR
    saved_h9 = h13_lib.H9.TR
    saved_raw = h13_lib.tokens_raw
    path = _TRANSCRIPTIONS / fname
    h09_lib.TR = path
    h13_lib.H9.TR = path
    if join:
        h13_lib.tokens_raw = _comma_deleted
    try:
        yield path
    finally:
        h09_lib.TR = saved_tr
        h13_lib.H9.TR = saved_h9
        h13_lib.tokens_raw = saved_raw


def load_paragraphs(hand: str, condition: str) -> list[list[str]]:
    """Paragraph-line word lists for one hand, via h30_lib.load_ms under a temporary loader swap."""
    with applied_transcription(condition):
        return [list(line["words"]) for line in h30_lib.load_ms(hand)]


def cap_lines(lines: list[list[str]], n: int = CAP) -> list[list[str]]:
    out: list[list[str]] = []
    k = 0
    for line in lines:
        if k >= n:
            break
        out.append(line)
        k += len(line)
    return out


def measure(lines: list[list[str]]) -> dict:
    """S on full and interior lines, junction on full lines. Same cap and seed as h33."""
    capped = cap_lines(lines, CAP)
    full = [line for line in capped if len(line) >= 2]
    interior = [line[1:-1] for line in capped if len(line) >= 4]
    s_full = h33_lib.space_predict(full)["entropy_removed"]
    s_interior = h33_lib.space_predict(interior)["entropy_removed"]
    junction = h33_lib.junction(full, np.random.default_rng(33))
    junction_interior = h33_lib.junction(interior, np.random.default_rng(33))
    return {
        "S_full": float(s_full),
        "S_interior": float(s_interior),
        "junction": float(junction),
        "junction_interior": float(junction_interior),
        "n_tokens_full": int(sum(len(line) for line in full)),
        "n_tokens_interior": int(sum(len(line) for line in interior)),
        "n_lines_capped": int(len(capped)),
    }
