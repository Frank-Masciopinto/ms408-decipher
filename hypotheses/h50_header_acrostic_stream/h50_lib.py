"""h50: do paragraph-initial or line-initial words form a hidden header or acrostic stream? (PREREG.md).

Extracts four vertical/header sequences per stream in reading order:
  1. para_words: first word of every paragraph-initial line (para_first == True).
  2. line_words_raw: first word (pos == 0) of every paragraph line.
  3. line_words_stripped: pos == 0 word after stripping a leading d/s/p/t/k/f onset
     when the remainder has >= 2 EVA units (or characters for controls).
  4. line_first_unit: first collapsed EVA unit (h13_lib.SEG(w)[0], or first character
     for controls) of every line (pos == 0).

Measures:
  M1: 5-fold cross-validated Kneser-Ney bigram gain D1_vert = bits(KN1) - bits(KN2),
      lag-1 class MI (top-30 types + OTHER), and adjacent repetition z-score vs
      200 within-folio line-order permutations (or within-quire paragraph permutations
      for para_words; seed 50).
  M2: Vertical glyph-acrostic redundancy R_acro = H1 - h2 within folios vs 200
      within-folio line-order permutations (seed 50) and vs horizontal within-word
      unit redundancy (H1 - h2), plus Sukhotin vowel/consonant alternation excess.
  M3: Mean unit-3gram cosine similarity (header_body_cos) and one-edit hit rate
      between onset-stripped Line-1 words and the rest of the same folio vs 200
      within-quire Line-1 swaps across folios (seed 50).

No semantic or translation claims are made.
"""
from __future__ import annotations

import json
import math
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
    "hypotheses/h16_line_initial_prefix",
    "hypotheses/h19_heldout_likelihood",
    "hypotheses/h20_generators_vs_italian",
    "hypotheses/h30_line_structure",
    "hypotheses/h42_near_repeat_decay",
    "hypotheses/h43_page_edge",
    "hypotheses/h47_page_line_generator",
):
    _p = str(ROOT / _rel)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import h09_lib  # noqa: E402
import h13_lib  # noqa: E402
import h16_lib  # noqa: E402
import h19_lib  # noqa: E402
import h30_lib  # noqa: E402
import h42_lib  # noqa: E402
import h43_lib  # noqa: E402
import h47_lib  # noqa: E402
import run_h19  # noqa: E402
from fetch_italian import load_italian  # noqa: E402
from msdecipher.controls_text import load_tokens  # noqa: E402
from msdecipher.stats import block_entropy, conditional_entropy, sukhotin  # noqa: E402

HANDS = ("1A", "2B", "3B")
MS_KEYS = ("MS_1A", "MS_2B", "MS_3B")
PLC_KEYS = ("page_line_copier_1A", "page_line_copier_2B", "page_line_copier_3B")
CONTROL_KEYS = ("it_boccaccio", "cucina", "la_pliny_herbal")
STREAM_ORDER = MS_KEYS + PLC_KEYS + CONTROL_KEYS

TRANSCRIPTION = "ZL3b-n.txt"
ONSETS = ("d", "s", "p", "t", "k", "f")
N_STREAM = 10500
N_PERM = 200
SEED = 50
N_FOLDS = 5
TOP_K_CLASS = 30
D1_MIN_BITS = 0.05
ACRO_HORIZ_MIN_RATIO = 0.50

H47_STREAMS_PATH = ROOT / "hypotheses" / "h47_page_line_generator" / "results" / "streams.json"


def bind_zl3b() -> None:
    """Bind h09_lib.TR and h13_lib.H9.TR to ZL3b-n.txt and verify comma splitting."""
    tr_path = ROOT / "data" / "transcriptions" / TRANSCRIPTION
    if not tr_path.is_file():
        raise FileNotFoundError(tr_path)
    h09_lib.TR = tr_path
    h13_lib.H9.TR = tr_path
    toks = [tok for tok, _ok in h13_lib.tokens_raw("aa,bb cc")[0]]
    if toks != ["aa", "bb", "cc"]:
        raise RuntimeError(f"comma is not a word space: {toks}")


def to_units(word: str, unit_kind: str = "eva") -> tuple[str, ...]:
    """Segment word into collapsed EVA units ('eva') or character tuple ('char')."""
    if unit_kind == "eva":
        return tuple(h13_lib.SEG(word))
    if unit_kind == "char":
        return tuple(word)
    raise ValueError(f"unknown unit_kind {unit_kind!r}")


def strip_onset_word(word: str, unit_kind: str = "eva", onsets: tuple[str, ...] = ONSETS) -> str:
    """Strip a leading d/s/p/t/k/f onset when the remainder has >= 2 units (h16 onset stripping)."""
    ons = h16_lib.onset(word, onsets)
    if ons is None:
        return word
    rem = word[len(ons) :]
    if not rem:
        return word
    if len(to_units(rem, unit_kind)) >= 2:
        return rem
    return word


def line_trigrams(units_seq: list[tuple[str, ...]]) -> Counter:
    """Count padded unit 3-grams (^ + units + $) across a list of segmented words."""
    counts: Counter = Counter()
    for u in units_seq:
        padded = ("^",) + u + ("$",)
        for i in range(len(padded) - 2):
            counts[padded[i : i + 3]] += 1
    return counts


