"""h48: within-folio copy drift vs fixed page palette (PREREG.md).

Measures within-folio line-lag decay on paragraph lines (restricted to folios with
at least 8 lines):
  M1 (edit1_lag, S_edit): one-edit rate across line lags 1, 2, 3-4, 5-8, 9+ and
      short-vs-long slope P(edit1 | Delta_l in {1,2}) - P(edit1 | Delta_l >= 5).
  M2 (jaccard_lag, cos3_lag, S_cos3): word-type Jaccard and unit-3gram cosine across
      line lags and slope mean_cos3(Delta_l in {1,2}) - mean_cos3(Delta_l >= 5).
  M3 (half_js): mean cosine between top-half and bottom-half folio word-count
      vectors minus the 200-permutation within-folio line-order null mean.
  D3 decomposition: decomposes short-lag same-folio one-edit excess over a 200-draw
      within-quire shuffle into a folio-palette component and a within-folio drift
      component.
"""
from __future__ import annotations

import json
import os
import platform
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"
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
    "hypotheses/h20_generators_vs_italian",
    "hypotheses/h30_line_structure",
    "hypotheses/h42_near_repeat_decay",
    "hypotheses/h43_page_edge",
):
    _p = str(ROOT / _rel)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import h13_lib  # noqa: E402
import h30_lib  # noqa: E402
import h42_lib  # noqa: E402
import h43_lib  # noqa: E402
from fetch_italian import load_italian  # noqa: E402
from msdecipher.controls_text import load_tokens  # noqa: E402

HANDS = ("1A", "2B", "3B")
MS_KEYS = ("MS_1A", "MS_2B", "MS_3B")
PROSE_KEYS = ("it_boccaccio", "la_pliny_herbal")
GENERATOR_KEYS = ("self_citation", "h39_native_tuned", "palette_ctrl")
STREAM_ORDER = MS_KEYS + PROSE_KEYS + GENERATOR_KEYS

LAG_BINS = (
    ("1", 1, 1),
    ("2", 2, 2),
    ("3-4", 3, 4),
    ("5-8", 5, 8),
    ("9+", 9, 100000),
)
LAG_NAMES = tuple(name for name, _, _ in LAG_BINS)

MIN_FOLIO_LINES = 8
FAKE_FOLIO_LINES = 25
FAKE_LINE_WORDS = 9
N_STREAM = 10500
N_PERM = 200
SEED = 48

SELF_CITATION_PATH = ROOT / "data" / "mechanisms" / "selfcitation" / "fitted_s1.txt"
H39_NATIVE_TUNED_PATH = (
    ROOT / "hypotheses" / "h39_graph_respell_and_tuned_copier" / "results" / "lines_2B_native_tuned.json"
)


def to_units(word: str, unit_kind: str) -> tuple[str, ...]:
    if unit_kind == "eva":
        return tuple(h13_lib.SEG(word))
    if unit_kind == "char":
        return tuple(word)
    raise ValueError(f"unknown unit_kind {unit_kind!r}")


def line_trigrams(units_line: list[tuple[str, ...]]) -> Counter:
    counts: Counter = Counter()
    for u in units_line:
        padded = ("^",) + u + ("$",)
        for i in range(len(padded) - 2):
            counts[padded[i : i + 3]] += 1
    return counts


