"""h55: whole-word order inside the line, and one-line paragraph steps (PREREG.md).

No translation claims.
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (
    ROOT / "hypotheses" / "h13_top_word_context",
    ROOT / "hypotheses" / "h30_line_structure",
    ROOT / "hypotheses" / "h47_page_line_generator",
    ROOT / "hypotheses" / "h52_non_boundary_slot_agreement",
    ROOT / "hypotheses" / "h53_paragraph_arc_structure",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import h30_lib  # noqa: E402
import h52_lib as H52  # noqa: E402
import h53_lib as H53  # noqa: E402

HANDS = ("1A", "2B", "3B")
N_PERM = 200
SEED = 55
MIN_PAIRS = 500
EXCESS_MIN = 0.01
Z_MIN = 2.58
GAP_MIN = 0.01
PLANT_ORDER_EXCESS = 0.02
MIN_SIDE = 200
PLANT_STEP_EXCESS = 0.05
MIN_ONSET = 20
MIN_SHARED_ONSETS = 8
SPEAR_MIN = 0.30


def shuffle_lines(slotted: list[list[tuple]], rng: np.random.Generator) -> list[list[tuple]]:
    """Permute whole words inside each line. Slot triples stay attached to their word."""
    out = []
    for line in slotted:
        row = list(line)
        if len(row) >= 2:
            rng.shuffle(row)
        out.append(row)
    return out


def _excess(observed: float, null: np.ndarray) -> dict:
    samples = np.asarray(null, dtype=float)
    finite = samples[np.isfinite(samples)]
    mean = float(finite.mean()) if len(finite) else float("nan")
    sd = float(finite.std()) if len(finite) else float("nan")
    excess = float(observed - mean) if np.isfinite(observed) and np.isfinite(mean) else float("nan")
    z = float(excess / sd) if np.isfinite(sd) and sd >= 1e-12 else 0.0
    return {
        "observed": float(observed) if np.isfinite(observed) else float("nan"),
        "null_mean": mean,
        "null_sd": sd if np.isfinite(sd) else float("nan"),
        "excess": excess,
        "z": z,
        "n_finite": int(len(finite)),
        "null_p95": float(np.sort(finite)[189]) if len(finite) == N_PERM else None,
    }


def score_s1(lines: list[list[str]], mode: str = "eva", n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """F2 against a shuffle of whole words inside each line."""
    slotted = H52.slotted_lines(lines, mode)
    observed = H52.cmi(H52.pair_rows(slotted, "F2", 1))
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm, dtype=float)
    for draw in range(n_perm):
        moved = shuffle_lines(slotted, rng)
        null[draw] = H52.cmi(H52.pair_rows(moved, "F2", 1))["cmi"]
    summary = _excess(observed["cmi"], null)
    summary.update({"cmi": observed["cmi"], "n_pairs": observed["n_pairs"], "n_strata": observed["n_strata"]})
    return summary


def plant_order(lines: list[list[str]], mode: str = "eva") -> list[list[str]]:
    """Stably sort each line by core. Words are otherwise unchanged."""
    slotted = H52.slotted_lines(lines, mode)
    planted = []
    for words, slots in zip(lines, slotted):
        order = sorted(range(len(words)), key=lambda i: slots[i][2])
        planted.append([words[i] for i in order])
    return planted


def _line_pairs(slotted: list[list[tuple[str, str, str]]]) -> list[list[tuple[str, str, tuple]]]:
    rows = []
    for line in slotted:
        pairs = []
        for i in range(len(line) - 1):
            onset_l, end_l, core_l = line[i]
            onset_r, _, core_r = line[i + 1]
            pairs.append((core_l, core_r, (end_l, onset_r)))
        rows.append(pairs)
    return rows


def _gain_from_pairs(lines: list[list[tuple[str, str, tuple]]], pages: list[str]) -> tuple[float, int]:
    """Leave-one-line-out gain of core_t inside each folio."""
    by_page: dict[str, list[int]] = defaultdict(list)
    for i, page in enumerate(pages):
        by_page[page].append(i)
    total = 0.0
    used = 0
    for idxs in by_page.values():
        folio_core: Counter = Counter()
        folio_key: dict[tuple, Counter] = defaultdict(Counter)
        folio_both: dict[tuple, Counter] = defaultdict(Counter)
        n_key: Counter = Counter()
        n_both: Counter = Counter()
        for i in idxs:
            for left, right, key in lines[i]:
                folio_core[left] += 1
                folio_core[right] += 1
                folio_key[key][right] += 1
                n_key[key] += 1
                folio_both[(key, left)][right] += 1
                n_both[(key, left)] += 1
        for i in idxs:
            line_core: Counter = Counter()
            line_key: dict[tuple, Counter] = defaultdict(Counter)
            line_both: dict[tuple, Counter] = defaultdict(Counter)
            line_n_key: Counter = Counter()
            line_n_both: Counter = Counter()
            for left, right, key in lines[i]:
                line_core[left] += 1
                line_core[right] += 1
                line_key[key][right] += 1
                line_n_key[key] += 1
                line_both[(key, left)][right] += 1
                line_n_both[(key, left)] += 1
            alphabet = {core for core, count in folio_core.items() if count - line_core[core] > 0}
            alphabet.add("OTHER")
            vsize = len(alphabet)
            for left, right, key in lines[i]:
                n_train = n_key[key] - line_n_key[key]
                if n_train <= 0:
                    continue
                target = right if right in alphabet else "OTHER"
                left_lab = left if left in alphabet else "OTHER"
                p0 = (folio_key[key][target] - line_key[key][target] + 0.5) / (n_train + 0.5 * vsize)
                both = (key, left_lab)
                p1 = (folio_both[both][target] - line_both[both][target] + 0.5) / (n_both[both] - line_n_both[both] + 0.5 * vsize)
                total += math.log2(p1) - math.log2(p0)
                used += 1
    return (total / used) if used else float("nan"), used


def score_s2(lines: list[list[str]], pages: list[str], mode: str = "eva", n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """Held-out gain of the previous core beyond the junction and the rest of the folio."""
    slotted = H52.slotted_lines(lines, mode)
    observed, n_used = _gain_from_pairs(_line_pairs(slotted), pages)
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm, dtype=float)
    for draw in range(n_perm):
        moved = shuffle_lines(slotted, rng)
        null[draw] = _gain_from_pairs(_line_pairs(moved), pages)[0]
    summary = _excess(observed, null)
    summary.update({"gain": observed, "n_pairs": n_used})
    return summary


def order_pass(ms: dict, copier: dict) -> bool:
    return bool(
        ms["n_pairs"] >= MIN_PAIRS
        and ms["excess"] >= EXCESS_MIN
        and ms["z"] >= Z_MIN
        and (ms["excess"] - copier["excess"]) >= GAP_MIN
    )


def plant_order_pass(plant: dict) -> bool:
    return bool(plant["excess"] >= PLANT_ORDER_EXCESS and plant["z"] >= Z_MIN)


def paragraphs_of(records: list[dict]) -> list[list[list[str]]]:
    groups: list[list[list[str]]] = []
    current: list[list[str]] = []
    page = None
    for rec in records:
        boundary = bool(rec["para_first"]) or (bool(current) and rec["page"] != page)
        if current and boundary:
            groups.append(current)
            current = []
        current.append(list(rec["words"]))
        page = rec["page"]
    if current:
        groups.append(current)
    return groups


def eligible_pairs(lines: list[list[str]]) -> list[int]:
    """Indexes i where both line i and line i+1 have at least 7 words."""
    return [i for i in range(len(lines) - 1) if len(lines[i]) >= 7 and len(lines[i + 1]) >= 7]


def interior(words: list[str]) -> list[str]:
    """Words at least two places in from either end."""
    if len(words) < 7:
        return []
    return list(words[2:-2])


def select_paragraphs(groups: list[list[list[str]]], side: str) -> list[list[list[str]]]:
    kept = []
    for lines in groups:
        elig = eligible_pairs(lines)
        if len(elig) < 2:
            continue
        anchor = 0 if side == "opening" else len(lines) - 2
        if anchor in elig:
            kept.append(lines)
    return kept


def plant_steps(groups: list[list[list[str]]]) -> list[list[list[str]]]:
    """Mark the deep interior of the first line and of the last line."""
    planted = []
    for lines in groups:
        new_lines = []
        last = len(lines) - 1
        for j, line in enumerate(lines):
            words = list(line)
            if len(words) >= 7 and j in (0, last):
                words[2:-2] = ["PLANT" if j == 0 else "ENDPLANT"] * (len(words) - 4)
            new_lines.append(words)
        planted.append(new_lines)
    return planted


def _class_map(words: list[str]) -> dict[str, str]:
    keep = {word for word, _ in Counter(words).most_common(H53.TOP_K)}
    return {word: word if word in keep else "OTHER" for word in set(words)}


def _apply(words: list[str], mapping: dict[str, str]) -> list[str]:
    return [mapping.get(word, "OTHER") for word in words]


def _js(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return float("nan")
    return float(h30_lib.js(Counter(left), Counter(right)))


def _pair_words(lines: list[list[str]], index: int) -> tuple[list[str], list[str]]:
    return interior(lines[index]), interior(lines[index + 1])


def _frozen_words(paras: list[list[list[str]]]) -> list[str]:
    words: list[str] = []
    for lines in paras:
        for index in eligible_pairs(lines):
            left, right = _pair_words(lines, index)
            words.extend(left)
            words.extend(right)
    return words


def _designated_js(paras: list[list[list[str]]], choose, mapping: dict[str, str]) -> tuple[float, int, int]:
    left: list[str] = []
    right: list[str] = []
    for lines in paras:
        index = choose(lines)
        a, b = _pair_words(lines, index)
        left.extend(a)
        right.extend(b)
    return _js(_apply(left, mapping), _apply(right, mapping)), len(left), len(right)


def score_step(paras: list[list[list[str]]], side: str, n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """JS of one designated step against a random neighbouring step in the same paragraphs."""
    mapping = _class_map(_frozen_words(paras))

    def anchor(lines: list[list[str]]) -> int:
        if side == "opening":
            return 0
        if side == "closing":
            return len(lines) - 2
        raise ValueError(side)

    observed, n_left, n_right = _designated_js(paras, anchor, mapping)
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm, dtype=float)
    for draw in range(n_perm):
        def choose(lines: list[list[str]], generator: np.random.Generator = rng) -> int:
            elig = eligible_pairs(lines)
            return int(elig[int(generator.integers(0, len(elig)))])

        null[draw] = _designated_js(paras, choose, mapping)[0]
    summary = _excess(observed, null)
    summary.update({
        "n_left": n_left,
        "n_right": n_right,
        "n_paragraphs": len(paras),
        "scored": bool(n_left >= MIN_SIDE and n_right >= MIN_SIDE and summary["n_finite"] == n_perm and np.isfinite(observed)),
    })
    return summary


def step_pass(ms: dict, copier: dict) -> bool:
    if not ms.get("scored") or not copier.get("scored"):
        return False
    if ms["null_p95"] is None or not np.isfinite(ms["observed"]) or not np.isfinite(ms["excess"]):
        return False
    return bool(ms["observed"] > ms["null_p95"] and ms["excess"] >= EXCESS_MIN and (ms["excess"] - copier["excess"]) >= GAP_MIN)


def plant_step_pass(plant: dict) -> bool:
    if plant.get("null_p95") is None or not np.isfinite(plant.get("observed", float("nan"))):
        return False
    return bool(plant["observed"] > plant["null_p95"] and plant["excess"] >= PLANT_STEP_EXCESS)


def _onset(word: str) -> str:
    units = H52.word_units(word, "eva")
    return units[0] if units else "EMPTY"


def _onset_ratios(paras: list[list[list[str]]], choose) -> dict[str, float]:
    left: list[str] = []
    right: list[str] = []
    for lines in paras:
        index = choose(lines)
        a, b = _pair_words(lines, index)
        left.extend(_onset(word) for word in a)
        right.extend(_onset(word) for word in b)
    left_c, right_c = Counter(left), Counter(right)
    n_left, n_right = len(left), len(right)
    ratios = {}
    for unit in set(left_c) | set(right_c):
        if left_c[unit] + right_c[unit] < MIN_ONSET:
            continue
        ratios[unit] = math.log((right_c[unit] + 0.5) / n_right) - math.log((left_c[unit] + 0.5) / n_left)
    return ratios


def _spearman(left: dict[str, float], right: dict[str, float]) -> tuple[float, int]:
    shared = sorted(set(left) & set(right))
    if len(shared) < 2:
        return float("nan"), len(shared)
    result = stats.spearmanr([left[unit] for unit in shared], [right[unit] for unit in shared])
    rho = getattr(result, "statistic", None)
    if rho is None:
        rho = result.correlation
    return float(rho), len(shared)


def score_shared(by_hand: dict[str, list[list[list[str]]]], side: str, n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """Spearman correlation of the onset shift across hands."""
    pairs = (("1A", "2B"), ("1A", "3B"), ("2B", "3B"))

    def anchor(lines: list[list[str]]) -> int:
        return 0 if side == "opening" else len(lines) - 2

    def correlations(choose) -> dict[str, dict]:
        tables = {hand: _onset_ratios(paras, choose) for hand, paras in by_hand.items()}
        out = {}
        for a, b in pairs:
            rho, n_units = _spearman(tables[a], tables[b])
            out[f"{a}-{b}"] = {"rho": rho, "n_units": n_units, "scored": bool(n_units >= MIN_SHARED_ONSETS and np.isfinite(rho))}
        return out

    observed = correlations(anchor)
    rng = np.random.default_rng(seed)
    null = {name: np.empty(n_perm, dtype=float) for name in observed}
    for draw in range(n_perm):
        def choose(lines: list[list[str]], generator: np.random.Generator = rng) -> int:
            elig = eligible_pairs(lines)
            return int(elig[int(generator.integers(0, len(elig)))])

        draw_corr = correlations(choose)
        for name in null:
            null[name][draw] = draw_corr[name]["rho"]
    results = {}
    for name, cell in observed.items():
        summary = _excess(cell["rho"], null[name])
        passed = bool(
            cell["scored"]
            and summary["null_p95"] is not None
            and np.isfinite(cell["rho"])
            and cell["rho"] >= SPEAR_MIN
            and cell["rho"] > summary["null_p95"]
        )
        results[name] = {**cell, **summary, "pass": passed}
    n_pass = sum(1 for cell in results.values() if cell["pass"])
    return {"pairs": results, "label": "shared" if n_pass >= 2 else "not_shared", "side": side}


def _three_way(n_pass: int, valid: bool, names: tuple[str, str, str]) -> str:
    if not valid:
        return "invalid"
    if n_pass >= 2:
        return names[0]
    if n_pass == 0:
        return names[1]
    return names[2]


def _side_label(valid: bool, n_pass: int) -> str:
    if not valid:
        return "invalid"
    if n_pass >= 2:
        return "pass"
    if n_pass == 0:
        return "none"
    return "one"


def paragraph_label(opening: str, closing: str) -> str:
    labels = [opening, closing]
    if all(label == "invalid" for label in labels):
        return "invalid"
    if any(label == "pass" for label in labels):
        return "role"
    if all(label in ("none", "invalid") for label in labels):
        return "no_role"
    return "partial"


def run(n_perm: int = N_PERM) -> dict:
    """Full pre-registered run."""
    ms_lines = {}
    ms_pages = {}
    copier_lines = {}
    for hand in HANDS:
        records = H53.load_ms_records(hand)
        ms_lines[hand] = [list(rec["words"]) for rec in records]
        ms_pages[hand] = [rec["page"] for rec in records]
        copier_lines[hand] = H52.load_copier_lines(hand)
    print("S1", flush=True)
    s1 = {}
    plants_s1 = {}
    for hand in HANDS:
        s1[f"MS_{hand}"] = score_s1(ms_lines[hand], n_perm=n_perm)
        s1[f"page_line_copier_{hand}"] = score_s1(copier_lines[hand], n_perm=n_perm)
        plants_s1[hand] = score_s1(plant_order(copier_lines[hand]), n_perm=n_perm)
    s1_hands = [h for h in HANDS if order_pass(s1[f"MS_{h}"], s1[f"page_line_copier_{h}"])]
    s1_copier = [h for h in HANDS if _absolute_pass(s1[f"page_line_copier_{h}"])]
    s1_plant = [h for h in HANDS if plant_order_pass(plants_s1[h])]
    s1_valid = len(s1_copier) < 2 and len(s1_plant) >= 2

    print("S2", flush=True)
    s2 = {}
    plants_s2 = {}
    for hand in HANDS:
        s2[f"MS_{hand}"] = score_s2(ms_lines[hand], ms_pages[hand], n_perm=n_perm)
        s2[f"page_line_copier_{hand}"] = score_s2(copier_lines[hand], ms_pages[hand], n_perm=n_perm)
        plants_s2[hand] = score_s2(plant_order(copier_lines[hand]), ms_pages[hand], n_perm=n_perm)
    s2_hands = [h for h in HANDS if order_pass(s2[f"MS_{h}"], s2[f"page_line_copier_{h}"])]
    s2_copier = [h for h in HANDS if _absolute_pass(s2[f"page_line_copier_{h}"])]
    s2_plant = [h for h in HANDS if plant_order_pass(plants_s2[h])]
    s2_valid = len(s2_copier) < 2 and len(s2_plant) >= 2

    print("P", flush=True)
    ms_groups = {h: paragraphs_of(H53.load_ms_records(h)) for h in HANDS}
    copier_groups = {h: paragraphs_of(H53.load_copier_records(h)) for h in HANDS}
    plant_groups = {h: plant_steps(copier_groups[h]) for h in HANDS}
    steps = {}
    plant_steps_scored = {}
    for side in ("opening", "closing"):
        steps[side] = {}
        plant_steps_scored[side] = {}
        for hand in HANDS:
            steps[side][f"MS_{hand}"] = score_step(select_paragraphs(ms_groups[hand], side), side, n_perm=n_perm)
            steps[side][f"page_line_copier_{hand}"] = score_step(select_paragraphs(copier_groups[hand], side), side, n_perm=n_perm)
            plant_steps_scored[side][hand] = score_step(select_paragraphs(plant_groups[hand], side), side, n_perm=n_perm)
    side_info = {}
    for side in ("opening", "closing"):
        hands = [h for h in HANDS if step_pass(steps[side][f"MS_{h}"], steps[side][f"page_line_copier_{h}"])]
        copier_hits = [h for h in HANDS if _step_absolute(steps[side][f"page_line_copier_{h}"])]
        plant_hits = [h for h in HANDS if plant_step_pass(plant_steps_scored[side][h])]
        valid = len(copier_hits) < 2 and len(plant_hits) >= 2
        side_info[side] = {
            "hands": hands if valid else [],
            "copier_hits": copier_hits,
            "plant_hits": plant_hits,
            "valid": valid,
            "label": _side_label(valid, len(hands)),
        }
    role = paragraph_label(side_info["opening"]["label"], side_info["closing"]["label"])
    shared: dict = {"label": "not_run"}
    if role == "role":
        print("X", flush=True)
        side = "opening" if side_info["opening"]["label"] == "pass" else "closing"
        selected = {h: select_paragraphs(ms_groups[h], side) for h in HANDS}
        shared = score_shared(selected, side, n_perm=n_perm)
    return {
        "S1": s1,
        "S1_plant": plants_s1,
        "S1_hands": s1_hands if s1_valid else [],
        "S1_copier_hits": s1_copier,
        "S1_plant_hits": s1_plant,
        "S1_valid": s1_valid,
        "slots": _three_way(len(s1_hands), s1_valid, ("adjacency", "no_adjacency", "partial")),
        "S2": s2,
        "S2_plant": plants_s2,
        "S2_hands": s2_hands if s2_valid else [],
        "S2_copier_hits": s2_copier,
        "S2_plant_hits": s2_plant,
        "S2_valid": s2_valid,
        "bits": _three_way(len(s2_hands), s2_valid, ("bits", "no_bits", "partial_bits")),
        "steps": steps,
        "step_plants": plant_steps_scored,
        "sides": side_info,
        "paragraphs": role,
        "X": shared,
    }


def _absolute_pass(cell: dict) -> bool:
    """The pass inequalities other than the gap against the copier."""
    return bool(cell["n_pairs"] >= MIN_PAIRS and cell["excess"] >= EXCESS_MIN and cell["z"] >= Z_MIN)


def _step_absolute(cell: dict) -> bool:
    if not cell.get("scored") or cell.get("null_p95") is None:
        return False
    return bool(np.isfinite(cell["observed"]) and cell["observed"] > cell["null_p95"] and cell["excess"] >= EXCESS_MIN)