def load_ms_records(hand: str) -> list[dict]:
    """Load MS line records for `hand` via h30_lib.load_ms(hand) on ZL3b-n.txt."""
    bind_zl3b()
    recs = h30_lib.load_ms(hand)
    out: list[dict] = []
    for r in recs:
        ws = [str(w) for w in r["words"] if w]
        if not ws:
            continue
        out.append(
            {
                "words": ws,
                "page": str(r["page"]),
                "quire": str(r["quire"]),
                "stratum": str(r["stratum"]),
                "para_first": bool(r["para_first"]),
            }
        )
    return out


def load_plc_records(hand: str) -> list[dict]:
    """Load h47 page_line_copier stream for `hand` on its real layout template."""
    bind_zl3b()
    name = f"page_line_copier_{hand}"
    if H47_STREAMS_PATH.is_file():
        payload = json.loads(H47_STREAMS_PATH.read_text(encoding="utf-8"))
        gen_lines = payload.get("generated_lines", {}).get(name)
        if gen_lines is not None:
            tmpl = h47_lib.load_template(hand, N_STREAM)
            if len(gen_lines) == len(tmpl):
                out: list[dict] = []
                for rec, words in zip(tmpl, gen_lines):
                    ws = [str(w) for w in words if w]
                    if not ws:
                        continue
                    out.append(
                        {
                            "words": ws,
                            "page": str(rec["page"]),
                            "quire": str(rec["quire"]),
                            "stratum": str(rec["stratum"]),
                            "para_first": bool(rec["para_first"]),
                        }
                    )
                return out
    _lines, recs = h47_lib.generate_page_line_copier(hand, seed=h47_lib.SEED)
    return [
        {
            "words": [str(w) for w in r["words"] if w],
            "page": str(r["page"]),
            "quire": str(r["quire"]),
            "stratum": str(r["stratum"]),
            "para_first": bool(r["para_first"]),
        }
        for r in recs
        if r["words"]
    ]


def _layout_tokens_on_2b_template(tokens: list[str], stream_name: str) -> list[dict]:
    """Lay a flat token list onto the Hand 2B folio/line/paragraph template."""
    bind_zl3b()
    tmpl = h47_lib.load_template("2B", N_STREAM)
    out: list[dict] = []
    ptr = 0
    n_tok = len(tokens)
    for rec in tmpl:
        line_len = len(rec["words"])
        if line_len <= 0:
            continue
        ws = [str(tokens[(ptr + k) % n_tok]) for k in range(line_len)]
        ptr += line_len
        out.append(
            {
                "words": ws,
                "page": str(rec["page"]),
                "quire": str(rec["quire"]),
                "stratum": f"{stream_name}|{rec['quire']}",
                "para_first": bool(rec["para_first"]),
            }
        )
    return out


def load_control_records(name: str) -> list[dict]:
    """Load prose/verse control records (it_boccaccio, dante or cucina, la_pliny_herbal)."""
    if name == "it_boccaccio":
        tokens = list(load_italian("it_boccaccio", N_STREAM))
        return _layout_tokens_on_2b_template(tokens, "it_boccaccio")
    if name == "la_pliny_herbal":
        tokens = list(load_tokens("la_pliny_herbal", N_STREAM))
        return _layout_tokens_on_2b_template(tokens, "la_pliny_herbal")
    if name in ("dante", "cucina"):
        dante_path = h30_lib.CTRL / h30_lib.CONTROLS["dante"][0]
        if name == "dante" and dante_path.is_file():
            fname = h30_lib.CONTROLS["dante"][0]
        else:
            fname = h30_lib.CONTROLS["cucina"][0]
        raw_recs = h30_lib.load_control(fname, ntok=N_STREAM, skip=0.25, block=25)
        pages_order = list(dict.fromkeys(str(r["page"]) for r in raw_recs))
        page_to_idx = {p: idx for idx, p in enumerate(pages_order)}
        out: list[dict] = []
        for r in raw_recs:
            ws = [str(w) for w in r["words"] if w]
            if not ws:
                continue
            page = str(r["page"])
            q_idx = page_to_idx[page] // 4
            quire = f"q{q_idx}"
            out.append(
                {
                    "words": ws,
                    "page": page,
                    "quire": quire,
                    "stratum": f"{name}|{quire}",
                    "para_first": bool(r["para_first"]),
                }
            )
        return out
    raise ValueError(f"unknown control stream {name!r}")


def load_all_streams() -> dict[str, tuple[list[dict], str]]:
    """Return mapping stream_name -> (records, unit_kind) for all streams in STREAM_ORDER."""
    out: dict[str, tuple[list[dict], str]] = {}
    for hand in HANDS:
        out[f"MS_{hand}"] = (load_ms_records(hand), "eva")
    for hand in HANDS:
        out[f"page_line_copier_{hand}"] = (load_plc_records(hand), "eva")
    for ctrl in CONTROL_KEYS:
        out[ctrl] = (load_control_records(ctrl), "char")
    return out


