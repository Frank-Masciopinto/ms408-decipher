"""h51: do diagram/plant/nymph labels match the de-padded seed stems of their folio or quire? (PREREG.md).

Implements:
  - Data extraction from ZL3b-n.txt via h09_lib.parse() and h09_lib.label_table():
    * All label words w with len(h13_lib.SEG(w)) >= 2 on folios with >= 20 paragraph tokens (P loci),
      plus the primary longest-word-per-locus view from h09_lib.label_table().
    * The herbal-pharmaceutical same-plant folio pairs from h09_lib.same_plant_pairs() (and the
      extended 16-pair set including h17 marginal/extra pairs).
  - Three paragraph representations per folio f:
    1. full_para: all paragraph tokens on folio f.
    2. seed_W25: paragraph tokens on folio f remaining after stripping any token within unit edit
       distance <= 1 of an earlier token in the last 25 tokens on folio f.
    3. header_tokens: first line (line == 1 or first P line on folio) and paragraph-initial line
       tokens on folio f (raw, d/s/p/t/k/f onset-stripped, and their union).
  - Three hit functions between label word w_L and paragraph token set P(f_P):
    1. exact_hit: w_L in P(f_P).
    2. edit1_hit: exists w in P(f_P) with unit Levenshtein distance <= 1.
    3. stem_hit: after stripping optional leading o-/q-/d-/s- (when >= 2 collapsed EVA units),
       stem_3(w_L) in {stem_3(w) : w in P(f_P)}.
  - Test 1 (own_folio): own-folio label <-> seed enrichment vs 2,000 within-quire permutations
    (seed 51) and length-matched random-word baseline on the same folio, with Holm adjustment
    across the 3 hit types.
  - Test 2 (same_plant_seeds): de-padded herbal <-> pharma same-plant pairs across all herbal
    folios and within-hand herbal folios vs 2,000 random partner permutations (seed 51).
  - Test 3 (chain_size): label-linked seeds vs length-matched unlinked seeds same-folio one-edit
    progeny size vs 2,000 within-folio permutations (seed 51).
  - Predictions L1, L2, L3.
"""
from __future__ import annotations

import os
import platform
import re
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
from rapidfuzz.distance import Levenshtein

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _rel in (
    "src",
    "hypotheses/h09_image_context_cribs",
    "hypotheses/h13_top_word_context",
):
    _p = str(ROOT / _rel)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import h09_lib as H9  # noqa: E402
import h13_lib as H13  # noqa: E402

SEED = 51
N_PERM = 2000
MIN_PARA_TOKENS = 20
MIN_LABEL_UNITS = 2
SEED_WINDOW = 25

HEADER_ONSETS = ("d", "s", "p", "t", "k", "f")
STEM_PREFIXES = ("o", "q", "d", "s")
HIT_TYPES = ("exact_hit", "edit1_hit", "stem_hit")
REP_NAMES = (
    "seed_W25",
    "full_para",
    "header_tokens_raw",
    "header_tokens_stripped",
    "header_tokens",
)

LOC_RE = re.compile(r"^<(f\d+[rv]\d*)\.(\d+),([@+&*=\-~])([A-Z])(\w)>\s*(.*)$")
EXTRA_PAIRS_CSV = ROOT / "hypotheses" / "h17_herbal_label_cribs" / "data" / "pharma_herbal_pairs_extra.csv"


def eva_units(word: str) -> tuple[str, ...]:
    """Return collapsed EVA units u(w) = tuple(h13_lib.SEG(w))."""
    return tuple(H13.SEG(word))


def unit_lev(ua: tuple[str, ...], ub: tuple[str, ...]) -> int:
    """Unit Levenshtein distance between two collapsed EVA unit tuples."""
    return int(Levenshtein.distance(ua, ub))


def is_edit1_or_exact(ua: tuple[str, ...], ub: tuple[str, ...]) -> bool:
    """True iff unit Levenshtein distance <= 1."""
    if abs(len(ua) - len(ub)) > 1:
        return False
    if ua == ub:
        return True
    return int(Levenshtein.distance(ua, ub)) <= 1


def stem3(word: str) -> tuple[str, ...]:
    """Strip optional leading o-/q-/d-/s- (when >= 2 EVA units) and take first 3 core units."""
    units = list(H13.SEG(word))
    if len(units) >= 2 and units[0] in STEM_PREFIXES:
        units = units[1:]
    return tuple(units[:3])


def strip_header_onset(word: str) -> str:
    """Strip leading d/s/p/t/k/f onset when remainder has >= 2 collapsed EVA units (h16/h50)."""
    units = list(H13.SEG(word))
    if len(units) >= 3 and units[0] in HEADER_ONSETS:
        return "".join(units[1:])
    return word


def exact_hit(w_label: str, para_words: list[str] | set[str]) -> bool:
    """1. exact_hit: w_L in P(f_P)."""
    return w_label in para_words


def edit1_hit(w_label: str, para_words: list[str] | set[str]) -> bool:
    """2. edit1_hit: exists w in P(f_P) with unit Levenshtein distance <= 1."""
    u_l = eva_units(w_label)
    for w in para_words:
        if is_edit1_or_exact(u_l, eva_units(w)):
            return True
    return False


def stem_hit(w_label: str, para_words: list[str] | set[str]) -> bool:
    """3. stem_hit: stem_3(w_L) in {stem_3(w) : w in P(f_P)}."""
    s_l = stem3(w_label)
    if not s_l:
        return False
    for w in para_words:
        if stem3(w) == s_l:
            return True
    return False


