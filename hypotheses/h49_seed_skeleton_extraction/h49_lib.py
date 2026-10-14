"""h49: De-padding / seed-skeleton extraction on MS 408 vs h47 page-line generator (PREREG.md).

Tests whether stripping same-folio exact repeats and one-edit echoes (`local_W25` and `folio_comp`)
uncovers a language-like seed skeleton with positive word-order syntax (`D1_seed > 0`), sequential
within-folio seed order (`mi_adj_z > 1.96`), or a distinct morpheme inventory (`morphs_per_type`),
or whether the stripped MS 408 skeleton matches the no-plaintext `h47` `page_line_copier` generator.
No translation claims are made.
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
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

for _rel in (
    "src",
    "hypotheses/h13_top_word_context",
    "hypotheses/h19_heldout_likelihood",
    "hypotheses/h20_generators_vs_italian",
    "hypotheses/h27_plaintext_ablation",
    "hypotheses/h30_line_structure",
    "hypotheses/h31_word_construction",
    "hypotheses/h42_near_repeat_decay",
    "hypotheses/h43_page_edge",
    "hypotheses/h47_page_line_generator",
):
    _p = str(ROOT / _rel)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import h13_lib  # noqa: E402
import h19_lib  # noqa: E402
import h20_lib  # noqa: E402
import h27_lib  # noqa: E402
import h30_lib  # noqa: E402
import h31_lib  # noqa: E402
import h42_lib  # noqa: E402
import h43_lib  # noqa: E402
import h47_lib  # noqa: E402
import run_h19  # noqa: E402
from fetch_italian import load_italian  # noqa: E402

HANDS = ("1A", "2B", "3B")
MS_KEYS = ("MS_1A", "MS_2B", "MS_3B")
PLC_KEYS = ("page_line_copier_1A", "page_line_copier_2B", "page_line_copier_3B")
CONTROL_KEYS = ("naibbe_boccaccio_swap", "it_boccaccio")
STREAM_ORDER = (
    "MS_1A",
    "page_line_copier_1A",
    "MS_2B",
    "page_line_copier_2B",
    "MS_3B",
    "page_line_copier_3B",
    "naibbe_boccaccio_swap",
    "it_boccaccio",
)
MODES = ("raw", "local_W25", "folio_comp")

N_STREAM = 10500
W_LOCAL = 25
SEED = 49
N_PERM_MI = 100
N_PERM_FOLIO = 200
BAYES_SWEEPS = 100
TOP_K_CLASSES = 50

S1_MIN_D1 = 0.05
S1_MIN_DELTA_PLC = 0.10
S2_MIN_Z = 1.96
S3_MAX_DIFF = 0.08
NAT_MORPH_THRESHOLD = 0.18

H47_STREAMS_PATH = ROOT / "hypotheses" / "h47_page_line_generator" / "results" / "streams.json"
QUIRES_CSV = ROOT / "data" / "quires.csv"


def to_units(word: str, unit_kind: str = "eva") -> tuple[str, ...]:
    """Convert a token into collapsed EVA units (`h13_lib.SEG`) or character units."""
    if unit_kind == "eva":
        return tuple(h13_lib.SEG(word))
    if unit_kind == "char":
        return tuple(word)
    raise ValueError(f"unknown unit_kind {unit_kind!r}")


def extract_folio_seeds(
    words: list[str],
    mode: str,
    unit_kind: str = "eva",
    window: int = W_LOCAL,
) -> list[str]:
    """Extract surviving seed tokens on a single folio under `raw`, `local_W25`, or `folio_comp`."""
    if mode == "raw":
        return list(words)
    if mode not in ("local_W25", "folio_comp"):
        raise ValueError(f"unknown seed extraction mode {mode!r}")

    units = [to_units(w, unit_kind) for w in words]
    kept: list[str] = []
    for t, (w, u_t) in enumerate(zip(words, units)):
        lo = max(0, t - window) if mode == "local_W25" else 0
        has_echo = False
        for s in range(lo, t):
            u_s = units[s]
            if u_t == u_s or h42_lib.edit1(u_t, u_s):
                has_echo = True
                break
        if not has_echo:
            kept.append(w)
    return kept


def extract_seeds(
    stream_or_words: list[dict] | list[str],
    mode: str,
    unit_kind: str = "eva",
    window: int = W_LOCAL,
) -> list[dict] | list[str]:
    """Apply `extract_folio_seeds` to either a list of folio dicts or a single folio's token list."""
    if not stream_or_words:
        return []
    if isinstance(stream_or_words[0], str):
        return extract_folio_seeds(stream_or_words, mode=mode, unit_kind=unit_kind, window=window)
    out_folios: list[dict] = []
    for f in stream_or_words:
        new_f = dict(f)
        new_f["words"] = extract_folio_seeds(
            list(f["words"]), mode=mode, unit_kind=unit_kind, window=window
        )
        out_folios.append(new_f)
    return out_folios


