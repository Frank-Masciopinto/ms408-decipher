"""h54: kill tests for the h52 slot residual and the h53 paragraph residual.

No translation claims. Pass rules are in PREREG.md.
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
    ROOT / "hypotheses" / "h42_near_repeat_decay",
    ROOT / "hypotheses" / "h47_page_line_generator",
    ROOT / "hypotheses" / "h52_non_boundary_slot_agreement",
    ROOT / "hypotheses" / "h53_paragraph_arc_structure",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import h30_lib  # noqa: E402
import h42_lib  # noqa: E402
import h52_lib as H52  # noqa: E402
import h53_lib as H53  # noqa: E402

HANDS = ("1A", "2B", "3B")
N_PERM = 200
SEED = 54
EXCESS_MIN = 0.01
Z_MIN = 2.58
GAP_MIN = 0.01
MIN_PAIRS = 500
MIN_SIDE = 200
MIN_B3 = 150
MIN_SPEAR_TYPES = 15
SPEAR_MIN = 0.30


def is_near_copy(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    """Identical, one unit edit, or the same non-empty interior."""
    if left == right or h42_lib.edit1(left, right):
        return True
    left_stem = left[1:-1]
    right_stem = right[1:-1]
    return len(left_stem) > 0 and left_stem == right_stem


def unit_lines(lines: list[list[str]], mode: str) -> list[list[tuple[str, ...]]]:
    return [[H52.word_units(word, mode) for word in line] for line in lines]


def f2_rows(
    slotted: list[list[tuple[str, str, str]]],
    units: list[list[tuple[str, ...]]],
    drop_near: bool,
) -> list[tuple[str, str, tuple]]:
    """F2 pairs. Near-copies are optional drops, judged on raw units."""
    rows: list[tuple[str, str, tuple]] = []
    for line, raw in zip(slotted, units):
        for i in range(len(line) - 1):
            if drop_near and is_near_copy(raw[i], raw[i + 1]):
                continue
            onset_l, end_l, core_l = line[i]
            onset_r, _, core_r = line[i + 1]
            rows.append((core_l, core_r, (end_l, onset_r)))
    return rows


def permute_cores(slotted: list[list[tuple[str, str, str]]], rng: np.random.Generator):
    """Move core labels inside each line. Onsets and ends stay put."""
    out = []
    for line in slotted:
        cores = [core for _, _, core in line]
        if len(cores) >= 2:
            rng.shuffle(cores)
        out.append([(onset, end, core) for (onset, end, _), core in zip(line, cores)])
    return out


def _excess(observed: float, null: np.ndarray) -> dict:
    samples = np.asarray(null, dtype=float)
    finite = samples[np.isfinite(samples)]
    mean = float(finite.mean()) if len(finite) else float("nan")
    sd = float(finite.std()) if len(finite) else float("nan")
    excess = float(observed - mean) if np.isfinite(mean) else float("nan")
    if not np.isfinite(sd) or sd < 1e-12:
        z = 0.0
    else:
        z = float(excess / sd)
    return {
        "observed": float(observed) if np.isfinite(observed) else float("nan"),
        "null_mean": mean,
        "null_sd": sd if np.isfinite(sd) else float("nan"),
        "excess": excess,
        "z": z,
        "n_finite": int(len(finite)),
        "null_p95": float(np.sort(finite)[189]) if len(finite) == N_PERM else None,
    }


def score_a1(lines: list[list[str]], mode: str = "eva", n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """F2 after near-copy pairs are removed. Null is the h52 stratum shuffle."""
    slotted = H52.slotted_lines(lines, mode)
    rows = f2_rows(slotted, unit_lines(lines, mode), drop_near=True)
    scored = H52.score_rows(rows, n_perm=n_perm, seed=seed)
    return {
        "cmi": scored["cmi"],
        "n_pairs": scored["n_pairs"],
        "n_strata": scored["n_strata"],
        "excess": scored["excess"],
        "z": scored["z"],
        "null_mean": scored["null_mean"],
        "null_sd": scored["null_sd"],
    }


def score_a2(lines: list[list[str]], mode: str = "eva", n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """F2 against a shuffle of cores inside each line."""
    slotted = H52.slotted_lines(lines, mode)
    rows = H52.pair_rows(slotted, "F2", 1)
    observed = H52.cmi(rows)
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm, dtype=float)
    for draw in range(n_perm):
        moved = permute_cores(slotted, rng)
        null[draw] = H52.cmi(H52.pair_rows(moved, "F2", 1))["cmi"]
    summary = _excess(observed["cmi"], null)
    summary.update({"n_pairs": observed["n_pairs"], "n_strata": observed["n_strata"], "cmi": observed["cmi"]})
    return summary


def slot_pass(ms: dict, copier: dict) -> bool:
    """Shared four-part rule for A1 and A2."""
    return bool(
        ms["n_pairs"] >= MIN_PAIRS
        and ms["excess"] >= EXCESS_MIN
        and ms["z"] >= Z_MIN
        and (ms["excess"] - copier["excess"]) >= GAP_MIN
    )


def paragraphs_of(records: list[dict]) -> list[dict]:
    """Paragraph word-lists, with a flag for a folio-opening paragraph."""
    folio_first: set[int] = set()
    seen: set[str] = set()
    for i, rec in enumerate(records):
        if rec["page"] not in seen:
            seen.add(rec["page"])
            folio_first.add(i)
    groups: list[dict] = []
    current: list[list[str]] = []
    page = None
    start = 0
    for i, rec in enumerate(records):
        boundary = bool(rec["para_first"]) or (bool(current) and rec["page"] != page)
        if current and boundary:
            groups.append({"start": start, "folio_first": start in folio_first, "lines": current})
            current = []
            start = i
        current.append(list(rec["words"]))
        page = rec["page"]
    if current:
        groups.append({"start": start, "folio_first": start in folio_first, "lines": current})
    return groups


def _interiors(lines: list[list[str]]) -> list[str]:
    return [word for line in lines for word in H53.line_interior(line)]


def _class_map(words: list[str]) -> dict[str, str]:
    keep = {word for word, _ in Counter(words).most_common(H53.TOP_K)}
    return {word: word if word in keep else "OTHER" for word in set(words)}


def _apply(words: list[str], mapping: dict[str, str]) -> list[str]:
    return [mapping.get(word, "OTHER") for word in words]


def _js(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return float("nan")
    return float(h30_lib.js(Counter(left), Counter(right)))


def _word_js(paras: list[list[list[str]]], mapping: dict[str, str]) -> tuple[float, int, int]:
    opening: list[str] = []
    closing: list[str] = []
    for para in paras:
        opening.extend(H53.line_interior(para[0]))
        closing.extend(H53.line_interior(para[-1]))
    return _js(_apply(opening, mapping), _apply(closing, mapping)), len(opening), len(closing)


def score_role(paras: list[list[list[str]]], n_perm: int = N_PERM, seed: int = SEED, floor: int = MIN_SIDE) -> dict:
    """Opening-vs-closing JS and a within-paragraph line shuffle."""
    mapping = _class_map(_interiors([line for para in paras for line in para]))
    observed, n_open, n_close = _word_js(paras, mapping)
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm, dtype=float)
    for draw in range(n_perm):
        shuffled = []
        for para in paras:
            order = [list(line) for line in para]
            rng.shuffle(order)
            shuffled.append(order)
        null[draw] = _word_js(shuffled, mapping)[0]
    summary = _excess(observed, null)
    summary.update({
        "n_open": n_open,
        "n_close": n_close,
        "n_paragraphs": len(paras),
        "scored": bool(n_open >= floor and n_close >= floor and summary["n_finite"] == n_perm),
    })
    return summary


def select_b3(lines: list[list[str]]) -> tuple[list[str], list[str], list[str], list[str]] | None:
    """Opening, closing, earliest long middle, latest long middle. None if the paragraph does not qualify."""
    if len(lines) < 4 or len(lines[0]) < 6 or len(lines[-1]) < 6:
        return None
    middles = [i for i in range(1, len(lines) - 1) if len(lines[i]) >= 6]
    if len(middles) < 2:
        return None
    return lines[0], lines[-1], lines[middles[0]], lines[middles[-1]]


def b3_bags(groups: list[dict]) -> list[list[list[str]]]:
    """Paragraphs eligible for B3, as full line lists."""
    kept = []
    for group in groups:
        if group["folio_first"]:
            continue
        if select_b3(group["lines"]) is None:
            continue
        kept.append(group["lines"])
    return kept


def _four(paras: list[list[list[str]]]) -> tuple[list[str], list[str], list[str], list[str]]:
    opening: list[str] = []
    closing: list[str] = []
    early: list[str] = []
    late: list[str] = []
    for para in paras:
        chosen = select_b3(para)
        if chosen is None:
            continue
        open_line, close_line, early_line, late_line = chosen
        opening.extend(H53.line_interior(open_line))
        closing.extend(H53.line_interior(close_line))
        early.extend(H53.line_interior(early_line))
        late.extend(H53.line_interior(late_line))
    return opening, closing, early, late


def score_b3(paras: list[list[list[str]]], n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """D = JS(open, close) − JS(earlier middle, later middle)."""
    opening, closing, early, late = _four(paras)
    mapping = _class_map(opening + closing + early + late)

    def difference(groups: list[list[list[str]]]) -> float:
        o, c, e, l = _four(groups)
        return _js(_apply(o, mapping), _apply(c, mapping)) - _js(_apply(e, mapping), _apply(l, mapping))

    observed = difference(paras)
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm, dtype=float)
    for draw in range(n_perm):
        shuffled = []
        for para in paras:
            order = [list(line) for line in para]
            rng.shuffle(order)
            shuffled.append(order)
        null[draw] = difference(shuffled)
    summary = _excess(observed, null)
    counts = (len(opening), len(closing), len(early), len(late))
    summary.update({
        "n_open": counts[0],
        "n_close": counts[1],
        "n_early": counts[2],
        "n_late": counts[3],
        "n_paragraphs": len(paras),
        "scored": bool(min(counts) >= MIN_B3 and summary["n_finite"] == n_perm and np.isfinite(observed)),
    })
    return summary


def role_pass(ms: dict, copier: dict) -> bool:
    if not ms["scored"] or not copier["scored"]:
        return False
    if ms["null_p95"] is None or not np.isfinite(ms["observed"]) or not np.isfinite(ms["excess"]):
        return False
    return bool(
        ms["observed"] > ms["null_p95"]
        and ms["excess"] >= EXCESS_MIN
        and (ms["excess"] - copier["excess"]) >= GAP_MIN
    )


def b_label(n_pass: int) -> str:
    if n_pass >= 2:
        return "stands"
    if n_pass == 0:
        return "killed"
    return "partial"


def overall_label(slots: str, paragraphs: str) -> str:
    if slots == "stands" and paragraphs == "stands":
        return "both_stand"
    if slots == "stands":
        return "slots_only"
    if paragraphs == "stands":
        return "paragraphs_only"
    if slots == "killed" and paragraphs == "killed":
        return "both_killed"
    return "mixed"


def normalize_edy(word: str) -> str:
    if word.endswith("edy"):
        return word[:-3] + "ol"
    return word


def log_ratios(opening: list[str], closing: list[str], floor: int = 8) -> dict[str, float]:
    """Close-versus-open log rate after edy→ol pooling."""
    open_counts: Counter[str] = Counter(normalize_edy(word) for word in opening)
    close_counts: Counter[str] = Counter(normalize_edy(word) for word in closing)
    n_open = sum(open_counts.values())
    n_close = sum(close_counts.values())
    ratios = {}
    for word in set(open_counts) | set(close_counts):
        if open_counts[word] + close_counts[word] < floor:
            continue
        ratios[word] = math.log((close_counts[word] + 0.5) / n_close) - math.log((open_counts[word] + 0.5) / n_open)
    return ratios


def spearman(left: dict[str, float], right: dict[str, float]) -> tuple[float, int]:
    shared = sorted(set(left) & set(right))
    if len(shared) < 2:
        return float("nan"), len(shared)
    result = stats.spearmanr([left[w] for w in shared], [right[w] for w in shared])
    rho = getattr(result, "statistic", None)
    if rho is None:
        rho = result.correlation
    return float(rho), len(shared)


def _b3_ends(paras: list[list[list[str]]]) -> tuple[list[str], list[str]]:
    opening, closing, _, _ = _four(paras)
    return opening, closing


def score_shared(by_hand: dict[str, list[list[list[str]]]], n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """Spearman of closing log-ratios across hands, with a line-swap null."""
    pairs = (("1A", "2B"), ("1A", "3B"), ("2B", "3B"))
    original = {hand: log_ratios(*_b3_ends(paras)) for hand, paras in by_hand.items()}

    def correlations(tables: dict[str, dict[str, float]]) -> dict[str, dict]:
        out = {}
        for a, b in pairs:
            rho, n_types = spearman(tables[a], tables[b])
            out[f"{a}-{b}"] = {"rho": rho, "n_types": n_types, "scored": bool(n_types >= MIN_SPEAR_TYPES and np.isfinite(rho))}
        return out

    observed = correlations(original)
    rng = np.random.default_rng(seed)
    null = {name: np.empty(n_perm, dtype=float) for name in observed}
    for draw in range(n_perm):
        tables = {}
        for hand, paras in by_hand.items():
            swapped = []
            for para in paras:
                order = [list(line) for line in para]
                if rng.random() < 0.5 and len(order) >= 2:
                    order[0], order[-1] = order[-1], order[0]
                swapped.append(order)
            tables[hand] = log_ratios(*_b3_ends(swapped))
        draw_corr = correlations(tables)
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
    return {"pairs": results, "label": "shared" if all(v["pass"] for v in results.values()) else "not_shared"}


def fold_of_pages(pages: list[str]) -> dict[str, int]:
    order: list[str] = []
    for page in pages:
        if page not in order:
            order.append(page)
    return {page: i % 5 for i, page in enumerate(order)}


def conditional_gain(rows: list[tuple[str, str, tuple, int]]) -> dict:
    """Pair-weighted held-out gain of adding core_t. Rows are (left, right, key, fold)."""
    total = 0.0
    n_used = 0
    folds = []
    for fold in range(5):
        train = [row for row in rows if row[3] != fold]
        test = [row for row in rows if row[3] == fold]
        gain, n_test = _fold_gain(train, test)
        folds.append({"fold": fold, "gain": gain, "n": n_test})
        if n_test:
            total += gain * n_test
            n_used += n_test
    return {"gain": (total / n_used) if n_used else float("nan"), "n": n_used, "folds": folds}


def _fold_gain(train: list[tuple], test: list[tuple]) -> tuple[float, int]:
    alphabet = {row[0] for row in train} | {row[1] for row in train}
    alphabet.add("OTHER")
    vsize = len(alphabet)
    by_key: dict[tuple, Counter] = defaultdict(Counter)
    by_both: dict[tuple, Counter] = defaultdict(Counter)
    n_key: Counter = Counter()
    n_both: Counter = Counter()
    for left, right, key, _fold in train:
        by_key[key][right] += 1
        n_key[key] += 1
        by_both[(key, left)][right] += 1
        n_both[(key, left)] += 1
    total = 0.0
    used = 0
    for left, right, key, _fold in test:
        if key not in n_key:
            continue
        target = right if right in alphabet else "OTHER"
        left_lab = left if left in alphabet else "OTHER"
        p0 = (by_key[key][target] + 0.5) / (n_key[key] + 0.5 * vsize)
        both = (key, left_lab)
        p1 = (by_both[both][target] + 0.5) / (n_both[both] + 0.5 * vsize)
        total += math.log2(p1) - math.log2(p0)
        used += 1
    return (total / used) if used else float("nan"), used


def attach_folds(lines: list[list[str]], pages: list[str], mode: str, drop_near: bool) -> list[tuple[str, str, tuple, int]]:
    slotted = H52.slotted_lines(lines, mode)
    units = unit_lines(lines, mode)
    folds = fold_of_pages(pages)
    rows = []
    for line, raw, page in zip(slotted, units, pages):
        fold = folds[page]
        for i in range(len(line) - 1):
            if drop_near and is_near_copy(raw[i], raw[i + 1]):
                continue
            onset_l, end_l, core_l = line[i]
            onset_r, _, core_r = line[i + 1]
            rows.append((core_l, core_r, (end_l, onset_r), fold))
    return rows


def scale_label(gains: dict[str, float], cucina: float) -> str:
    if not np.isfinite(cucina) or cucina <= 0:
        return "invalid_control"
    n_hit = sum(1 for hand in HANDS if np.isfinite(gains[hand]) and gains[hand] > 0 and gains[hand] >= 0.5 * cucina)
    if n_hit >= 2:
        return "language_scale"
    return "not_language_scale"


def load_copier_records(hand: str) -> list[dict]:
    return H53.load_copier_records(hand)


def run(n_perm: int = N_PERM) -> dict:
    """Full pre-registered run, including conditional C and D."""
    ms_lines = {hand: H52.load_ms_lines(hand) for hand in HANDS}
    copier_lines = {hand: H52.load_copier_lines(hand) for hand in HANDS}
    print("A1", flush=True)
    a1 = {f"MS_{h}": score_a1(ms_lines[h], n_perm=n_perm) for h in HANDS}
    a1.update({f"page_line_copier_{h}": score_a1(copier_lines[h], n_perm=n_perm) for h in HANDS})
    print("A2", flush=True)
    a2 = {f"MS_{h}": score_a2(ms_lines[h], n_perm=n_perm) for h in HANDS}
    a2.update({f"page_line_copier_{h}": score_a2(copier_lines[h], n_perm=n_perm) for h in HANDS})
    a1_hands = [h for h in HANDS if slot_pass(a1[f"MS_{h}"], a1[f"page_line_copier_{h}"])]
    a2_hands = [h for h in HANDS if slot_pass(a2[f"MS_{h}"], a2[f"page_line_copier_{h}"])]
    if len(a1_hands) >= 2 and len(a2_hands) >= 2:
        slots = "stands"
    elif len(a1_hands) < 2 and len(a2_hands) < 2:
        slots = "killed"
    else:
        slots = "partial"

    ms_records = {hand: H53.load_ms_records(hand) for hand in HANDS}
    copier_records = {hand: load_copier_records(hand) for hand in HANDS}
    ms_groups = {hand: paragraphs_of(ms_records[hand]) for hand in HANDS}
    copier_groups = {hand: paragraphs_of(copier_records[hand]) for hand in HANDS}

    def lines_where(groups: dict[str, list[dict]], pred) -> dict[str, list]:
        return {hand: [g["lines"] for g in groups[hand] if pred(g)] for hand in HANDS}

    print("B1", flush=True)
    b1_ms = lines_where(ms_groups, lambda g: (not g["folio_first"]) and len(g["lines"]) >= 3)
    b1_co = lines_where(copier_groups, lambda g: (not g["folio_first"]) and len(g["lines"]) >= 3)
    b1 = {f"MS_{h}": score_role(b1_ms[h], n_perm=n_perm) for h in HANDS}
    b1.update({f"page_line_copier_{h}": score_role(b1_co[h], n_perm=n_perm) for h in HANDS})
    print("B2", flush=True)
    b2_pred = lambda g: len(g["lines"]) >= 3 and len(g["lines"][0]) >= 6 and len(g["lines"][-1]) >= 6
    b2_ms = lines_where(ms_groups, b2_pred)
    b2_co = lines_where(copier_groups, b2_pred)
    b2 = {f"MS_{h}": score_role(b2_ms[h], n_perm=n_perm) for h in HANDS}
    b2.update({f"page_line_copier_{h}": score_role(b2_co[h], n_perm=n_perm) for h in HANDS})
    print("B3", flush=True)
    b3_ms = {hand: b3_bags(ms_groups[hand]) for hand in HANDS}
    b3_co = {hand: b3_bags(copier_groups[hand]) for hand in HANDS}
    b3 = {f"MS_{h}": score_b3(b3_ms[h], n_perm=n_perm) for h in HANDS}
    b3.update({f"page_line_copier_{h}": score_b3(b3_co[h], n_perm=n_perm) for h in HANDS})

    b1_hands = [h for h in HANDS if role_pass(b1[f"MS_{h}"], b1[f"page_line_copier_{h}"])]
    b2_hands = [h for h in HANDS if role_pass(b2[f"MS_{h}"], b2[f"page_line_copier_{h}"])]
    b3_hands = [h for h in HANDS if role_pass(b3[f"MS_{h}"], b3[f"page_line_copier_{h}"])]
    paragraphs = b_label(len(b3_hands))
    label = overall_label(slots, paragraphs)

    conditional: dict = {"C": {"label": "not_run"}, "D": {"label": "not_run"}}
    if len(a2_hands) >= 2:
        print("C", flush=True)
        drop_near = len(a1_hands) >= 2
        gains = {}
        for hand in HANDS:
            records = ms_records[hand]
            rows = attach_folds(ms_lines[hand], [rec["page"] for rec in records], "eva", drop_near)
            gains[hand] = conditional_gain(rows)["gain"]
        cucina_recs = H53.load_cucina_records()
        cucina_rows = attach_folds(
            [list(rec["words"]) for rec in cucina_recs],
            [rec["page"] for rec in cucina_recs],
            "char",
            drop_near,
        )
        cucina_gain = conditional_gain(cucina_rows)["gain"]
        conditional["C"] = {
            "label": scale_label(gains, cucina_gain),
            "drop_near": drop_near,
            "gains": gains,
            "cucina": cucina_gain,
        }
    if len(b3_hands) >= 2:
        print("D", flush=True)
        conditional["D"] = score_shared(b3_ms, n_perm=n_perm)

    return {
        "A1": a1,
        "A2": a2,
        "A1_hands": a1_hands,
        "A2_hands": a2_hands,
        "slots": slots,
        "B1": b1,
        "B2": b2,
        "B3": b3,
        "B1_hands": b1_hands,
        "B2_hands": b2_hands,
        "B3_hands": b3_hands,
        "paragraphs": paragraphs,
        "overall": label,
        "conditional": conditional,
    }