def extract_seed_w25(tokens: list[str], window: int = SEED_WINDOW) -> list[str]:
    """h49 de-padded seeds: strip any token within unit edit distance <= 1 of an earlier token in last 25 tokens."""
    units = [eva_units(w) for w in tokens]
    kept: list[str] = []
    for t, (w, ut) in enumerate(zip(tokens, units)):
        lo = max(0, t - window)
        duplicated = False
        for s in range(lo, t):
            if is_edit1_or_exact(ut, units[s]):
                duplicated = True
                break
        if not duplicated:
            kept.append(w)
    return kept


def parse_paragraph_lines(path: Path = H9.TR) -> dict[str, list[dict]]:
    """Parse paragraph (P) lines from ZL3b-n.txt with line number and paragraph-initial flag."""
    by_folio: dict[str, list[dict]] = defaultdict(list)
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = LOC_RE.match(ln)
        if not m:
            continue
        f, n_str, plc, g, sub, txt = m.groups()
        if g != "P":
            continue
        para_init = txt.lstrip().startswith("<%>") or plc == "@"
        ws = H9.words(txt)
        if ws:
            by_folio[f].append(
                {
                    "folio": f,
                    "line": int(n_str),
                    "placement": plc,
                    "sub": sub,
                    "para_initial": bool(para_init),
                    "words": ws,
                }
            )
    return dict(by_folio)


def build_folio_representations(
    loci: pd.DataFrame | None = None,
    min_para_tokens: int = MIN_PARA_TOKENS,
    path: Path = H9.TR,
) -> dict[str, dict[str, list[str]]]:
    """Build full_para, seed_W25, and header_tokens (raw, onset-stripped, union) for folios with >= 20 P tokens."""
    if loci is None:
        loci = H9.parse(path)
    p_lines = parse_paragraph_lines(path)
    p_loci = loci[loci.gtype == "P"]
    reps: dict[str, dict[str, list[str]]] = {}

    for folio, grp in p_loci.groupby("folio", sort=True):
        full_para = [w for ws in grp.words for w in ws]
        if len(full_para) < min_para_tokens:
            continue
        seed_w25 = extract_seed_w25(full_para, window=SEED_WINDOW)
        lines = p_lines.get(str(folio), [])
        hdr_raw: list[str] = []
        for idx, line_rec in enumerate(lines):
            if line_rec["line"] == 1 or idx == 0 or line_rec["para_initial"]:
                hdr_raw.extend(line_rec["words"])
        hdr_stripped = [strip_header_onset(w) for w in hdr_raw]
        hdr_union = list(dict.fromkeys(hdr_raw + hdr_stripped))
        reps[str(folio)] = {
            "full_para": full_para,
            "seed_W25": seed_w25,
            "header_tokens_raw": hdr_raw,
            "header_tokens_stripped": hdr_stripped,
            "header_tokens": hdr_union,
        }
    return reps


def extract_label_records(
    loci: pd.DataFrame,
    lt: pd.DataFrame,
    valid_folios: set[str],
    min_units: int = MIN_LABEL_UNITS,
    all_words_in_locus: bool = True,
) -> list[dict]:
    """Extract label words w with len(SEG(w)) >= 2 on folios with paragraph text."""
    records: list[dict] = []
    for r in lt.itertuples():
        folio = str(r.folio)
        if folio not in valid_folios:
            continue
        candidate_words = list(r.words) if all_words_in_locus else [str(r.w)]
        for w in candidate_words:
            u = eva_units(w)
            if len(u) >= min_units:
                records.append(
                    {
                        "folio": folio,
                        "line": int(r.n),
                        "sub": str(r.sub),
                        "obj": str(r.obj),
                        "quire": int(r.quire),
                        "section": str(r.section),
                        "w": str(w),
                        "units": u,
                        "unit_len": len(u),
                        "stem3": stem3(w),
                    }
                )
    return records


def resolve_pharma_folios(pharma_id: str, quires_df: pd.DataFrame) -> list[str]:
    """Resolve a pharma folio prefix (e.g. f89v -> f89v1, f89v2) to pharmaceutical pages in quires.csv."""
    clean = re.sub(r"\[.*", "", pharma_id)
    pages = list(quires_df.index)
    resolved = [clean] if clean in quires_df.index else sorted(p for p in pages if re.fullmatch(clean + r"\d", p))
    return [p for p in resolved if quires_df.loc[p, "section"] == "pharmaceutical"]


def load_same_plant_pairs(
    loci: pd.DataFrame,
    quires_df: pd.DataFrame,
    valid_herbal_folios: set[str],
    include_extra: bool = True,
    path: Path = H9.TR,
) -> list[dict]:
    """Load herbal-pharmaceutical same-plant pairs from h09_lib.same_plant_pairs() (and optional h17 extra pairs)."""
    raw_pairs: list[tuple[str, str, str, bool, str]] = [
        (h, t, src, bool(unc), "zl3b") for h, t, src, unc in H9.same_plant_pairs(path)
    ]
    if include_extra and EXTRA_PAIRS_CSV.exists():
        extra_df = pd.read_csv(EXTRA_PAIRS_CSV)
        for r in extra_df.itertuples():
            raw_pairs.append((str(r.herbal), str(r.pharma), str(r.source), bool(r.uncertain), "h17_extra"))

    out: list[dict] = []
    for herbal, pharma, source, uncertain, origin in raw_pairs:
        if herbal not in valid_herbal_folios:
            continue
        pharma_pages = resolve_pharma_folios(pharma, quires_df)
        if not pharma_pages:
            continue
        pharma_loci = loci[loci.folio.isin(pharma_pages) & (loci.gtype == "L")]
        labels = [w for r in pharma_loci.itertuples() for w in r.words if len(eva_units(w)) >= MIN_LABEL_UNITS]
        if not labels:
            continue
        out.append(
            {
                "herbal": herbal,
                "pharma": pharma,
                "pharma_pages": pharma_pages,
                "source": source,
                "uncertain": bool(uncertain),
                "origin": origin,
                "labels": labels,
                "n_labels": len(labels),
            }
        )
    return out


