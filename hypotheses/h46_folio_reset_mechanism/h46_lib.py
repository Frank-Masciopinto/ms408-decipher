"""h46: how does the folio reset work? (PREREG.md).

Three mechanism checks on paragraph words from h14_lib.table() (ZL3b, comma as space,
collapsed EVA units via h13_lib.SEG):
1. Cross-folio drop in one-edit pairs at matched lag (6-20, 21-100, 101-500) against
   100 within-quire circular rotations (seed 46).
2. Folio-opening line-1 seed rate vs interior baseline rate on folios with >= 6
   paragraph lines against 200 within-folio line-order permutations (seed 46).
3. Visible spread (v -> r) vs page turn (r -> v) for consecutive manuscript folios
   (folio_index[j] == folio_index[i] + 1) in 21-100 and 101-500 against 200
   folio-transition label swaps (seed 46).
"""
from __future__ import annotations

import os

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import rapidfuzz

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _rel in (
    "src",
    "hypotheses/h09_image_context_cribs",
    "hypotheses/h13_top_word_context",
    "hypotheses/h14_line_position_controls",
    "hypotheses/h42_near_repeat_decay",
    "hypotheses/h43_page_edge",
):
    _path = str(ROOT / _rel)
    if _path not in sys.path:
        sys.path.insert(0, _path)

import h09_lib  # noqa: E402
import h13_lib  # noqa: E402
import h14_lib  # noqa: E402
import h42_lib  # noqa: E402
import h43_lib  # noqa: E402

HANDS = ("1A", "2B", "3B")
TRANSCRIPTION = "ZL3b-n.txt"
TEST1_BINS = (
    ("6-20", 6, 20),
    ("21-100", 21, 100),
    ("101-500", 101, 500),
)
TEST3_BINS = (
    ("21-100", 21, 100),
    ("101-500", 101, 500),
)
MAX_PAIRS_PER_SIDE = 20000
MIN_ELIGIBLE = 200
MIN_FOLIO_LINES = 6
N_ROTATIONS = 100
N_LINE_PERMS = 200
N_TRANS_SWAPS = 200
NULL_SEED = 46

edit1 = h42_lib.edit1
systematic_ranks = h42_lib.systematic_ranks
rotate_tokens = h43_lib.rotate_tokens
split_lengths = h43_lib.split_lengths


@dataclass
class HandData:
    hand: str
    words: list[str]
    units: list[tuple[str, ...]]
    folios: list[str]
    quires: list[str]
    lines: list[int]
    folio_index: list[int]
    quires_grouped: list[list[list[tuple[str, ...]]]]
    folio_lines: list[tuple[str, list[list[tuple[str, ...]]]]]


def _bind_zl3b() -> None:
    path = ROOT / "data" / "transcriptions" / TRANSCRIPTION
    if not path.is_file():
        raise FileNotFoundError(path)
    h09_lib.TR = path
    h13_lib.H9.TR = path
    words = [token for token, _ok in h13_lib.tokens_raw("aa,bb cc")[0]]
    if words != ["aa", "bb", "cc"]:
        raise RuntimeError(f"comma is not a word space under the h14 splitter: {words}")


def manuscript_folio_order(table: pd.DataFrame | None = None) -> dict[str, int]:
    """0-based index of folios in manuscript reading order."""
    quires_csv = ROOT / "data" / "quires.csv"
    if quires_csv.is_file():
        q = pd.read_csv(quires_csv, dtype=str, keep_default_na=False)
        order = {str(page): idx for idx, page in enumerate(q["page"].tolist())}
        if table is not None:
            for folio in dict.fromkeys(table["folio"].astype(str).tolist()):
                if folio not in order:
                    order[folio] = len(order)
        return order
    if table is None:
        _bind_zl3b()
        table = h14_lib.table()
    return {str(f): idx for idx, f in enumerate(dict.fromkeys(table["folio"].astype(str).tolist()))}