def extract_vertical_sequences(records: list[dict], unit_kind: str = "eva") -> dict:
    """Extract the 4 preregistered vertical/header sequences and folio/quire groupings."""
    recs = [r for r in records if r.get("words")]
    para_words: list[str] = []
    line_words_raw: list[str] = []
    line_words_stripped: list[str] = []
    line_first_unit: list[str] = []

    folio_raw_map: dict[str, list[str]] = defaultdict(list)
    folio_strip_map: dict[str, list[str]] = defaultdict(list)
    folio_unit_map: dict[str, list[str]] = defaultdict(list)
    folio_lines_map: dict[str, list[list[str]]] = defaultdict(list)
    folio_quire: dict[str, str] = {}
    folio_order: list[str] = []

    quire_para_map: dict[str, list[str]] = defaultdict(list)
    quire_order: list[str] = []

    for r in recs:
        ws = r["words"]
        w0 = ws[0]
        w0_strip = strip_onset_word(w0, unit_kind)
        u0 = to_units(w0, unit_kind)[0]
        page = str(r["page"])
        quire = str(r["quire"])

        if page not in folio_quire:
            folio_quire[page] = quire
            folio_order.append(page)
        if quire not in quire_para_map and quire not in quire_order:
            quire_order.append(quire)

        line_words_raw.append(w0)
        line_words_stripped.append(w0_strip)
        line_first_unit.append(u0)

        folio_raw_map[page].append(w0)
        folio_strip_map[page].append(w0_strip)
        folio_unit_map[page].append(u0)
        folio_lines_map[page].append(list(ws))

        if r.get("para_first"):
            para_words.append(w0)
            quire_para_map[quire].append(w0)

    folios_raw = [(f, folio_quire[f], folio_raw_map[f]) for f in folio_order]
    folios_stripped = [(f, folio_quire[f], folio_strip_map[f]) for f in folio_order]
    folios_first_unit = [(f, folio_quire[f], tuple(folio_unit_map[f])) for f in folio_order]
    folios_full = [{"folio": f, "quire": folio_quire[f], "lines": folio_lines_map[f]} for f in folio_order]
    quires_para = [(q, quire_para_map[q]) for q in quire_order if quire_para_map[q]]

    return {
        "para_words": para_words,
        "line_words_raw": line_words_raw,
        "line_words_stripped": line_words_stripped,
        "line_first_unit": line_first_unit,
        "folios_raw": folios_raw,
        "folios_stripped": folios_stripped,
        "folios_first_unit": folios_first_unit,
        "folios_full": folios_full,
        "quires_para": quires_para,
    }


def _build_cv_pages(seqs_with_ids: list[tuple[str, list[str]]], n_folds: int = N_FOLDS) -> tuple[list[dict], list[tuple[list[int], list[int]]]]:
    """Build page dicts and 5-fold CV splits; subdivide if fewer than n_folds sequences exist."""
    items: list[tuple[str, list[str]]] = [(sid, list(ws)) for sid, ws in seqs_with_ids if ws]
    if len(items) < n_folds:
        flat_items: list[tuple[str, list[str]]] = []
        flat_all = [w for _, ws in items for w in ws]
        n_tot = len(flat_all)
        for k in range(n_folds):
            a = (k * n_tot) // n_folds
            b = ((k + 1) * n_tot) // n_folds
            chunk = flat_all[a:b]
            if chunk:
                flat_items.append((f"chunk_{k}", chunk))
        items = flat_items
    pages = [{"id": sid, "words": ws} for sid, ws in items]
    folds = run_h19.group_folds(pages, "id", n_folds)
    return pages, folds


def compute_kn_d1_5fold(seqs_with_ids: list[tuple[str, list[str]]], n_folds: int = N_FOLDS) -> dict:
    """Compute 5-fold cross-validated KN1 and KN2 bits/word and D1 = bits(KN1) - bits(KN2)."""
    pages, folds = _build_cv_pages(seqs_with_ids, n_folds=n_folds)
    if len(folds) < 2:
        return {"kn1_bits": 0.0, "kn2_bits": 0.0, "D1_vert": 0.0, "n_tokens": 0, "n_folds": len(folds)}

    kn1_sum = 0.0
    kn2_sum = 0.0
    n_tok = 0
    for tr_idx, te_idx in folds:
        tr_seqs = [pages[i]["words"] for i in tr_idx if pages[i]["words"]]
        te_seqs = [pages[i]["words"] for i in te_idx if pages[i]["words"]]
        tr_words = [w for s in tr_seqs for w in s]
        if not tr_words or not te_seqs:
            continue
        char_lm = h19_lib.CharLM(4).fit(tr_words)
        kn1 = h19_lib.KN(1, char_lm).fit(tr_seqs)
        kn2 = h19_lib.KN(2, char_lm).fit(tr_seqs)
        for ws in te_seqs:
            for i, w in enumerate(ws):
                hist = ws[:i]
                kn1_sum += -kn1.logp(w, hist)
                kn2_sum += -kn2.logp(w, hist)
                n_tok += 1

    if n_tok == 0:
        return {"kn1_bits": 0.0, "kn2_bits": 0.0, "D1_vert": 0.0, "n_tokens": 0, "n_folds": len(folds)}

    kn1_bits = float(kn1_sum / n_tok)
    kn2_bits = float(kn2_sum / n_tok)
    return {
        "kn1_bits": kn1_bits,
        "kn2_bits": kn2_bits,
        "D1_vert": float(kn1_bits - kn2_bits),
        "n_tokens": int(n_tok),
        "n_folds": int(len(folds)),
    }