def _precompute_folio_sets(
    folios: list[str],
    reps: dict[str, dict[str, list[str]]],
    rep_name: str,
) -> tuple[list[set[str]], list[set[tuple[str, ...]]], list[set[tuple[str, ...]]]]:
    exact_sets: list[set[str]] = []
    unit_sets: list[set[tuple[str, ...]]] = []
    stem_sets: list[set[tuple[str, ...]]] = []
    for f in folios:
        ws = reps[f][rep_name]
        exact_sets.append(set(ws))
        unit_sets.append({eva_units(w) for w in ws})
        stem_sets.append({stem3(w) for w in ws if stem3(w)})
    return exact_sets, unit_sets, stem_sets


def _build_hit_matrices(
    words: list[str],
    folios: list[str],
    reps: dict[str, dict[str, list[str]]],
    rep_name: str,
) -> dict[str, np.ndarray]:
    """Build (n_words x n_folios) binary hit matrices for exact_hit, edit1_hit, stem_hit."""
    exact_sets, unit_sets, stem_sets = _precompute_folio_sets(folios, reps, rep_name)
    n_w = len(words)
    n_f = len(folios)
    m_exact = np.zeros((n_w, n_f), dtype=np.float64)
    m_edit1 = np.zeros((n_w, n_f), dtype=np.float64)
    m_stem = np.zeros((n_w, n_f), dtype=np.float64)

    unique_words = sorted(set(words))
    u_map = {w: eva_units(w) for w in unique_words}
    s_map = {w: stem3(w) for w in unique_words}
    w_row_exact: dict[str, np.ndarray] = {}
    w_row_edit1: dict[str, np.ndarray] = {}
    w_row_stem: dict[str, np.ndarray] = {}

    for w in unique_words:
        uw = u_map[w]
        sw = s_map[w]
        r_ex = np.zeros(n_f, dtype=np.float64)
        r_ed = np.zeros(n_f, dtype=np.float64)
        r_st = np.zeros(n_f, dtype=np.float64)
        for j in range(n_f):
            if w in exact_sets[j]:
                r_ex[j] = 1.0
            if any(is_edit1_or_exact(uw, up) for up in unit_sets[j]):
                r_ed[j] = 1.0
            if sw and sw in stem_sets[j]:
                r_st[j] = 1.0
        w_row_exact[w] = r_ex
        w_row_edit1[w] = r_ed
        w_row_stem[w] = r_st

    for i, w in enumerate(words):
        m_exact[i] = w_row_exact[w]
        m_edit1[i] = w_row_edit1[w]
        m_stem[i] = w_row_stem[w]

    return {
        "exact_hit": m_exact,
        "edit1_hit": m_edit1,
        "stem_hit": m_stem,
    }


