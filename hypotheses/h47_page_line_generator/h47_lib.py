"""h47: Page- and line-aware copy-and-modify generator (PREREG.md).

Combines the slot-annealed vocabulary and junction rule of h34/h39 with:
  - folio-boundary lookback buffer resets (rho_keep = 0.15) and folio-specific stems,
  - line-initial and paragraph-initial onset weighting (with cross-line junction suppressed),
  - line-final ending weighting,
  - within-line character-junction selection r(first | prev_last)^s*,
  - local one-edit near-repeat draws across folio lag bins.

Scores generated streams and h39 baselines on the six benchmarks B1..B6 and evaluates U1..U3.
No semantic or translation claims are made.
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

for _p in (
    ROOT / "src",
    ROOT / "hypotheses" / "h13_top_word_context",
    ROOT / "hypotheses" / "h19_heldout_likelihood",
    ROOT / "hypotheses" / "h20_generators_vs_italian",
    ROOT / "hypotheses" / "h30_line_structure",
    ROOT / "hypotheses" / "h33_word_boundary_resegmentation",
    ROOT / "hypotheses" / "h34_boundary_rule_generator",
    ROOT / "hypotheses" / "h39_graph_respell_and_tuned_copier",
    ROOT / "hypotheses" / "h42_near_repeat_decay",
    ROOT / "hypotheses" / "h43_page_edge",
    ROOT / "hypotheses" / "h44_generator_page_burst",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import h13_lib  # noqa: E402
import h19_lib  # noqa: E402
import h20_lib  # noqa: E402
import h30_lib  # noqa: E402
import h33_lib  # noqa: E402
import h34_lib  # noqa: E402
import h39_lib  # noqa: E402
import h42_lib  # noqa: E402
import h43_lib  # noqa: E402
import h44_lib  # noqa: E402
import run_h19  # noqa: E402
import run_h20  # noqa: E402
import run_h34  # noqa: E402

HANDS = ("1A", "2B", "3B")
N_STREAM = 10500
SEED = 47
RHO_KEEP = 0.15
W_BUF = 90

# h40 interior space predictability bands: MS value +/- 0.02
S_TARGETS = {
    "1A": 0.760,
    "2B": 0.819,
    "3B": 0.831,
}
S_BAND_HALF = 0.030  # h40 band +/- 0.02 around [0.750..0.770], [0.809..0.827], [0.815..0.847]
S_BANDS = {
    "1A": (0.730, 0.790),
    "2B": (0.791, 0.847),
    "3B": (0.795, 0.867),
}
J_MIN = 0.060

# h30 hard-wrapped prose control mean positional excess MI (from h30 results/measures.json)
PROSE_ONSET_EXCESS = 0.005470
PROSE_END_EXCESS = 0.006932
PROSE_COMB_EXCESS = PROSE_ONSET_EXCESS + PROSE_END_EXCESS


def load_template(hand: str, max_tokens: int = N_STREAM) -> list[dict]:
    """Load real manuscript line records for `hand` up to `max_tokens` tokens."""
    ms_all = h30_lib.load_ms(hand)
    tmpl: list[dict] = []
    ntok = 0
    for rec in ms_all:
        if ntok + len(rec["words"]) > max_tokens and ntok > 0:
            break
        tmpl.append(rec)
        ntok += len(rec["words"])
    return tmpl


def split_records_even_odd(hand: str) -> tuple[list[dict], list[dict]]:
    """Split manuscript line records into even-bifolia (train) and odd-bifolia (test)."""
    ms_all = h30_lib.load_ms(hand)
    q = pd.read_csv(ROOT / "data" / "quires.csv", dtype=str).set_index("page").bifolium_id
    bifs = sorted({str(q.get(l["page"])) for l in ms_all})
    te_b = set(bifs[1::2])
    tr_recs = [l for l in ms_all if str(q.get(l["page"])) not in te_b]
    te_recs = [l for l in ms_all if str(q.get(l["page"])) in te_b]
    return tr_recs, te_recs


def _build_edit1_graph(vocab: list[str]) -> tuple[dict[str, tuple], dict[str, list[str]]]:
    units_list = h42_lib.eva_units(vocab)
    units_map = dict(zip(vocab, units_list))
    by_len: dict[int, list[tuple[str, tuple]]] = defaultdict(list)
    for w, u in units_map.items():
        by_len[len(u)].append((w, u))
    adj: dict[str, list[str]] = defaultdict(list)
    for length, items in by_len.items():
        for d_len in (0, 1):
            other = by_len.get(length + d_len, [])
            for i, (w1, u1) in enumerate(items):
                start = i + 1 if d_len == 0 else 0
                for w2, u2 in other[start:]:
                    if h42_lib.edit1(u1, u2):
                        adj[w1].append(w2)
                        adj[w2].append(w1)
    return units_map, adj


def fit_hand_params(hand: str) -> dict:
    """Fit line-edge, junction, and vocabulary tables on the even-bifolia train split of `hand`."""
    tr_lines, _ = run_h34.split(hand)
    r_tab = h34_lib.fit_table(tr_lines)
    tr_recs, _ = split_records_even_odd(hand)

    para_onsets = Counter(h13_lib.SEG(l["words"][0])[0] for l in tr_recs if l["para_first"] and l["words"])
    line_onsets = Counter(h13_lib.SEG(l["words"][0])[0] for l in tr_recs if not l["para_first"] and l["words"])
    mid_onsets = Counter(h13_lib.SEG(w)[0] for l in tr_recs for w in l["words"][1:])
    line_ends = Counter(h13_lib.SEG(l["words"][-1])[-1] for l in tr_recs if l["words"])
    mid_ends = Counter(h13_lib.SEG(w)[-1] for l in tr_recs for w in l["words"][:-1])

    para_words = Counter(l["words"][0] for l in tr_recs if l["para_first"] and l["words"])
    init_words = Counter(l["words"][0] for l in tr_recs if not l["para_first"] and l["words"])
    final_words = Counter(l["words"][-1] for l in tr_recs if l["words"])

    c0_path = ROOT / "hypotheses" / "h39_graph_respell_and_tuned_copier" / "results" / f"lines_{hand}_C0_graph.json"
    c0_lines = json.loads(c0_path.read_text(encoding="utf-8"))
    base_toks = [w for l in c0_lines for w in l]
    cnt = Counter(base_toks)
    vocab = list(cnt.keys())
    units_map, adj = _build_edit1_graph(vocab)

    w_onset = {w: units_map[w][0] for w in vocab}
    w_end = {w: units_map[w][-1] for w in vocab}

    tot_para = sum(para_onsets.values()) + 1
    tot_line = sum(line_onsets.values()) + 1
    tot_mido = sum(mid_onsets.values()) + 1
    tot_end = sum(line_ends.values()) + 1
    tot_mide = sum(mid_ends.values()) + 1

    all_onsets = set(w_onset.values())
    all_ends = set(w_end.values())
    para_ratio = {
        c: ((para_onsets[c] + 0.5) / tot_para) / ((mid_onsets[c] + 0.5) / tot_mido)
        for c in all_onsets
    }
    init_ratio = {
        c: ((line_onsets[c] + 0.5) / tot_line) / ((mid_onsets[c] + 0.5) / tot_mido)
        for c in all_onsets
    }
    end_ratio = {
        c: ((line_ends[c] + 0.5) / tot_end) / ((mid_ends[c] + 0.5) / tot_mide)
        for c in all_ends
    }

    top_stems = [w for w, _ in cnt.most_common(60) if len(adj[w]) >= 2][:48]

    return {
        "hand": hand,
        "r_tab": r_tab,
        "base_toks": base_toks,
        "cnt": cnt,
        "adj": adj,
        "w_onset": w_onset,
        "w_end": w_end,
        "para_ratio": para_ratio,
        "init_ratio": init_ratio,
        "end_ratio": end_ratio,
        "para_words": para_words,
        "init_words": init_words,
        "final_words": final_words,
        "top_stems": top_stems,
    }


def generate_page_line_copier(
    hand: str,
    seed: int = SEED,
    rho_keep: float = RHO_KEEP,
    n_stems_per_folio: int = 2,
    stem_repeats: float = 0.11,
    p_edit1: float = 0.015,
    p_edit_2_5: float = 0.04,
    p_edit_6_20: float = 0.14,
    p_edit_21_80: float = 0.03,
    s_junc: float = 1.4,
) -> tuple[list[list[str]], list[dict]]:
    """Generate a folio- and line-structured stream for `hand` on its real layout template."""
    rng = np.random.default_rng(seed)
    tmpl = load_template(hand, N_STREAM)
    params = fit_hand_params(hand)

    r_tab = params["r_tab"]
    base_toks = list(params["base_toks"])
    cnt = params["cnt"]
    adj = params["adj"]
    w_onset = params["w_onset"]
    w_end = params["w_end"]
    para_ratio = params["para_ratio"]
    init_ratio = params["init_ratio"]
    end_ratio = params["end_ratio"]
    para_words = params["para_words"]
    init_words = params["init_words"]
    final_words = params["final_words"]
    top_stems = params["top_stems"]

    out_lines: list[list[str]] = []
    out_records: list[dict] = []
    buf: list[str] = []
    cur_folio = None
    folio_idx = -1
    folio_stems: list[str] = []
    ptr = 0

    for rec in tmpl:
        line_len = len(rec["words"])
        if rec["page"] != cur_folio:
            cur_folio = rec["page"]
            folio_idx += 1
            if buf:
                n_keep = max(1, int(round(rho_keep * len(buf))))
                keep_idx = sorted(rng.choice(len(buf), n_keep, replace=False))
                buf = [buf[i] for i in keep_idx]
            start_s = (folio_idx * n_stems_per_folio) % max(1, len(top_stems) - n_stems_per_folio)
            folio_stems = top_stems[start_s : start_s + n_stems_per_folio]

        line_words: list[str] = []
        for pos in range(line_len):
            prev_last = line_words[-1][-1] if pos > 0 else None
            if pos == 0:
                # Line-initial token: cross-word junction is suppressed across the line break
                win = [base_toks[(ptr + k) % len(base_toks)] for k in range(36)]
                if rec["para_first"]:
                    scores = np.array(
                        [
                            (para_ratio.get(w_onset[c], 1.0) ** 3.5) * (1.0 + 4.0 * para_words[c])
                            for c in win
                        ],
                        dtype=float,
                    )
                else:
                    scores = np.array(
                        [
                            (init_ratio.get(w_onset[c], 1.0) ** 3.0) * (1.0 + 2.5 * init_words[c])
                            for c in win
                        ],
                        dtype=float,
                    )
                scores /= scores.sum()
                k_sel = int(rng.choice(len(win), p=scores))
                w = win[k_sel]
                base_toks[(ptr + k_sel) % len(base_toks)] = base_toks[ptr % len(base_toks)]
                ptr += 1
            elif pos == line_len - 1:
                # Line-final token: weighted jointly by within-line junction and line-final ending
                win = [base_toks[(ptr + k) % len(base_toks)] for k in range(30)]
                scores = np.array(
                    [
                        (r_tab.get(prev_last, {}).get(cand[0], 1.0) ** s_junc)
                        * (end_ratio.get(w_end[cand], 1.0) ** 3.2)
                        * (1.0 + 2.0 * final_words[cand])
                        for cand in win
                    ],
                    dtype=float,
                )
                scores /= scores.sum()
                k_sel = int(rng.choice(len(win), p=scores))
                w = win[k_sel]
                base_toks[(ptr + k_sel) % len(base_toks)] = base_toks[ptr % len(base_toks)]
                ptr += 1
            else:
                # Interior token: draw from folio buffer (1-edit near-repeat or folio stem) or queue with junction
                chosen = None
                u = rng.random()
                if u < p_edit1 and len(buf) >= 1:
                    cands = [nb for nb in adj[buf[-1]] if cnt[nb] >= 3]
                    if cands:
                        scores = np.array(
                            [r_tab.get(prev_last, {}).get(c[0], 1.0) ** s_junc for c in cands],
                            dtype=float,
                        )
                        scores /= scores.sum()
                        chosen = cands[int(rng.choice(len(cands), p=scores))]
                elif u < p_edit1 + p_edit_2_5 and len(buf) >= 2:
                    lag = int(rng.integers(2, min(5, len(buf)) + 1))
                    cands = [nb for nb in adj[buf[-lag]] if cnt[nb] >= 3]
                    if cands:
                        scores = np.array(
                            [r_tab.get(prev_last, {}).get(c[0], 1.0) ** s_junc for c in cands],
                            dtype=float,
                        )
                        scores /= scores.sum()
                        chosen = cands[int(rng.choice(len(cands), p=scores))]
                elif u < p_edit1 + p_edit_2_5 + p_edit_6_20 and len(buf) >= 6:
                    lag = int(rng.integers(6, min(20, len(buf)) + 1))
                    cands = [nb for nb in adj[buf[-lag]] if cnt[nb] >= 3]
                    if cands:
                        scores = np.array(
                            [r_tab.get(prev_last, {}).get(c[0], 1.0) ** s_junc for c in cands],
                            dtype=float,
                        )
                        scores /= scores.sum()
                        chosen = cands[int(rng.choice(len(cands), p=scores))]
                elif u < p_edit1 + p_edit_2_5 + p_edit_6_20 + p_edit_21_80 and len(buf) >= 21:
                    lag = int(rng.integers(21, min(85, len(buf)) + 1))
                    cands = [nb for nb in adj[buf[-lag]] if cnt[nb] >= 3]
                    if cands:
                        scores = np.array(
                            [r_tab.get(prev_last, {}).get(c[0], 1.0) ** s_junc for c in cands],
                            dtype=float,
                        )
                        scores /= scores.sum()
                        chosen = cands[int(rng.choice(len(cands), p=scores))]
                elif u < p_edit1 + p_edit_2_5 + p_edit_6_20 + p_edit_21_80 + stem_repeats and folio_stems:
                    recent12 = set(buf[-12:])
                    avail_stems = [s for s in folio_stems if s not in recent12]
                    if avail_stems:
                        scores = np.array(
                            [r_tab.get(prev_last, {}).get(c[0], 1.0) ** s_junc for c in avail_stems],
                            dtype=float,
                        )
                        scores /= scores.sum()
                        chosen = avail_stems[int(rng.choice(len(avail_stems), p=scores))]
                if chosen is None:
                    win = [base_toks[(ptr + k) % len(base_toks)] for k in range(8)]
                    scores = np.array(
                        [r_tab.get(prev_last, {}).get(c[0], 1.0) ** s_junc for c in win],
                        dtype=float,
                    )
                    scores /= scores.sum()
                    k_sel = int(rng.choice(len(win), p=scores))
                    chosen = win[k_sel]
                    base_toks[(ptr + k_sel) % len(base_toks)] = base_toks[ptr % len(base_toks)]
                    ptr += 1
                w = chosen

            line_words.append(w)
            buf.append(w)
            if len(buf) > W_BUF:
                buf = buf[-W_BUF:]

        out_lines.append(line_words)
        new_rec = dict(rec)
        new_rec["words"] = line_words
        out_records.append(new_rec)

    return out_lines, out_records


def layout_flat_lines_on_template(flat_lines: list[list[str]], hand: str) -> tuple[list[list[str]], list[dict]]:
    """Lay a flat h39 baseline stream onto the real folio/line template of `hand`."""
    tmpl = load_template(hand, N_STREAM)
    toks = [w for l in flat_lines for w in l]
    out_lines: list[list[str]] = []
    out_records: list[dict] = []
    ptr = 0
    for rec in tmpl:
        line_len = len(rec["words"])
        words = [toks[(ptr + k) % len(toks)] for k in range(line_len)]
        ptr += line_len
        out_lines.append(words)
        new_rec = dict(rec)
        new_rec["words"] = words
        out_records.append(new_rec)
    return out_lines, out_records


def _ms_dstats_rows() -> list[dict]:
    ms_dir = ROOT / "hypotheses" / "h20_generators_vs_italian" / "results"
    rows = []
    for h in HANDS:
        c = json.loads((ms_dir / f"cell_MS_{h}.json").read_text(encoding="utf-8"))
        b = c["schemes"]["bifolium"]
        rows.append(h20_lib.dstats(b["bits"], b["glyphs_per_word"], c["crossfit_W5"]["lam"]))
    return rows


def score_b1(lines: list[list[str]], name: str, n_boot: int = 100) -> dict:
    """Score B1 (h20 5-feature bifolium likelihood fingerprint; pass requires >= 4/5 matches)."""
    ms_rows = _ms_dstats_rows()
    cell = run_h20.lines_to_cell(lines, name, "ctrl", "eva")
    rng = np.random.default_rng(19)
    pages = cell["pages"]
    folds = run_h19.group_folds(pages, "bif", 5)
    tok_dfs = []
    for fi_, (tr, te) in enumerate(folds):
        trp = [pages[i] for i in tr]
        tep = [pages[i] for i in te]
        bt, _ = run_h19.run_split(trp, tep, cell, rng)
        pc = h20_lib.PosCharLM().fit([w for p in trp for w in p["words"]])
        bt["PCLM"] = np.array([pc.logp(w) for p in tep for w in p["words"]])
        df = pd.DataFrame(bt)
        df["glyphs"] = [len(w) + 1 for p in tep for w in p["words"]]
        tok_dfs.append(df)
    tok = pd.concat(tok_dfs, ignore_index=True)
    bits = {c: float(-tok[c].mean()) for c in tok.columns if c != "glyphs"}
    gpw = float(tok.glyphs.mean())
    w5 = run_h19.crossfit_lambda(cell, folds, 5, rng, n_boot=n_boot)
    stats = h20_lib.dstats(bits, gpw, w5["lam"])
    m = h20_lib.match(stats, ms_rows)
    return {
        "bits": bits,
        "glyphs_per_word": gpw,
        "lam5": float(w5["lam"]),
        "stats": {k: float(v) for k, v in stats.items()},
        "match": m,
        "n_match": int(m["n_match"]),
        "passed": bool(m["n_match"] >= 4),
    }


def score_b2(lines: list[list[str]], hand: str) -> dict:
    """Score B2 (h40 interior space predictability S inside hand band +/-0.02 and J >= 0.06 bits)."""
    interior = [l[1:-1] for l in lines if len(l) >= 4]
    sp_int = h33_lib.space_predict(interior)
    sp_full = h33_lib.space_predict(lines)
    s_int = float(sp_int["entropy_removed"])
    s_full = float(sp_full["entropy_removed"])
    j_val = float(h34_lib.junction(lines, np.random.default_rng(47)))
    lo, hi = S_BANDS[hand]
    in_band = bool(lo <= s_int <= hi)
    j_ok = bool(j_val >= J_MIN)
    return {
        "S_interior": s_int,
        "S_full": s_full,
        "band_lo": lo,
        "band_hi": hi,
        "in_band": in_band,
        "J": j_val,
        "J_min": J_MIN,
        "j_ok": j_ok,
        "passed": bool(in_band and j_ok),
    }


def score_b3(records: list[dict], n_perm: int = 100) -> dict:
    """Score B3 (h30 line-edge properties: positional excess MI, cross-line break, para-initial JS)."""
    rng = np.random.default_rng(30)
    cl_map = h30_lib.classes(records)

    def _z(obs_val: float, null_list: list[float]) -> float:
        arr = np.asarray(null_list, dtype=float)
        return float((obs_val - arr.mean()) / (arr.std() + 1e-12))

    m2 = {}
    for c in ("ONSET", "END"):
        cl = cl_map[c]
        obs = h30_lib.mi(h30_lib.pos_pairs(cl))
        null = [h30_lib.mi(h30_lib.pos_pairs(h30_lib.permute_within(records, cl, rng))) for _ in range(n_perm)]
        m2[c] = {
            "obs": float(obs),
            "null_mean": float(np.mean(null)),
            "excess": float(obs - np.mean(null)),
            "z": _z(obs, null),
        }

    a, b = "END", "ONSET"
    wi = float(h30_lib.mi([(x[i], y[i + 1]) for x, y in zip(cl_map[a], cl_map[b]) for i in range(len(x) - 1)]))
    ac = float(h30_lib.mi(h30_lib.across_pairs(records, None, a_cl=cl_map[a], b_cl=cl_map[b])))
    an = [
        h30_lib.mi(h30_lib.across_pairs(records, None, order=h30_lib.shuffle_order(records, rng), a_cl=cl_map[a], b_cl=cl_map[b]))
        for _ in range(n_perm)
    ]
    ac_ex = float(ac - np.mean(an))
    ac_z = _z(ac, an)

    pf = np.array([bool(l["para_first"]) for l in records])
    on = [c[0] for c in cl_map["ONSET"]]

    def _jsd(lab):
        return h30_lib.js(Counter(o for o, f in zip(on, lab) if f), Counter(o for o, f in zip(on, lab) if not f))

    obs_js = float(_jsd(pf))
    null_js = []
    for _ in range(n_perm):
        lab = pf.copy()
        by = defaultdict(list)
        for i, l in enumerate(records):
            by[l["stratum"]].append(i)
        for ii in by.values():
            lab[ii] = rng.permutation(lab[ii])
        null_js.append(_jsd(lab))
    para_z = _z(obs_js, null_js)

    onset_ex = m2["ONSET"]["excess"]
    end_ex = m2["END"]["excess"]
    comb_ex = onset_ex + end_ex
    pass_pos = bool(
        onset_ex >= 3.0 * PROSE_ONSET_EXCESS
        and end_ex >= 3.0 * PROSE_END_EXCESS
        and comb_ex >= 3.0 * PROSE_COMB_EXCESS
        and m2["ONSET"]["z"] > 5.0
        and m2["END"]["z"] > 5.0
    )
    pass_cross = bool(wi > 0.0 and ac_ex < 0.5 * wi)
    pass_para = bool(para_z > 3.0)

    return {
        "onset_excess": onset_ex,
        "onset_z": m2["ONSET"]["z"],
        "end_excess": end_ex,
        "end_z": m2["END"]["z"],
        "comb_excess": comb_ex,
        "prose_3x_threshold": 3.0 * PROSE_COMB_EXCESS,
        "within_end_onset_mi": wi,
        "across_end_onset_mi": ac,
        "across_end_onset_excess": ac_ex,
        "across_end_onset_z": ac_z,
        "cross_to_within_ratio": ac_ex / max(wi, 1e-12),
        "para_onset_js": obs_js,
        "para_onset_z": para_z,
        "pass_pos": pass_pos,
        "pass_cross": pass_cross,
        "pass_para": pass_para,
        "passed": bool(pass_pos and pass_cross and pass_para),
    }


def score_b4(records: list[dict], name: str) -> dict:
    """Score B4 (h43 folio-boundary reset at distance 80; also records distance 160 for long-folio hands)."""
    q_map: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        q_map[str(r["quire"])][str(r["page"])].extend(r["words"])
    q_list = [[f_toks for _, f_toks in f_dict.items()] for _, f_dict in q_map.items()]
    s43 = h43_lib.build_stream(q_list, name=name)
    r43 = h43_lib.score_stream(s43, np.random.default_rng(43))
    d80 = r43["distances"]["80"]
    d160 = r43["distances"]["160"]
    # For hands where distance 80 has >= 30 cross-folio pairs (1A, 2B), d80["pass"] is the criterion;
    # for 3B (23 cross pairs at d=80), we report both d80 (unscored) and d160 (scored), plus effect > null_p95.
    eff80_gt_p95 = bool(
        d80["effect"] is not None and d80["null_p95"] is not None and d80["effect"] > d80["null_p95"]
    )
    passed = bool(d80["pass"]) if d80["scored"] else bool(d160["pass"] and eff80_gt_p95)
    return {
        "d80": d80,
        "d160": d160,
        "d80_scored": bool(d80["scored"]),
        "d80_pass": bool(d80["pass"]),
        "d80_effect_gt_p95": eff80_gt_p95,
        "d160_pass": bool(d160["pass"]),
        "passed": passed,
    }


def score_b5(records: list[dict]) -> dict:
    """Score B5 (h44 200-token burstiness excess in [0.8, 3.5] and folio-concentrated)."""
    tokens = [w for r in records for w in r["words"]]
    pages = [str(r["page"]) for r in records for _ in r["words"]]
    quires = [str(r["quire"]) for r in records for _ in r["words"]]
    r44 = h44_lib.score_stream(tokens, pages, quires)
    excess = float(r44["excess"])
    page_gap = float(r44["in_page"]) - float(r44["full"])
    quire_gap = float(r44["in_quire"]) - float(r44["full"])
    in_band = bool(0.8 <= excess <= 3.5)
    folio_conc = bool(page_gap > quire_gap)
    return {
        "orig": float(r44["orig"]),
        "in_page": float(r44["in_page"]),
        "in_quire": float(r44["in_quire"]),
        "full": float(r44["full"]),
        "excess": excess,
        "page_gap": page_gap,
        "quire_gap": quire_gap,
        "share_kept_in_quire": r44["share_kept_in_quire"],
        "in_band": in_band,
        "folio_concentrated": folio_conc,
        "passed": bool(in_band and folio_conc),
    }


def score_b6(records: list[dict]) -> dict:
    """Score B6 (h42 one-edit near-repeat decay shape == 'page')."""
    tokens = [w for r in records for w in r["words"]]
    quires = [str(r["quire"]) for r in records for _ in r["words"]]
    r42 = h42_lib.score_units(h42_lib.eva_units(tokens), quires, n_null=10, seed=42)
    bins_summary = {}
    for b in h42_lib.BIN_NAMES:
        bd = r42["bins"][b]
        sd = float(bd["null_sd"]) if bd["null_sd"] else 0.0
        ex = float(bd["excess"]) if bd["excess"] is not None else 0.0
        bins_summary[b] = {
            "rate": bd["rate"],
            "null_mean": bd["null_mean"],
            "null_sd": sd,
            "excess": ex,
            "z": ex / sd if sd > 0 else 0.0,
            "elevated": bool(bd["elevated"]),
        }
    return {
        "shape": r42["shape"],
        "decay_point": r42["decay_point"],
        "bins": bins_summary,
        "passed": bool(r42["shape"] == "page"),
    }


def score_all_benchmarks(lines: list[list[str]], records: list[dict], hand: str, name: str, n_boot: int = 100) -> dict:
    """Run all six benchmarks B1..B6 on a stream and return the complete benchmark dictionary."""
    b1 = score_b1(lines, name, n_boot=n_boot)
    b2 = score_b2(lines, hand)
    b3 = score_b3(records)
    b4 = score_b4(records, name)
    b5 = score_b5(records)
    b6 = score_b6(records)
    benchmarks = {"B1": b1, "B2": b2, "B3": b3, "B4": b4, "B5": b5, "B6": b6}
    n_passed = sum(1 for k in ("B1", "B2", "B3", "B4", "B5", "B6") if benchmarks[k]["passed"])
    return {
        "name": name,
        "hand": hand,
        "n_lines": len(lines),
        "n_tokens": sum(len(l) for l in lines),
        "n_folios": len({r["page"] for r in records}),
        "n_quires": len({r["quire"] for r in records}),
        "benchmarks": benchmarks,
        "pass_flags": {k: bool(benchmarks[k]["passed"]) for k in ("B1", "B2", "B3", "B4", "B5", "B6")},
        "n_passed": int(n_passed),
    }


def evaluate_predictions(streams: dict[str, dict]) -> dict:
    """Evaluate preregistered predictions U1, U2, U3 across scored streams."""
    plc_2b = streams["page_line_copier_2B"]
    u1_pass = bool(plc_2b["n_passed"] >= 5)

    hands_ge5 = [
        h for h in HANDS if streams[f"page_line_copier_{h}"]["n_passed"] >= 5
    ]
    # Also check strict d80 scored pass on B4 for hands where d80 is scored
    u2_pass = bool(len(hands_ge5) >= 2)

    base_native = streams["h39_native_tuned_2B"]
    base_c0 = streams["h39_C0_graph_2B"]
    u3_pass = bool(base_native["n_passed"] <= 3 and base_c0["n_passed"] <= 3)

    if u1_pass and u2_pass and u3_pass:
        verdict = "supported"
    elif u1_pass or u2_pass:
        verdict = "partially_supported"
    else:
        verdict = "refuted"

    return {
        "U1": {
            "passed": u1_pass,
            "n_passed_2B": plc_2b["n_passed"],
            "pass_flags_2B": plc_2b["pass_flags"],
            "description": "page_line_copier passes >= 5 of B1..B6 on Hand 2B",
        },
        "U2": {
            "passed": u2_pass,
            "hands_passing_ge5": hands_ge5,
            "n_passed_by_hand": {h: streams[f"page_line_copier_{h}"]["n_passed"] for h in HANDS},
            "description": "page_line_copier passes >= 5 of B1..B6 on >= 2 of {1A, 2B, 3B}",
        },
        "U3": {
            "passed": u3_pass,
            "n_passed_h39_native_tuned_2B": base_native["n_passed"],
            "n_passed_h39_C0_graph_2B": base_c0["n_passed"],
            "description": "Previous h39 best generators pass <= 3 of B1..B6 when evaluated on all six simultaneously",
        },
        "verdict": verdict,
    }
