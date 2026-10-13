"""h28: permutations of the real Naibbe tables. No translation claims.

Shuffle seed for every condition is 4000 + s. Encryption seed stays s.
"""
from __future__ import annotations

import csv
import random
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h19_heldout_likelihood"))

from msdecipher.mech_naibbe import ALPHABET, TABLES  # noqa: E402
import run_h19  # noqa: E402

NAIBBE = (ROOT / "data" / "mechanisms" / "naibbe_tables.csv").resolve()
TABLES_DIR = HERE / "tables"
STATES = ("unigram", "prefix", "suffix")
CONDITIONS = ("letter", "state", "unit")
SEEDS = (1, 2, 3, 4, 5)
DIST_MAX = 5.43
RATE4_MIN = 0.60
ANCHOR_DIST = 3.43
EXPECT_MATCH = {"letter": True, "state": False, "unit": False}
PREDICTION_ID = {"letter": "A1", "state": "A2", "unit": "A3"}
_TABLE_NAME = re.compile(r"^h28_(letter|state|unit)_s[1-5]\.csv$")


def shuffle_seed(s: int) -> int:
    return 4000 + s


def segmenter():
    return run_h19.seg_fn("eva")


def cell_name(cond: str, s: int) -> str:
    if cond not in CONDITIONS or s not in SEEDS:
        raise ValueError((cond, s))
    return f"T_boccaccio_{cond}_s{s}"


def table_path(cond: str, s: int) -> Path:
    if cond not in CONDITIONS or s not in SEEDS:
        raise ValueError((cond, s))
    return TABLES_DIR / f"h28_{cond}_s{s}.csv"


def load_rows(path: Path | None = None) -> list[dict]:
    src = NAIBBE if path is None else Path(path)
    with src.open(encoding="utf-8", newline="") as f:
        return [{"code": r["code"], "glyphs": r["glyphs"]} for r in csv.DictReader(f)]


def validate_real(rows: list[dict]) -> None:
    need = {f"{st}_{tb}_{lt}" for st in STATES for tb in TABLES for lt in ALPHABET}
    got = [r["code"] for r in rows]
    if len(got) != len(need) or set(got) != need:
        raise SystemExit(f"Naibbe table is not the 3×6×23 grid ({len(got)} rows)")
    if any(r["glyphs"] == "" for r in rows):
        raise SystemExit("empty glyph string in the Naibbe table")


def _parse(code: str) -> tuple[str, str, str]:
    state, table, letter = code.split("_")
    return state, table, letter


def _letter_key(code: str) -> int:
    return ALPHABET.index(_parse(code)[2])


def _copy(rows: list[dict], glyphs: dict[str, str]) -> list[dict]:
    return [{"code": r["code"], "glyphs": glyphs[r["code"]]} for r in rows]


def permute_letter(rows: list[dict], seed: int) -> list[dict]:
    """Shuffle the glyph strings across letters inside each (state, table)."""
    rng = random.Random(seed)
    glyphs = {r["code"]: r["glyphs"] for r in rows}
    groups: dict[tuple[str, str], list[str]] = {}
    for r in rows:
        state, table, _letter = _parse(r["code"])
        groups.setdefault((state, table), []).append(r["code"])
    for key in sorted(groups, key=lambda k: (STATES.index(k[0]), TABLES.index(k[1]))):
        codes = sorted(groups[key], key=_letter_key)
        vals = [glyphs[c] for c in codes]
        rng.shuffle(vals)
        for code, val in zip(codes, vals):
            glyphs[code] = val
    return _copy(rows, glyphs)


def permute_state(rows: list[dict], seed: int) -> list[dict]:
    """Keep unigram strings. Shuffle the pooled prefix+suffix strings within each table."""
    rng = random.Random(seed)
    glyphs = {r["code"]: r["glyphs"] for r in rows}
    by_table: dict[str, list[str]] = {}
    for r in rows:
        state, table, _letter = _parse(r["code"])
        if state == "unigram":
            continue
        if state not in ("prefix", "suffix"):
            raise ValueError(state)
        by_table.setdefault(table, []).append(r["code"])
    for table in sorted(by_table, key=TABLES.index):
        codes = sorted(by_table[table], key=lambda c: (0 if _parse(c)[0] == "prefix" else 1, _letter_key(c)))
        vals = [glyphs[c] for c in codes]
        rng.shuffle(vals)
        for code, val in zip(codes, vals):
            glyphs[code] = val
    return _copy(rows, glyphs)


def assert_roundtrip(rows: list[dict], seg) -> None:
    """Every original table string must satisfy ''.join(seg(s)) == s."""
    for r in rows:
        parts = seg(r["glyphs"])
        if "".join(parts) != r["glyphs"]:
            raise SystemExit(
                f"segmentation does not round-trip: {r['code']} {r['glyphs']!r} -> {parts!r}"
            )