def run_test1_own_folio(
    label_records: list[dict],
    reps: dict[str, dict[str, list[str]]],
    n_perm: int = N_PERM,
    seed: int = SEED,
) -> dict:
    """Test 1: Own-folio label <-> seed enrichment vs within-quire permutations and length-matched baseline."""
    words = [r["w"] for r in label_records]
    folios_arr = np.asarray([r["folio"] for r in label_records])
    quires_arr = np.asarray([int(r["quire"]) for r in label_records], dtype=int)
    lengths_arr = np.asarray([int(r["unit_len"]) for r in label_records], dtype=int)

    u_folios = sorted(set(folios_arr.tolist()))
    folio_to_idx = {f: i for i, f in enumerate(u_folios)}
    label_folio_idx = np.asarray([folio_to_idx[f] for f in folios_arr], dtype=int)
    u_quires = np.asarray(
        [next(int(r["quire"]) for r in label_records if r["folio"] == f) for f in u_folios],
        dtype=int,
    )

    # Precompute permutation arrays with seed 51:
    # 1) Label-level within-quire permutation (as in h09_lib.test_label_in_text: perm_within(Lw.quire.values))
    rng_label = np.random.default_rng(seed)
    perm_label_quire = H9.perm_within(quires_arr, rng_label, n_perm)

    # 2) Folio-level within-quire permutation (shuffling whole folios within quire)
    rng_folio = np.random.default_rng(seed)
    perm_folio_quire = H9.perm_within(u_quires, rng_folio, n_perm)

    # 3) Length-matched within-quire label-word sampling on the same folio
    grp_quire_len = np.asarray([f"{q}|{l}" for q, l in zip(quires_arr, lengths_arr)])
    rng_len = np.random.default_rng(seed)
    perm_quire_len = H9.perm_within(grp_quire_len, rng_len, n_perm)

    # 4) Length-matched random word types from manuscript vocabulary evaluated on the same folio
    all_ms_types = sorted({w for f_rep in reps.values() for w in f_rep["full_para"]} | set(words))
    by_len_ms: dict[int, list[str]] = defaultdict(list)
    for w in all_ms_types:
        by_len_ms[len(eva_units(w))].append(w)

    rng_rand_words = np.random.default_rng(seed)
    sampled_rand_words: list[list[str]] = []
    pool_words_set: set[str] = set(words)
    for L in lengths_arr:
        pool = by_len_ms.get(int(L)) or all_ms_types
        picks = [pool[int(k)] for k in rng_rand_words.integers(0, len(pool), size=n_perm)]
        sampled_rand_words.append(picks)
        pool_words_set.update(picks)

    all_eval_words = sorted(pool_words_set)
    eval_w_to_idx = {w: i for i, w in enumerate(all_eval_words)}
    obs_w_idx = np.asarray([eval_w_to_idx[w] for w in words], dtype=int)
    rand_w_idx = np.asarray(
        [[eval_w_to_idx[sampled_rand_words[col][row]] for col in range(len(words))] for row in range(n_perm)],
        dtype=int,
    )

    rep_results: dict[str, dict] = {}
    idx_range = np.arange(len(label_records))

    for rep_name in REP_NAMES:
        mats_all = _build_hit_matrices(all_eval_words, u_folios, reps, rep_name)
        hit_stats: dict[str, dict] = {}
        raw_p_label_quire: list[float] = []
        raw_p_folio_quire: list[float] = []
        raw_p_quire_len: list[float] = []
        raw_p_rand_word: list[float] = []

        for htype in HIT_TYPES:
            M_full = mats_all[htype]
            M = M_full[obs_w_idx]  # (n_labels x n_u_folios)
            obs_vec = M[idx_range, label_folio_idx]
            obs_rate = float(obs_vec.mean())
            obs_hits = int(obs_vec.sum())

            null_lq = np.asarray([M[idx_range, label_folio_idx[p]].mean() for p in perm_label_quire], dtype=np.float64)
            p_lq = float((1 + int((null_lq >= obs_rate).sum())) / (n_perm + 1))

            null_fq = np.asarray([M[idx_range, p[label_folio_idx]].mean() for p in perm_folio_quire], dtype=np.float64)
            p_fq = float((1 + int((null_fq >= obs_rate).sum())) / (n_perm + 1))

            null_ql = np.asarray([M[p, label_folio_idx].mean() for p in perm_quire_len], dtype=np.float64)
            p_ql = float((1 + int((null_ql >= obs_rate).sum())) / (n_perm + 1))

            null_rw = M_full[rand_w_idx, label_folio_idx[None, :]].mean(axis=1)
            p_rw = float((1 + int((null_rw >= obs_rate).sum())) / (n_perm + 1))

            raw_p_label_quire.append(p_lq)
            raw_p_folio_quire.append(p_fq)
            raw_p_quire_len.append(p_ql)
            raw_p_rand_word.append(p_rw)

            hit_stats[htype] = {
                "obs_hits": obs_hits,
                "n_labels": int(len(label_records)),
                "obs_rate": obs_rate,
                "within_quire_null_mean": float(null_lq.mean()),
                "within_quire_null_sd": float(null_lq.std(ddof=1)),
                "within_quire_ratio": float(obs_rate / null_lq.mean()) if null_lq.mean() > 0 else 0.0,
                "within_quire_z": float((obs_rate - null_lq.mean()) / (null_lq.std(ddof=1) + 1e-12)),
                "p_within_quire": p_lq,
                "folio_quire_null_mean": float(null_fq.mean()),
                "folio_quire_null_sd": float(null_fq.std(ddof=1)),
                "p_folio_quire": p_fq,
                "same_folio_quire_len_null_mean": float(null_ql.mean()),
                "same_folio_quire_len_null_sd": float(null_ql.std(ddof=1)),
                "p_same_folio_quire_len": p_ql,
                "same_folio_rand_word_null_mean": float(null_rw.mean()),
                "same_folio_rand_word_null_sd": float(null_rw.std(ddof=1)),
                "p_same_folio_rand_word": p_rw,
            }

        holm_lq = H9.holm(raw_p_label_quire)
        holm_fq = H9.holm(raw_p_folio_quire)
        holm_ql = H9.holm(raw_p_quire_len)
        holm_rw = H9.holm(raw_p_rand_word)

        for i, htype in enumerate(HIT_TYPES):
            hit_stats[htype]["p_holm_within_quire"] = float(holm_lq[i])
            hit_stats[htype]["p_holm_folio_quire"] = float(holm_fq[i])
            hit_stats[htype]["p_holm_same_folio_quire_len"] = float(holm_ql[i])
            hit_stats[htype]["p_holm_same_folio_rand_word"] = float(holm_rw[i])

        rep_results[rep_name] = hit_stats

    # Per-object breakdown on seed_W25
    mats_seed = _build_hit_matrices(words, u_folios, reps, "seed_W25")
    by_obj: dict[str, dict] = {}
    objs = sorted({r["obj"] for r in label_records})
    for obj in objs:
        mask = np.asarray([r["obj"] == obj for r in label_records], dtype=bool)
        m_idx = np.where(mask)[0]
        by_obj[obj] = {
            "n_labels": int(len(m_idx)),
            "n_folios": int(len({folios_arr[i] for i in m_idx})),
            "exact_hit_rate": float(mats_seed["exact_hit"][m_idx, label_folio_idx[m_idx]].mean()),
            "edit1_hit_rate": float(mats_seed["edit1_hit"][m_idx, label_folio_idx[m_idx]].mean()),
            "stem_hit_rate": float(mats_seed["stem_hit"][m_idx, label_folio_idx[m_idx]].mean()),
        }

    return {
        "n_labels": int(len(label_records)),
        "n_folios": int(len(u_folios)),
        "n_quires": int(len(set(u_quires.tolist()))),
        "folios": u_folios,
        "representations": rep_results,
        "by_object_seed_W25": by_obj,
    }


