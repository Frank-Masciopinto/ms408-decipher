"""Library for hypothesis h02: candidate frequency (Hz) maps for every manuscript unit, and tests of the pitch sequences they produce.

A frequency assignment is a hypothesis-generation device. It has NO evidential link to the manuscript unless the pitch sequence it
produces shows structure beyond (i) random re-assignments of the same pitches to the units and (ii) the same units shuffled inside each
word, and (iii) beyond what control texts show under the same scheme. Maps fitted to the data (position, slot, entropy, seriation) are
partly circular for contour statistics (a map that is monotone in a unit's position makes words monotone by construction); every fitted map
is therefore cross-fitted (fitted on half the folios / blocks and evaluated on the other half).
"""
from __future__ import annotations

import itertools
import math
import sys
import zlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h01_tone_sheet"))

import h01_lib as H1  # noqa: E402
from msdecipher.segment import Segmenter, PRESETS  # noqa: E402
from msdecipher import stats as MS  # noqa: E402
from msdecipher.slot_grammar import SlotGrammar  # noqa: E402

TR = ROOT / "data" / "transcriptions"
F0 = 174.0                                   # lowest tone on the sheet; tonic of every scale map
SHEET = dict(zip(H1.load_table()["glyph"], H1.load_table()["tone_hz"].astype(float)))
SHEET_UNITS = list(SHEET)
_LIN = H1.linear_rank_fit(list(SHEET.values()))
STEP_HZ = _LIN["step_hz"]                    # 35.57 Hz: the sheet's own near-even spacing
HI_HZ = max(SHEET.values())                  # 433
RANGE_CENTS = 1200 * math.log2(HI_HZ / F0)   # 1577.5 cents: the sheet's span, used for range-matched continuous maps
MIN_COUNT = 20
MAX_LEN = 24

# ------------------------------------------------------------------------------------------------
# texts
# ------------------------------------------------------------------------------------------------


@dataclass
class Text:
    name: str
    family: str                       # natural | cipher | generator | ms408
    tok: str                          # T1 collapsed EVA units / T2 = T1 + the sheet's 8 digraphs / C characters
    inv: list[str]                    # inventory (units with count >= MIN_COUNT, plus sheet units in T2)
    U: np.ndarray                     # (n_words, MAX) int16 unit ids, -1 padded
    L: np.ndarray                     # (n_words,) lengths
    fold: np.ndarray                  # 0/1 cross-fitting fold of each word
    folio: np.ndarray | None = None   # folio index per word (MS only)
    folio_names: list = field(default_factory=list)
    folio_section: list = field(default_factory=list)
    folio_language: list = field(default_factory=list)
    n_dropped: int = 0
    n_total: int = 0

    @property
    def units_of(self):
        return self.inv


def _build(name, family, tok, unit_words, fold, inv_force=(), folio=None, meta=None, min_count=MIN_COUNT):
    cnt = Counter(u for w in unit_words for u in w)
    inv = sorted([u for u, c in cnt.items() if c >= min_count or u in inv_force and c >= 1], key=str)
    idx = {u: i for i, u in enumerate(inv)}
    keep, rows = [], []
    for i, w in enumerate(unit_words):
        if 0 < len(w) <= MAX_LEN and all(u in idx for u in w):
            keep.append(i)
            rows.append([idx[u] for u in w])
    n = len(rows)
    U = np.full((n, MAX_LEN), -1, dtype=np.int16)
    L = np.zeros(n, dtype=np.int16)
    for r, row in enumerate(rows):
        U[r, :len(row)] = row
        L[r] = len(row)
    keep = np.array(keep)
    t = Text(name, family, tok, inv, U, L, np.asarray(fold)[keep], n_dropped=len(unit_words) - n, n_total=len(unit_words))
    if folio is not None:
        t.folio = np.asarray(folio)[keep]
        t.folio_names, t.folio_section, t.folio_language = meta
    return t


def build_ms(tok: str = "T1", path: Path | None = None) -> Text:
    folios = H1.load_folios(path or TR / "ZL3b-n.txt", "P")
    comps = PRESETS["collapsed"] + (tuple(SHEET_UNITS) if tok == "T2" else ())
    seg = Segmenter(comps, name=tok)
    words, fol = [], []
    for fi, f in enumerate(folios):
        for w in f.tokens:
            words.append(seg(w))
            fol.append(fi)
    fold = [f % 2 for f in fol]
    return _build("MS408", "ms408", tok, words, fold, inv_force=SHEET_UNITS if tok == "T2" else (), folio=fol,
                  meta=([f.folio for f in folios], [f.section for f in folios], [f.language for f in folios]))