def records_to_folios(records: list[dict]) -> list[dict]:
    """Aggregate line records from `h30_lib` / `h47_lib` into ordered folio records with bifolium IDs."""
    q_df = pd.read_csv(QUIRES_CSV, dtype=str).set_index("page")
    by_page: dict[str, list[str]] = defaultdict(list)
    meta: dict[str, tuple[str, str]] = {}
    for rec in records:
        page = str(rec["page"])
        by_page[page].extend(rec["words"])
        if page not in meta:
            quire = str(rec["quire"])
            bif = str(q_df.bifolium_id.get(page, page))
            meta[page] = (quire, bif)
    folios: list[dict] = []
    for page, ws in by_page.items():
        quire, bif = meta[page]
        folios.append(
            {
                "id": page,
                "folio": page,
                "quire": quire,
                "bif": bif,
                "words": list(ws),
            }
        )
    return folios


def load_ms_folios(hand: str, max_tokens: int = N_STREAM) -> list[dict]:
    """Load real MS 408 line records for `hand` up to `max_tokens` and group by folio."""
    h43_lib._bind_zl3b()
    recs = h47_lib.load_template(hand, max_tokens=max_tokens)
    return records_to_folios(recs)


def load_plc_folios(hand: str, seed: int = h47_lib.SEED) -> list[dict]:
    """Load or generate `page_line_copier` for `hand` on its real layout template."""
    h43_lib._bind_zl3b()
    key = f"page_line_copier_{hand}"
    if seed == h47_lib.SEED and H47_STREAMS_PATH.is_file():
        payload = json.loads(H47_STREAMS_PATH.read_text(encoding="utf-8"))
        gen_lines = payload.get("generated_lines", {}).get(key)
        if gen_lines is not None:
            _, recs = h47_lib.layout_flat_lines_on_template(gen_lines, hand)
            return records_to_folios(recs)
    _, recs = h47_lib.generate_page_line_copier(hand, seed=seed)
    return records_to_folios(recs)


def load_naibbe_boccaccio_swap_folios(seed: int = 1) -> list[dict]:
    """Build Naibbe-Italian on Boccaccio + 5% suffix-swap copy laid onto the Hand 2B template."""
    h43_lib._bind_zl3b()
    bocc = list(load_italian("it_boccaccio"))
    cipher_toks, _ = h27_lib.encrypt_swap(bocc, seed=seed, n_words_out=2 * N_STREAM)
    _, recs = h47_lib.layout_flat_lines_on_template([cipher_toks[:N_STREAM]], "2B")
    return records_to_folios(recs)


def load_it_boccaccio_folios() -> list[dict]:
    """Lay the first 10,500 tokens of `it_boccaccio` onto the Hand 2B folio/line template."""
    h43_lib._bind_zl3b()
    bocc = list(load_italian("it_boccaccio"))[:N_STREAM]
    _, recs = h47_lib.layout_flat_lines_on_template([bocc], "2B")
    return records_to_folios(recs)


def load_all_streams() -> dict[str, tuple[list[dict], str]]:
    """Load all eight preregistered streams and their unit segmentation kinds."""
    streams: dict[str, tuple[list[dict], str]] = {}
    for hand in HANDS:
        streams[f"MS_{hand}"] = (load_ms_folios(hand, N_STREAM), "eva")
        streams[f"page_line_copier_{hand}"] = (load_plc_folios(hand, seed=h47_lib.SEED), "eva")
    streams["naibbe_boccaccio_swap"] = (load_naibbe_boccaccio_swap_folios(seed=1), "eva")
    streams["it_boccaccio"] = (load_it_boccaccio_folios(), "char")
    return streams