def _score_pair_set_test2(
    pairs: list[dict],
    herbal_folios: list[str],
    quires_df: pd.DataFrame,
    reps: dict[str, dict[str, list[str]]],
    n_perm: int = N_PERM,
    seed: int = SEED,
) -> dict:
    """Evaluate Test 2 on a list of (herbal, pharma) pairs across representations, hit modes, and pools."""
    all_pharma_words = sorted({w for p in pairs for w in p["labels"]})
    w_to_idx = {w: i for i, w in enumerate(all_pharma_words)}
    herb_to_idx = {f: j for j, f in enumerate(herbal_folios)}
    hands = [str(quires_df.loc[f, "lfd_hand"]) for f in herbal_folios]

    rep_out: dict[str, dict] = {}
    for rep_name in ("seed_W25", "full_para", "header_tokens"):
        mats = _build_hit_matrices(all_pharma_words, herbal_folios, reps, rep_name)
        mats["edit1_or_stem"] = np.maximum(mats["edit1_hit"], mats["stem_hit"])

        mode_out: dict[str, dict] = {}
        for mode in ("exact_hit", "edit1_hit", "stem_hit", "edit1_or_stem"):
            M = mats[mode]
            # Pair x herbal_folio fraction of pharma labels hitting
            S = np.zeros((len(pairs), len(herbal_folios)), dtype=np.float64)
            for i, p in enumerate(pairs):
                l_idx = np.asarray([w_to_idx[w] for w in p["labels"]], dtype=int)
                S[i] = M[l_idx].mean(axis=0)

            scopes_out: dict[str, dict] = {}
            for scope in ("all_herbal", "within_hand"):
                pair_rows: list[dict] = []
                pools: list[tuple[int, np.ndarray, np.ndarray]] = []
                for i, p in enumerate(pairs):
                    h_folio = p["herbal"]
                    h_idx = herb_to_idx[h_folio]
                    obs_frac = float(S[i, h_idx])
                    if scope == "all_herbal":
                        pool_idx = np.arange(len(herbal_folios), dtype=int)
                    else:
                        h_hand = str(quires_df.loc[h_folio, "lfd_hand"])
                        pool_idx = np.asarray(
                            [j for j, hd in enumerate(hands) if hd == h_hand],
                            dtype=int,
                        )
                    pool_vals = S[i, pool_idx]
                    rank_pct = float((pool_vals < obs_frac).mean() + 0.5 * (pool_vals == obs_frac).mean())
                    pools.append((i, pool_idx, pool_vals))
                    pair_rows.append(
                        {
                            "herbal": h_folio,
                            "pharma": p["pharma"],
                            "pharma_pages": p["pharma_pages"],
                            "source": p["source"],
                            "uncertain": p["uncertain"],
                            "origin": p["origin"],
                            "n_labels": p["n_labels"],
                            "obs_hit_frac": obs_frac,
                            "pool_mean_hit_frac": float(pool_vals.mean()),
                            "pool_size": int(len(pool_idx)),
                            "rank_pct": rank_pct,
                        }
                    )

                mean_rank_pct = float(np.mean([r["rank_pct"] for r in pair_rows]))
                mean_hit_frac = float(np.mean([r["obs_hit_frac"] for r in pair_rows]))
                rng = np.random.default_rng(seed)
                null_rank_pcts = np.empty(n_perm, dtype=np.float64)
                null_hit_fracs = np.empty(n_perm, dtype=np.float64)
                for k in range(n_perm):
                    rp_sum = 0.0
                    hf_sum = 0.0
                    for i, pool_idx, pool_vals in pools:
                        pick_j = pool_idx[int(rng.integers(0, len(pool_idx)))]
                        pick_val = S[i, pick_j]
                        hf_sum += float(pick_val)
                        rp_sum += float((pool_vals < pick_val).mean() + 0.5 * (pool_vals == pick_val).mean())
                    null_rank_pcts[k] = rp_sum / len(pools)
                    null_hit_fracs[k] = hf_sum / len(pools)

                p_rank = float((1 + int((null_rank_pcts >= mean_rank_pct).sum())) / (n_perm + 1))
                p_frac = float((1 + int((null_hit_fracs >= mean_hit_frac).sum())) / (n_perm + 1))
                scopes_out[scope] = {
                    "n_pairs": int(len(pair_rows)),
                    "mean_hit_frac": mean_hit_frac,
                    "null_hit_frac_mean": float(null_hit_fracs.mean()),
                    "null_hit_frac_sd": float(null_hit_fracs.std(ddof=1)),
                    "p_hit_frac": p_frac,
                    "mean_rank_pct": mean_rank_pct,
                    "null_rank_pct_mean": float(null_rank_pcts.mean()),
                    "null_rank_pct_sd": float(null_rank_pcts.std(ddof=1)),
                    "p_rank_pct": p_rank,
                    "pairs": pair_rows,
                }
            mode_out[mode] = scopes_out
        rep_out[rep_name] = mode_out
    return rep_out