def fast_en_matrix(lines_units: list[list[tuple[str, ...]]]) -> tuple[np.ndarray, np.ndarray]:
    """Compute M x M matrices of one-edit pair counts E and eligible pair counts N."""
    m = len(lines_units)
    vocab: dict[tuple[str, ...], int] = {}
    for line in lines_units:
        for u in line:
            if u not in vocab:
                vocab[u] = len(vocab)
    v = len(vocab)
    ulist = list(vocab.keys())
    max_len = max((len(u) for u in ulist), default=0)
    l_mat = np.zeros((m, max_len + 2), dtype=np.float64)
    w_mat = np.zeros((m, v), dtype=np.float64)
    for i, line in enumerate(lines_units):
        for u in line:
            l_mat[i, len(u)] += 1.0
            w_mat[i, vocab[u]] += 1.0
    b_len = np.zeros((max_len + 2, max_len + 2), dtype=np.float64)
    for l1 in range(max_len + 2):
        for l2 in range(max(0, l1 - 1), min(max_len + 2, l1 + 2)):
            b_len[l1, l2] = 1.0
    n_mat = np.rint((l_mat @ b_len) @ l_mat.T).astype(np.int64)
    by_len: dict[int, list[tuple[int, tuple[str, ...]]]] = defaultdict(list)
    for idx, u in enumerate(ulist):
        by_len[len(u)].append((idx, u))
    a_edit = np.zeros((v, v), dtype=np.float64)
    for length, items in by_len.items():
        n_it = len(items)
        for a_i in range(n_it):
            id_a, ua = items[a_i]
            for b_i in range(a_i + 1, n_it):
                id_b, ub = items[b_i]
                if h42_lib.edit1(ua, ub):
                    a_edit[id_a, id_b] = a_edit[id_b, id_a] = 1.0
        for id_a, ua in items:
            for id_b, ub in by_len.get(length + 1, ()):
                if h42_lib.edit1(ua, ub):
                    a_edit[id_a, id_b] = a_edit[id_b, id_a] = 1.0
    e_mat = np.rint((w_mat @ a_edit) @ w_mat.T).astype(np.int64)
    np.fill_diagonal(e_mat, 0)
    np.fill_diagonal(n_mat, 0)
    return e_mat, n_mat


def folio_matrices(folio_lines: list[list[str]], unit_kind: str = "eva") -> tuple:
    """Precompute line-pair matrices (E, N, J, C3, W, mask_bins) for a single folio."""
    n_lines = len(folio_lines)
    ulines = [[to_units(w, unit_kind) for w in line] for line in folio_lines]
    e_mat, n_mat = fast_en_matrix(ulines)
    j_mat = np.zeros((n_lines, n_lines), dtype=np.float64)
    c3_mat = np.zeros((n_lines, n_lines), dtype=np.float64)
    sets = [set(line) for line in folio_lines]
    c3s = [line_trigrams(ul) for ul in ulines]
    wcounts = [Counter(line) for line in folio_lines]
    for i in range(n_lines):
        si = sets[i]
        c3i = c3s[i]
        for j in range(i + 1, n_lines):
            union_sz = len(si | sets[j])
            jac = len(si & sets[j]) / union_sz if union_sz else 0.0
            j_mat[i, j] = j_mat[j, i] = jac
            cos3 = h43_lib.cosine_counts(c3i, c3s[j]) if c3i and c3s[j] else 0.0
            c3_mat[i, j] = c3_mat[j, i] = cos3
    vocab: dict[str, int] = {}
    for wc in wcounts:
        for w in wc:
            if w not in vocab:
                vocab[w] = len(vocab)
    w_mat = np.zeros((n_lines, len(vocab)), dtype=np.float64)
    for idx, wc in enumerate(wcounts):
        for w, cnt in wc.items():
            w_mat[idx, vocab[w]] = float(cnt)
    mask_bins = []
    for bname, lo, hi in LAG_BINS:
        rows, cols = [], []
        for i in range(n_lines):
            for j in range(i + 1, n_lines):
                if lo <= j - i <= hi:
                    rows.append(i)
                    cols.append(j)
        mask_bins.append((bname, np.asarray(rows, dtype=np.int64), np.asarray(cols, dtype=np.int64)))
    return e_mat, n_mat, j_mat, c3_mat, w_mat, mask_bins