def build_tokens_text(name: str, family: str, tokens: list[str]) -> Text:
    words = [tuple(t) for t in tokens]
    fold = [(i // 500) % 2 for i in range(len(words))]
    return _build(name, family, "C", words, fold)


# ------------------------------------------------------------------------------------------------
# per-unit statistics from a training set (everything a data-driven map may use)
# ------------------------------------------------------------------------------------------------


def unit_stats(t: Text, mask: np.ndarray, slot_grammar: bool = True, seed: int = 0) -> dict:
    """Statistics of every inventory unit computed ONLY from words where ``mask`` is True."""
    inv = t.inv
    A = len(inv)
    U, L = t.U[mask].astype(np.int64), t.L[mask].astype(np.int64)
    n, Lm = U.shape
    valid = np.arange(Lm)[None, :] < L[:, None]
    cnt = np.bincount(U[valid], minlength=A).astype(float)
    j = np.arange(Lm)[None, :]
    two = (L >= 2)[:, None] & valid
    rel = np.where(two, j / np.maximum(L[:, None] - 1, 1), 0.0)
    n2 = np.bincount(U[two], minlength=A).astype(float)
    meanpos = np.where(n2 > 0, np.bincount(U[two], weights=rel[two], minlength=A) / np.maximum(n2, 1), np.nan)
    init = np.bincount(U[:, 0][L >= 2], minlength=A) / np.maximum(n2, 1)
    last = U[np.arange(n), np.maximum(L - 1, 0)]
    fin = np.bincount(last[L >= 2], minlength=A) / np.maximum(n2, 1)
    # bigram counts (inside words) with an end marker
    a_ = U[:, :-1]
    b_ = U[:, 1:]
    vv = (j[:, :-1] < (L[:, None] - 1))
    C = np.zeros((A, A + 1))
    np.add.at(C, (a_[vv], b_[vv]), 1)
    np.add.at(C, (last, np.full(n, A)), 1)
    p = C / np.maximum(C.sum(1, keepdims=True), 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        Hn = -np.nansum(np.where(p > 0, p * np.log2(p), 0.0), axis=1)
    Hn = np.where(cnt > 0, Hn, np.nan)
    tot = max(cnt.sum(), 1)
    surpr = np.where(cnt > 0, -np.log2(np.maximum(cnt, 1) / tot), np.nan)
    # fiedler vector of the symmetric within-word adjacency graph (seriation)
    W = C[:, :A] + C[:, :A].T
    np.fill_diagonal(W, 0)
    deg = W.sum(1)
    with np.errstate(divide="ignore"):
        dinv = np.where(deg > 0, 1 / np.sqrt(deg), 0)
    Ln = np.eye(A) - dinv[:, None] * W * dinv[None, :]
    ev, evec = np.linalg.eigh(Ln)
    fied = dinv * evec[:, 1] if A > 2 else np.zeros(A)
    mp_fill = np.where(np.isnan(meanpos), 0.5, meanpos)
    if np.corrcoef(fied, mp_fill)[0, 1] < 0:
        fied = -fied
    # Sukhotin class
    seqs = [tuple(inv[u] for u in U[i, :L[i]]) for i in range(0, n)]
    vowels, _ = MS.sukhotin(seqs)
    is_vowel = np.array([u in set(vowels) for u in inv])
    # slot grammar expected slot (learned on word types of the training set)
    slot_exp = np.full(A, np.nan)
    if slot_grammar:
        counts = Counter(tuple(int(x) for x in U[i, :L[i]]) for i in range(n) if L[i] <= 12)
        sg = SlotGrammar(K=12).fit(counts, iters=25, seed=seed)
        mass = sg.P * sg.e[:, None]                       # (K, A') emission mass per slot
        ks = np.arange(sg.K)[:, None]
        e_slot = (mass * ks).sum(0) / np.maximum(mass.sum(0), 1e-12)
        for ui, a in enumerate(sg.units):
            slot_exp[a] = e_slot[ui]
    # cluster of units by positional behaviour (k-means, k=5)
    from sklearn.cluster import KMeans
    seen = cnt > 0
    feats = np.column_stack([init, fin, np.maximum(1 - init - fin, 0), np.nan_to_num(Hn, nan=np.nanmedian(Hn)), mp_fill])
    feats = (feats - feats[seen].mean(0)) / (feats[seen].std(0) + 1e-9)
    k = min(5, int(seen.sum()))
    cl = np.zeros(A, dtype=int)
    if k >= 2:
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(feats[seen])
        lab = km.labels_
        order = np.argsort([mp_fill[seen][lab == c].mean() for c in range(k)])
        remap = {int(c): r for r, c in enumerate(order)}
        cl[seen] = [remap[int(c)] for c in lab]
        cl[~seen] = int(np.median(cl[seen]))
    return {"count": cnt, "meanpos": mp_fill, "init": init, "final": fin, "final_minus_init": fin - init, "H_next": np.where(np.isnan(Hn), np.nanmedian(Hn), Hn),
            "surprisal": np.where(np.isnan(surpr), np.nanmax(surpr), surpr), "fiedler": fied, "is_vowel": is_vowel, "vowels": vowels,
            "slot_exp": np.where(np.isnan(slot_exp), np.nanmedian(slot_exp) if slot_grammar and not np.all(np.isnan(slot_exp)) else 0.0, slot_exp),
            "cluster": cl, "W": W, "seen": seen}


def alpha_rank(inv: list[str]) -> np.ndarray:
    order = sorted(range(len(inv)), key=lambda i: str(inv[i]))
    r = np.empty(len(inv), dtype=int)
    r[order] = np.arange(len(inv))
    return r


def ordering_ranks(st: dict, inv: list[str]) -> dict[str, np.ndarray]:
    """Rank (0 = first/lowest) of every unit under each ordering. Ties are broken by frequency (most frequent first)."""
    cnt = st["count"]
    fr = np.argsort(np.argsort(-cnt, kind="stable"), kind="stable")

    def rk(key):
        order = np.lexsort((fr, key))
        r = np.empty(len(key), dtype=int)
        r[order] = np.arange(len(key))
        return r
    return {
        "freq": fr.copy(),
        "slot": rk(st["meanpos"]),                                    # mean relative position in the word: initial -> final
        "alpha": alpha_rank(inv),
        "vowel": rk(np.where(st["is_vowel"], 0.0, 1.0) * 1e6 + fr),   # vowel-like units first, then consonant-like; by frequency inside a class
        "entropy": rk(st["H_next"]),                                  # unit that makes the next unit most predictable first
        "seriation": rk(st["fiedler"]),                               # Fiedler order of the within-word adjacency graph
        "slotgrammar": rk(st["slot_exp"]),                            # expected slot of the learned 12-slot grammar
    }


# ------------------------------------------------------------------------------------------------
# candidate maps  (unit -> Hz).  Every map is a function of the training statistics, so it can be re-fitted on any text.
# ------------------------------------------------------------------------------------------------

SCALES = {   # cents above the tonic within one octave
    "chromatic12": [100.0 * i for i in range(12)],
    "major12": [0, 200, 400, 500, 700, 900, 1100],
    "pentatonic": [0, 200, 400, 700, 900],
    "just_diatonic": [1200 * math.log2(r) for r in (1, 9 / 8, 5 / 4, 4 / 3, 3 / 2, 5 / 3, 15 / 8)],
    "pythagorean": [1200 * math.log2(r) for r in (1, 9 / 8, 81 / 64, 4 / 3, 3 / 2, 27 / 16, 243 / 128)],
}
A_ORDERS = ["freq", "slot", "alpha", "vowel", "entropy", "seriation", "slotgrammar"]
B_ORDERS = ["freq", "slot", "vowel"]


def hz(cents_above_f0):
    return F0 * 2 ** (np.asarray(cents_above_f0, float) / 1200.0)


def _minmax(x, lo=0.0, hi=RANGE_CENTS):
    x = np.asarray(x, float)
    r = x.max() - x.min()
    return lo + (x - x.min()) / (r if r > 0 else 1.0) * (hi - lo)


def sheet_anchor_fit(inv: list[str], ranks: np.ndarray) -> tuple[float, float, np.ndarray]:
    """Regress the sheet's 8 Hz values on the rank of those 8 units within the full inventory ordering; returns (intercept, slope, idx of anchors)."""
    idx = np.array([inv.index(u) for u in SHEET_UNITS if u in inv])
    if len(idx) < 4:
        return F0, STEP_HZ, idx
    y = np.array([SHEET[inv[i]] for i in idx])
    A = np.vstack([np.ones(len(idx)), ranks[idx]]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(coef[0]), float(coef[1]), idx


def smooth_assignment(st: dict, n_iter: int = 30) -> np.ndarray:
    """Objective map: assign equally spaced pitches (rank r -> r semitone-ish steps across the sheet's span) to units so that
    sum_ij W_ij |p_i - p_j| is minimal (smoothest average melody). Fiedler order start, pairwise-swap hill climbing."""
    W = st["W"]
    A = W.shape[0]
    order = np.argsort(st["fiedler"], kind="stable")
    pos = np.empty(A)
    pos[order] = np.arange(A)
    cost = lambda p: (W * np.abs(p[:, None] - p[None, :])).sum() / 2     # noqa: E731
    best = cost(pos)
    for _ in range(n_iter):
        improved = False
        for i in range(A):
            for j in range(i + 1, A):
                pos[i], pos[j] = pos[j], pos[i]
                c = cost(pos)
                if c < best - 1e-9:
                    best, improved = c, True
                else:
                    pos[i], pos[j] = pos[j], pos[i]
        if not improved:
            break
    return pos


def map_names(with_slotgrammar: bool = True) -> list[str]:
    names = []
    for o in A_ORDERS:
        if o == "slotgrammar" and not with_slotgrammar:
            continue
        names += [f"a_{o}_ext", f"a_{o}_cmp"]
    for s in SCALES:
        for o in B_ORDERS:
            names.append(f"b_{s}_{o}")
    names += ["c_pos", "c_final", "c_entropy", "c_seriation", "c_cluster_pentatonic", "c_vowelclass"]
    if with_slotgrammar:
        names.append("c_slotgrammar")
    names += ["d_surprisal", "d_smooth"]
    if with_slotgrammar:
        names.append("d_slotmono")
    return names


GROUP = {"a": "a: extend the sheet's own pattern", "b": "b: musical scale", "c": "c: data-driven (behaviour -> pitch)", "d": "d: objective-driven"}


def describe_map(name: str) -> str:
    p = name.split("_")
    if p[0] == "a":
        if p[2] == "ext":
            return f"sheet pattern extended: Hz = a + b*rank in the '{p[1]}' ordering (a,b regressed on the sheet's 8 values where those units exist; else 174 + 35.57 Hz per rank), the 8 sheet units keep their printed Hz"
        return f"sheet range compressed: ranks in the '{p[1]}' ordering spread evenly over the sheet's 174-433 Hz span"
    if p[0] == "b":
        sc = "_".join(p[1:-1])
        return f"{sc} scale from 174 Hz tonic, one scale degree per unit going up, units ordered by '{p[-1]}'"
    return {"c_pos": "log-Hz linear in mean relative position in word (initial = 174, final = 433)",
            "c_final": "log-Hz linear in (share word-final - share word-initial)",
            "c_entropy": "log-Hz linear in H(next unit | this unit)",
            "c_seriation": "log-Hz linear in the Fiedler (seriation) coordinate of the within-word adjacency graph",
            "c_cluster_pentatonic": "k-means (k=5) cluster of positional behaviour -> pentatonic degree; units of a cluster share a pitch",
            "c_vowelclass": "Sukhotin class: vowel-like = 174 Hz, consonant-like = 433 Hz",
            "c_slotgrammar": "log-Hz linear in the expected slot of the learned 12-slot grammar",
            "d_surprisal": "log-Hz linear in surprisal -log2 p(unit): pitch spread proportional to information content",
            "d_smooth": "equally spaced pitches assigned to minimise sum W_ij|p_i - p_j| over within-word neighbours (smoothest melody)",
            "d_slotmono": "equally spaced pitches in order of expected slot (monotone with slot index so that words become contours)"}[name]


def build_map(name: str, st: dict, inv: list[str]) -> np.ndarray:
    """Hz for every inventory unit under map ``name`` using only the statistics ``st``."""
    A = len(inv)
    rk = ordering_ranks(st, inv)
    p = name.split("_")
    if p[0] == "a":
        o, kind = p[1], p[2]
        r = rk[o].astype(float)
        if kind == "cmp":
            return hz(_minmax(r))
        a, b, idx = sheet_anchor_fit(inv, r)
        out = np.clip(a + b * r, 60.0, None)
        for i in idx:
            out[i] = SHEET[inv[i]]
        return out
    if p[0] == "b":
        o = p[-1]
        scale = SCALES["_".join(p[1:-1])]
        n = len(scale)
        r = rk[o]
        cents = np.array([scale[k % n] + 1200 * (k // n) for k in r])
        return hz(cents)
    if name == "c_pos":
        return hz(_minmax(st["meanpos"]))
    if name == "c_final":
        return hz(_minmax(st["final_minus_init"]))
    if name == "c_entropy":
        return hz(_minmax(st["H_next"]))
    if name == "c_seriation":
        return hz(_minmax(st["fiedler"]))
    if name == "c_slotgrammar":
        return hz(_minmax(st["slot_exp"]))
    if name == "c_cluster_pentatonic":
        return hz(np.array(SCALES["pentatonic"])[np.minimum(st["cluster"], 4)])
    if name == "c_vowelclass":
        return hz(np.where(st["is_vowel"], 0.0, RANGE_CENTS))
    if name == "d_surprisal":
        return hz(_minmax(st["surprisal"]))
    if name == "d_smooth":
        return hz(_minmax(smooth_assignment(st)))
    if name == "d_slotmono":
        return hz(_minmax(rk["slotgrammar"].astype(float)))
    raise KeyError(name)


# ------------------------------------------------------------------------------------------------
# which ordering do the sheet's 8 values support?
# ------------------------------------------------------------------------------------------------


def ordering_support(t_full_stats: dict, inv: list[str], rk: dict[str, np.ndarray]) -> pd.DataFrame:
    """For every ordering: Spearman rho between the sheet's Hz and the unit's rank in that ordering (8 units), the exact permutation p-value
    (all 8! assignments of the Hz values), the R^2 and leave-one-out RMSE (Hz) of a linear fit Hz ~ rank, and the residual spacing."""
    idx = [inv.index(u) for u in SHEET_UNITS]
    y = np.array([SHEET[inv[i]] for i in idx])
    n = len(y)
    ry = np.argsort(np.argsort(y)).astype(float)
    rows = []
    perms = np.array(list(itertools.permutations(range(n))), dtype=float)       # 40320 x 8
    for o, r in list(rk.items()) + [("printed_row_order", None)]:
        x = np.arange(n, dtype=float) if r is None else r[idx].astype(float)
        rx = np.argsort(np.argsort(x)).astype(float)
        rho = float(np.corrcoef(rx, ry)[0, 1])
        null = np.array([np.corrcoef(rx, pr)[0, 1] for pr in perms[:: 4]])        # every 4th permutation: 10080 draws, enough for the p
        p_pos = float((np.sum(null >= rho - 1e-12) + 1) / (len(null) + 1))
        p_two = float((np.sum(np.abs(null) >= abs(rho) - 1e-12) + 1) / (len(null) + 1))
        A = np.vstack([np.ones(n), rx]).T
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        res = y - A @ coef
        r2 = 1 - (res ** 2).sum() / ((y - y.mean()) ** 2).sum()
        loo = []
        for k in range(n):
            m = np.arange(n) != k
            c2, *_ = np.linalg.lstsq(A[m], y[m], rcond=None)
            loo.append(y[k] - A[k] @ c2)
        rows.append({"ordering": o, "spearman_rho": rho, "p_one_sided": p_pos, "p_two_sided": p_two, "r2_linear_rank_fit": float(r2),
                     "slope_hz_per_rank": float(coef[1]), "loo_rmse_hz": float(np.sqrt(np.mean(np.square(loo))))})
    df = pd.DataFrame(rows)
    df["holm_p_two_sided"] = H1.holm(list(df.p_two_sided))
    return df


# ------------------------------------------------------------------------------------------------
# pitch sequences -> statistics
# ------------------------------------------------------------------------------------------------


def _ent(counts) -> float:
    c = np.asarray(counts, float)
    c = c[c > 0]
    if c.size == 0:
        return float("nan")
    p = c / c.sum()
    return float(-(p * np.log2(p)).sum())


STAT_NAMES = ["mono_frac", "mono_net_asc", "arch_frac", "valley_frac", "mean_abs_int_st", "int_entropy", "contour_H4", "contour_H5",
              "motif_top5", "repeat4", "zlib_ratio"]
# direction in which a statistic indicates MORE melodic regularity / structure (+1: larger = more regular, -1: smaller = more regular)
STAT_DIR = {"mono_frac": 1, "mono_net_asc": 0, "arch_frac": 1, "valley_frac": 1, "mean_abs_int_st": -1, "int_entropy": -1, "contour_H4": -1,
            "contour_H5": -1, "motif_top5": 1, "repeat4": 1, "zlib_ratio": -1}


def contour_stats(pv: np.ndarray, U: np.ndarray, L: np.ndarray, want_words: bool = False) -> dict:
    """Statistics of the pitch contour of every word. pv: Hz per inventory unit (any map, possibly non-injective)."""
    pc = 1200.0 * np.log2(np.asarray(pv, float) / F0)
    ext = np.append(pc, 0.0)
    U = U.astype(np.int64)
    L = L.astype(np.int64)
    P = ext[U]
    uniq, cls = np.unique(np.round(pc, 3), return_inverse=True)
    K = len(uniq)
    C = np.append(cls, 0)[U]
    n, Lm = U.shape
    j = np.arange(Lm - 1)[None, :]
    vs = j < (L[:, None] - 1)
    D = P[:, 1:] - P[:, :-1]
    S = np.where(np.abs(D) < 1e-6, 0, np.sign(D)).astype(np.int8)
    S = np.where(vs, S, 0)
    ups = ((S == 1)).sum(1)
    dns = ((S == -1)).sum(1)
    s3 = L >= 3
    mono = (ups == 0) | (dns == 0)
    big = Lm + 5
    up_last = np.where(S == 1, j, -1).max(1)
    up_first = np.where(S == 1, j, big).min(1)
    dn_last = np.where(S == -1, j, -1).max(1)
    dn_first = np.where(S == -1, j, big).min(1)
    arch = (ups > 0) & (dns > 0) & (up_last < dn_first)
    valley = (ups > 0) & (dns > 0) & (dn_last < up_first)
    out = {}
    m = max(int(s3.sum()), 1)
    out["mono_frac"] = float(mono[s3].sum() / m)
    out["mono_net_asc"] = float(((mono & (dns == 0) & (ups > 0))[s3].sum() - (mono & (ups == 0) & (dns > 0))[s3].sum()) / m)
    out["arch_frac"] = float(arch[s3].sum() / m)
    out["valley_frac"] = float(valley[s3].sum() / m)
    absd = np.abs(D) / 100.0
    out["mean_abs_int_st"] = float(absd[vs].mean()) if vs.any() else float("nan")
    out["int_entropy"] = _ent(np.unique(np.round(D[vs] / 100.0), return_counts=True)[1])
    pw = 3 ** np.arange(Lm - 1)

    def contour_entropy(length):
        sel = L == length
        if sel.sum() < 30:
            return float("nan")
        codes = ((S[sel][:, :length - 1].astype(np.int64) + 1) * pw[:length - 1][None, :]).sum(1)
        return _ent(np.bincount(codes))
    out["contour_H4"] = contour_entropy(4)
    out["contour_H5"] = contour_entropy(5)
    # motifs: Parsons 3-grams (windows of 4 units) inside words
    if Lm >= 4:
        jj = np.arange(Lm - 3)[None, :]
        okw = jj <= (L[:, None] - 4)
        code3 = (S[:, :-2].astype(np.int64) + 1) * 9 + (S[:, 1:-1].astype(np.int64) + 1) * 3 + (S[:, 2:].astype(np.int64) + 1)
        cc = np.bincount(code3[okw], minlength=27)
        out["motif_top5"] = float(np.sort(cc)[::-1][:5].sum() / max(cc.sum(), 1))
        key = ((C[:, :-3] * K + C[:, 1:-2]) * K + C[:, 2:-1]) * K + C[:, 3:]
        kk = key[okw]
        if kk.size:
            _, cnts = np.unique(kk, return_counts=True)
            out["repeat4"] = float(cnts[cnts >= 2].sum() / cnts.sum())
        else:
            out["repeat4"] = float("nan")
    else:
        out["motif_top5"] = out["repeat4"] = float("nan")
    # compression of the Parsons stream (words separated by a marker)
    ok2 = L >= 2
    jj2 = np.arange(Lm)[None, :]
    code = np.full((n, Lm), 255, dtype=np.uint8)
    sc = (np.concatenate([S, np.zeros((n, 1), np.int8)], axis=1) + 1).astype(np.uint8)
    code = np.where(jj2 < (L[:, None] - 1), sc, code)
    code = np.where(jj2 == (L[:, None] - 1), 3, code)
    stream = code[ok2].ravel()
    stream = stream[stream != 255].tobytes()
    out["zlib_ratio"] = len(zlib.compress(stream, 6)) / max(len(stream), 1)
    if want_words:
        valid = np.arange(Lm)[None, :] < L[:, None]
        out["_word_meanP"] = (np.where(valid, P, 0).sum(1) / np.maximum(L, 1))
        out["_word_mai"] = np.where(ok2, (np.where(vs, absd, 0).sum(1) / np.maximum(L - 1, 1)), np.nan)
        out["_word_mono"] = np.where(s3, mono.astype(float), np.nan)
    return out


def shuffle_within_words(U: np.ndarray, L: np.ndarray, rng) -> np.ndarray:
    n, Lm = U.shape
    keys = rng.random((n, Lm))
    valid = np.arange(Lm)[None, :] < L[:, None]
    keys = np.where(valid, keys, 2.0)
    return np.take_along_axis(U, np.argsort(keys, axis=1), axis=1)


# ------------------------------------------------------------------------------------------------
# the cross-fitted evaluation of one map on one text
# ------------------------------------------------------------------------------------------------


class Evaluator:
    """Caches the training statistics (per fold) and the shuffled test matrices so that many maps share them."""

    def __init__(self, t: Text, n_shuf: int, n_rand: int, seed: int = 0, slot_grammar: bool = True):
        self.t, self.n_shuf, self.n_rand = t, n_shuf, n_rand
        self.rng = np.random.default_rng(seed)
        self.st = {}
        self.test = {}
        self.shuf = {}
        for f in (0, 1):
            tr = t.fold != f
            te = t.fold == f
            self.st[f] = unit_stats(t, tr, slot_grammar=slot_grammar, seed=seed)
            self.test[f] = (t.U[te], t.L[te])
            Ut, Lt = self.test[f]
            self.shuf[f] = [shuffle_within_words(Ut, Lt, self.rng) for _ in range(n_shuf)]
        self.st_all = unit_stats(t, np.ones(len(t.L), bool), slot_grammar=slot_grammar, seed=seed)

    def map_all(self, name):
        return build_map(name, self.st_all, self.t.inv)

    def evaluate(self, name: str, want_words: bool = False, seed: int = 0) -> dict:
        t = self.t
        rng = np.random.default_rng(abs(hash((t.name, t.tok, name, seed))) % (2 ** 32))
        obs = {s: [] for s in STAT_NAMES}
        shuf = {s: [[] for _ in range(self.n_shuf)] for s in STAT_NAMES}
        rnd = {s: [[] for _ in range(self.n_rand)] for s in STAT_NAMES}
        words = {}
        for f in (0, 1):
            pv = build_map(name, self.st[f], t.inv)
            Ut, Lt = self.test[f]
            o = contour_stats(pv, Ut, Lt, want_words=want_words)
            for s in STAT_NAMES:
                obs[s].append(o[s])
            if want_words:
                words[f] = {k: v for k, v in o.items() if k.startswith("_")}
            for r in range(self.n_shuf):
                x = contour_stats(pv, self.shuf[f][r], Lt)
                for s in STAT_NAMES:
                    shuf[s][r].append(x[s])
            for r in range(self.n_rand):
                x = contour_stats(rng.permutation(pv), Ut, Lt)
                for s in STAT_NAMES:
                    rnd[s][r].append(x[s])
        def nm(v):
            v = np.asarray(v, float)
            v = v[~np.isnan(v)]
            return float(v.mean()) if v.size else float("nan")
        res = {"obs": {s: nm(obs[s]) for s in STAT_NAMES},
               "shuf": {s: np.array([nm(v) for v in shuf[s]]) for s in STAT_NAMES},
               "rand": {s: np.array([nm(v) for v in rnd[s]]) for s in STAT_NAMES}}
        # in-sample (map fitted on all words, evaluated on all words)
        pv = build_map(name, self.st_all, t.inv)
        ins = contour_stats(pv, t.U, t.L)
        res["insample"] = {s: float(ins[s]) for s in STAT_NAMES}
        res["n_unique_pitches"] = int(len(np.unique(np.round(pv, 3))))
        if want_words:
            res["words"] = words
        return res


def summarise_eval(res: dict) -> list[dict]:
    rows = []
    for s in STAT_NAMES:
        o = res["obs"][s]
        a, b = res["shuf"][s], res["rand"][s]
        a, b = a[~np.isnan(a)], b[~np.isnan(b)]
        row = {"stat": s, "obs": o, "insample_obs": res["insample"][s]}
        for nm, arr in (("shuf", a), ("rand", b)):
            if arr.size >= 2 and arr.std(ddof=1) > 0:
                z = (o - arr.mean()) / arr.std(ddof=1)
            else:
                z = float("nan")
            d = STAT_DIR[s]
            if arr.size:
                p = (1 + (arr >= o - 1e-12).sum()) / (1 + arr.size) if d >= 0 else (1 + (arr <= o + 1e-12).sum()) / (1 + arr.size)
            else:
                p = float("nan")
            row.update({f"{nm}_mean": float(arr.mean()) if arr.size else float("nan"), f"{nm}_sd": float(arr.std(ddof=1)) if arr.size > 1 else float("nan"),
                        f"z_{nm}": float(z), f"p_{nm}_regular": float(p)})
        rows.append(row)
    return rows


# ------------------------------------------------------------------------------------------------
# section / Currier tests (MS 408 only)
# ------------------------------------------------------------------------------------------------


def fold_stat_by_folio(t: Text, words: dict, key: str) -> np.ndarray:
    """Per-folio mean of a per-word held-out statistic (word values come from the map fitted on the OTHER fold)."""
    nf = len(t.folio_names)
    num = np.zeros(nf)
    den = np.zeros(nf)
    for f in (0, 1):
        te = t.fold == f
        v = words[f][key]
        fo = t.folio[te]
        ok = ~np.isnan(v)
        num += np.bincount(fo[ok], weights=v[ok], minlength=nf)
        den += np.bincount(fo[ok], minlength=nf)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan), den


def eta_squared(x: np.ndarray, groups: np.ndarray, w: np.ndarray | None = None) -> float:
    ok = ~np.isnan(x)
    x, g = x[ok], groups[ok]
    gm = x.mean()
    ss_t = ((x - gm) ** 2).sum()
    if ss_t == 0:
        return 0.0
    ss_b = sum(((x[g == k].mean() - gm) ** 2) * (g == k).sum() for k in np.unique(g))
    return float(ss_b / ss_t)


def perm_eta_p(x, groups, n_perm, rng):
    obs = eta_squared(x, groups)
    c = 0
    for _ in range(n_perm):
        c += eta_squared(x, rng.permutation(groups)) >= obs - 1e-12
    return obs, (1 + c) / (1 + n_perm)


def ab_effect(x, lang, n_perm, rng):
    """Standardised A-vs-B difference of per-folio values and its permutation p (two-sided); folios with language ? are excluded."""
    ok = (~np.isnan(x)) & np.isin(lang, ["A", "B"])
    xv, lv = x[ok], lang[ok]

    def d(lab):
        a, b = xv[lab == "A"], xv[lab == "B"]
        sp = math.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
        return (a.mean() - b.mean()) / sp if sp > 0 else 0.0
    obs = d(lv)
    c = sum(abs(d(rng.permutation(lv))) >= abs(obs) - 1e-12 for _ in range(n_perm))
    return obs, (1 + c) / (1 + n_perm)


def light_word_stats(pv: np.ndarray, U: np.ndarray, L: np.ndarray) -> dict:
    """Per-word mean pitch (cents), mean |interval| (semitones) and monotone flag only (cheap; used for the section tests and their null)."""
    pc = 1200.0 * np.log2(np.asarray(pv, float) / F0)
    ext = np.append(pc, 0.0)
    U = U.astype(np.int64)
    L = L.astype(np.int64)
    P = ext[U]
    n, Lm = U.shape
    valid = np.arange(Lm)[None, :] < L[:, None]
    j = np.arange(Lm - 1)[None, :]
    vs = j < (L[:, None] - 1)
    D = P[:, 1:] - P[:, :-1]
    S = np.where(np.abs(D) < 1e-6, 0, np.sign(D))
    S = np.where(vs, S, 0)
    mono = ((S == 1).sum(1) == 0) | ((S == -1).sum(1) == 0)
    return {"meanP": np.where(valid, P, 0).sum(1) / np.maximum(L, 1),
            "mai": np.where(L >= 2, np.where(vs, np.abs(D) / 100.0, 0).sum(1) / np.maximum(L - 1, 1), np.nan),
            "mono": np.where(L >= 3, mono.astype(float), np.nan)}


def folio_means(t: Text, per_fold_words: dict, key: str):
    nf = len(t.folio_names)
    num = np.zeros(nf)
    den = np.zeros(nf)
    for f in (0, 1):
        te = t.fold == f
        v = per_fold_words[f][key]
        fo = t.folio[te]
        ok = ~np.isnan(v)
        num += np.bincount(fo[ok], weights=v[ok], minlength=nf)
        den += np.bincount(fo[ok], minlength=nf)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)