def permute_unit(rows: list[dict], seed: int, seg=None) -> tuple[list[dict], int]:
    """Shuffle collapsed EVA units inside each original string. Returns (rows, n_changed)."""
    seg = segmenter() if seg is None else seg
    assert_roundtrip(rows, seg)
    rng = random.Random(seed)
    out = []
    changed = 0
    for r in rows:
        orig = list(seg(r["glyphs"]))
        units = orig.copy()
        rng.shuffle(units)
        if units != orig:
            changed += 1
        out.append({"code": r["code"], "glyphs": "".join(units)})
    return out, changed


def permute(rows: list[dict], cond: str, s: int, seg=None):
    """Apply one pre-registered permutation. s is the encryption seed, 1..5."""
    seed = shuffle_seed(s)
    if cond == "letter":
        return permute_letter(rows, seed), None
    if cond == "state":
        return permute_state(rows, seed), None
    if cond == "unit":
        return permute_unit(rows, seed, seg)
    raise ValueError(cond)


def _group_counters(rows: list[dict], states: tuple[str, ...]) -> dict:
    grouped: dict[tuple[str, str], list[str]] = {}
    for r in rows:
        state, table, _letter = _parse(r["code"])
        if state not in states:
            continue
        grouped.setdefault((state, table), []).append(r["glyphs"])
    return {k: Counter(v) for k, v in grouped.items()}


def _affix_counters(rows: list[dict]) -> dict:
    """Prefix and suffix strings pooled per table."""
    grouped: dict[str, list[str]] = {}
    for r in rows:
        state, table, _letter = _parse(r["code"])
        if state == "unigram":
            continue
        grouped.setdefault(table, []).append(r["glyphs"])
    return {k: Counter(v) for k, v in grouped.items()}


def assert_permutation(cond: str, original: list[dict], permuted: list[dict], seg=None) -> None:
    if [r["code"] for r in original] != [r["code"] for r in permuted]:
        raise SystemExit("permutation changed codes or their order")
    if cond == "letter":
        if _group_counters(original, STATES) != _group_counters(permuted, STATES):
            raise SystemExit("letter permutation changed a (state, table) multiset")
        return
    if cond == "state":
        before = {r["code"]: r["glyphs"] for r in original if _parse(r["code"])[0] == "unigram"}
        after = {r["code"]: r["glyphs"] for r in permuted if _parse(r["code"])[0] == "unigram"}
        if before != after:
            raise SystemExit("state permutation changed a unigram string")
        if _affix_counters(original) != _affix_counters(permuted):
            raise SystemExit("state permutation changed a table's prefix+suffix multiset")
        return
    if cond == "unit":
        seg = segmenter() if seg is None else seg
        for a, b in zip(original, permuted):
            if Counter(seg(a["glyphs"])) != Counter(seg(b["glyphs"])):
                raise SystemExit(f"unit permutation changed the unit multiset of {a['code']}")
        return
    raise ValueError(cond)


def unit_change_report(rows: list[dict] | None = None, seg=None) -> dict:
    rows = load_rows() if rows is None else rows
    seg = segmenter() if seg is None else seg
    by_seed = {}
    changed = 0
    for s in SEEDS:
        _out, n_changed = permute_unit(rows, shuffle_seed(s), seg)
        by_seed[str(s)] = {"changed": n_changed, "n": len(rows), "share": n_changed / len(rows)}
        changed += n_changed
    total = len(rows) * len(SEEDS)
    return {
        "unit_change_share": changed / total,
        "changed": changed,
        "n": total,
        "n_strings": len(rows),
        "n_one_unit": sum(len(seg(r["glyphs"])) == 1 for r in rows),
        "by_seed": by_seed,
    }


def write_table(path: Path, rows: list[dict]) -> None:
    path = Path(path)
    resolved = path.resolve()
    if resolved == NAIBBE:
        raise SystemExit(f"refusing to write the original Naibbe table at {NAIBBE}")
    tables = TABLES_DIR.resolve()
    if resolved.parent != tables or _TABLE_NAME.match(resolved.name) is None:
        raise SystemExit(f"refusing to write outside the h28 tables directory: {resolved}")
    tables.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    try:
        with tmp.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(["code", "glyphs"])
            for r in rows:
                writer.writerow([r["code"], r["glyphs"]])
        tmp.replace(path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


def condition_matches(dist_mean: float, rate4: float) -> bool:
    return dist_mean <= DIST_MAX and rate4 >= RATE4_MIN


def prediction_pass(cond: str, matched: bool) -> bool:
    if cond not in EXPECT_MATCH:
        raise ValueError(cond)
    return bool(matched) is EXPECT_MATCH[cond]


def reading(letter_match: bool, state_match: bool, unit_match: bool) -> str:
    """Reading from the three match calls. A call passes when that condition matches."""
    if letter_match and not unit_match:
        return "orthography"
    if (not state_match) and letter_match and unit_match:
        return "complementarity"
    if letter_match and state_match and unit_match:
        return "length+homophony"
    if not letter_match and not state_match and not unit_match:
        return "none"
    return "unlisted"