def compute_d1_seed(folios: list[dict], n_folds: int = 5) -> dict:
    """Compute 5-fold bifolium-grouped Kneser-Ney bits/word and word-order gain D1_seed."""
    non_empty = [f for f in folios if f["words"]]
    if len(non_empty) < 2:
        return {
            "KN1_bits": 0.0,
            "KN2_bits": 0.0,
            "KN3_bits": 0.0,
            "G_bits": 0.0,
            "D1_seed": 0.0,
            "n_scored_tokens": 0,
        }
    folds = run_h19.group_folds(non_empty, "bif", n_folds)
    lp1: list[float] = []
    lp2: list[float] = []
    lp3: list[float] = []
    lpg: list[float] = []
    for tr_idx, te_idx in folds:
        tr_pages = [non_empty[i]["words"] for i in tr_idx if non_empty[i]["words"]]
        te_pages = [non_empty[i]["words"] for i in te_idx if non_empty[i]["words"]]
        if not tr_pages or not te_pages:
            continue
        tr_words = [w for ws in tr_pages for w in ws]
        g_lm = h19_lib.CharLM(4).fit(tr_words)
        kn1 = h19_lib.KN(1, g_lm).fit(tr_pages)
        kn2 = h19_lib.KN(2, g_lm).fit(tr_pages)
        kn3 = h19_lib.KN(3, g_lm).fit(tr_pages)
        for ws in te_pages:
            for i, w in enumerate(ws):
                hist = ws[:i]
                lpg.append(g_lm.logp(w))
                lp1.append(kn1.logp(w, hist))
                lp2.append(kn2.logp(w, hist))
                lp3.append(kn3.logp(w, hist))

    b1 = float(-np.mean(lp1)) if lp1 else 0.0
    b2 = float(-np.mean(lp2)) if lp2 else 0.0
    b3 = float(-np.mean(lp3)) if lp3 else 0.0
    bg = float(-np.mean(lpg)) if lpg else 0.0
    d1_val = float(b1 - min(b2, b3))
    return {
        "KN1_bits": b1,
        "KN2_bits": b2,
        "KN3_bits": b3,
        "G_bits": bg,
        "D1_seed": d1_val,
        "n_scored_tokens": int(len(lp1)),
    }


def compute_morphs_per_type(
    tokens: list[str],
    sweeps: int = BAYES_SWEEPS,
    seed: int = 0,
) -> tuple[dict, dict[str, tuple]]:
    """Compute h31 Bayesian stem+suffix and AffixModel inventory ratios on unique seed types."""
    ty = Counter(tokens)
    if not ty:
        return (
            {
                "morphs_per_type": 0.0,
                "morphs_per_type_bayes": 0.0,
                "morphs_per_type_affix": 0.0,
                "n_types": 0,
                "n_morph_bayes": 0,
                "n_suffix_bayes": 0,
                "n_morph_affix": 0,
                "n_suffix_affix": 0,
                "language_like_ge_018": False,
            },
            {},
        )
    seg_b, _ = h31_lib.seg_bayes(ty, seed=seed, sweeps=sweeps)
    morphs_b = {m for w in ty for m in seg_b[w][2]}
    sufs_b = {seg_b[w][1] for w in ty}
    mpt_b = float(len(morphs_b) / len(ty))

    seg_a, _ = h31_lib.seg_affix(ty)
    morphs_a = {m for w in ty for m in seg_a[w][2]}
    sufs_a = {seg_a[w][1] for w in ty}
    mpt_a = float(len(morphs_a) / len(ty))

    return (
        {
            "morphs_per_type": mpt_b,
            "morphs_per_type_bayes": mpt_b,
            "morphs_per_type_affix": mpt_a,
            "n_types": int(len(ty)),
            "n_morph_bayes": int(len(morphs_b)),
            "n_suffix_bayes": int(len(sufs_b)),
            "n_morph_affix": int(len(morphs_a)),
            "n_suffix_affix": int(len(sufs_a)),
            "language_like_ge_018": bool(mpt_b >= NAT_MORPH_THRESHOLD),
        },
        seg_b,
    )