def run_test2_same_plant(
    loci: pd.DataFrame,
    quires_df: pd.DataFrame,
    reps: dict[str, dict[str, list[str]]],
    n_perm: int = N_PERM,
    seed: int = SEED,
) -> dict:
    """Test 2: De-padded herbal <-> pharmaceutical same-plant pairs."""
    herbal_folios = sorted(
        f for f in reps if f in quires_df.index and quires_df.loc[f, "section"] == "herbal"
    )
    pairs_16 = load_same_plant_pairs(
        loci, quires_df, set(herbal_folios), include_extra=True
    )
    pairs_zl3b = [p for p in pairs_16 if p["origin"] == "zl3b"]

    return {
        "n_herbal_folios": int(len(herbal_folios)),
        "pairs_16": _score_pair_set_test2(
            pairs_16, herbal_folios, quires_df, reps, n_perm=n_perm, seed=seed
        ),
        "pairs_zl3b_12": _score_pair_set_test2(
            pairs_zl3b, herbal_folios, quires_df, reps, n_perm=n_perm, seed=seed
        ),
    }


def run_test3_chain_size(
    label_records: list[dict],
    reps: dict[str, dict[str, list[str]]],
    n_perm: int = N_PERM,
    seed: int = SEED,
) -> dict:
    """Test 3: Label-seeded chain length (progeny size) on own folio vs length-matched unlinked seeds."""
    labs_by_folio: dict[str, list[dict]] = defaultdict(list)
    for r in label_records:
        labs_by_folio[r["folio"]].append(r)

    folios = sorted(labs_by_folio.keys())
    seed_rows: list[dict] = []

    for f in folios:
        f_labs = labs_by_folio[f]
        lab_units = [r["units"] for r in f_labs]
        lab_stems = {r["stem3"] for r in f_labs if r["stem3"]}
        body_words = reps[f]["full_para"]
        body_units = [eva_units(w) for w in body_words]
        seed_words = reps[f]["seed_W25"]

        for sw in seed_words:
            usw = eva_units(sw)
            ssw = stem3(sw)
            hit_ed = any(is_edit1_or_exact(usw, lu) for lu in lab_units)
            hit_st = bool(ssw and ssw in lab_stems)
            progeny = sum(1 for bu in body_units if is_edit1_or_exact(usw, bu))
            seed_rows.append(
                {
                    "folio": f,
                    "quire": int(f_labs[0]["quire"]),
                    "seed_word": sw,
                    "unit_len": int(len(usw)),
                    "edit1_linked": bool(hit_ed),
                    "stem_linked": bool(hit_st),
                    "linked": bool(hit_ed or hit_st),
                    "progeny_size": int(progeny),
                }
            )

    f_arr = np.asarray([r["folio"] for r in seed_rows])
    l_arr = np.asarray([r["unit_len"] for r in seed_rows], dtype=int)
    p_arr = np.asarray([r["progeny_size"] for r in seed_rows], dtype=np.float64)
    grp_folio_len = np.asarray([f"{f}|{l}" for f, l in zip(f_arr, l_arr)])

    rng_fl = np.random.default_rng(seed)
    perm_folio_len = H9.perm_within(grp_folio_len, rng_fl, n_perm)

    rng_f = np.random.default_rng(seed)
    perm_folio_only = H9.perm_within(f_arr, rng_f, n_perm)

    link_Results: dict[str, dict] = {}
    for link_key, col_name in (
        ("edit1_or_stem", "linked"),
        ("edit1_only", "edit1_linked"),
        ("stem_only", "stem_linked"),
    ):
        k_arr = np.asarray([r[col_name] for r in seed_rows], dtype=bool)
        n_linked = int(k_arr.sum())
        n_unlinked = int((~k_arr).sum())
        mean_linked = float(p_arr[k_arr].mean()) if n_linked > 0 else 0.0
        mean_unlinked = float(p_arr[~k_arr].mean()) if n_unlinked > 0 else 0.0
        obs_diff = float(mean_linked - mean_unlinked)

        null_fl = np.empty(n_perm, dtype=np.float64)
        for i, perm in enumerate(perm_folio_len):
            kp = k_arr[perm]
            null_fl[i] = float(p_arr[kp].mean() - p_arr[~kp].mean())
        p_fl = float((1 + int((null_fl >= obs_diff).sum())) / (n_perm + 1))

        null_f = np.empty(n_perm, dtype=np.float64)
        for i, perm in enumerate(perm_folio_only):
            kp = k_arr[perm]
            null_f[i] = float(p_arr[kp].mean() - p_arr[~kp].mean())
        p_f = float((1 + int((null_f >= obs_diff).sum())) / (n_perm + 1))

        link_Results[link_key] = {
            "n_seeds": int(len(seed_rows)),
            "n_linked": n_linked,
            "n_unlinked": n_unlinked,
            "linked_fraction": float(n_linked / len(seed_rows)),
            "mean_progeny_linked": mean_linked,
            "mean_progeny_unlinked": mean_unlinked,
            "obs_diff": obs_diff,
            "within_folio_len_null_mean": float(null_fl.mean()),
            "within_folio_len_null_sd": float(null_fl.std(ddof=1)),
            "within_folio_len_excess": float(obs_diff - null_fl.mean()),
            "within_folio_len_z": float((obs_diff - null_fl.mean()) / (null_fl.std(ddof=1) + 1e-12)),
            "p_within_folio_len": p_fl,
            "within_folio_null_mean": float(null_f.mean()),
            "within_folio_null_sd": float(null_f.std(ddof=1)),
            "within_folio_excess": float(obs_diff - null_f.mean()),
            "within_folio_z": float((obs_diff - null_f.mean()) / (null_f.std(ddof=1) + 1e-12)),
            "p_within_folio": p_f,
        }

    # Diagnostic: does swapping label sets across folios within the same quire produce the same
    # progeny difference (degree-selection bias of central EVA stems), or is it folio-specific?
    u_quires = np.asarray([labs_by_folio[f][0]["quire"] for f in folios], dtype=int)
    rng_diag = np.random.default_rng(seed)
    perm_diag = H9.perm_within(u_quires, rng_diag, n_perm)

    # Precompute for each folio f and each candidate label-folio lf whether each seed on f is linked
    seed_u_by_f = {f: [eva_units(w) for w in reps[f]["seed_W25"]] for f in folios}
    seed_s_by_f = {f: [stem3(w) for w in reps[f]["seed_W25"]] for f in folios}
    prog_by_f = {
        f: np.asarray([r["progeny_size"] for r in seed_rows if r["folio"] == f], dtype=np.float64)
        for f in folios
    }
    lab_u_by_f = {f: [r["units"] for r in labs_by_folio[f]] for f in folios}
    lab_s_by_f = {f: {r["stem3"] for r in labs_by_folio[f] if r["stem3"]} for f in folios}

    link_mat_by_pair: dict[tuple[int, int], np.ndarray] = {}
    for i_f, f in enumerate(folios):
        su = seed_u_by_f[f]
        ss = seed_s_by_f[f]
        for j_f, lf in enumerate(folios):
            if u_quires[i_f] != u_quires[j_f]:
                continue
            lu = lab_u_by_f[lf]
            ls = lab_s_by_f[lf]
            mask = np.asarray(
                [
                    any(is_edit1_or_exact(u_s, u_l) for u_l in lu) or (bool(s_s) and s_s in ls)
                    for u_s, s_s in zip(su, ss)
                ],
                dtype=bool,
            )
            link_mat_by_pair[(i_f, j_f)] = mask

    quire_swap_diffs = np.empty(n_perm, dtype=np.float64)
    for k, perm in enumerate(perm_diag):
        l_sum = 0.0
        l_cnt = 0
        u_sum = 0.0
        u_cnt = 0
        for i_f in range(len(folios)):
            j_f = int(perm[i_f])
            mask = link_mat_by_pair[(i_f, j_f)]
            pr = prog_by_f[folios[i_f]]
            l_sum += float(pr[mask].sum())
            l_cnt += int(mask.sum())
            u_sum += float(pr[~mask].sum())
            u_cnt += int((~mask).sum())
        quire_swap_diffs[k] = (l_sum / l_cnt if l_cnt else 0.0) - (u_sum / u_cnt if u_cnt else 0.0)

    obs_diff_main = link_Results["edit1_or_stem"]["obs_diff"]
    p_quire_swap = float((1 + int((quire_swap_diffs >= obs_diff_main).sum())) / (n_perm + 1))

    # Per-length breakdown for edit1_or_stem
    by_len_rows: list[dict] = []
    for L in sorted(set(l_arr.tolist())):
        m_l = l_arr == L
        k_l = np.asarray([r["linked"] for r in seed_rows], dtype=bool) & m_l
        u_l = (~np.asarray([r["linked"] for r in seed_rows], dtype=bool)) & m_l
        if int(k_l.sum()) > 0 and int(u_l.sum()) > 0:
            by_len_rows.append(
                {
                    "unit_len": int(L),
                    "n_linked": int(k_l.sum()),
                    "n_unlinked": int(u_l.sum()),
                    "mean_progeny_linked": float(p_arr[k_l].mean()),
                    "mean_progeny_unlinked": float(p_arr[u_l].mean()),
                    "diff": float(p_arr[k_l].mean() - p_arr[u_l].mean()),
                }
            )

    return {
        "n_folios": int(len(folios)),
        "n_seeds_total": int(len(seed_rows)),
        "link_modes": link_Results,
        "by_unit_length": by_len_rows,
        "quire_label_swap_diagnostic": {
            "obs_diff": obs_diff_main,
            "quire_swap_null_mean": float(quire_swap_diffs.mean()),
            "quire_swap_null_sd": float(quire_swap_diffs.std(ddof=1)),
            "p_vs_quire_label_swap": p_quire_swap,
        },
    }