def build_hand_data(
    hand: str,
    words: list[str],
    folios: list[str],
    quires: list[str],
    lines: list[int],
    ms_order: dict[str, int] | None = None,
    units: list[tuple[str, ...]] | None = None,
) -> HandData:
    """Package token stream, quire/folio grouping, and folio line grouping for one hand."""
    n = len(words)
    if not (len(folios) == len(quires) == len(lines) == n):
        raise ValueError("words, folios, quires, and lines must have equal length")
    if units is None:
        units = [tuple(h13_lib.SEG(w)) for w in words]
    elif len(units) != n:
        raise ValueError("units length does not match words length")

    if ms_order is None:
        ms_order = {f: idx for idx, f in enumerate(dict.fromkeys(folios))}
    folio_index = [int(ms_order[f]) for f in folios]

    quires_grouped: list[list[list[tuple[str, ...]]]] = []
    cur_quire: list[list[tuple[str, ...]]] = []
    cur_folio: list[tuple[str, ...]] = []
    seen_quire = None
    seen_folio = None
    for folio, quire, unit in zip(folios, quires, units):
        if quire != seen_quire:
            if cur_folio:
                cur_quire.append(cur_folio)
                cur_folio = []
            if cur_quire:
                quires_grouped.append(cur_quire)
                cur_quire = []
            seen_quire = quire
            seen_folio = folio
        elif folio != seen_folio:
            cur_quire.append(cur_folio)
            cur_folio = []
            seen_folio = folio
        cur_folio.append(unit)
    if cur_folio:
        cur_quire.append(cur_folio)
    if cur_quire:
        quires_grouped.append(cur_quire)

    folio_lines_list: list[tuple[str, list[list[tuple[str, ...]]]]] = []
    i = 0
    while i < n:
        f = folios[i]
        j = i
        lines_on_folio: list[list[tuple[str, ...]]] = []
        while j < n and folios[j] == f:
            lno = lines[j]
            cur_line: list[tuple[str, ...]] = []
            while j < n and folios[j] == f and lines[j] == lno:
                cur_line.append(units[j])
                j += 1
            if cur_line:
                lines_on_folio.append(cur_line)
        folio_lines_list.append((f, lines_on_folio))
        i = j

    return HandData(
        hand=hand,
        words=list(words),
        units=list(units),
        folios=list(folios),
        quires=list(quires),
        lines=list(lines),
        folio_index=folio_index,
        quires_grouped=quires_grouped,
        folio_lines=folio_lines_list,
    )


def load_hands() -> dict[str, HandData]:
    """Load paragraph words of hands 1A, 2B, 3B from h14_lib.table() (ZL3b)."""
    _bind_zl3b()
    table = h14_lib.table()
    ms_order = manuscript_folio_order(table)
    out: dict[str, HandData] = {}
    for hand in HANDS:
        sub = table.loc[table.HL == hand, ["folio", "quire", "line", "w"]]
        words = [str(w) for w in sub["w"].tolist()]
        folios = [str(f) for f in sub["folio"].tolist()]
        quires = [str(q) for q in sub["quire"].tolist()]
        lines = [int(ln) for ln in sub["line"].tolist()]
        out[hand] = build_hand_data(
            hand=hand,
            words=words,
            folios=folios,
            quires=quires,
            lines=lines,
            ms_order=ms_order,
        )
    return out


def build_edit1_matrix(uniq: list[tuple[str, ...]]) -> np.ndarray:
    """Boolean (V, V) matrix where entry (a, b) is True iff Levenshtein(uniq[a], uniq[b]) == 1."""
    v = len(uniq)
    mat = np.zeros((v, v), dtype=bool)
    idx_of = {u: i for i, u in enumerate(uniq)}
    by_wild: dict[tuple[int, tuple[str, ...]], list[int]] = defaultdict(list)
    for i, u in enumerate(uniq):
        m = len(u)
        for k in range(m):
            sub = u[:k] + u[k + 1 :]
            j = idx_of.get(sub)
            if j is not None:
                mat[i, j] = True
                mat[j, i] = True
            by_wild[(k, sub)].append(i)
    for group in by_wild.values():
        if len(group) > 1:
            arr = np.asarray(group, dtype=np.int32)
            mat[np.ix_(arr, arr)] = True
            mat[arr, arr] = False
    return mat