def eval_prepared_folios(mats: list[tuple], perms: list[np.ndarray] | None = None) -> dict:
    """Evaluate M1, M2, and M3 raw statistics across folios under optional line permutations."""
    e_bin = {b: 0 for b in LAG_NAMES}
    n_bin = {b: 0 for b in LAG_NAMES}
    j_sum = {b: 0.0 for b in LAG_NAMES}
    c3_sum = {b: 0.0 for b in LAG_NAMES}
    lp_cnt = {b: 0 for b in LAG_NAMES}
    half_cos_vals: list[float] = []

    for f_idx, (e_mat, n_mat, j_mat, c3_mat, w_mat, mask_bins) in enumerate(mats):
        n_lines = e_mat.shape[0]
        if perms is not None:
            p = perms[f_idx]
            ep = e_mat[np.ix_(p, p)]
            np_ = n_mat[np.ix_(p, p)]
            jp = j_mat[np.ix_(p, p)]
            c3p = c3_mat[np.ix_(p, p)]
            wp = w_mat[p]
        else:
            ep, np_, jp, c3p, wp = e_mat, n_mat, j_mat, c3_mat, w_mat
        for bname, rows, cols in mask_bins:
            if len(rows):
                e_bin[bname] += int(ep[rows, cols].sum())
                n_bin[bname] += int(np_[rows, cols].sum())
                j_sum[bname] += float(jp[rows, cols].sum())
                c3_sum[bname] += float(c3p[rows, cols].sum())
                lp_cnt[bname] += int(len(rows))
        half = n_lines // 2
        top_v = wp[:half].sum(axis=0)
        bot_v = wp[n_lines - half :].sum(axis=0)
        denom = float(np.linalg.norm(top_v) * np.linalg.norm(bot_v))
        half_cos_vals.append(float(np.dot(top_v, bot_v) / denom) if denom > 0.0 else 0.0)

    edit1_lag = {b: (e_bin[b] / n_bin[b] if n_bin[b] > 0 else 0.0) for b in LAG_NAMES}
    jaccard_lag = {b: (j_sum[b] / lp_cnt[b] if lp_cnt[b] > 0 else 0.0) for b in LAG_NAMES}
    cos3_lag = {b: (c3_sum[b] / lp_cnt[b] if lp_cnt[b] > 0 else 0.0) for b in LAG_NAMES}

    e12 = e_bin["1"] + e_bin["2"]
    n12 = n_bin["1"] + n_bin["2"]
    e5p = e_bin["5-8"] + e_bin["9+"]
    n5p = n_bin["5-8"] + n_bin["9+"]
    p12 = e12 / n12 if n12 > 0 else 0.0
    p5p = e5p / n5p if n5p > 0 else 0.0
    s_edit = p12 - p5p

    lp12 = lp_cnt["1"] + lp_cnt["2"]
    lp5p = lp_cnt["5-8"] + lp_cnt["9+"]
    c12 = (c3_sum["1"] + c3_sum["2"]) / lp12 if lp12 > 0 else 0.0
    c5p = (c3_sum["5-8"] + c3_sum["9+"]) / lp5p if lp5p > 0 else 0.0
    s_cos3 = c12 - c5p

    j12 = (j_sum["1"] + j_sum["2"]) / lp12 if lp12 > 0 else 0.0
    j5p = (j_sum["5-8"] + j_sum["9+"]) / lp5p if lp5p > 0 else 0.0
    s_jaccard = j12 - j5p

    return {
        "e_bin": e_bin,
        "n_bin": n_bin,
        "lp_cnt": lp_cnt,
        "edit1_lag": edit1_lag,
        "jaccard_lag": jaccard_lag,
        "cos3_lag": cos3_lag,
        "p_edit1_12": p12,
        "p_edit1_5p": p5p,
        "S_edit": s_edit,
        "mean_cos3_12": c12,
        "mean_cos3_5p": c5p,
        "S_cos3": s_cos3,
        "mean_jaccard_12": j12,
        "mean_jaccard_5p": j5p,
        "S_jaccard": s_jaccard,
        "half_cos": float(np.mean(half_cos_vals)) if half_cos_vals else 0.0,
    }