def _score_vertical_word_sequence(
    seqs_with_ids: list[tuple[str, list[str]]],
    perm_scope: str,
    n_perm: int = N_PERM,
    seed: int = SEED,
) -> dict:
    """Compute M1 metrics (D1_vert, lag1_class_mi, adj_repeat_z) on a grouped vertical word sequence."""
    seqs = [list(ws) for _, ws in seqs_with_ids if ws]
    all_words = [w for s in seqs for w in s]
    n_words = len(all_words)
    n_types = len(set(all_words))

    kn_res = compute_kn_d1_5fold(seqs_with_ids, n_folds=N_FOLDS)
    d1_vert = float(kn_res["D1_vert"])

    top_types = {w for w, _ in Counter(all_words).most_common(TOP_K_CLASS)}
    class_seqs = [[w if w in top_types else "OTHER" for w in s] for s in seqs]

    obs_class_pairs = [(cs[i], cs[i + 1]) for cs in class_seqs for i in range(len(cs) - 1)]
    obs_word_pairs = [(s[i], s[i + 1]) for s in seqs for i in range(len(s) - 1)]
    n_pairs = len(obs_word_pairs)
    obs_mi = float(h30_lib.mi(obs_class_pairs)) if n_pairs > 0 else 0.0
    obs_rep = float(sum(1 for a, b in obs_word_pairs if a == b) / n_pairs) if n_pairs > 0 else 0.0

    rng = np.random.default_rng(seed)
    null_mis: list[float] = []
    null_reps: list[float] = []
    for _ in range(n_perm):
        p_class_pairs: list[tuple[str, str]] = []
        rep_hits = 0
        for s, cs in zip(seqs, class_seqs):
            m = len(s)
            if m < 2:
                continue
            perm = rng.permutation(m)
            for k in range(m - 1):
                ia = int(perm[k])
                ib = int(perm[k + 1])
                p_class_pairs.append((cs[ia], cs[ib]))
                if s[ia] == s[ib]:
                    rep_hits += 1
        null_mis.append(float(h30_lib.mi(p_class_pairs)) if n_pairs > 0 else 0.0)
        null_reps.append(float(rep_hits / n_pairs) if n_pairs > 0 else 0.0)

    mi_arr = np.asarray(null_mis, dtype=np.float64)
    mi_mean = float(mi_arr.mean()) if len(mi_arr) else 0.0
    mi_sd = float(mi_arr.std(ddof=1)) if len(mi_arr) >= 2 else 0.0
    mi_p95 = float(np.percentile(mi_arr, 95, method="linear")) if len(mi_arr) else 0.0
    mi_z = float((obs_mi - mi_mean) / (mi_sd + 1e-12))
    mi_above_p95 = bool(obs_mi > mi_p95)

    rep_arr = np.asarray(null_reps, dtype=np.float64)
    rep_mean = float(rep_arr.mean()) if len(rep_arr) else 0.0
    rep_sd = float(rep_arr.std(ddof=1)) if len(rep_arr) >= 2 else 0.0
    rep_z = float((obs_rep - rep_mean) / (rep_sd + 1e-12))

    d1_positive = bool(d1_vert > D1_MIN_BITS)
    pass_a1 = bool(d1_positive and mi_above_p95)

    return {
        "perm_scope": perm_scope,
        "n_groups": len(seqs),
        "n_tokens": n_words,
        "n_types": n_types,
        "n_lag1_pairs": n_pairs,
        "kn1_bits": kn_res["kn1_bits"],
        "kn2_bits": kn_res["kn2_bits"],
        "D1_vert": d1_vert,
        "d1_gt_005": d1_positive,
        "lag1_class_mi": obs_mi,
        "lag1_class_mi_null_mean": mi_mean,
        "lag1_class_mi_null_sd": mi_sd,
        "lag1_class_mi_null_p95": mi_p95,
        "lag1_class_mi_excess": float(obs_mi - mi_mean),
        "lag1_class_mi_z": mi_z,
        "lag1_class_mi_above_p95": mi_above_p95,
        "adj_repeat_rate": obs_rep,
        "adj_repeat_null_mean": rep_mean,
        "adj_repeat_null_sd": rep_sd,
        "adj_repeat_z": rep_z,
        "pass_a1": pass_a1,
    }