def _folio_ends(folios: list[str]) -> np.ndarray:
    """For each token position i, the first token index j > i with folios[j] != folios[i]."""
    n = len(folios)
    ends = np.empty(n, dtype=np.int32)
    i = 0
    while i < n:
        j = i + 1
        f = folios[i]
        while j < n and folios[j] == f:
            j += 1
        ends[i:j] = j
        i = j
    return ends


def is_scored_and_pass(
    n_left: int,
    n_right: int,
    effect: float | None,
    p95: float | None,
    min_eligible: int = MIN_ELIGIBLE,
) -> tuple[bool, bool]:
    """Scored iff both sides have >= min_eligible pairs; passes iff scored and effect > p95."""
    scored = int(n_left) >= min_eligible and int(n_right) >= min_eligible
    if not scored or effect is None or p95 is None:
        return scored, False
    return True, bool(float(effect) > float(p95))


def _eval_test1_stream(
    type_ids: np.ndarray,
    len_arr: np.ndarray,
    ends_arr: np.ndarray,
    mat: np.ndarray,
    max_l: int,
    bins: tuple[tuple[str, int, int], ...] = TEST1_BINS,
    max_pairs: int = MAX_PAIRS_PER_SIDE,
) -> dict[str, dict[str, tuple[int, int, int, float | None]]]:
    """Evaluate same and cross eligible counts, sampled counts, edit1 hits, and rates per lag bin."""
    n = len(len_arr)
    pref = np.zeros((max_l, n + 1), dtype=np.int32)
    compat_pos: list[np.ndarray | None] = [None] * max_l
    for length in range(1, max_l - 1):
        mask = np.abs(len_arr - length) <= 1
        np.cumsum(mask, dtype=np.int32, out=pref[length, 1:])
        compat_pos[length] = np.flatnonzero(mask).astype(np.int32)
    i_idx = np.arange(n, dtype=np.int32)
    out: dict[str, dict[str, tuple[int, int, int, float | None]]] = {}
    for bname, lo, hi in bins:
        side_res: dict[str, tuple[int, int, int, float | None]] = {}
        for sname, same_side in (("same", True), ("cross", False)):
            if same_side:
                j0 = np.minimum(i_idx + lo, n)
                j1 = np.minimum(np.minimum(ends_arr, i_idx + hi + 1), n)
            else:
                j0 = np.minimum(np.maximum(i_idx + lo, ends_arr), n)
                j1 = np.minimum(i_idx + hi + 1, n)
            j1 = np.maximum(j0, j1)
            counts = pref[len_arr, j1] - pref[len_arr, j0]
            n_elig = int(counts.sum())
            ranks = systematic_ranks(n_elig, min(max_pairs, n_elig))
            if not ranks:
                side_res[sname] = (n_elig, 0, 0, None)
                continue
            ranks_arr = np.asarray(ranks, dtype=np.int64)
            cum = np.cumsum(counts, dtype=np.int64)
            i_sel = np.searchsorted(cum, ranks_arr, side="right")
            prev_cum = np.where(i_sel > 0, cum[np.maximum(i_sel - 1, 0)], 0)
            local_k = (ranks_arr - prev_cum).astype(np.int32)
            l_sel = len_arr[i_sel]
            bases = pref[l_sel, j0[i_sel]] + local_k
            j_sel = np.empty(len(ranks_arr), dtype=np.int32)
            for length in range(1, max_l - 1):
                m_l = l_sel == length
                if np.any(m_l):
                    pos_arr = compat_pos[length]
                    assert pos_arr is not None
                    j_sel[m_l] = pos_arr[bases[m_l]]
            hits = int(mat[type_ids[i_sel], type_ids[j_sel]].sum())
            n_samp = int(len(ranks_arr))
            side_res[sname] = (n_elig, n_samp, hits, hits / n_samp)
        out[bname] = side_res
    return out