def compute_d3_decomposition(
    folios: list[dict],
    obs_p12: float,
    folio_perm_p12: list[float],
    unit_kind: str = "eva",
    n_perm: int = N_PERM,
    seed: int = SEED,
) -> dict:
    """Decompose short-lag (Delta_l in {1,2}) same-folio edit1 excess over within-quire shuffle."""
    by_q: dict[str, list[list[list[tuple[str, ...]]]]] = defaultdict(list)
    for f in folios:
        ulines = [[to_units(w, unit_kind) for w in line] for line in f["lines"]]
        by_q[str(f["quire"])].append(ulines)

    q_mats = []
    for _q, flist in by_q.items():
        all_lines = [line for f in flist for line in f]
        eq, nq = fast_en_matrix(all_lines)
        r12, c12 = [], []
        offset = 0
        for f in flist:
            n_lines = len(f)
            for i in range(n_lines):
                for j in (i + 1, i + 2):
                    if j < n_lines:
                        r12.append(offset + i)
                        c12.append(offset + j)
            offset += n_lines
        q_mats.append((eq, nq, np.asarray(r12, dtype=np.int64), np.asarray(c12, dtype=np.int64)))

    rng_q = np.random.default_rng(seed)
    quire_rates: list[float] = []
    for _ in range(n_perm):
        e_tot = 0
        n_tot = 0
        for eq, nq, r12, c12 in q_mats:
            perm = rng_q.permutation(eq.shape[0])
            e_tot += int(eq[perm[r12], perm[c12]].sum())
            n_tot += int(nq[perm[r12], perm[c12]].sum())
        quire_rates.append(e_tot / n_tot if n_tot > 0 else 0.0)

    fp_arr = np.asarray(folio_perm_p12, dtype=np.float64)
    qp_arr = np.asarray(quire_rates, dtype=np.float64)
    fp_mean = float(fp_arr.mean())
    fp_sd = float(fp_arr.std(ddof=1)) if len(fp_arr) >= 2 else 0.0
    qp_mean = float(qp_arr.mean())
    qp_sd = float(qp_arr.std(ddof=1)) if len(qp_arr) >= 2 else 0.0

    total_excess = float(obs_p12 - qp_mean)
    palette_comp = float(fp_mean - qp_mean)
    drift_comp = float(obs_p12 - fp_mean)
    palette_z = float(palette_comp / qp_sd) if qp_sd > 0.0 else 0.0
    drift_z = float(drift_comp / fp_sd) if fp_sd > 0.0 else 0.0
    palette_share = float(palette_comp / total_excess) if total_excess > 0.0 else 0.0
    drift_share = float(drift_comp / total_excess) if total_excess > 0.0 else 0.0

    return {
        "observed_Delta12_rate": float(obs_p12),
        "same_folio_line_permuted_rate": fp_mean,
        "same_folio_line_permuted_sd": fp_sd,
        "quire_shuffle_rate": qp_mean,
        "quire_shuffle_sd": qp_sd,
        "total_excess": total_excess,
        "folio_palette_component": palette_comp,
        "folio_palette_z": palette_z,
        "folio_palette_share": palette_share,
        "within_folio_drift_component": drift_comp,
        "within_folio_drift_z": drift_z,
        "within_folio_drift_share": drift_share,
        "both_positive_gt_2sd": bool(
            palette_comp > 0.0 and drift_comp > 0.0 and palette_z > 2.0 and drift_z > 2.0
        ),
    }