def compute_mi_adj(
    folios: list[dict],
    seg_map: dict[str, tuple],
    n_perm: int = N_PERM_MI,
    seed: int = SEED,
    top_k: int = TOP_K_CLASSES,
) -> dict:
    """Compute adjacent seed-word class (top-50 stems) bigram MI vs 100 within-folio permutations."""
    toks = [w for f in folios for w in f["words"]]
    if len(toks) < 2:
        return {
            "mi_adj_obs": 0.0,
            "mi_adj_null_mean": 0.0,
            "mi_adj_null_sd": 0.0,
            "mi_adj_null_p95": 0.0,
            "mi_adj_excess": 0.0,
            "mi_adj_z": 0.0,
            "pass_gt_196": False,
        }

    stems = [seg_map[w][0] if w in seg_map else w for w in toks]
    top_stems = {s for s, _ in Counter(stems).most_common(top_k)}
    folio_seqs = [
        [
            (seg_map[w][0] if w in seg_map else w)
            if (seg_map[w][0] if w in seg_map else w) in top_stems
            else "OTHER"
            for w in f["words"]
        ]
        for f in folios
        if len(f["words"]) >= 2
    ]

    def _seq_mi(seqs: list[list[str]]) -> float:
        pairs = [(s[i], s[i + 1]) for s in seqs for i in range(len(s) - 1)]
        return float(h30_lib.mi(pairs)) if pairs else 0.0

    obs = _seq_mi(folio_seqs)
    rng = np.random.default_rng(seed)
    null_vals: list[float] = []
    for _ in range(n_perm):
        perm_seqs = [list(rng.permutation(s)) for s in folio_seqs]
        null_vals.append(_seq_mi(perm_seqs))

    arr = np.asarray(null_vals, dtype=np.float64)
    null_mean = float(arr.mean()) if len(arr) else 0.0
    null_sd = float(arr.std(ddof=1)) if len(arr) >= 2 else 0.0
    null_p95 = float(np.percentile(arr, 95, method="linear")) if len(arr) else 0.0
    excess = float(obs - null_mean)
    z_val = float(excess / null_sd) if null_sd > 0.0 else 0.0

    return {
        "mi_adj_obs": obs,
        "mi_adj_null_mean": null_mean,
        "mi_adj_null_sd": null_sd,
        "mi_adj_null_p95": null_p95,
        "mi_adj_excess": excess,
        "mi_adj_z": z_val,
        "pass_gt_196": bool(z_val > S2_MIN_Z and obs > null_p95),
    }


def build_unit_edit1_lookup(
    folios: list[dict], unit_kind: str = "eva"
) -> dict[tuple[str, ...], set[tuple[str, ...]]]:
    """Precompute unit-level self+edit1 neighborhood sets for all unique unit tuples in a stream."""
    unique_units = list({to_units(w, unit_kind) for f in folios for w in f["words"]})
    by_len: dict[int, list[tuple[str, ...]]] = defaultdict(list)
    for u in unique_units:
        by_len[len(u)].append(u)
    neighbors: dict[tuple[str, ...], set[tuple[str, ...]]] = {u: {u} for u in unique_units}
    for length, items in by_len.items():
        n_it = len(items)
        for i in range(n_it):
            ua = items[i]
            for j in range(i + 1, n_it):
                ub = items[j]
                if h42_lib.edit1(ua, ub):
                    neighbors[ua].add(ub)
                    neighbors[ub].add(ua)
        for ua in items:
            for ub in by_len.get(length + 1, ()):
                if h42_lib.edit1(ua, ub):
                    neighbors[ua].add(ub)
                    neighbors[ub].add(ua)
    return neighbors