def score_test1_hand(
    data: HandData,
    rng: np.random.Generator,
    bins: tuple[tuple[str, int, int], ...] = TEST1_BINS,
    max_pairs: int = MAX_PAIRS_PER_SIDE,
    min_eligible: int = MIN_ELIGIBLE,
    n_null: int = N_ROTATIONS,
) -> dict:
    """Test 1: Cross-folio drop in one-edit pairs at matched lag against 100 quire rotations."""
    uniq = list(dict.fromkeys(data.units))
    idx_of = {u: i for i, u in enumerate(uniq)}
    mat = build_edit1_matrix(uniq)
    type_ids = np.asarray([idx_of[u] for u in data.units], dtype=np.int32)
    len_arr = np.asarray([len(u) for u in data.units], dtype=np.int32)
    max_l = (int(len_arr.max()) + 2) if len(len_arr) else 2
    ends_arr = _folio_ends(data.folios)

    quire_tids: list[np.ndarray] = []
    quire_lens: list[np.ndarray] = []
    cursor = 0
    for quire in data.quires_grouped:
        q_len = sum(len(folio) for folio in quire)
        if q_len <= 0:
            raise ValueError("empty quire")
        quire_tids.append(type_ids[cursor : cursor + q_len])
        quire_lens.append(len_arr[cursor : cursor + q_len])
        cursor += q_len

    obs = _eval_test1_stream(type_ids, len_arr, ends_arr, mat, max_l, bins=bins, max_pairs=max_pairs)

    shifts: list[list[int]] = []
    for _ in range(n_null):
        shifts.append([int(rng.integers(0, len(qt))) for qt in quire_tids])

    null_effects: dict[str, list[float]] = {bname: [] for bname, _, _ in bins}
    for shift_vec in shifts:
        rot_tids = np.concatenate([np.roll(qt, -s) for qt, s in zip(quire_tids, shift_vec)])
        rot_lens = np.concatenate([np.roll(ql, -s) for ql, s in zip(quire_lens, shift_vec)])
        rot_res = _eval_test1_stream(rot_tids, rot_lens, ends_arr, mat, max_l, bins=bins, max_pairs=max_pairs)
        for bname, _, _ in bins:
            sr = rot_res[bname]["same"][3]
            cr = rot_res[bname]["cross"][3]
            if sr is not None and cr is not None:
                null_effects[bname].append(float(sr - cr))

    bin_records: dict[str, dict] = {}
    for bname, lo, hi in bins:
        s_elig, s_samp, s_hits, s_rate = obs[bname]["same"]
        c_elig, c_samp, c_hits, c_rate = obs[bname]["cross"]
        effect = (float(s_rate - c_rate) if (s_rate is not None and c_rate is not None) else None)
        ne = null_effects[bname]
        if ne and len(ne) == n_null:
            arr = np.asarray(ne, dtype=np.float64)
            p95 = float(np.percentile(arr, 95, method="linear"))
            null_mean = float(arr.mean())
            null_sd = float(arr.std(ddof=1)) if len(arr) >= 2 else 0.0
        else:
            p95 = None
            null_mean = None
            null_sd = None
        scored, passed = is_scored_and_pass(s_elig, c_elig, effect, p95, min_eligible=min_eligible)
        bin_records[bname] = {
            "lo": int(lo),
            "hi": int(hi),
            "n_same_eligible": int(s_elig),
            "n_same_sampled": int(s_samp),
            "n_same_edit1": int(s_hits),
            "same_rate": s_rate,
            "n_cross_eligible": int(c_elig),
            "n_cross_sampled": int(c_samp),
            "n_cross_edit1": int(c_hits),
            "cross_rate": c_rate,
            "effect": effect,
            "null_mean": null_mean,
            "null_sd": null_sd,
            "null_p95": p95,
            "null_effects": ne,
            "scored": bool(scored),
            "pass": bool(passed),
        }

    return {
        "hand": data.hand,
        "n_tokens": len(data.units),
        "n_folios": len(data.folio_lines),
        "n_quires": len(data.quires_grouped),
        "bins": bin_records,
    }