def measure_stream(
    folios: list[dict],
    unit_kind: str = "eva",
    name: str = "",
    n_perm: int = N_PERM,
    seed: int = SEED,
    compute_d3: bool = False,
) -> dict:
    """Measure M1, M2, M3 (and optional D3 decomposition) against n_perm within-folio permutations."""
    t0 = time.perf_counter()
    mats = [folio_matrices(f["lines"], unit_kind) for f in folios]
    obs = eval_prepared_folios(mats, None)

    rng = np.random.default_rng(seed)
    null_draws = []
    for _ in range(n_perm):
        perms = [rng.permutation(m[0].shape[0]) for m in mats]
        null_draws.append(eval_prepared_folios(mats, perms))

    m1_bins: dict[str, dict] = {}
    m2_jaccard_bins: dict[str, dict] = {}
    m2_cos3_bins: dict[str, dict] = {}
    for b in LAG_NAMES:
        null_e = np.asarray([d["edit1_lag"][b] for d in null_draws], dtype=np.float64)
        m1_bins[b] = {
            "rate": float(obs["edit1_lag"][b]),
            "n_edit1": int(obs["e_bin"][b]),
            "n_eligible": int(obs["n_bin"][b]),
            "null_mean": float(null_e.mean()),
            "null_sd": float(null_e.std(ddof=1)) if len(null_e) >= 2 else 0.0,
            "null_p95": float(np.percentile(null_e, 95, method="linear")),
        }
        null_j = np.asarray([d["jaccard_lag"][b] for d in null_draws], dtype=np.float64)
        m2_jaccard_bins[b] = {
            "mean": float(obs["jaccard_lag"][b]),
            "n_line_pairs": int(obs["lp_cnt"][b]),
            "null_mean": float(null_j.mean()),
            "null_sd": float(null_j.std(ddof=1)) if len(null_j) >= 2 else 0.0,
            "null_p95": float(np.percentile(null_j, 95, method="linear")),
        }
        null_c = np.asarray([d["cos3_lag"][b] for d in null_draws], dtype=np.float64)
        m2_cos3_bins[b] = {
            "mean": float(obs["cos3_lag"][b]),
            "n_line_pairs": int(obs["lp_cnt"][b]),
            "null_mean": float(null_c.mean()),
            "null_sd": float(null_c.std(ddof=1)) if len(null_c) >= 2 else 0.0,
            "null_p95": float(np.percentile(null_c, 95, method="linear")),
        }

    s_edit_null = np.asarray([d["S_edit"] for d in null_draws], dtype=np.float64)
    s_edit_mean = float(s_edit_null.mean())
    s_edit_sd = float(s_edit_null.std(ddof=1)) if len(s_edit_null) >= 2 else 0.0
    s_edit_p95 = float(np.percentile(s_edit_null, 95, method="linear"))
    s_edit_obs = float(obs["S_edit"])
    s_edit_z = float((s_edit_obs - s_edit_mean) / s_edit_sd) if s_edit_sd > 0.0 else 0.0
    s_edit_pass = bool(s_edit_obs > s_edit_p95)

    s_cos3_null = np.asarray([d["S_cos3"] for d in null_draws], dtype=np.float64)
    s_cos3_mean = float(s_cos3_null.mean())
    s_cos3_sd = float(s_cos3_null.std(ddof=1)) if len(s_cos3_null) >= 2 else 0.0
    s_cos3_p95 = float(np.percentile(s_cos3_null, 95, method="linear"))
    s_cos3_obs = float(obs["S_cos3"])
    s_cos3_z = float((s_cos3_obs - s_cos3_mean) / s_cos3_sd) if s_cos3_sd > 0.0 else 0.0
    s_cos3_pass = bool(s_cos3_obs > s_cos3_p95)

    s_jac_null = np.asarray([d["S_jaccard"] for d in null_draws], dtype=np.float64)
    s_jac_mean = float(s_jac_null.mean())
    s_jac_sd = float(s_jac_null.std(ddof=1)) if len(s_jac_null) >= 2 else 0.0
    s_jac_p95 = float(np.percentile(s_jac_null, 95, method="linear"))
    s_jac_obs = float(obs["S_jaccard"])

    half_null = np.asarray([d["half_cos"] for d in null_draws], dtype=np.float64)
    half_null_mean = float(half_null.mean())
    half_null_sd = float(half_null.std(ddof=1)) if len(half_null) >= 2 else 0.0
    half_null_p05 = float(np.percentile(half_null, 5, method="linear"))
    half_obs = float(obs["half_cos"])
    half_js = float(half_obs - half_null_mean)
    half_z = float(half_js / half_null_sd) if half_null_sd > 0.0 else 0.0

    d3_rec = None
    if compute_d3:
        folio_perm_p12 = [float(d["p_edit1_12"]) for d in null_draws]
        d3_rec = compute_d3_decomposition(
            folios,
            float(obs["p_edit1_12"]),
            folio_perm_p12,
            unit_kind=unit_kind,
            n_perm=n_perm,
            seed=seed,
        )

    n_folios = len(folios)
    n_lines = sum(len(f["lines"]) for f in folios)
    n_tokens = sum(len(line) for f in folios for line in f["lines"])
    n_quires = len({str(f["quire"]) for f in folios})

    return {
        "name": name,
        "unit_kind": unit_kind,
        "n_folios": int(n_folios),
        "n_quires": int(n_quires),
        "n_lines": int(n_lines),
        "n_tokens": int(n_tokens),
        "M1": {
            "edit1_lag": m1_bins,
            "p_edit1_12": float(obs["p_edit1_12"]),
            "p_edit1_5p": float(obs["p_edit1_5p"]),
            "S_edit": s_edit_obs,
            "S_edit_null_mean": s_edit_mean,
            "S_edit_null_sd": s_edit_sd,
            "S_edit_null_p95": s_edit_p95,
            "S_edit_z": s_edit_z,
            "pass": s_edit_pass,
        },
        "M2": {
            "jaccard_lag": m2_jaccard_bins,
            "cos3_lag": m2_cos3_bins,
            "mean_cos3_12": float(obs["mean_cos3_12"]),
            "mean_cos3_5p": float(obs["mean_cos3_5p"]),
            "S_cos3": s_cos3_obs,
            "S_cos3_null_mean": s_cos3_mean,
            "S_cos3_null_sd": s_cos3_sd,
            "S_cos3_null_p95": s_cos3_p95,
            "S_cos3_z": s_cos3_z,
            "pass": s_cos3_pass,
            "mean_jaccard_12": float(obs["mean_jaccard_12"]),
            "mean_jaccard_5p": float(obs["mean_jaccard_5p"]),
            "S_jaccard": s_jac_obs,
            "S_jaccard_null_mean": s_jac_mean,
            "S_jaccard_null_sd": s_jac_sd,
            "S_jaccard_null_p95": s_jac_p95,
        },
        "M3": {
            "half_cos_obs": half_obs,
            "half_cos_null_mean": half_null_mean,
            "half_cos_null_sd": half_null_sd,
            "half_cos_null_p05": half_null_p05,
            "half_js": half_js,
            "half_js_z": half_z,
            "drifted_apart": bool(half_obs < half_null_p05),
        },
        "D3": d3_rec,
        "runtime_sec": float(time.perf_counter() - t0),
    }