def compute_adj_folio_cos(
    folios: list[dict],
    unit_kind: str = "eva",
    n_perm: int = N_PERM_FOLIO,
    seed: int = SEED,
    unit_neighbors: dict[tuple[str, ...], set[tuple[str, ...]]] | None = None,
) -> dict:
    """Compute cross-folio seed continuity (`adj_folio_cos` and 1-edit overlap) vs 200 quire permutations."""
    if unit_neighbors is None:
        unit_neighbors = build_unit_edit1_lookup(folios, unit_kind=unit_kind)

    by_quire: dict[str, list[list[str]]] = defaultdict(list)
    for f in folios:
        by_quire[str(f["quire"])].append(list(f["words"]))

    q_mats: list[tuple[int, np.ndarray, np.ndarray]] = []
    for _q, flist in by_quire.items():
        m = len(flist)
        if m < 2:
            continue
        cnts = [Counter(ws) for ws in flist]
        usets = [{to_units(w, unit_kind) for w in ws} for ws in flist]
        unb_sets = [
            set().union(*(unit_neighbors[u] for u in us)) if us else set()
            for us in usets
        ]
        c_mat = np.zeros((m, m), dtype=np.float64)
        e_mat = np.zeros((m, m), dtype=np.float64)
        for i in range(m):
            for j in range(i + 1, m):
                cos_ij = h43_lib.cosine_counts(cnts[i], cnts[j]) if cnts[i] and cnts[j] else 0.0
                c_mat[i, j] = c_mat[j, i] = cos_ij
                ui, uj = usets[i], usets[j]
                if ui and uj:
                    ov_i = len(ui & unb_sets[j]) / len(ui)
                    ov_j = len(uj & unb_sets[i]) / len(uj)
                    e_mat[i, j] = e_mat[j, i] = 0.5 * (ov_i + ov_j)
        q_mats.append((m, c_mat, e_mat))

    n_adj_pairs = sum(m - 1 for m, _, _ in q_mats)
    if n_adj_pairs == 0:
        return {
            "n_adj_folio_pairs": 0,
            "adj_folio_cos": 0.0,
            "adj_folio_cos_null_mean": 0.0,
            "adj_folio_cos_null_sd": 0.0,
            "adj_folio_cos_null_p95": 0.0,
            "adj_folio_cos_excess": 0.0,
            "adj_folio_cos_z": 0.0,
            "adj_folio_edit1_overlap": 0.0,
            "adj_folio_edit1_null_mean": 0.0,
            "adj_folio_edit1_null_sd": 0.0,
            "adj_folio_edit1_null_p95": 0.0,
            "adj_folio_edit1_excess": 0.0,
            "adj_folio_edit1_z": 0.0,
        }

    obs_cos = (
        sum(float(c_mat[np.arange(m - 1), np.arange(1, m)].sum()) for m, c_mat, _ in q_mats)
        / n_adj_pairs
    )
    obs_e1 = (
        sum(float(e_mat[np.arange(m - 1), np.arange(1, m)].sum()) for m, _, e_mat in q_mats)
        / n_adj_pairs
    )

    rng = np.random.default_rng(seed)
    null_cos: list[float] = []
    null_e1: list[float] = []
    for _ in range(n_perm):
        sc = 0.0
        se = 0.0
        for m, c_mat, e_mat in q_mats:
            perm = rng.permutation(m)
            sc += float(c_mat[perm[:-1], perm[1:]].sum())
            se += float(e_mat[perm[:-1], perm[1:]].sum())
        null_cos.append(sc / n_adj_pairs)
        null_e1.append(se / n_adj_pairs)

    ac = np.asarray(null_cos, dtype=np.float64)
    ae = np.asarray(null_e1, dtype=np.float64)
    cos_mean = float(ac.mean())
    cos_sd = float(ac.std(ddof=1)) if len(ac) >= 2 else 0.0
    cos_p95 = float(np.percentile(ac, 95, method="linear"))
    cos_ex = float(obs_cos - cos_mean)
    cos_z = float(cos_ex / cos_sd) if cos_sd > 0.0 else 0.0

    e1_mean = float(ae.mean())
    e1_sd = float(ae.std(ddof=1)) if len(ae) >= 2 else 0.0
    e1_p95 = float(np.percentile(ae, 95, method="linear"))
    e1_ex = float(obs_e1 - e1_mean)
    e1_z = float(e1_ex / e1_sd) if e1_sd > 0.0 else 0.0

    return {
        "n_adj_folio_pairs": int(n_adj_pairs),
        "adj_folio_cos": float(obs_cos),
        "adj_folio_cos_null_mean": cos_mean,
        "adj_folio_cos_null_sd": cos_sd,
        "adj_folio_cos_null_p95": cos_p95,
        "adj_folio_cos_excess": cos_ex,
        "adj_folio_cos_z": cos_z,
        "adj_folio_edit1_overlap": float(obs_e1),
        "adj_folio_edit1_null_mean": e1_mean,
        "adj_folio_edit1_null_sd": e1_sd,
        "adj_folio_edit1_null_p95": e1_p95,
        "adj_folio_edit1_excess": e1_ex,
        "adj_folio_edit1_z": e1_z,
    }