def measure_m1(vert: dict, n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """Measure M1 across line_words_raw, line_words_stripped, and para_words."""
    raw_items = [(f, ws) for f, _q, ws in vert["folios_raw"]]
    strip_items = [(f, ws) for f, _q, ws in vert["folios_stripped"]]
    para_items = [(q, ws) for q, ws in vert["quires_para"]]

    res_raw = _score_vertical_word_sequence(raw_items, "within_folio_line_order", n_perm=n_perm, seed=seed)
    res_strip = _score_vertical_word_sequence(strip_items, "within_folio_line_order", n_perm=n_perm, seed=seed)
    res_para = _score_vertical_word_sequence(para_items, "within_quire_para_order", n_perm=n_perm, seed=seed)

    hand_pass = bool(res_strip["pass_a1"] or res_para["pass_a1"])
    return {
        "line_words_raw": res_raw,
        "line_words_stripped": res_strip,
        "para_words": res_para,
        "pass_a1": hand_pass,
    }


def _cv_switch_stats(
    seqs: list[tuple[str, ...]],
    vowel_set: set[str],
    n_perm: int = N_PERM,
    seed: int = SEED,
) -> dict:
    """Compute Sukhotin C/V alternation rate and excess over within-sequence permutations."""
    cv_seqs = [tuple(1 if u in vowel_set else 0 for u in s) for s in seqs if len(s) >= 2]
    tot_pairs = sum(len(s) - 1 for s in cv_seqs)
    if tot_pairs == 0:
        return {
            "switch_rate": 0.0,
            "null_mean": 0.0,
            "null_sd": 0.0,
            "null_p95": 0.0,
            "excess": 0.0,
            "z": 0.0,
            "n_pairs": 0,
        }
    obs_sw = sum(sum(1 for i in range(len(s) - 1) if s[i] != s[i + 1]) for s in cv_seqs)
    obs_rate = float(obs_sw / tot_pairs)

    rng = np.random.default_rng(seed)
    null_rates: list[float] = []
    for _ in range(n_perm):
        sw = 0
        for s in cv_seqs:
            perm = rng.permutation(len(s))
            for i in range(len(s) - 1):
                if s[int(perm[i])] != s[int(perm[i + 1])]:
                    sw += 1
        null_rates.append(float(sw / tot_pairs))

    arr = np.asarray(null_rates, dtype=np.float64)
    mean = float(arr.mean())
    sd = float(arr.std(ddof=1)) if len(arr) >= 2 else 0.0
    p95 = float(np.percentile(arr, 95, method="linear"))
    excess = float(obs_rate - mean)
    z = float(excess / (sd + 1e-12))
    return {
        "switch_rate": obs_rate,
        "null_mean": mean,
        "null_sd": sd,
        "null_p95": p95,
        "excess": excess,
        "z": z,
        "n_pairs": int(tot_pairs),
    }


def measure_m2(
    records: list[dict],
    vert: dict,
    unit_kind: str = "eva",
    n_perm: int = N_PERM,
    seed: int = SEED,
) -> dict:
    """Measure M2: vertical line_first_unit acrostic redundancy R_acro and Sukhotin alternation."""
    folio_unit_seqs = [u_seq for _f, _q, u_seq in vert["folios_first_unit"] if len(u_seq) >= 1]
    h1_acro = float(block_entropy(folio_unit_seqs, 1))
    h2_acro = float(conditional_entropy(folio_unit_seqs, 2))
    r_acro = float(h1_acro - h2_acro)

    rng = np.random.default_rng(seed)
    null_r_acro: list[float] = []
    for _ in range(n_perm):
        perm_seqs = [
            tuple(u_seq[int(i)] for i in rng.permutation(len(u_seq)))
            for u_seq in folio_unit_seqs
        ]
        h2_p = float(conditional_entropy(perm_seqs, 2))
        null_r_acro.append(float(h1_acro - h2_p))

    r_arr = np.asarray(null_r_acro, dtype=np.float64)
    r_null_mean = float(r_arr.mean()) if len(r_arr) else 0.0
    r_null_sd = float(r_arr.std(ddof=1)) if len(r_arr) >= 2 else 0.0
    r_null_p95 = float(np.percentile(r_arr, 95, method="linear")) if len(r_arr) else 0.0
    r_z = float((r_acro - r_null_mean) / (r_null_sd + 1e-12))
    r_above_p95 = bool(r_acro > r_null_p95)

    word_unit_seqs = [
        to_units(w, unit_kind)
        for r in records
        for w in r["words"]
        if len(to_units(w, unit_kind)) >= 1
    ]
    h1_horiz = float(block_entropy(word_unit_seqs, 1))
    h2_horiz = float(conditional_entropy(word_unit_seqs, 2))
    r_horiz = float(h1_horiz - h2_horiz)

    ratio_to_horiz = float(r_acro / r_horiz) if r_horiz > 0.0 else 0.0
    reaches_50pct_horiz = bool(r_acro >= ACRO_HORIZ_MIN_RATIO * r_horiz)
    pass_a2 = bool(r_above_p95 and reaches_50pct_horiz)

    vowels, _rows = sukhotin(word_unit_seqs)
    vowel_set = set(vowels)
    vert_cv = _cv_switch_stats(folio_unit_seqs, vowel_set, n_perm=n_perm, seed=seed)
    horiz_cv = _cv_switch_stats(word_unit_seqs, vowel_set, n_perm=min(50, n_perm), seed=seed)

    return {
        "n_folios": len(folio_unit_seqs),
        "n_vertical_units": sum(len(s) for s in folio_unit_seqs),
        "n_vertical_bigrams": sum(max(len(s) - 1, 0) for s in folio_unit_seqs),
        "H1_acro": h1_acro,
        "h2_acro": h2_acro,
        "R_acro": r_acro,
        "H2_acrostic_drop": r_acro,
        "R_acro_null_mean": r_null_mean,
        "R_acro_null_sd": r_null_sd,
        "R_acro_null_p95": r_null_p95,
        "R_acro_excess": float(r_acro - r_null_mean),
        "R_acro_z": r_z,
        "R_acro_above_p95": r_above_p95,
        "H1_horiz": h1_horiz,
        "h2_horiz": h2_horiz,
        "R_horiz": r_horiz,
        "acro_to_horiz_ratio": ratio_to_horiz,
        "reaches_50pct_horiz": reaches_50pct_horiz,
        "sukhotin_vowels": [str(v) for v in vowels],
        "sukhotin_alt": vert_cv["excess"],
        "sukhotin_vert_cv": vert_cv,
        "sukhotin_horiz_cv": horiz_cv,
        "pass_a2": pass_a2,
    }


def _header_body_pair_matrices(
    headers_units: list[list[tuple[str, ...]]],
    bodies_units: list[list[tuple[str, ...]]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute K x K matrices of unit-3gram cosine, eligible pairs, and edit1 hits."""
    k = len(headers_units)
    cos_mat = np.zeros((k, k), dtype=np.float64)
    elig_mat = np.zeros((k, k), dtype=np.int64)
    hit_mat = np.zeros((k, k), dtype=np.int64)

    h_c3 = [line_trigrams(hu) for hu in headers_units]
    b_c3 = [line_trigrams(bu) for bu in bodies_units]

    vocab: dict[tuple[str, ...], int] = {}
    for seq in headers_units + bodies_units:
        for u in seq:
            if u not in vocab:
                vocab[u] = len(vocab)
    v_sz = len(vocab)
    ulist = list(vocab.keys())
    max_len = max((len(u) for u in ulist), default=0)

    h_len = np.zeros((k, max_len + 2), dtype=np.float64)
    b_len = np.zeros((k, max_len + 2), dtype=np.float64)
    h_w = np.zeros((k, v_sz), dtype=np.float64)
    b_w = np.zeros((k, v_sz), dtype=np.float64)

    for i in range(k):
        for u in headers_units[i]:
            h_len[i, len(u)] += 1.0
            h_w[i, vocab[u]] += 1.0
        for u in bodies_units[i]:
            b_len[i, len(u)] += 1.0
            b_w[i, vocab[u]] += 1.0

    len_compat = np.zeros((max_len + 2, max_len + 2), dtype=np.float64)
    for l1 in range(max_len + 2):
        for l2 in range(max(0, l1 - 1), min(max_len + 2, l1 + 2)):
            len_compat[l1, l2] = 1.0
    elig_mat = np.rint((h_len @ len_compat) @ b_len.T).astype(np.int64)

    by_len: dict[int, list[tuple[int, tuple[str, ...]]]] = defaultdict(list)
    for idx, u in enumerate(ulist):
        by_len[len(u)].append((idx, u))
    a_edit = np.zeros((v_sz, v_sz), dtype=np.float64)
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
    hit_mat = np.rint((h_w @ a_edit) @ b_w.T).astype(np.int64)

    for a in range(k):
        ca = h_c3[a]
        for b in range(k):
            cb = b_c3[b]
            cos_mat[a, b] = float(h43_lib.cosine_counts(ca, cb)) if (ca and cb) else 0.0

    return cos_mat, elig_mat, hit_mat


def measure_m3(
    vert: dict,
    unit_kind: str = "eva",
    n_perm: int = N_PERM,
    seed: int = SEED,
) -> dict:
    """Measure M3: onset-stripped Line-1 header to same-folio body similarity vs within-quire Line-1 swaps."""
    folios = [f for f in vert["folios_full"] if len(f["lines"]) >= 2]
    by_quire: dict[str, list[dict]] = defaultdict(list)
    for f in folios:
        by_quire[str(f["quire"])].append(f)

    quire_mats: list[tuple[int, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
    n_folios_used = 0
    for _q, flist in by_quire.items():
        k = len(flist)
        if k == 0:
            continue
        headers_stripped: list[list[tuple[str, ...]]] = []
        headers_raw: list[list[tuple[str, ...]]] = []
        bodies: list[list[tuple[str, ...]]] = []
        for f in flist:
            l1 = f["lines"][0]
            body_words = [w for line in f["lines"][1:] for w in line]
            h_strip = [to_units(strip_onset_word(w, unit_kind), unit_kind) for w in l1]
            h_raw = [to_units(w, unit_kind) for w in l1]
            b_u = [to_units(w, unit_kind) for w in body_words]
            headers_stripped.append(h_strip)
            headers_raw.append(h_raw)
            bodies.append(b_u)

        cos_mat, elig_mat, hit_mat = _header_body_pair_matrices(headers_stripped, bodies)
        raw_cos_diag = np.array(
            [
                float(h43_lib.cosine_counts(line_trigrams(headers_raw[i]), line_trigrams(bodies[i])))
                for i in range(k)
            ],
            dtype=np.float64,
        )
        quire_mats.append((k, cos_mat, elig_mat, hit_mat, raw_cos_diag))
        n_folios_used += k

    if n_folios_used == 0:
        return {
            "n_folios": 0,
            "n_quires": 0,
            "header_body_cos": 0.0,
            "header_body_cos_raw": 0.0,
            "header_body_cos_null_mean": 0.0,
            "header_body_cos_null_sd": 0.0,
            "header_body_cos_null_p95": 0.0,
            "header_body_cos_excess": 0.0,
            "header_body_cos_z": 0.0,
            "header_body_cos_above_p95": False,
            "header_body_edit1": 0.0,
            "header_body_edit1_null_mean": 0.0,
            "header_body_edit1_null_sd": 0.0,
            "header_body_edit1_null_p95": 0.0,
            "header_body_edit1_excess": 0.0,
            "header_body_edit1_z": 0.0,
            "header_body_edit1_above_p95": False,
            "pass_a3": False,
        }

    obs_cos_sum = 0.0
    obs_raw_cos_sum = 0.0
    obs_elig = 0
    obs_hits = 0
    for k, cos_mat, elig_mat, hit_mat, raw_cos_diag in quire_mats:
        idx = np.arange(k)
        obs_cos_sum += float(cos_mat[idx, idx].sum())
        obs_raw_cos_sum += float(raw_cos_diag.sum())
        obs_elig += int(elig_mat[idx, idx].sum())
        obs_hits += int(hit_mat[idx, idx].sum())

    obs_cos = float(obs_cos_sum / n_folios_used)
    obs_raw_cos = float(obs_raw_cos_sum / n_folios_used)
    obs_edit1 = float(obs_hits / obs_elig) if obs_elig > 0 else 0.0

    rng = np.random.default_rng(seed)
    null_cos_list: list[float] = []
    null_edit1_list: list[float] = []
    for _ in range(n_perm):
        c_sum = 0.0
        el_sum = 0
        ht_sum = 0
        for k, cos_mat, elig_mat, hit_mat, _raw_diag in quire_mats:
            perm = rng.permutation(k)
            cols = np.arange(k)
            c_sum += float(cos_mat[perm, cols].sum())
            el_sum += int(elig_mat[perm, cols].sum())
            ht_sum += int(hit_mat[perm, cols].sum())
        null_cos_list.append(float(c_sum / n_folios_used))
        null_edit1_list.append(float(ht_sum / el_sum) if el_sum > 0 else 0.0)

    cos_arr = np.asarray(null_cos_list, dtype=np.float64)
    cos_mean = float(cos_arr.mean())
    cos_sd = float(cos_arr.std(ddof=1)) if len(cos_arr) >= 2 else 0.0
    cos_p95 = float(np.percentile(cos_arr, 95, method="linear"))
    cos_excess = float(obs_cos - cos_mean)
    cos_z = float(cos_excess / (cos_sd + 1e-12))
    cos_above_p95 = bool(obs_cos > cos_p95)

    ed_arr = np.asarray(null_edit1_list, dtype=np.float64)
    ed_mean = float(ed_arr.mean())
    ed_sd = float(ed_arr.std(ddof=1)) if len(ed_arr) >= 2 else 0.0
    ed_p95 = float(np.percentile(ed_arr, 95, method="linear"))
    ed_excess = float(obs_edit1 - ed_mean)
    ed_z = float(ed_excess / (ed_sd + 1e-12))
    ed_above_p95 = bool(obs_edit1 > ed_p95)

    return {
        "n_folios": int(n_folios_used),
        "n_quires": int(len(quire_mats)),
        "header_body_cos": obs_cos,
        "header_body_cos_raw": obs_raw_cos,
        "header_body_cos_null_mean": cos_mean,
        "header_body_cos_null_sd": cos_sd,
        "header_body_cos_null_p95": cos_p95,
        "header_body_cos_excess": cos_excess,
        "header_body_cos_z": cos_z,
        "header_body_cos_above_p95": cos_above_p95,
        "n_header_body_eligible": int(obs_elig),
        "n_header_body_edit1": int(obs_hits),
        "header_body_edit1": obs_edit1,
        "header_body_edit1_null_mean": ed_mean,
        "header_body_edit1_null_sd": ed_sd,
        "header_body_edit1_null_p95": ed_p95,
        "header_body_edit1_excess": ed_excess,
        "header_body_edit1_z": ed_z,
        "header_body_edit1_above_p95": ed_above_p95,
        "pass_a3": cos_above_p95,
    }


def measure_stream(
    records: list[dict],
    unit_kind: str = "eva",
    name: str = "",
    n_perm: int = N_PERM,
    seed: int = SEED,
) -> dict:
    """Extract the 4 vertical sequences and compute M1, M2, M3 for one stream."""
    t0 = time.perf_counter()
    vert = extract_vertical_sequences(records, unit_kind=unit_kind)
    m1 = measure_m1(vert, n_perm=n_perm, seed=seed)
    m2 = measure_m2(records, vert, unit_kind=unit_kind, n_perm=n_perm, seed=seed)
    m3 = measure_m3(vert, unit_kind=unit_kind, n_perm=n_perm, seed=seed)

    n_tokens = sum(len(r["words"]) for r in records)
    n_lines = len(vert["line_words_raw"])
    n_paras = len(vert["para_words"])
    n_folios = len(vert["folios_raw"])
    n_quires = len({str(r["quire"]) for r in records})

    n_stripped_changed = sum(
        1 for raw_w, str_w in zip(vert["line_words_raw"], vert["line_words_stripped"]) if raw_w != str_w
    )

    return {
        "name": name,
        "unit_kind": unit_kind,
        "n_tokens": int(n_tokens),
        "n_lines": int(n_lines),
        "n_paras": int(n_paras),
        "n_folios": int(n_folios),
        "n_quires": int(n_quires),
        "n_line_words_stripped_changed": int(n_stripped_changed),
        "share_line_words_stripped": float(n_stripped_changed / n_lines) if n_lines > 0 else 0.0,
        "M1": m1,
        "M2": m2,
        "M3": m3,
        "runtime_sec": float(time.perf_counter() - t0),
    }


def evaluate_predictions(streams: dict[str, dict]) -> dict:
    """Evaluate preregistered predictions A1, A2, A3 across MS hands 1A, 2B, 3B."""
    a1_hands: list[str] = []
    a2_hands: list[str] = []
    a3_hands: list[str] = []

    a1_by_hand: dict[str, dict] = {}
    a2_by_hand: dict[str, dict] = {}
    a3_by_hand: dict[str, dict] = {}

    for hand in HANDS:
        key = f"MS_{hand}"
        rec = streams[key]
        m1 = rec["M1"]
        m2 = rec["M2"]
        m3 = rec["M3"]

        lws = m1["line_words_stripped"]
        pw = m1["para_words"]
        h_a1 = bool(lws["pass_a1"] or pw["pass_a1"])
        if h_a1:
            a1_hands.append(hand)
        a1_by_hand[hand] = {
            "passed": h_a1,
            "line_words_stripped_D1": lws["D1_vert"],
            "line_words_stripped_mi_above_p95": lws["lag1_class_mi_above_p95"],
            "line_words_stripped_pass": lws["pass_a1"],
            "para_words_D1": pw["D1_vert"],
            "para_words_mi_above_p95": pw["lag1_class_mi_above_p95"],
            "para_words_pass": pw["pass_a1"],
        }

        h_a2 = bool(m2["pass_a2"])
        if h_a2:
            a2_hands.append(hand)
        a2_by_hand[hand] = {
            "passed": h_a2,
            "R_acro": m2["R_acro"],
            "R_acro_null_p95": m2["R_acro_null_p95"],
            "R_acro_above_p95": m2["R_acro_above_p95"],
            "R_horiz": m2["R_horiz"],
            "acro_to_horiz_ratio": m2["acro_to_horiz_ratio"],
            "reaches_50pct_horiz": m2["reaches_50pct_horiz"],
        }

        h_a3 = bool(m3["pass_a3"])
        if h_a3:
            a3_hands.append(hand)
        a3_by_hand[hand] = {
            "passed": h_a3,
            "header_body_cos": m3["header_body_cos"],
            "header_body_cos_null_p95": m3["header_body_cos_null_p95"],
            "header_body_cos_above_p95": m3["header_body_cos_above_p95"],
            "header_body_edit1": m3["header_body_edit1"],
            "header_body_edit1_null_p95": m3["header_body_edit1_null_p95"],
        }

    a1_pass = len(a1_hands) >= 2
    a2_pass = len(a2_hands) >= 2
    a3_pass = len(a3_hands) >= 2

    if a1_pass and a2_pass and a3_pass:
        verdict = "supported"
    elif a1_pass or a2_pass or a3_pass:
        verdict = "partially_supported"
    else:
        verdict = "refuted"

    return {
        "A1": a1_pass,
        "A1_passing_hands": a1_hands,
        "A1_by_hand": a1_by_hand,
        "A2": a2_pass,
        "A2_passing_hands": a2_hands,
        "A2_by_hand": a2_by_hand,
        "A3": a3_pass,
        "A3_passing_hands": a3_hands,
        "A3_by_hand": a3_by_hand,
        "verdict": verdict,
    }


def measure_all(n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """Load all MS, h47 synthetic, and control streams and compute M1, M2, M3 and A1-A3."""
    t0 = time.perf_counter()
    raw_streams = load_all_streams()
    streams: dict[str, dict] = {}

    for name in STREAM_ORDER:
        recs, unit_kind = raw_streams[name]
        print(f"h50 measuring {name} (lines={len(recs)}, unit={unit_kind})...", flush=True)
        res = measure_stream(recs, unit_kind=unit_kind, name=name, n_perm=n_perm, seed=seed)
        streams[name] = res
        m1_s = res["M1"]["line_words_stripped"]
        m1_p = res["M1"]["para_words"]
        m2 = res["M2"]
        m3 = res["M3"]
        print(
            f"  {name}: M1_strip(D1={m1_s['D1_vert']:.4f}, MI={m1_s['lag1_class_mi']:.4f}/p95={m1_s['lag1_class_mi_null_p95']:.4f}) "
            f"M1_para(D1={m1_p['D1_vert']:.4f}, MI={m1_p['lag1_class_mi']:.4f}/p95={m1_p['lag1_class_mi_null_p95']:.4f}) "
            f"M2(R_acro={m2['R_acro']:.4f}/p95={m2['R_acro_null_p95']:.4f}, ratio={m2['acro_to_horiz_ratio']:.3f}) "
            f"M3(cos={m3['header_body_cos']:.4f}/p95={m3['header_body_cos_null_p95']:.4f}, edit1={m3['header_body_edit1']:.4f})",
            flush=True,
        )

    preds = evaluate_predictions(streams)
    return {
        "hypothesis": "h50_header_acrostic_stream",
        "transcription": TRANSCRIPTION,
        "comma": "space",
        "hands": list(HANDS),
        "stream_order": list(STREAM_ORDER),
        "onsets_stripped": list(ONSETS),
        "n_stream": N_STREAM,
        "n_perm": int(n_perm),
        "seed": int(seed),
        "n_folds": N_FOLDS,
        "top_k_class": TOP_K_CLASS,
        "d1_min_bits": D1_MIN_BITS,
        "acro_horiz_min_ratio": ACRO_HORIZ_MIN_RATIO,
        "streams": streams,
        "predictions": preds,
        "numpy": np.__version__,
        "python": platform.python_version(),
        "runtime_sec": float(time.perf_counter() - t0),
    }
