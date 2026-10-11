"""Library for hypothesis h03: pitch tied to slot index in a slot grammar, words as slot paths ("chords"), and a 'slot = syllable position' test.

Honesty note. A slot grammar assigns the units of a word to strictly increasing slots, so a pitch that rises with slot index makes every
covered word a strictly rising contour BY DEFINITION. That monotonicity carries no information. What can carry information is (i) how
many held-out words the grammar covers at all, (ii) which slot patterns occur and how they behave (vocabulary, neighbours, line position,
section/hand), and (iii) whether the slots behave like consonant/vowel (syllable-like) positions. Those are tested here with held-out
data and controls, never with the tautological contour statistic.
"""
from __future__ import annotations

import itertools
import math
import random
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h01_tone_sheet"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h02_full_tone_map"))

import h01_lib as H1  # noqa: E402
import h02_lib as H2  # noqa: E402
from msdecipher import mech_grammars as G  # noqa: E402
from msdecipher import stats as MS  # noqa: E402
from msdecipher.segment import Segmenter, PRESETS  # noqa: E402
from msdecipher.slot_grammar import SlotGrammar  # noqa: E402

TR = ROOT / "data" / "transcriptions"
K = 12
F0 = H2.F0
SHEET = H2.SHEET
SHEET_UNITS = H2.SHEET_UNITS
SLOT_CENTS = H2.RANGE_CENTS / (K - 1)         # 143.4 cents per slot: 12 slots span the sheet's 174-433 Hz
EVA_FAMILIES = ("ms408", "generator_eva", "naibbe", "selfcite")
SEG_EVA = Segmenter(PRESETS["collapsed"], name="collapsed")


# ------------------------------------------------------------------------------------------------ corpora

@dataclass
class Corpus:
    name: str
    family: str
    words: list[str]
    line_id: np.ndarray               # line index per word
    line_pos: np.ndarray              # position in line
    line_len: np.ndarray              # length of the word's line
    fold: np.ndarray                  # cross-fitting fold (0/1)
    block: np.ndarray                 # bootstrap block id (folio for MS, 500-word block otherwise)
    folio: np.ndarray | None = None
    folio_names: list = field(default_factory=list)
    folio_section: list = field(default_factory=list)
    folio_language: list = field(default_factory=list)
    has_lines: bool = True

    @property
    def eva_like(self) -> bool:
        return self.family in EVA_FAMILIES