def score_test2_hand(
    data: HandData,
    rng: np.random.Generator,
    min_lines: int = MIN_FOLIO_LINES,
    n_null: int = N_LINE_PERMS,
) -> dict:
    """Test 2: Folio-opening line-1 seed rate vs interior baseline rate on folios with >= 6 lines."""
    uniq = list(dict.fromkeys(data.units))
    idx_of = {u: i for i, u in enumerate(uniq)}
    mat = build_edit1_matrix(uniq)

    folio_mats: list[tuple[str, int, np.ndarray, np.ndarray, int, int]] = []
    for folio, lines in data.folio_lines:
        if len(lines) < min_lines:
            continue
        k = len(lines)
        elig_mat = np.zeros((k, k), dtype=np.int64)
        hit_mat = np.zeros((k, k), dtype=np.int64)
        line_tids = [np.asarray([idx_of[u] for u in line], dtype=np.int32) for line in lines]
        line_lens = [np.asarray([len(u) for u in line], dtype=np.int32) for line in lines]
        for a in range(k):
            la_t = line_tids[a]
            la_l = line_lens[a]
            for b in range(a + 1, k):
                lb_t = line_tids[b]
                lb_l = line_lens[b]
                compat = np.abs(la_l[:, None] - lb_l[None, :]) <= 1
                el = int(compat.sum())
                ht = int(mat[la_t[:, None], lb_t[None, :]].sum()) if el else 0
                elig_mat[a, b] = elig_mat[b, a] = el
                hit_mat[a, b] = hit_mat[b, a] = ht
        tot_el = int(elig_mat.sum() // 2)
        tot_ht = int(hit_mat.sum() // 2)
        folio_mats.append((folio, k, elig_mat, hit_mat, tot_el, tot_ht))

    n_folios_total = len(data.folio_lines)
    n_folios_used = len(folio_mats)
    seed_elig = sum(int(em[0, 1:].sum()) for _, _, em, _, _, _ in folio_mats)
    seed_hits = sum(int(hm[0, 1:].sum()) for _, _, _, hm, _, _ in folio_mats)
    total_elig = sum(te for _, _, _, _, te, _ in folio_mats)
    total_hits = sum(th for _, _, _, _, _, th in folio_mats)
    interior_elig = total_elig - seed_elig
    interior_hits = total_hits - seed_hits

    seed_rate = (seed_hits / seed_elig) if seed_elig > 0 else None
    interior_rate = (interior_hits / interior_elig) if interior_elig > 0 else None
    effect = (
        float(seed_rate - interior_rate)
        if (seed_rate is not None and interior_rate is not None)
        else None
    )

    null_effects: list[float] = []
    if seed_elig > 0 and interior_elig > 0:
        elig_row_sums = [em.sum(axis=1) for _, _, em, _, _, _ in folio_mats]
        hit_row_sums = [hm.sum(axis=1) for _, _, _, hm, _, _ in folio_mats]
        ks = [k for _, k, _, _, _, _ in folio_mats]
        for _ in range(n_null):
            se = 0
            sh = 0
            for k, erow, hrow in zip(ks, elig_row_sums, hit_row_sums):
                perm = rng.permutation(k)
                first = int(perm[0])
                se += int(erow[first])
                sh += int(hrow[first])
            ie = total_elig - se
            ih = total_hits - sh
            null_effects.append(float((sh / se) - (ih / ie)))

    if null_effects and len(null_effects) == n_null and effect is not None:
        arr = np.asarray(null_effects, dtype=np.float64)
        p95 = float(np.percentile(arr, 95, method="linear"))
        null_mean = float(arr.mean())
        null_sd = float(arr.std(ddof=1)) if len(arr) >= 2 else 0.0
        passed = bool(effect > p95)
    else:
        p95 = None
        null_mean = None
        null_sd = None
        passed = False

    return {
        "hand": data.hand,
        "n_folios_total": int(n_folios_total),
        "n_folios_eligible": int(n_folios_used),
        "min_folio_lines": int(min_lines),
        "n_seed_eligible": int(seed_elig),
        "n_seed_edit1": int(seed_hits),
        "seed_rate": seed_rate,
        "n_interior_eligible": int(interior_elig),
        "n_interior_edit1": int(interior_hits),
        "interior_rate": interior_rate,
        "effect": effect,
        "null_mean": null_mean,
        "null_sd": null_sd,
        "null_p95": p95,
        "null_effects": null_effects,
        "pass": bool(passed),
    }


def _transition_kind(folio_left: str, folio_right: str) -> str | None:
    if folio_left.endswith("r") and folio_right.endswith("v"):
        return "r_to_v"
    if folio_left.endswith("v") and folio_right.endswith("r"):
        return "v_to_r"
    return None


def score_test3_hand(
    data: HandData,
    rng: np.random.Generator,
    bins: tuple[tuple[str, int, int], ...] = TEST3_BINS,
    min_eligible: int = MIN_ELIGIBLE,
    n_null: int = N_TRANS_SWAPS,
) -> dict:
    """Test 3: Visible spread (v -> r) vs page turn (r -> v) across consecutive folios."""
    uniq = list(dict.fromkeys(data.units))
    idx_of = {u: i for i, u in enumerate(uniq)}
    mat = build_edit1_matrix(uniq)
    type_ids = np.asarray([idx_of[u] for u in data.units], dtype=np.int32)
    len_arr = np.asarray([len(u) for u in data.units], dtype=np.int32)

    folio_spans: list[tuple[str, int, int, int]] = []
    n = len(data.units)
    i = 0
    while i < n:
        f = data.folios[i]
        f_idx = data.folio_index[i]
        j = i + 1
        while j < n and data.folios[j] == f:
            j += 1
        folio_spans.append((f, f_idx, i, j))
        i = j

    transitions: list[tuple[str, str, str, int, int, int, int]] = []
    for (f1, idx1, s1, e1), (f2, idx2, s2, e2) in zip(folio_spans, folio_spans[1:]):
        if idx2 != idx1 + 1:
            continue
        kind = _transition_kind(f1, f2)
        if kind is not None:
            transitions.append((f1, f2, kind, s1, e1, s2, e2))

    bin_records: dict[str, dict] = {}
    for bname, lo, hi in bins:
        trans_rows: list[dict] = []
        for f1, f2, kind, s1, e1, s2, e2 in transitions:
            idx_i = np.arange(s1, e1, dtype=np.int32)[:, None]
            idx_j = np.arange(s2, e2, dtype=np.int32)[None, :]
            lag = idx_j - idx_i
            mask = (lag >= lo) & (lag <= hi) & (np.abs(len_arr[idx_i] - len_arr[idx_j]) <= 1)
            n_elig = int(mask.sum())
            if n_elig > 0:
                ii, jj = np.nonzero(mask)
                hits = int(mat[type_ids[s1 + ii], type_ids[s2 + jj]].sum())
            else:
                hits = 0
            trans_rows.append(
                {
                    "folio_i": f1,
                    "folio_j": f2,
                    "type": kind,
                    "n_eligible": n_elig,
                    "n_edit1": hits,
                }
            )

        labels = np.asarray([1 if row["type"] == "v_to_r" else 0 for row in trans_rows], dtype=np.int32)
        eligs = np.asarray([row["n_eligible"] for row in trans_rows], dtype=np.int64)
        hits_arr = np.asarray([row["n_edit1"] for row in trans_rows], dtype=np.int64)

        vr_mask = labels == 1
        rv_mask = labels == 0
        n_vr_trans = int(vr_mask.sum())
        n_rv_trans = int(rv_mask.sum())
        vr_elig = int(eligs[vr_mask].sum()) if len(eligs) else 0
        vr_hits = int(hits_arr[vr_mask].sum()) if len(hits_arr) else 0
        rv_elig = int(eligs[rv_mask].sum()) if len(eligs) else 0
        rv_hits = int(hits_arr[rv_mask].sum()) if len(hits_arr) else 0

        vr_rate = (vr_hits / vr_elig) if vr_elig > 0 else None
        rv_rate = (rv_hits / rv_elig) if rv_elig > 0 else None
        effect = (
            float(vr_rate - rv_rate)
            if (vr_rate is not None and rv_rate is not None)
            else None
        )

        null_effects: list[float] = []
        for _ in range(n_null):
            perm = rng.permutation(labels)
            p_vr = perm == 1
            p_rv = perm == 0
            ve = int(eligs[p_vr].sum()) if len(eligs) else 0
            vh = int(hits_arr[p_vr].sum()) if len(hits_arr) else 0
            re_ = int(eligs[p_rv].sum()) if len(eligs) else 0
            rh = int(hits_arr[p_rv].sum()) if len(hits_arr) else 0
            if ve > 0 and re_ > 0:
                null_effects.append(float((vh / ve) - (rh / re_)))

        if null_effects and len(null_effects) == n_null and effect is not None:
            arr = np.asarray(null_effects, dtype=np.float64)
            p95 = float(np.percentile(arr, 95, method="linear"))
            null_mean = float(arr.mean())
            null_sd = float(arr.std(ddof=1)) if len(arr) >= 2 else 0.0
        else:
            p95 = None
            null_mean = None
            null_sd = None

        scored, passed = is_scored_and_pass(vr_elig, rv_elig, effect, p95, min_eligible=min_eligible)
        bin_records[bname] = {
            "lo": int(lo),
            "hi": int(hi),
            "n_transitions": len(trans_rows),
            "n_v_to_r_transitions": n_vr_trans,
            "n_r_to_v_transitions": n_rv_trans,
            "n_v_to_r_eligible": vr_elig,
            "n_v_to_r_edit1": vr_hits,
            "v_to_r_rate": vr_rate,
            "n_r_to_v_eligible": rv_elig,
            "n_r_to_v_edit1": rv_hits,
            "r_to_v_rate": rv_rate,
            "effect": effect,
            "null_mean": null_mean,
            "null_sd": null_sd,
            "null_p95": p95,
            "null_effects": null_effects,
            "transitions": trans_rows,
            "scored": bool(scored),
            "pass": bool(passed),
        }

    return {
        "hand": data.hand,
        "n_transitions_total": len(transitions),
        "bins": bin_records,
    }


def predictions(test1: dict, test2: dict, test3: dict) -> dict:
    """Evaluate pre-registered predictions F1, F2, F3."""
    f1_1a_bins = [
        bname
        for bname in ("21-100", "101-500")
        if test1["1A"]["bins"][bname]["scored"] and test1["1A"]["bins"][bname]["pass"]
    ]
    f1_2b_bins = [
        bname
        for bname in ("21-100", "101-500")
        if test1["2B"]["bins"][bname]["scored"] and test1["2B"]["bins"][bname]["pass"]
    ]
    f1 = len(f1_1a_bins) >= 1 and len(f1_2b_bins) >= 1

    f2_pass_hands = [hand for hand in HANDS if test2[hand]["pass"]]
    f2 = len(f2_pass_hands) >= 2

    f3_2b_bins = [
        bname
        for bname in ("21-100", "101-500")
        if test3["2B"]["bins"][bname]["scored"] and test3["2B"]["bins"][bname]["pass"]
    ]
    f3 = len(f3_2b_bins) >= 1

    return {
        "F1": bool(f1),
        "F1_1A_passing_bins": f1_1a_bins,
        "F1_2B_passing_bins": f1_2b_bins,
        "F2": bool(f2),
        "F2_passing_hands": f2_pass_hands,
        "F3": bool(f3),
        "F3_2B_passing_bins": f3_2b_bins,
    }


def measure_all(seed: int = NULL_SEED) -> dict:
    """Run Test 1, Test 2, and Test 3 across hands 1A, 2B, 3B."""
    hands_data = load_hands()
    rng1 = np.random.default_rng(seed)
    rng2 = np.random.default_rng(seed)
    rng3 = np.random.default_rng(seed)

    test1: dict[str, dict] = {}
    test2: dict[str, dict] = {}
    test3: dict[str, dict] = {}

    for hand in HANDS:
        data = hands_data[hand]
        print(
            f"h46 {hand}: tokens={len(data.units)} folios={len(data.folio_lines)} "
            f"quires={len(data.quires_grouped)}",
            flush=True,
        )
        t1 = score_test1_hand(data, rng1)
        for bname in ("6-20", "21-100", "101-500"):
            row = t1["bins"][bname]
            print(
                f"  Test1 {hand} {bname}: same={row['same_rate']:.6f} ({row['n_same_sampled']}/{row['n_same_eligible']}) "
                f"cross={row['cross_rate']:.6f} ({row['n_cross_sampled']}/{row['n_cross_eligible']}) "
                f"eff={row['effect']:.6f} p95={row['null_p95']:.6f} pass={row['pass']}",
                flush=True,
            )
        test1[hand] = t1

        t2 = score_test2_hand(data, rng2)
        print(
            f"  Test2 {hand}: folios={t2['n_folios_eligible']}/{t2['n_folios_total']} "
            f"seed={t2['seed_rate']:.6f} ({t2['n_seed_edit1']}/{t2['n_seed_eligible']}) "
            f"interior={t2['interior_rate']:.6f} ({t2['n_interior_edit1']}/{t2['n_interior_eligible']}) "
            f"eff={t2['effect']:.6f} p95={t2['null_p95']:.6f} pass={t2['pass']}",
            flush=True,
        )
        test2[hand] = t2

        t3 = score_test3_hand(data, rng3)
        for bname in ("21-100", "101-500"):
            row = t3["bins"][bname]
            print(
                f"  Test3 {hand} {bname}: v_to_r={row['v_to_r_rate']:.6f} ({row['n_v_to_r_edit1']}/{row['n_v_to_r_eligible']}) "
                f"r_to_v={row['r_to_v_rate']:.6f} ({row['n_r_to_v_edit1']}/{row['n_r_to_v_eligible']}) "
                f"eff={row['effect']:.6f} p95={row['null_p95']:.6f} pass={row['pass']}",
                flush=True,
            )
        test3[hand] = t3

    pred = predictions(test1, test2, test3)
    return {
        "transcription": TRANSCRIPTION,
        "comma": "space",
        "loader": "h14_lib.table paragraph words, ZL3b, collapsed EVA units via h13_lib.SEG",
        "hands": list(HANDS),
        "test1_bins": [name for name, _, _ in TEST1_BINS],
        "test3_bins": [name for name, _, _ in TEST3_BINS],
        "max_pairs_per_side": MAX_PAIRS_PER_SIDE,
        "min_eligible": MIN_ELIGIBLE,
        "min_folio_lines": MIN_FOLIO_LINES,
        "n_rotations": N_ROTATIONS,
        "n_line_perms": N_LINE_PERMS,
        "n_trans_swaps": N_TRANS_SWAPS,
        "null_seed": seed,
        "test1": test1,
        "test2": test2,
        "test3": test3,
        "predictions": pred,
        "numpy": np.__version__,
        "rapidfuzz": rapidfuzz.__version__,
    }