def measure_stream_mode(
    folios: list[dict],
    raw_n_tokens: int,
    mode: str,
    unit_kind: str = "eva",
    sweeps: int = BAYES_SWEEPS,
    n_perm_mi: int = N_PERM_MI,
    n_perm_folio: int = N_PERM_FOLIO,
    seed: int = SEED,
    unit_neighbors: dict[tuple[str, ...], set[tuple[str, ...]]] | None = None,
) -> dict:
    """Compute all four preregistered measures on a single stream and seed-filter mode."""
    seed_folios = extract_seeds(folios, mode=mode, unit_kind=unit_kind, window=W_LOCAL)
    tokens = [w for f in seed_folios for w in f["words"]]
    n_tokens = len(tokens)
    keep_rate = float(n_tokens / raw_n_tokens) if raw_n_tokens > 0 else 0.0

    d1_res = compute_d1_seed(seed_folios, n_folds=5)
    morph_res, seg_map = compute_morphs_per_type(tokens, sweeps=sweeps, seed=0)
    mi_res = compute_mi_adj(seed_folios, seg_map=seg_map, n_perm=n_perm_mi, seed=seed)
    cos_res = compute_adj_folio_cos(
        seed_folios,
        unit_kind=unit_kind,
        n_perm=n_perm_folio,
        seed=seed,
        unit_neighbors=unit_neighbors,
    )

    return {
        "mode": mode,
        "n_tokens": int(n_tokens),
        "n_types": int(morph_res["n_types"]),
        "keep_rate": keep_rate,
        "D1_seed": float(d1_res["D1_seed"]),
        "KN1_bits": float(d1_res["KN1_bits"]),
        "KN2_bits": float(d1_res["KN2_bits"]),
        "KN3_bits": float(d1_res["KN3_bits"]),
        "G_bits": float(d1_res["G_bits"]),
        "mi_adj_obs": float(mi_res["mi_adj_obs"]),
        "mi_adj_null_mean": float(mi_res["mi_adj_null_mean"]),
        "mi_adj_null_sd": float(mi_res["mi_adj_null_sd"]),
        "mi_adj_null_p95": float(mi_res["mi_adj_null_p95"]),
        "mi_adj_excess": float(mi_res["mi_adj_excess"]),
        "mi_adj_z": float(mi_res["mi_adj_z"]),
        "mi_adj_pass": bool(mi_res["pass_gt_196"]),
        "morphs_per_type": float(morph_res["morphs_per_type"]),
        "morphs_per_type_bayes": float(morph_res["morphs_per_type_bayes"]),
        "morphs_per_type_affix": float(morph_res["morphs_per_type_affix"]),
        "n_morph_bayes": int(morph_res["n_morph_bayes"]),
        "n_suffix_bayes": int(morph_res["n_suffix_bayes"]),
        "n_morph_affix": int(morph_res["n_morph_affix"]),
        "n_suffix_affix": int(morph_res["n_suffix_affix"]),
        "language_like_morphs": bool(morph_res["language_like_ge_018"]),
        "adj_folio_cos": float(cos_res["adj_folio_cos"]),
        "adj_folio_cos_null_mean": float(cos_res["adj_folio_cos_null_mean"]),
        "adj_folio_cos_null_sd": float(cos_res["adj_folio_cos_null_sd"]),
        "adj_folio_cos_null_p95": float(cos_res["adj_folio_cos_null_p95"]),
        "adj_folio_cos_excess": float(cos_res["adj_folio_cos_excess"]),
        "adj_folio_cos_z": float(cos_res["adj_folio_cos_z"]),
        "adj_folio_edit1_overlap": float(cos_res["adj_folio_edit1_overlap"]),
        "adj_folio_edit1_null_mean": float(cos_res["adj_folio_edit1_null_mean"]),
        "adj_folio_edit1_null_sd": float(cos_res["adj_folio_edit1_null_sd"]),
        "adj_folio_edit1_null_p95": float(cos_res["adj_folio_edit1_null_p95"]),
        "adj_folio_edit1_excess": float(cos_res["adj_folio_edit1_excess"]),
        "adj_folio_edit1_z": float(cos_res["adj_folio_edit1_z"]),
        "n_adj_folio_pairs": int(cos_res["n_adj_folio_pairs"]),
    }