def _from_lines(name, family, lines, has_lines=True, folio=None, meta=None):
    words, lid, lpos, llen, fol = [], [], [], [], []
    for li, ln in enumerate(lines):
        for j, w in enumerate(ln):
            words.append(w)
            lid.append(li)
            lpos.append(j)
            llen.append(len(ln))
            fol.append(-1 if folio is None else folio[li])
    n = len(words)
    idx = np.arange(n)
    if folio is not None:
        fol = np.array(fol)
        fold = fol % 2
        block = fol
    else:
        fol = None
        fold = (idx // 500) % 2
        block = idx // 500
    c = Corpus(name, family, words, np.array(lid), np.array(lpos), np.array(llen), fold, block, fol, has_lines=has_lines)
    if meta:
        c.folio_names, c.folio_section, c.folio_language = meta
    return c


def ms_corpus(path: Path | None = None) -> Corpus:
    folios = H1.load_folios(path or TR / "ZL3b-n.txt", "P")
    lines, fo = [], []
    for fi, f in enumerate(folios):
        for ln in f.lines:
            if ln:
                lines.append(ln)
                fo.append(fi)
    return _from_lines("MS408", "ms408", lines, True, fo, ([f.folio for f in folios], [f.section for f in folios], [f.language for f in folios]))


def tokens_corpus(name, family, tokens, pseudo_len=8):
    lines = [tokens[i:i + pseudo_len] for i in range(0, len(tokens), pseudo_len)]
    return _from_lines(name, family, lines, has_lines=False)


def selfcite_corpus(tag, seed, n=35000):
    path = ROOT / "data" / "mechanisms" / "selfcitation" / f"{tag}_s{seed}.txt"
    lines, tot = [], 0
    for l in open(path, encoding="utf-8"):
        ws = l.split()
        if ws:
            lines.append(ws)
            tot += len(ws)
        if tot >= n:
            break
    return _from_lines(f"selfcite_{tag}_s{seed}", "selfcite", lines, True)


# ------------------------------------------------------------------------------------------------ slot grammar fits and decoding

def segment_words(words: list[str], kind: str, eva_like: bool) -> list[tuple | None]:
    if kind == "zattera":
        return [G.zattera_segment(w) for w in words]
    if eva_like:
        return [tuple(SEG_EVA(w)) for w in words]
    return [tuple(w) for w in words]


class SlotFit:
    """A fitted K=12 slot grammar (learned by EM, or Zattera's hand-coded slots with EM probabilities) that can decode a word into slots."""

    def __init__(self, kind: str):
        self.kind = kind

    def fit(self, units_words: list[tuple | None], iters: int = 25, seed: int = 0):
        words = [w for w in units_words if w is not None and 0 < len(w) <= K]
        counts = Counter(words)
        if self.kind == "learned":
            sg = SlotGrammar(K=K).fit(counts, iters=iters, seed=seed)
            self._sg = sg
            P, e = sg._smoothed()
            self.units, self.idx = sg.units, sg.idx
            A = len(self.units)
            self.LP = np.log(P)                               # (K, A+1); last column = unknown unit
            self.hard = sg.allowed()[:, :A]
            self.P_raw, self.e = sg.P, np.clip(sg.e, 1e-4, 1 - 1e-4)
        else:
            m = G.SlotModel(mask=G.ZATTERA_SLOTS, order=0).fit(counts, iters=iters, seed=seed)
            self.units, self.idx = m.units, m.idx
            A = len(self.units)
            with np.errstate(divide="ignore"):
                lp = np.log(np.where(m.M, np.maximum(m.P, 1e-12), 0.0))
            self.LP = np.concatenate([lp, np.full((K, 1), -np.inf)], axis=1)
            self.hard = m.M.copy()
            self.P_raw, self.e = m.P, np.clip(m.e, 1e-4, 1 - 1e-4)
        self.le, self.l1e = np.log(self.e), np.log(1 - self.e)
        self._cache: dict = {}
        return self

    def decode_one(self, w: tuple | None):
        """Most probable strictly increasing slot path (tuple of slot indices), or None if the grammar cannot generate the word."""
        if w is None or not (0 < len(w) <= K):
            return None
        if w in self._cache:
            return self._cache[w]
        A = len(self.units)
        ids = [self.idx.get(u, A) for u in w]
        L = len(ids)
        NEG = -1e18
        f = np.full((L + 1, K + 1), NEG)
        f[0, 0] = 0.0
        bk = np.zeros((L + 1, K + 1), dtype=np.int8)
        LP = self.LP
        for k in range(K):
            for i in range(L + 1):
                best = f[i, k] + self.l1e[k]
                b = 0
                if i > 0 and f[i - 1, k] > NEG / 2:
                    lp = LP[k, ids[i - 1]]
                    if np.isfinite(lp):
                        c = f[i - 1, k] + self.le[k] + lp
                        if c > best:
                            best, b = c, 1
                f[i, k + 1] = best if f[i, k] > NEG / 2 or b == 1 else NEG
                bk[i, k + 1] = b
        if f[L, K] < NEG / 2:
            self._cache[w] = None
            return None
        slots = []
        i = L
        for k in range(K, 0, -1):
            if bk[i, k] == 1:
                slots.append(k - 1)
                i -= 1
        out = tuple(reversed(slots))
        self._cache[w] = out
        return out

    def decode(self, units_words):
        return [self.decode_one(w) for w in units_words]

    def covered_hard(self, units_words) -> np.ndarray:
        """Can the pruned (hard) grammar generate the word (increasing-slot alignment using only allowed units)?"""
        A = len(self.units)
        out = np.zeros(len(units_words), dtype=bool)
        M = np.concatenate([self.hard, np.zeros((K, 1), bool)], axis=1)
        for i, w in enumerate(units_words):
            if w is None or not (0 < len(w) <= K):
                continue
            ids = [self.idx.get(u, A) for u in w]
            reach = np.zeros(len(ids) + 1, dtype=bool)
            reach[0] = True
            for k in range(K):
                new = reach.copy()
                new[1:] |= reach[:-1] & M[k, ids]
                reach = new
            out[i] = reach[-1]
        return out


# ------------------------------------------------------------------------------------------------ pitch maps tied to slots

def slot_hz_log(slot) -> np.ndarray:
    """12 slots span the sheet's 174-433 Hz, log-spaced (143.4 cents per slot)."""
    return F0 * 2 ** (np.asarray(slot, float) * SLOT_CENTS / 1200.0)


def slot_unit_table(fit: SlotFit, units_words, paths) -> pd.DataFrame:
    """Counts of (slot, unit) over the decoded words -> per-unit slot distribution, modal slot, mean slot and Hz under three maps."""
    cnt = Counter()
    for w, p in zip(units_words, paths):
        if p is None:
            continue
        for u, s in zip(w, p):
            cnt[(u, s)] += 1
    rows = []
    per_slot = {k: Counter() for k in range(K)}
    for (u, s), c in cnt.items():
        per_slot[s][u] += c
    rank_in_slot = {}
    for s in range(K):
        for r, (u, c) in enumerate(sorted(per_slot[s].items(), key=lambda kv: (-kv[1], str(kv[0])))):
            rank_in_slot[(u, s)] = (r, len(per_slot[s]))
    byu: dict = {}
    for (u, s), c in cnt.items():
        byu.setdefault(u, {})[s] = c
    for u, d in byu.items():
        tot = sum(d.values())
        modal = max(d, key=lambda s: (d[s], -s))
        mean_slot = sum(s * c for s, c in d.items()) / tot
        r, n_k = rank_in_slot[(u, modal)]
        hz_rank = F0 * 2 ** ((modal * SLOT_CENTS + (r / max(n_k, 1)) * 0.8 * SLOT_CENTS) / 1200.0)
        rows.append({"unit": u, "count": tot, "modal_slot": modal + 1, "p_modal": d[modal] / tot, "n_slots_used": len(d),
                     "slot_distribution": ";".join(f"{s + 1}:{c / tot:.2f}" for s, c in sorted(d.items(), key=lambda kv: -kv[1])[:4]),
                     "mean_slot": mean_slot + 1, "rank_in_modal_slot": r + 1, "units_in_modal_slot": n_k,
                     "hz_slot": float(slot_hz_log(modal)), "hz_slot_rank": float(hz_rank)})
    return pd.DataFrame(rows).sort_values("count", ascending=False).reset_index(drop=True)


# ------------------------------------------------------------------------------------------------ where do the sheet's 8 values fall in slot order?

def _spearman_tie(x, y) -> float:
    rx = pd.Series(x).rank().values
    ry = pd.Series(y).rank().values
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def sheet_occurrences(units_words, paths) -> dict[str, list[tuple[int, int]]]:
    """(slot of first letter, slot of second letter), 0-based, for every decoded occurrence of each sheet digraph as two adjacent units."""
    occ = {u: [] for u in SHEET_UNITS}
    for w, p in zip(units_words, paths):
        if p is None:
            continue
        for i in range(len(w) - 1):
            d = w[i] + w[i + 1]
            if d in occ and len(w[i]) == 1 and len(w[i + 1]) == 1:
                occ[d].append((p[i], p[i + 1]))
    return occ


def sheet_slot_spearman(occ: dict, n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Spearman between the sheet's Hz and each digraph's slot position (first letter / second letter / mean of the two), with
    (i) a bootstrap CI over occurrences (uncertainty of each unit's slot estimate), (ii) a Fisher-z CI for n units,
    (iii) the exact permutation p (all assignments of the Hz values to the units that have a slot)."""
    rng = np.random.default_rng(seed)
    rows = []
    for variant, fn in (("first_letter_slot", lambda a: a[:, 0]), ("second_letter_slot", lambda a: a[:, 1]), ("mean_slot", lambda a: a.mean(1))):
        units = [u for u in SHEET_UNITS if len(occ[u]) > 0]
        arrs = {u: np.array(occ[u], float) for u in units}
        x = np.array([fn(arrs[u]).mean() + 1 for u in units])
        y = np.array([SHEET[u] for u in units])
        n = len(units)
        rho = _spearman_tie(x, y)
        # exact permutation test
        ry = pd.Series(y).rank().values
        rx = pd.Series(x).rank().values
        perms = np.array(list(itertools.permutations(range(n))))
        ryp = ry[perms]
        ryc = ryp - ryp.mean(1, keepdims=True)
        rxc = rx - rx.mean()
        with np.errstate(invalid="ignore", divide="ignore"):
            null = (ryc * rxc).sum(1) / np.sqrt((ryc ** 2).sum(1) * (rxc ** 2).sum())
        null = np.nan_to_num(null, nan=0.0)
        p1 = float((np.sum(null >= rho - 1e-12)) / len(null))
        p2 = float((np.sum(np.abs(null) >= abs(rho) - 1e-12)) / len(null))
        boots = []
        for _ in range(n_boot):
            xb = np.array([fn(arrs[u][rng.integers(0, len(arrs[u]), len(arrs[u]))]).mean() + 1 for u in units])
            r = _spearman_tie(xb, y)
            if not np.isnan(r):
                boots.append(r)
        lo, hi = np.percentile(boots, [2.5, 97.5]) if boots else (np.nan, np.nan)
        z = np.arctanh(np.clip(rho, -0.999, 0.999))
        se = 1 / math.sqrt(max(n - 3, 1))
        # linear fit of Hz on slot
        A = np.vstack([np.ones(n), x]).T
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        res = y - A @ coef
        r2 = 1 - (res ** 2).sum() / ((y - y.mean()) ** 2).sum()
        loo = []
        for k in range(n):
            m = np.arange(n) != k
            c2, *_ = np.linalg.lstsq(A[m], y[m], rcond=None)
            loo.append(y[k] - A[k] @ c2)
        rows.append({"variant": variant, "n_units": n, "units": " ".join(units), "spearman_rho": rho, "p_one_sided_perm": p1, "p_two_sided_perm": p2,
                     "boot_ci_lo": float(lo), "boot_ci_hi": float(hi), "fisher_ci_lo": float(np.tanh(z - 1.96 * se)), "fisher_ci_hi": float(np.tanh(z + 1.96 * se)),
                     "r2_linear": float(r2), "slope_hz_per_slot": float(coef[1]), "intercept_hz": float(coef[0]), "loo_rmse_hz": float(np.sqrt(np.mean(np.square(loo))))})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ pattern ("chord") vocabulary

def pattern_stats(paths: list, tokens_n: int | None = None) -> dict:
    cov = [p for p in paths if p is not None]
    c = Counter(cov)
    n = sum(c.values())
    if n == 0:
        return {"coverage": 0.0}
    freqs = np.array(sorted(c.values(), reverse=True), float)
    p = freqs / n
    cum = np.cumsum(p)
    ent = float(-(p * np.log2(p)).sum())
    nfill = np.array([len(x) for x in cov])
    span = np.array([x[-1] - x[0] + 1 for x in cov])
    return {"coverage": n / len(paths), "n_covered": n, "n_pattern_types": len(c), "types_per_1000_tokens": 1000 * len(c) / n,
            "pattern_entropy_bits": ent, "top1_share": float(p[0]), "types_for_50pct": int(np.searchsorted(cum, 0.5) + 1), "types_for_90pct": int(np.searchsorted(cum, 0.9) + 1),
            "hapax_share_of_types": float((freqs == 1).mean()), "zipf_slope_ols_r1_100": MS.zipf_ols_slope(freqs, 1, 100) if len(freqs) > 20 else float("nan"),
            "mean_slots_filled": float(nfill.mean()), "mean_skipped_inside_span": float((span - nfill).mean())}


def slot_fill_probability(paths) -> np.ndarray:
    cov = [p for p in paths if p is not None]
    f = np.zeros(K)
    for p in cov:
        f[list(p)] += 1
    return f / max(len(cov), 1)


# ------------------------------------------------------------------------------------------------ held-out predictive gain of slot patterns

def _top_classes(keys: list, n_top: int, train_mask: np.ndarray) -> dict:
    c = Counter(k for k, m in zip(keys, train_mask) if m)
    return {k: i for i, (k, _) in enumerate(c.most_common(n_top))}


def class_ids(keys: list, n_top: int, train_mask: np.ndarray, none_class=True):
    """Map keys to ids 0..n_top-1 (top classes of the training part), n_top = 'other', n_top+1 = 'uncovered' (key None)."""
    top = _top_classes([k for k in keys if k is not None] + [None] * 0, n_top, np.array([m and k is not None for k, m in zip(keys, train_mask)]))
    out = np.empty(len(keys), dtype=np.int64)
    for i, k in enumerate(keys):
        out[i] = n_top + 1 if k is None else top.get(k, n_top)
    return out


ALPHAS = (1.0, 5.0, 20.0, 80.0, 300.0)


def _gain_table(feat, y, n_f, n_y, train, alpha):
    cy = np.bincount(y[train], minlength=n_y).astype(float) + 0.5
    q = cy / cy.sum()
    C = np.zeros((n_f, n_y))
    np.add.at(C, (feat[train], y[train]), 1)
    nf = C.sum(1)
    return (C + alpha * q[None, :]) / (nf[:, None] + alpha), q


def cond_gain(feat: np.ndarray, y: np.ndarray, n_f: int, n_y: int, train: np.ndarray, test: np.ndarray):
    """Per-item held-out log2 [P(y|f)/P(y)] for items in ``test``. Tables come from ``train`` only; the smoothing strength alpha (shrinkage towards the
    training marginal) is chosen by 2-fold validation INSIDE the training items, so a high-capacity feature cannot win by luck on the test items."""
    tr_idx = np.where(train)[0]
    a_mask = np.zeros(len(feat), bool)
    a_mask[tr_idx[::2]] = True
    b_mask = train & ~a_mask
    best, best_a = -np.inf, ALPHAS[0]
    for a in ALPHAS:
        tot = 0.0
        for fit_m, val_m in ((a_mask, b_mask), (b_mask, a_mask)):
            P, q = _gain_table(feat, y, n_f, n_y, fit_m, a)
            tot += np.log2(P[feat[val_m], y[val_m]] / q[y[val_m]]).mean()
        if tot > best:
            best, best_a = tot, a
    P, q = _gain_table(feat, y, n_f, n_y, train, best_a)
    return np.log2(P[feat[test], y[test]] / q[y[test]])


def block_bootstrap(vals: dict[str, np.ndarray], blocks: np.ndarray, n_boot: int = 2000, seed: int = 0):
    """Bootstrap over blocks (folios): mean of every series and of differences are computed from block sums."""
    rng = np.random.default_rng(seed)
    ub, inv = np.unique(blocks, return_inverse=True)
    nb = len(ub)
    cnt = np.bincount(inv, minlength=nb).astype(float)
    sums = {k: np.bincount(inv, weights=v, minlength=nb) for k, v in vals.items()}
    draws = rng.integers(0, nb, size=(n_boot, nb))
    den = cnt[draws].sum(1)
    boots = {k: s[draws].sum(1) / den for k, s in sums.items()}
    return boots


def ci(b: np.ndarray):
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def build_task_features(corp: Corpus, kind: str, fold: int, seed: int = 0, n_top: int = 60):
    """Fit the grammar on the training fold (unsupervised, words only), decode every word, return per-word feature class ids."""
    words = corp.words
    uw = segment_words(words, kind, corp.eva_like)
    tr = corp.fold != fold
    fit = SlotFit(kind).fit([u for u, t in zip(uw, tr) if t], seed=seed)
    paths = fit.decode(uw)
    return fit, uw, paths, tr


def predictive_tasks(corp: Corpus, kind: str, seed: int = 0, n_boot: int = 2000, n_top: int = 60, n_perm: int = 0) -> list[dict]:
    """Held-out (2-fold, cross-fitted) predictive gain in bits per word of slot-pattern features over letter features, with block-bootstrap CIs."""
    n = len(corp.words)
    nxt = np.full(n, -1)
    same = (corp.line_id[:-1] == corp.line_id[1:])
    nxt[:-1] = np.where(same, np.arange(1, n), -1)
    gains: dict[str, list] = {}
    keep_blocks = []
    store: dict[str, np.ndarray] = {}

    def put(task, feat_name, vals, idx):
        store.setdefault((task, feat_name), np.full(n, np.nan))
        store[(task, feat_name)][idx] = vals
    cov_hold = []
    for f in (0, 1):
        fit, uw, paths, tr = build_task_features(corp, kind, f, seed)
        te = ~tr
        F_slot = class_ids(paths, n_top, tr)
        F_ll = class_ids([None if u is None or not u else (u[0], u[-1]) for u in uw], n_top, tr)
        F_word = class_ids([None if u is None else corp.words[i] for i, u in enumerate(uw)], n_top, tr)
        F_len = np.array([min(len(u), 10) if u else 0 for u in uw])
        F_last = class_ids([None if not u else u[-1] for u in uw], 30, tr)
        F_alt = class_ids([None if not u else (u[min(1, len(u) - 1)], u[max(len(u) - 2, 0)]) for u in uw], n_top, tr)          # second / second-to-last unit: a letter feature of the same capacity (every word has one)
        F_f2 = class_ids([None if not u else u[:2] for u in uw], n_top, tr)
        F_l2 = class_ids([None if not u else u[-2:] for u in uw], n_top, tr)
        F_cov = (F_slot == n_top + 1).astype(np.int64)                                                   # only: did the grammar cover the word?
        F_none = np.zeros(n, dtype=np.int64)
        joint_ll_alt = F_ll * (n_top + 2) + F_alt
        joint_last_alt = F_last * (n_top + 2) + F_alt
        joint_ll_slot = F_ll * (n_top + 2) + F_slot
        joint_last_slot = F_last * (n_top + 2) + F_slot
        feats = {"none": (F_none, 1), "slot_pattern": (F_slot, n_top + 2), "first_last_pair": (F_ll, n_top + 2), "word_identity": (F_word, n_top + 2),
                 "length": (F_len, 11), "covered_flag": (F_cov, 2), "first_two": (F_f2, n_top + 2), "last_two": (F_l2, n_top + 2), "last_unit": (F_last, 32), "second_penult_pair": (F_alt, n_top + 2),
                 "first_last+slot": (joint_ll_slot, (n_top + 2) ** 2), "first_last+second_penult": (joint_ll_alt, (n_top + 2) ** 2),
                 "last_unit+slot": (joint_last_slot, 32 * (n_top + 2)), "last_unit+second_penult": (joint_last_alt, 32 * (n_top + 2))}
        # Y1a: slot class of next word ; Y1b: first unit of next word
        has_next = nxt >= 0
        idx_tr = tr & has_next
        idx_te = te & has_next
        y1a = np.where(has_next, F_slot[np.maximum(nxt, 0)], 0)
        first_unit = class_ids([None if not u else u[0] for u in uw], 30, tr)
        y1b = np.where(has_next, first_unit[np.maximum(nxt, 0)], 0)
        for task, y, ny in (("next_word_slot_pattern", y1a, n_top + 2), ("next_word_first_unit", y1b, 32)):
            for fn, (ft, nf_) in feats.items():
                g = cond_gain(ft, y, nf_, ny, idx_tr, idx_te)
                put(task, fn, g, np.where(idx_te)[0])
        # Y2: line position (first / middle / last word of a line with >= 3 words)
        if corp.has_lines:
            ok = corp.line_len >= 3
            y2 = np.where(corp.line_pos == 0, 0, np.where(corp.line_pos == corp.line_len - 1, 2, 1))
            for fn, (ft, nf_) in feats.items():
                if fn in ("last_unit", "last_unit+slot", "last_unit+second_penult"):
                    continue
                g = cond_gain(ft, y2, nf_, 3, tr & ok, te & ok)
                put("line_position", fn, g, np.where(te & ok)[0])
        if corp.folio is not None:
            lang = np.array([corp.folio_language[i] for i in corp.folio])
            sec = np.array([corp.folio_section[i] for i in corp.folio])
            okl = np.isin(lang, ["A", "B"])
            y3 = (lang == "B").astype(np.int64)
            secs = sorted(set(sec))
            y4 = np.array([secs.index(s) for s in sec])
            for task, y, ny, ok in (("currier_language_AB", y3, 2, okl), ("illustration_section", y4, len(secs), np.ones(n, bool))):
                for fn, (ft, nf_) in feats.items():
                    if fn in ("last_unit", "last_unit+slot", "last_unit+second_penult"):
                        continue
                    g = cond_gain(ft, y, nf_, ny, tr & ok, te & ok)
                    put(task, fn, g, np.where(te & ok)[0])
        cov_hold.append(np.mean([p is not None for p, t in zip(paths, te) if t]))
    rows = []
    tasks = sorted({t for t, _ in store})
    for task in tasks:
        names = [fn for (t, fn) in store if t == task]
        ok = ~np.isnan(store[(task, names[0])])
        vals = {fn: store[(task, fn)][ok] for fn in names}
        blocks = corp.block[ok]
        b = block_bootstrap(vals, blocks, n_boot, seed)
        pairs = [("slot_pattern", "first_last_pair"), ("slot_pattern", "second_penult_pair"), ("slot_pattern", "covered_flag"), ("first_last+slot", "first_last_pair"),
                 ("first_last+second_penult", "first_last_pair"), ("first_last+slot", "first_last+second_penult"), ("slot_pattern", "length")]
        if task == "next_word_first_unit":
            pairs = [("last_unit+slot", "last_unit"), ("last_unit+second_penult", "last_unit"), ("last_unit+slot", "last_unit+second_penult"), ("slot_pattern", "last_unit")]
        for fn in names:
            rows.append({"corpus": corp.name, "grammar": kind, "task": task, "feature": fn, "n_items": int(ok.sum()), "gain_bits_per_word": float(vals[fn].mean()),
                         "ci_lo": ci(b[fn])[0], "ci_hi": ci(b[fn])[1]})
        letter_feats = [f for f in ("first_last_pair", "second_penult_pair", "first_two", "last_two") if f in vals]
        if letter_feats and task != "next_word_first_unit":
            best_means = [vals[f].mean() for f in letter_feats]
            bb = np.max([b[f] for f in letter_feats], axis=0)
            d = b["slot_pattern"] - bb
            rows.append({"corpus": corp.name, "grammar": kind, "task": task, "feature": "best_letter_feature(max of 4)", "n_items": int(ok.sum()),
                         "gain_bits_per_word": float(max(best_means)), "ci_lo": ci(bb)[0], "ci_hi": ci(bb)[1]})
            rows.append({"corpus": corp.name, "grammar": kind, "task": task, "feature": "DIFF slot_pattern - best_letter_feature(max of 4)", "n_items": int(ok.sum()),
                         "gain_bits_per_word": float(vals["slot_pattern"].mean() - max(best_means)), "ci_lo": ci(d)[0], "ci_hi": ci(d)[1]})
        for a, c in pairs:
            if a in vals and c in vals:
                d = b[a] - b[c]
                rows.append({"corpus": corp.name, "grammar": kind, "task": task, "feature": f"DIFF {a} - {c}", "n_items": int(ok.sum()),
                             "gain_bits_per_word": float(vals[a].mean() - vals[c].mean()), "ci_lo": ci(d)[0], "ci_hi": ci(d)[1]})
    return rows


# ------------------------------------------------------------------------------------------------ syllable-like (CV) analysis

MIN_UNIT = 30


def frequent_only(units_words, min_count: int = MIN_UNIT):
    """Words made only of units that occur >= min_count times (the rest become None): rare units cannot be classified reliably."""
    cnt = Counter(u for w in units_words if w for u in w)
    return [w if (w and all(cnt[u] >= min_count for u in w)) else None for w in units_words]


def vowel_classes(units_words: list[tuple]) -> tuple[set, dict]:
    words = [w for w in units_words if w]
    vowels, _ = MS.sukhotin(words, min_count=MIN_UNIT)
    return set(vowels), Counter(u for w in words for u in w)


def cv_strings(units_words, vowels: set) -> list[str]:
    return ["".join("V" if u in vowels else "C" for u in w) for w in units_words if w]


def runs(s: str):
    out, i = [], 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        out.append((s[i], j - i))
        i = j
    return out


def cv_stats(units_words: list[tuple], vowels: set, rng, n_shuf: int = 20) -> dict:
    """Consonant/vowel-like structure of words under a Sukhotin split: switch rate (CV alternation) against letters shuffled inside words,
    nuclei (vowel-like runs) per word and their dependence on length, share of words with no vowel-like unit, longest consonant-like run."""
    ws = [w for w in units_words if w]
    cv = cv_strings(ws, vowels)

    def switch_rate(strings):
        sw = tot = 0
        for s in strings:
            for a, b in zip(s, s[1:]):
                sw += a != b
                tot += 1
        return sw / max(tot, 1)
    obs = switch_rate(cv)
    nulls = []
    for _ in range(n_shuf):
        sh = []
        for s in cv:
            l = list(s)
            rng.shuffle(l)
            sh.append("".join(l))
        nulls.append(switch_rate(sh))
    nuc = np.array([sum(1 for ch, ln in runs(s) if ch == "V") for s in cv])
    ln = np.array([len(s) for s in cv])
    maxc = np.array([max([l for ch, l in runs(s) if ch == "C"] or [0]) for s in cv])
    maxv = np.array([max([l for ch, l in runs(s) if ch == "V"] or [0]) for s in cv])
    m = ln >= 2
    slope = float(np.polyfit(ln[m], nuc[m], 1)[0]) if m.sum() > 10 else float("nan")
    parsable = (nuc >= 1) & (maxc <= 2) & (maxv <= 2)
    return {"vowel_like_units": " ".join(sorted(vowels)), "vowel_like_token_share": float(np.mean([u in vowels for w in ws for u in w])),
            "cv_switch_rate": obs, "cv_switch_rate_shuffled": float(np.mean(nulls)), "cv_switch_z": float((obs - np.mean(nulls)) / (np.std(nulls, ddof=1) + 1e-12)),
            "cv_switch_excess": float(obs - np.mean(nulls)),
            "mean_nuclei_per_word": float(nuc.mean()), "nuclei_per_extra_unit_slope": slope, "share_words_no_vowel": float((nuc == 0).mean()),
            "share_words_one_nucleus": float((nuc == 1).mean()), "mean_longest_consonant_run": float(maxc.mean()), "share_cc_cluster_gt2": float((maxc > 2).mean()),
            "share_syllable_parsable_C<=2,V<=2": float(parsable.mean()), "mean_word_len_units": float(ln.mean())}


def slot_cv_profile(fit_units_words, paths, vowels: set) -> pd.DataFrame:
    """Vowel-like share of the units sitting in each slot, and the slot's fill probability."""
    num = np.zeros(K)
    den = np.zeros(K)
    for w, p in zip(fit_units_words, paths):
        if p is None:
            continue
        for u, s in zip(w, p):
            den[s] += 1
            num[s] += u in vowels
    return pd.DataFrame({"slot": np.arange(1, K + 1), "n": den, "vowel_like_share": np.where(den > 0, num / np.maximum(den, 1), np.nan)})


def slot_segregation(units_words, paths, vowels: set, rng, n_perm: int = 200) -> dict:
    """Do slots separate vowel-like from consonant-like units? Index = weighted mean |share_k - overall share| / max possible, against permuting the
    vowel-like label across unit TYPES (keeping the number of vowel-like units): a syllable-position reading predicts slots that are mostly V or mostly C."""
    pairs = [(u, s) for w, p in zip(units_words, paths) if p is not None for u, s in zip(w, p)]
    units = sorted({u for u, _ in pairs}, key=str)
    uid = {u: i for i, u in enumerate(units)}
    U = np.array([uid[u] for u, _ in pairs])
    S = np.array([s for _, s in pairs])
    n_v = sum(1 for u in units if u in vowels)

    def index(vmask):
        isv = vmask[U]
        shares = np.array([isv[S == k].mean() if (S == k).sum() else np.nan for k in range(K)])
        w = np.bincount(S, minlength=K) / len(S)
        base = isv.mean()
        ok = ~np.isnan(shares)
        return float((w[ok] * np.abs(shares[ok] - base)).sum() / (2 * base * (1 - base) + 1e-12))
    vm = np.array([u in vowels for u in units])
    obs = index(vm)
    null = []
    for _ in range(n_perm):
        pm = np.zeros(len(units), bool)
        pm[rng.choice(len(units), n_v, replace=False)] = True
        null.append(index(pm))
    null = np.array(null)
    return {"segregation_index": obs, "null_mean": float(null.mean()), "null_p95": float(np.percentile(null, 95)), "p_perm": float((1 + (null >= obs).sum()) / (1 + len(null)))}


# ------------------------------------------------------------------------------------------------ held-out overview, syllable overview, label-permutation null

def heldout_overview(corp: Corpus, kind: str, seed: int = 0, shuffle_letters: bool = False) -> dict:
    """2-fold cross-fit: hard coverage of held-out words, bits per word of the slot grammar vs a unit-bigram model (learned grammar),
    and the pattern vocabulary of the held-out words."""
    uw = segment_words(corp.words, kind, corp.eva_like)
    if shuffle_letters:
        rng = random.Random(seed)
        uw = [None if u is None else tuple(rng.sample(list(u), len(u))) for u in uw]
    cov, bits_s, bits_b, all_paths, fills = [], [], [], [], []
    for f in (0, 1):
        tr = corp.fold != f
        te = ~tr
        fit = SlotFit(kind).fit([u for u, t in zip(uw, tr) if t], seed=seed)
        test_words = [u for u, t in zip(uw, te) if t]
        cov.append(fit.covered_hard(test_words).mean())
        paths = fit.decode(test_words)
        all_paths += paths
        if kind == "learned":
            from msdecipher.slot_grammar import UnitNgram
            bg = UnitNgram(1).fit(Counter(u for u, t in zip(uw, tr) if t and u))
            tw = [w for w in test_words if w and len(w) <= K]
            a = fit._sg.logprob2(tw)
            b = bg.logprob2(tw)
            ok = np.isfinite(a) & np.isfinite(b)
            bits_s.append(-a[ok].mean())
            bits_b.append(-b[ok].mean())
    out = {"corpus": corp.name + ("_letters_shuffled" if shuffle_letters else ""), "grammar": kind, "hard_coverage_heldout": float(np.mean(cov))}
    if bits_s:
        out["bits_per_word_slot12"] = float(np.mean(bits_s))
        out["bits_per_word_unit_bigram"] = float(np.mean(bits_b))
    out.update(pattern_stats(all_paths))
    return out, slot_fill_probability(all_paths), Counter(p for p in all_paths if p is not None)


def syllable_overview(corp: Corpus, kind: str, seed: int = 0, n_perm: int = 200):
    """Whole-corpus descriptive CV analysis: Sukhotin classes on the units, word-level CV statistics, per-slot vowel-like share and its
    segregation index against permuting the vowel-like label over unit types."""
    rng = random.Random(seed)
    rng_np = np.random.default_rng(seed)
    uw = frequent_only(segment_words(corp.words, kind, corp.eva_like))
    valid = [u for u in uw if u]
    vowels, _ = vowel_classes(valid)
    cs = cv_stats(valid, vowels, rng)
    fit = SlotFit(kind).fit(uw, seed=seed)
    paths = fit.decode(uw)
    prof = slot_cv_profile(uw, paths, vowels)
    seg = slot_segregation(uw, paths, vowels, rng_np, n_perm)
    row = {"corpus": corp.name, "grammar": kind, **cs, **{f"slot_{k}": v for k, v in seg.items()}}
    prof.insert(0, "corpus", corp.name)
    prof.insert(1, "grammar", kind)
    return row, prof, fit, uw, paths, vowels


def label_perm_null(corp: Corpus, kind: str, n_perm: int = 40, seed: int = 0) -> pd.DataFrame:
    """Permute the section / Currier labels across folios and recompute the held-out gain DIFFs (slot pattern vs first/last letters)."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_perm):
        c = Corpus(**{**corp.__dict__})
        perm = rng.permutation(len(corp.folio_names))
        c.folio_section = [corp.folio_section[j] for j in perm]
        c.folio_language = [corp.folio_language[j] for j in perm]
        for r in predictive_tasks(c, kind, seed=seed, n_boot=5):
            if r["task"] in ("currier_language_AB", "illustration_section") and r["feature"].startswith("DIFF"):
                rows.append({"perm": i, **{k: r[k] for k in ("task", "feature", "gain_bits_per_word")}})
            if r["task"] in ("currier_language_AB", "illustration_section") and r["feature"] in ("slot_pattern", "first_last_pair"):
                rows.append({"perm": i, **{k: r[k] for k in ("task", "feature", "gain_bits_per_word")}})
    return pd.DataFrame(rows)