def score_predictions(test1: dict, test2: dict, test3: dict) -> dict:
    """Evaluate pre-registered predictions L1, L2, L3 from PREREG.md."""
    t1_seed = test1["representations"]["seed_W25"]
    l1_edit1_p_holm = float(t1_seed["edit1_hit"]["p_holm_within_quire"])
    l1_stem_p_holm = float(t1_seed["stem_hit"]["p_holm_within_quire"])
    l1_min_p_holm = min(l1_edit1_p_holm, l1_stem_p_holm)
    l1_pass = bool(l1_min_p_holm < 0.05)

    # L2: In Test 2, matching pharmaceutical labels to the de-padded seed_W25 of their paired herbal folio
    # via edit1_hit or stem_hit achieves a mean rank percentile > 0.65 with p < 0.05.
    t2_16_seed = test2["pairs_16"]["seed_W25"]
    t2_12_seed = test2["pairs_zl3b_12"]["seed_W25"]
    l2_candidates = {}
    for pset_name, d_seed in (("pairs_16", t2_16_seed), ("pairs_zl3b_12", t2_12_seed)):
        for mode in ("edit1_hit", "stem_hit", "edit1_or_stem"):
            for scope in ("all_herbal", "within_hand"):
                rec = d_seed[mode][scope]
                l2_candidates[f"{pset_name}|{mode}|{scope}"] = {
                    "mean_rank_pct": float(rec["mean_rank_pct"]),
                    "p_rank_pct": float(rec["p_rank_pct"]),
                    "pass": bool(rec["mean_rank_pct"] > 0.65 and rec["p_rank_pct"] < 0.05),
                }
    primary_t2 = t2_16_seed["edit1_or_stem"]["all_herbal"]
    l2_pass = bool(
        any(
            t2_16_seed[m]["all_herbal"]["mean_rank_pct"] > 0.65
            and t2_16_seed[m]["all_herbal"]["p_rank_pct"] < 0.05
            for m in ("edit1_hit", "stem_hit", "edit1_or_stem")
        )
    )

    # L3: In Test 3, label-linked seeds on a folio have significantly larger same-folio one-edit progeny
    # than length-matched unlinked seeds (p < 0.05).
    t3_main = test3["link_modes"]["edit1_or_stem"]
    l3_p_len = float(t3_main["p_within_folio_len"])
    l3_p_folio = float(t3_main["p_within_folio"])
    l3_obs_diff = float(t3_main["obs_diff"])
    l3_pass = bool(l3_obs_diff > 0.0 and l3_p_len < 0.05)

    return {
        "L1": l1_pass,
        "L1_edit1_p_holm": l1_edit1_p_holm,
        "L1_stem_p_holm": l1_stem_p_holm,
        "L1_min_p_holm": l1_min_p_holm,
        "L2": l2_pass,
        "L2_primary_mean_rank_pct": float(primary_t2["mean_rank_pct"]),
        "L2_primary_p": float(primary_t2["p_rank_pct"]),
        "L2_variants": l2_candidates,
        "L3": l3_pass,
        "L3_obs_diff": l3_obs_diff,
        "L3_p_within_folio_len": l3_p_len,
        "L3_p_within_folio": l3_p_folio,
    }