def measure_stream(
    folios: list[dict],
    unit_kind: str = "eva",
    name: str = "",
    sweeps: int = BAYES_SWEEPS,
    n_perm_mi: int = N_PERM_MI,
    n_perm_folio: int = N_PERM_FOLIO,
    seed: int = SEED,
) -> dict:
    """Measure `raw`, `local_W25`, and `folio_comp` on a stream."""
    t0 = time.perf_counter()
    raw_n_tokens = sum(len(f["words"]) for f in folios)
    unit_neighbors = build_unit_edit1_lookup(folios, unit_kind=unit_kind)
    modes_out: dict[str, dict] = {}
    for mode in MODES:
        modes_out[mode] = measure_stream_mode(
            folios,
            raw_n_tokens=raw_n_tokens,
            mode=mode,
            unit_kind=unit_kind,
            sweeps=sweeps,
            n_perm_mi=n_perm_mi,
            n_perm_folio=n_perm_folio,
            seed=seed,
            unit_neighbors=unit_neighbors,
        )
    return {
        "name": name,
        "unit_kind": unit_kind,
        "n_folios": int(len(folios)),
        "n_quires": int(len({str(f["quire"]) for f in folios})),
        "raw_n_tokens": int(raw_n_tokens),
        "modes": modes_out,
        "runtime_sec": float(time.perf_counter() - t0),
    }


def evaluate_predictions(streams: dict[str, dict]) -> dict:
    """Evaluate preregistered predictions S1, S2, S3 across Hands 1A, 2B, 3B."""
    s1_by_hand: dict[str, dict] = {}
    s1_passing_hands: list[str] = []

    s2_by_hand: dict[str, dict] = {}
    s2_passing_hands: list[str] = []

    s3_by_hand: dict[str, dict] = {}
    s3_passing_hands: list[str] = []

    for hand in HANDS:
        ms = streams[f"MS_{hand}"]["modes"]
        plc = streams[f"page_line_copier_{hand}"]["modes"]

        raw_neg = bool(ms["raw"]["D1_seed"] < 0.0)
        w25_d1 = float(ms["local_W25"]["D1_seed"])
        w25_delta = float(w25_d1 - plc["local_W25"]["D1_seed"])
        w25_ok = bool(raw_neg and w25_d1 >= S1_MIN_D1 and w25_delta >= S1_MIN_DELTA_PLC)

        fc_d1 = float(ms["folio_comp"]["D1_seed"])
        fc_delta = float(fc_d1 - plc["folio_comp"]["D1_seed"])
        fc_ok = bool(raw_neg and fc_d1 >= S1_MIN_D1 and fc_delta >= S1_MIN_DELTA_PLC)

        hand_s1 = bool(w25_ok or fc_ok)
        if hand_s1:
            s1_passing_hands.append(hand)
        s1_by_hand[hand] = {
            "raw_D1": float(ms["raw"]["D1_seed"]),
            "local_W25_D1": w25_d1,
            "local_W25_plc_D1": float(plc["local_W25"]["D1_seed"]),
            "local_W25_delta_vs_plc": w25_delta,
            "local_W25_pass": w25_ok,
            "folio_comp_D1": fc_d1,
            "folio_comp_plc_D1": float(plc["folio_comp"]["D1_seed"]),
            "folio_comp_delta_vs_plc": fc_delta,
            "folio_comp_pass": fc_ok,
            "passed": hand_s1,
        }

        fc_mi_z = float(ms["folio_comp"]["mi_adj_z"])
        fc_mi_obs = float(ms["folio_comp"]["mi_adj_obs"])
        fc_mi_p95 = float(ms["folio_comp"]["mi_adj_null_p95"])
        hand_s2 = bool(fc_mi_z > S2_MIN_Z and fc_mi_obs > fc_mi_p95)
        if hand_s2:
            s2_passing_hands.append(hand)
        s2_by_hand[hand] = {
            "folio_comp_mi_adj_obs": fc_mi_obs,
            "folio_comp_mi_adj_null_p95": fc_mi_p95,
            "folio_comp_mi_adj_z": fc_mi_z,
            "passed": hand_s2,
        }

        diff_keep = abs(float(ms["local_W25"]["keep_rate"] - plc["local_W25"]["keep_rate"]))
        diff_d1 = abs(float(ms["local_W25"]["D1_seed"] - plc["local_W25"]["D1_seed"]))
        diff_morph = abs(
            float(ms["local_W25"]["morphs_per_type"] - plc["local_W25"]["morphs_per_type"])
        )
        hand_s3 = bool(
            diff_keep <= S3_MAX_DIFF and diff_d1 <= S3_MAX_DIFF and diff_morph <= S3_MAX_DIFF
        )
        if hand_s3:
            s3_passing_hands.append(hand)
        s3_by_hand[hand] = {
            "ms_keep_rate": float(ms["local_W25"]["keep_rate"]),
            "plc_keep_rate": float(plc["local_W25"]["keep_rate"]),
            "abs_diff_keep_rate": diff_keep,
            "ms_D1_seed": float(ms["local_W25"]["D1_seed"]),
            "plc_D1_seed": float(plc["local_W25"]["D1_seed"]),
            "abs_diff_D1_seed": diff_d1,
            "ms_morphs_per_type": float(ms["local_W25"]["morphs_per_type"]),
            "plc_morphs_per_type": float(plc["local_W25"]["morphs_per_type"]),
            "abs_diff_morphs_per_type": diff_morph,
            "within_008": hand_s3,
        }

    s1_pass = bool(len(s1_passing_hands) >= 2)
    s2_pass = bool(len(s2_passing_hands) >= 2)
    s3_pass = bool(len(s3_passing_hands) == len(HANDS) and not s1_pass)

    if s3_pass and not s1_pass and not s2_pass:
        verdict = "no_plaintext_skeleton_matched"
    elif s1_pass and s2_pass:
        verdict = "seed_syntax_supported"
    else:
        verdict = "mixed"

    return {
        "S1": {
            "passed": s1_pass,
            "passing_hands": s1_passing_hands,
            "by_hand": s1_by_hand,
            "description": (
                "In >= 2 MS hands, local_W25 or folio_comp flips D1 from negative to >= +0.05 "
                "and exceeds page_line_copier by >= +0.10 bits/word"
            ),
        },
        "S2": {
            "passed": s2_pass,
            "passing_hands": s2_passing_hands,
            "by_hand": s2_by_hand,
            "description": (
                "In >= 2 MS hands, folio_comp seed stream has adjacent top-50 stem bigram MI "
                "above the 95th percentile of 100 within-folio permutations (mi_adj_z > 1.96)"
            ),
        },
        "S3": {
            "passed": s3_pass,
            "passing_hands": s3_passing_hands,
            "by_hand": s3_by_hand,
            "description": (
                "Across Hands 1A, 2B, 3B, MS local_W25 keep_rate, D1_seed, and morphs_per_type "
                "all lie within +/- 0.08 of page_line_copier (and S1 fails)"
            ),
        },
        "verdict": verdict,
    }