def load_ms_folios(hand: str) -> list[dict]:
    """Load paragraph lines for MS hand via h30_lib.load_ms(hand), restricted to folios with >= 8 lines."""
    h43_lib._bind_zl3b()
    lines = h30_lib.load_ms(hand)
    by_page: dict[str, list[list[str]]] = defaultdict(list)
    page_quire: dict[str, str] = {}
    for line in lines:
        page = str(line["page"])
        by_page[page].append(list(line["words"]))
        page_quire[page] = str(line["quire"])
    folios = []
    for page, flines in by_page.items():
        if len(flines) >= MIN_FOLIO_LINES:
            folios.append({"folio": page, "quire": page_quire[page], "lines": flines})
    return folios


def load_prose_folios(name: str, n_tokens: int = N_STREAM) -> list[dict]:
    """Load real chapter stretches from h43 with >= 8 lines of 9 tokens, segmented into <=25-line folios."""
    if name == "it_boccaccio":
        stream, _ = h43_lib.load_boccaccio()
        tokens = list(load_italian("it_boccaccio"))
    elif name == "la_pliny_herbal":
        stream, _ = h43_lib.load_pliny()
        tokens = list(load_tokens("la_pliny_herbal", None))
    else:
        raise ValueError(f"unknown prose control {name!r}")
    stretches = h43_lib.split_lengths(tokens, list(stream.quires[0].folio_lengths))
    folios: list[dict] = []
    tot_tok = 0
    f_idx = 0
    for st in stretches:
        n_full = (len(st) // FAKE_LINE_WORDS) * FAKE_LINE_WORDS
        lines = [st[i : i + FAKE_LINE_WORDS] for i in range(0, n_full, FAKE_LINE_WORDS)]
        if len(lines) < MIN_FOLIO_LINES:
            continue
        for k in range(0, len(lines), FAKE_FOLIO_LINES):
            chunk = lines[k : k + FAKE_FOLIO_LINES]
            if len(chunk) >= MIN_FOLIO_LINES:
                folios.append({"folio": f"{name}_f{f_idx}", "quire": "q0", "lines": chunk})
                f_idx += 1
                tot_tok += sum(len(line) for line in chunk)
                if tot_tok >= n_tokens:
                    break
        if tot_tok >= n_tokens:
            break
    return folios


def load_self_citation_folios(n_tokens: int = N_STREAM) -> list[dict]:
    """Load fitted_s1.txt lines up to n_tokens, segmented into fake folios of 25 lines (>= 8 lines)."""
    raw_lines = SELF_CITATION_PATH.read_text(encoding="utf-8").splitlines()
    lines: list[list[str]] = []
    seen = 0
    for raw in raw_lines:
        ws = raw.split()
        if not ws or seen >= n_tokens:
            continue
        chunk = ws[: n_tokens - seen]
        lines.append(chunk)
        seen += len(chunk)
    folios: list[dict] = []
    for idx, k in enumerate(range(0, len(lines), FAKE_FOLIO_LINES)):
        flines = lines[k : k + FAKE_FOLIO_LINES]
        if len(flines) >= MIN_FOLIO_LINES:
            folios.append({"folio": f"sc_f{idx}", "quire": f"q{idx // 8}", "lines": flines})
    return folios


def load_h39_native_tuned_folios() -> list[dict]:
    """Load lines_2B_native_tuned.json, segmented into fake folios of 25 lines (>= 8 lines)."""
    lines = json.loads(H39_NATIVE_TUNED_PATH.read_text(encoding="utf-8"))
    folios: list[dict] = []
    for idx, k in enumerate(range(0, len(lines), FAKE_FOLIO_LINES)):
        flines = [list(line) for line in lines[k : k + FAKE_FOLIO_LINES]]
        if len(flines) >= MIN_FOLIO_LINES:
            folios.append({"folio": f"h39_f{idx}", "quire": f"q{idx // 8}", "lines": flines})
    return folios


def load_palette_ctrl_folios(seed: int = SEED) -> list[dict]:
    """MS 2B folios (>= 8 lines) with line order randomly permuted within each folio (seed 48)."""
    base = load_ms_folios("2B")
    rng = np.random.default_rng(seed)
    folios: list[dict] = []
    for f in base:
        perm = rng.permutation(len(f["lines"]))
        folios.append(
            {
                "folio": f["folio"],
                "quire": f["quire"],
                "lines": [list(f["lines"][int(i)]) for i in perm],
            }
        )
    return folios


def score_predictions(streams: dict) -> dict:
    """Score D1, D2, D3 from PREREG.md across MS hands 1A, 2B, 3B."""
    d1_hands = [h for h in HANDS if streams[f"MS_{h}"]["M1"]["pass"]]
    d2_hands = [h for h in HANDS if streams[f"MS_{h}"]["M2"]["pass"]]
    d3_hands = [
        h
        for h in HANDS
        if streams[f"MS_{h}"]["D3"] is not None and streams[f"MS_{h}"]["D3"]["both_positive_gt_2sd"]
    ]
    return {
        "D1": len(d1_hands) >= 2,
        "D1_pass_hands": d1_hands,
        "D2": len(d2_hands) >= 2,
        "D2_pass_hands": d2_hands,
        "D3": len(d3_hands) >= 2,
        "D3_pass_hands": d3_hands,
    }


def measure_all(n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """Measure all MS hands, prose controls, and drift/palette generators."""
    t0 = time.perf_counter()
    streams: dict[str, dict] = {}

    for hand in HANDS:
        key = f"MS_{hand}"
        print(f"load and measure {key}", flush=True)
        folios = load_ms_folios(hand)
        streams[key] = measure_stream(
            folios, unit_kind="eva", name=key, n_perm=n_perm, seed=seed, compute_d3=True
        )
        m1 = streams[key]["M1"]
        m2 = streams[key]["M2"]
        m3 = streams[key]["M3"]
        d3 = streams[key]["D3"]
        print(
            f"  {key}: S_edit={m1['S_edit']:.6f} (p95={m1['S_edit_null_p95']:.6f}, pass={m1['pass']}) "
            f"S_cos3={m2['S_cos3']:.6f} (p95={m2['S_cos3_null_p95']:.6f}, pass={m2['pass']}) "
            f"half_js={m3['half_js']:.6f} "
            f"D3_both={d3['both_positive_gt_2sd']} (pal_z={d3['folio_palette_z']:.2f}, drift_z={d3['within_folio_drift_z']:.2f})",
            flush=True,
        )

    for cname in PROSE_KEYS:
        print(f"load and measure {cname}", flush=True)
        folios = load_prose_folios(cname, n_tokens=N_STREAM)
        streams[cname] = measure_stream(
            folios, unit_kind="char", name=cname, n_perm=n_perm, seed=seed, compute_d3=False
        )
        m1 = streams[cname]["M1"]
        m2 = streams[cname]["M2"]
        m3 = streams[cname]["M3"]
        print(
            f"  {cname}: S_edit={m1['S_edit']:.6f} (p95={m1['S_edit_null_p95']:.6f}, pass={m1['pass']}) "
            f"S_cos3={m2['S_cos3']:.6f} (p95={m2['S_cos3_null_p95']:.6f}, pass={m2['pass']}) "
            f"half_js={m3['half_js']:.6f}",
            flush=True,
        )

    for gname, loader in (
        ("self_citation", load_self_citation_folios),
        ("h39_native_tuned", load_h39_native_tuned_folios),
        ("palette_ctrl", load_palette_ctrl_folios),
    ):
        print(f"load and measure {gname}", flush=True)
        folios = loader()
        streams[gname] = measure_stream(
            folios, unit_kind="eva", name=gname, n_perm=n_perm, seed=seed, compute_d3=False
        )
        m1 = streams[gname]["M1"]
        m2 = streams[gname]["M2"]
        m3 = streams[gname]["M3"]
        print(
            f"  {gname}: S_edit={m1['S_edit']:.6f} (p95={m1['S_edit_null_p95']:.6f}, pass={m1['pass']}) "
            f"S_cos3={m2['S_cos3']:.6f} (p95={m2['S_cos3_null_p95']:.6f}, pass={m2['pass']}) "
            f"half_js={m3['half_js']:.6f}",
            flush=True,
        )

    preds = score_predictions(streams)
    return {
        "hypothesis": "h48_within_folio_drift",
        "lag_bins": list(LAG_NAMES),
        "min_folio_lines": MIN_FOLIO_LINES,
        "fake_folio_lines": FAKE_FOLIO_LINES,
        "fake_line_words": FAKE_LINE_WORDS,
        "n_stream": N_STREAM,
        "n_perm": n_perm,
        "seed": seed,
        "streams": streams,
        "predictions": preds,
        "numpy": np.__version__,
        "python": platform.python_version(),
        "runtime_sec": float(time.perf_counter() - t0),
    }