def measure_all(n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """Run all three pre-registered tests (own_folio, same_plant_seeds, chain_size) and score L1-L3."""
    t0 = time.perf_counter()
    loci = H9.parse(H9.TR)
    lt = H9.label_table(loci)
    quires_df = pd.read_csv(ROOT / "data" / "quires.csv", dtype=str, keep_default_na=False).set_index("page")

    reps = build_folio_representations(loci=loci, min_para_tokens=MIN_PARA_TOKENS, path=H9.TR)
    valid_folios = set(reps.keys())

    # All label words w with >= 2 collapsed EVA units in label_table on folios with >= 20 P tokens
    labels_all_words = extract_label_records(
        loci, lt, valid_folios, min_units=MIN_LABEL_UNITS, all_words_in_locus=True
    )
    # Also compute primary longest-word-per-locus view from h09_lib.label_table()
    labels_locus_primary = extract_label_records(
        loci, lt, valid_folios, min_units=MIN_LABEL_UNITS, all_words_in_locus=False
    )

    test1_all = run_test1_own_folio(labels_all_words, reps, n_perm=n_perm, seed=seed)
    test1_primary_locus = run_test1_own_folio(labels_locus_primary, reps, n_perm=n_perm, seed=seed)

    test2 = run_test2_same_plant(loci, quires_df, reps, n_perm=n_perm, seed=seed)

    test3_all = run_test3_chain_size(labels_all_words, reps, n_perm=n_perm, seed=seed)
    test3_primary_locus = run_test3_chain_size(labels_locus_primary, reps, n_perm=n_perm, seed=seed)

    predictions = score_predictions(test1_all, test2, test3_all)
    predictions_locus_primary = score_predictions(test1_primary_locus, test2, test3_primary_locus)

    para_summary = {
        "n_folios_ge20_para": int(len(reps)),
        "mean_full_para_tokens": float(np.mean([len(r["full_para"]) for r in reps.values()])),
        "mean_seed_W25_tokens": float(np.mean([len(r["seed_W25"]) for r in reps.values()])),
        "mean_seed_retention": float(
            np.mean([len(r["seed_W25"]) / len(r["full_para"]) for r in reps.values()])
        ),
        "mean_header_raw_tokens": float(np.mean([len(r["header_tokens_raw"]) for r in reps.values()])),
        "mean_header_union_tokens": float(np.mean([len(r["header_tokens"]) for r in reps.values()])),
    }

    return {
        "hypothesis": "h51_label_to_seed_link",
        "seed": int(seed),
        "n_perm": int(n_perm),
        "min_para_tokens": int(MIN_PARA_TOKENS),
        "min_label_units": int(MIN_LABEL_UNITS),
        "seed_window": int(SEED_WINDOW),
        "paragraph_summary": para_summary,
        "test1_own_folio": test1_all,
        "test1_own_folio_locus_longest": test1_primary_locus,
        "test2_same_plant_seeds": test2,
        "test3_chain_size": test3_all,
        "test3_chain_size_locus_longest": test3_primary_locus,
        "predictions": predictions,
        "predictions_locus_longest": predictions_locus_primary,
        "numpy": np.__version__,
        "python": platform.python_version(),
        "runtime_sec": float(time.perf_counter() - t0),
    }