def measure_all(
    sweeps: int = BAYES_SWEEPS,
    n_perm_mi: int = N_PERM_MI,
    n_perm_folio: int = N_PERM_FOLIO,
    seed: int = SEED,
) -> dict:
    """Load all streams, compute all four measures across all three modes, and score S1..S3."""
    t0 = time.perf_counter()
    raw_streams = load_all_streams()
    streams_out: dict[str, dict] = {}

    for key in STREAM_ORDER:
        folios, ukind = raw_streams[key]
        print(f"measuring {key} ({len(folios)} folios, unit={ukind})...", flush=True)
        rec = measure_stream(
            folios,
            unit_kind=ukind,
            name=key,
            sweeps=sweeps,
            n_perm_mi=n_perm_mi,
            n_perm_folio=n_perm_folio,
            seed=seed,
        )
        streams_out[key] = rec
        m_w25 = rec["modes"]["local_W25"]
        m_fc = rec["modes"]["folio_comp"]
        print(
            f"  {key}: W25 keep={m_w25['keep_rate']:.4f} D1={m_w25['D1_seed']:+.4f} "
            f"morph={m_w25['morphs_per_type']:.4f} cos={m_w25['adj_folio_cos']:.4f} | "
            f"FC keep={m_fc['keep_rate']:.4f} D1={m_fc['D1_seed']:+.4f} "
            f"mi_z={m_fc['mi_adj_z']:+.2f} ({rec['runtime_sec']:.1f}s)",
            flush=True,
        )

    predictions = evaluate_predictions(streams_out)
    return {
        "hypothesis": "h49_seed_skeleton_extraction",
        "modes": list(MODES),
        "stream_order": list(STREAM_ORDER),
        "n_stream": N_STREAM,
        "w_local": W_LOCAL,
        "seed": int(seed),
        "n_perm_mi": int(n_perm_mi),
        "n_perm_folio": int(n_perm_folio),
        "bayes_sweeps": int(sweeps),
        "streams": streams_out,
        "predictions": predictions,
        "numpy": np.__version__,
        "python": platform.python_version(),
        "runtime_sec": float(time.perf_counter() - t0),
    }
