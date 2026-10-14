"""h52: non-touching slot agreement given the boundary junction (PREREG.md).

No translation claims. Conditional mutual information is estimated only inside
strata with at least 20 pairs, and the null shuffles the right-hand label
inside each stratum.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (
    ROOT / "hypotheses" / "h13_top_word_context",
    ROOT / "hypotheses" / "h30_line_structure",
    ROOT / "hypotheses" / "h47_page_line_generator",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import h13_lib  # noqa: E402
import h30_lib  # noqa: E402
import h47_lib  # noqa: E402

HANDS = ("1A", "2B", "3B")
FEATURES = ("F1", "F2", "F3")
MIN_COUNT = 30
MIN_STRATUM = 20
MIN_PAIRS = 500
N_PERM = 200
SEED = 52
EXCESS_MIN = 0.01
Z_MIN = 2.58
GAP_MIN = 0.01


def word_units(word: str, mode: str) -> tuple[str, ...]:
    """Collapsed EVA units, or characters for a prose control."""
    if mode == "eva":
        return tuple(h13_lib.SEG(word))
    if mode == "char":
        return tuple(word)
    raise ValueError(mode)


def slot_labels(units: tuple[str, ...]) -> tuple[str, str, str]:
    """onset, end, and core (second unit, or SHORT when the word has no interior)."""
    if not units:
        return "EMPTY", "EMPTY", "SHORT"
    onset = units[0]
    end = units[-1]
    core = units[1] if len(units) >= 3 else "SHORT"
    return onset, end, core


def bucket_map(labels: list[str], min_count: int = MIN_COUNT) -> dict[str, str]:
    """Map rare labels to OTHER. SHORT is kept even when it is rare."""
    counts = Counter(labels)
    out = {}
    for lab in counts:
        if lab == "SHORT" or counts[lab] >= min_count:
            out[lab] = lab
        else:
            out[lab] = "OTHER"
    return out


def slotted_lines(lines: list[list[str]], mode: str) -> list[list[tuple[str, str, str]]]:
    """Bucket onset, end, and core on the whole stream, then label every word."""
    raw: list[list[tuple[str, str, str]]] = []
    onsets: list[str] = []
    ends: list[str] = []
    cores: list[str] = []
    for line in lines:
        row = []
        for word in line:
            onset, end, core = slot_labels(word_units(word, mode))
            row.append((onset, end, core))
            onsets.append(onset)
            ends.append(end)
            cores.append(core)
        raw.append(row)
    onset_map = bucket_map(onsets)
    end_map = bucket_map(ends)
    core_map = bucket_map(cores)
    return [
        [(onset_map[o], end_map[e], core_map[c]) for o, e, c in line]
        for line in raw
    ]


def pair_rows(slotted: list[list[tuple[str, str, str]]], feature: str, lag: int) -> list[tuple[str, str, tuple]]:
    """Within-line pairs. The row is (left slot, right slot, conditioning stratum)."""
    if feature not in FEATURES:
        raise ValueError(feature)
    if lag < 1:
        raise ValueError(lag)
    rows: list[tuple[str, str, tuple]] = []
    for line in slotted:
        if len(line) <= lag:
            continue
        for i in range(len(line) - lag):
            onset_l, end_l, core_l = line[i]
            onset_r, end_r, core_r = line[i + lag]
            if feature == "F1":
                rows.append((onset_l, end_r, (end_l, onset_r)))
            elif feature == "F2":
                rows.append((core_l, core_r, (end_l, onset_r)))
            elif feature == "F3":
                rows.append((end_l, end_r, (onset_r,)))
            else:
                raise AssertionError(feature)
    return rows


def _mi(left: list[str], right: list[str]) -> float:
    n = len(left)
    if n == 0:
        return 0.0
    joint = Counter(zip(left, right))
    left_c = Counter(left)
    right_c = Counter(right)
    total = 0.0
    for (a, b), v in joint.items():
        total += v / n * math.log2(v * n / (left_c[a] * right_c[b]))
    return total


def cmi(rows: list[tuple[str, str, tuple]], min_stratum: int = MIN_STRATUM) -> dict:
    """I(L; R | K) over strata with at least `min_stratum` pairs."""
    groups: dict[tuple, list[tuple[str, str]]] = defaultdict(list)
    for left, right, key in rows:
        groups[key].append((left, right))
    weighted = 0.0
    n_pairs = 0
    n_strata = 0
    for pairs in groups.values():
        if len(pairs) < min_stratum:
            continue
        left = [a for a, _ in pairs]
        right = [b for _, b in pairs]
        weighted += len(pairs) * _mi(left, right)
        n_pairs += len(pairs)
        n_strata += 1
    return {
        "cmi": (weighted / n_pairs) if n_pairs else 0.0,
        "n_pairs": n_pairs,
        "n_strata": n_strata,
    }


def permute_cmi(rows: list[tuple[str, str, tuple]], n_perm: int, seed: int, min_stratum: int = MIN_STRATUM) -> np.ndarray:
    """Shuffle R inside every stratum. Each call uses its own Generator(seed)."""
    rng = np.random.default_rng(seed)
    groups: dict[tuple, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        groups[row[2]].append(i)
    usable = [idx for idx in groups.values() if len(idx) >= min_stratum]
    lefts = [row[0] for row in rows]
    base_rights = [row[1] for row in rows]
    out = np.empty(n_perm, dtype=float)
    for draw in range(n_perm):
        rights = base_rights.copy()
        for idx in groups.values():
            if len(idx) < 2:
                continue
            vals = [rights[i] for i in idx]
            rng.shuffle(vals)
            for i, val in zip(idx, vals):
                rights[i] = val
        weighted = 0.0
        n_pairs = 0
        for idx in usable:
            left = [lefts[i] for i in idx]
            right = [rights[i] for i in idx]
            weighted += len(idx) * _mi(left, right)
            n_pairs += len(idx)
        out[draw] = (weighted / n_pairs) if n_pairs else 0.0
    return out


def score_rows(rows: list[tuple[str, str, tuple]], n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """Observed conditional MI, excess over the stratum shuffle, and z."""
    observed = cmi(rows)
    null = permute_cmi(rows, n_perm, seed)
    null_mean = float(null.mean()) if len(null) else 0.0
    null_sd = float(null.std()) if len(null) else 0.0
    excess = float(observed["cmi"] - null_mean)
    z = float(excess / null_sd) if null_sd >= 1e-12 else 0.0
    return {
        "cmi": observed["cmi"],
        "n_pairs": observed["n_pairs"],
        "n_strata": observed["n_strata"],
        "null_mean": null_mean,
        "null_sd": null_sd,
        "excess": excess,
        "z": z,
        "n_perm": n_perm,
        "seed": seed,
    }


def bind_rights_to_lefts(rows: list[tuple[str, str, tuple]]) -> list[tuple[str, str, tuple]]:
    """Validity stream: the right slot is a copy of the left slot."""
    return [(left, left, key) for left, _, key in rows]


def cell_passes(ms: dict, copier: dict) -> bool:
    """G1 cell rule from PREREG.md."""
    return bool(
        ms["n_pairs"] >= MIN_PAIRS
        and ms["excess"] >= EXCESS_MIN
        and ms["z"] >= Z_MIN
        and (ms["excess"] - copier["excess"]) >= GAP_MIN
    )


def copier_accounts(ms: dict, copier: dict) -> bool:
    """One cell of G2: no reliable excess, or the excess matches the copier."""
    return bool(ms["z"] < Z_MIN or abs(ms["excess"] - copier["excess"]) <= GAP_MIN)


def load_ms_lines(hand: str) -> list[list[str]]:
    return [list(rec["words"]) for rec in h47_lib.load_template(hand)]


def load_copier_lines(hand: str) -> list[list[str]]:
    blob = json.loads(
        (ROOT / "hypotheses" / "h47_page_line_generator" / "results" / "streams.json").read_text(encoding="utf-8")
    )
    generated = blob["generated_lines"][f"page_line_copier_{hand}"]
    template = h47_lib.load_template(hand)
    if len(generated) != len(template):
        raise RuntimeError(f"{hand}: line count {len(generated)} != template {len(template)}")
    for i, (line, rec) in enumerate(zip(generated, template)):
        if len(line) != len(rec["words"]):
            raise RuntimeError(f"{hand}: line {i} length mismatch")
    return [list(line) for line in generated]


def load_prose_lines(fname: str) -> list[list[str]]:
    return [list(rec["words"]) for rec in h30_lib.load_control(fname)]


def score_stream(lines: list[list[str]], mode: str, n_perm: int = N_PERM) -> dict:
    """Lag-1 F1, F2, F3 and lag-2 F1, F2 for one stream."""
    slotted = slotted_lines(lines, mode)
    out = {"n_lines": len(lines), "n_tokens": sum(len(line) for line in lines), "lag1": {}, "lag2": {}}
    for feature in FEATURES:
        out["lag1"][feature] = score_rows(pair_rows(slotted, feature, 1), n_perm=n_perm)
    for feature in ("F1", "F2"):
        out["lag2"][feature] = score_rows(pair_rows(slotted, feature, 2), n_perm=n_perm)
    return out


def evaluate(streams: dict, synthetic: dict) -> dict:
    """G1, G2, and the validity check. Prose does not enter the verdict."""
    valid = bool(synthetic["excess"] >= 0.05 and synthetic["z"] >= 5.0)
    by_feature = {}
    for feature in ("F1", "F2"):
        hands = []
        for hand in HANDS:
            ms = streams[f"MS_{hand}"]["lag1"][feature]
            copier = streams[f"page_line_copier_{hand}"]["lag1"][feature]
            hands.append(hand if cell_passes(ms, copier) else None)
        by_feature[feature] = [h for h in hands if h]
    g1_feature = next((f for f in ("F1", "F2") if len(by_feature[f]) >= 2), None)
    g1 = g1_feature is not None
    g2_cells = []
    for feature in ("F1", "F2"):
        for hand in HANDS:
            ms = streams[f"MS_{hand}"]["lag1"][feature]
            copier = streams[f"page_line_copier_{hand}"]["lag1"][feature]
            g2_cells.append(copier_accounts(ms, copier))
    g2 = (not g1) and all(g2_cells)
    if not valid:
        verdict = "invalid"
    elif g1:
        verdict = "supported"
    elif g2:
        verdict = "refuted"
    else:
        verdict = "mixed"
    return {
        "valid": valid,
        "G1": g1,
        "G1_feature": g1_feature,
        "G1_hands": by_feature,
        "G2": g2,
        "verdict": verdict,
    }
