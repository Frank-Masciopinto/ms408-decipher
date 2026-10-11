"""Library for hypothesis h01: the 'Voynich Manuscript Codex Translation Sheet' (tone/glyph/meaning table).

Nothing here assumes the sheet is right or wrong. Every claim on the sheet is turned into a measurable
prediction and compared with a null (within-word letter shuffle, folio-label permutation, frequency-matched
random digraphs, control texts). The sheet's own table is in table.csv / table.json; the operationalisation of
its 'meaning' column into illustration-section predictions is in predictions.csv (written before the section
enrichment was computed).
"""
from __future__ import annotations

import itertools
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from msdecipher.ivtff import parse_file, words_of, readable  # noqa: E402
from msdecipher.segment import Segmenter  # noqa: E402

# ------------------------------------------------------------------------------------------------
# the sheet
# ------------------------------------------------------------------------------------------------


def load_table() -> pd.DataFrame:
    return pd.read_csv(HERE / "table.csv")


def load_predictions() -> pd.DataFrame:
    df = pd.read_csv(HERE / "predictions.csv", comment="#").fillna("")
    return df


def sheet_units() -> list[str]:
    return list(load_table()["glyph"])


# ------------------------------------------------------------------------------------------------
# corpus view
# ------------------------------------------------------------------------------------------------


@dataclass
class Folio:
    folio: str
    section: str
    language: str
    lines: list[list[str]]          # readable tokens per line

    @property
    def tokens(self) -> list[str]:
        return [w for ln in self.lines for w in ln]


def load_folios(path: str | Path, generic: str = "P") -> list[Folio]:
    c = parse_file(path)
    by: dict[str, dict] = {}
    for lc in c.select(generic=generic):
        words = [w for w in words_of(lc, "split") if readable(w) and w]
        if not words:
            continue
        d = by.setdefault(lc.folio, {"lines": [], "sec": lc.section or "?", "lang": Counter()})
        d["lines"].append(words)
        d["lang"][lc.language or "?"] += len(words)
    out = []
    for f, d in by.items():
        out.append(Folio(f, d["sec"], d["lang"].most_common(1)[0][0], d["lines"]))
    return out


def all_tokens(folios: list[Folio]) -> list[str]:
    return [w for f in folios for w in f.tokens]


# ------------------------------------------------------------------------------------------------
# tones
# ------------------------------------------------------------------------------------------------


def cents(f, f0):
    return 1200.0 * np.log2(np.asarray(f, float) / f0)


def grid_rms(tones, f0, step: float = 100.0) -> float:
    """RMS deviation (cents) of ``tones`` from the nearest point of an equal grid of ``step`` cents anchored at f0."""
    c = cents(tones, f0)
    d = (c + step / 2) % step - step / 2
    return float(np.sqrt(np.mean(d ** 2)))


def best_grid_fit(tones, step: float = 100.0, resolution: float = 1.0):
    """Free reference pitch: min over anchors in one grid step of the RMS deviation. Returns (rms, f0, max_abs_dev)."""
    t = np.asarray(tones, float)
    anchors = np.arange(0.0, step, resolution)
    c = 1200.0 * np.log2(t)[None, :] - anchors[:, None]
    d = (c + step / 2) % step - step / 2
    rms = np.sqrt((d ** 2).mean(axis=1))
    i = int(rms.argmin())
    f0 = float(2 ** (anchors[i] / 1200.0))
    return float(rms[i]), f0, float(np.abs(d[i]).max())


JI_MAJOR = np.array([0, 203.91, 386.31, 498.04, 701.96, 884.36, 1088.27])
JI_CHROM = np.array([0, 111.73, 203.91, 315.64, 386.31, 498.04, 590.22, 701.96, 813.69, 884.36, 996.09, 1088.27])
TET_MAJOR = np.array([0, 200, 400, 500, 700, 900, 1100], float)


def _fit_pitchclass_set(tones, allowed, resolution: float = 2.0):
    """Min over tonic of RMS (cents) distance of each tone's octave-reduced pitch class to the nearest allowed class."""
    t = np.asarray(tones, float)
    allowed = np.asarray(allowed, float)
    tonics = np.arange(0.0, 1200.0, resolution)
    c = (1200.0 * np.log2(t)[None, :] - tonics[:, None]) % 1200.0          # (T, n)
    diff = np.abs(c[:, :, None] - allowed[None, None, :])
    diff = np.minimum(diff, 1200.0 - diff)
    m = diff.min(axis=2)
    rms = np.sqrt((m ** 2).mean(axis=1))
    i = int(rms.argmin())
    return float(rms[i]), float(2 ** (tonics[i] / 1200.0))


def linear_rank_fit(tones) -> dict:
    """Arithmetic progression test: sort tones, fit f = a + b*k by least squares. Returns r2, rms (Hz)."""
    t = np.sort(np.asarray(tones, float))
    k = np.arange(len(t), dtype=float)
    A = np.vstack([np.ones_like(k), k]).T
    coef, *_ = np.linalg.lstsq(A, t, rcond=None)
    res = t - A @ coef
    r2 = 1 - (res ** 2).sum() / ((t - t.mean()) ** 2).sum()
    return {"intercept": float(coef[0]), "step_hz": float(coef[1]), "r2": float(r2), "rms_hz": float(np.sqrt((res ** 2).mean()))}


def scale_models(tones, fast: bool = False) -> dict[str, float]:
    """Best-fit RMS (cents) of the tone set to several scale models (lower = better fit). Free reference pitch
    / tonic for every model, so all models have comparable freedom."""
    res = 2.0 if fast else 1.0
    out = {
        "12-TET chromatic (free ref)": best_grid_fit(tones, 100.0, res)[0],
        "whole-tone 6-TET (free ref)": best_grid_fit(tones, 200.0, res)[0],
        "quarter-tone 24-TET (free ref)": best_grid_fit(tones, 50.0, res)[0],
        "12-TET major scale (free tonic)": _fit_pitchclass_set(tones, TET_MAJOR, 2.0 if fast else 1.0)[0],
        "5-limit JI diatonic (free tonic)": _fit_pitchclass_set(tones, JI_MAJOR, 2.0 if fast else 1.0)[0],
        "5-limit JI chromatic (free tonic)": _fit_pitchclass_set(tones, JI_CHROM, 2.0 if fast else 1.0)[0],
    }
    return out


def fixed_reference_rms(tones) -> dict[str, float]:
    return {"12-TET, A4=440": grid_rms(tones, 440.0, 100.0),
            "12-TET, A4=432": grid_rms(tones, 432.0, 100.0)}


def nearest_12tet(f, a4: float = 440.0) -> tuple[str, float]:
    names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    n = 12 * math.log2(f / a4)
    k = round(n)
    midi = 69 + k
    name = f"{names[midi % 12]}{midi // 12 - 1}"
    return name, float((n - k) * 100.0)


def tone_null(tones, n_sets: int = 20000, seed: int = 7, mode: str = "log") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Monte-Carlo null: n_sets random 8-tone sets in [min, max] of the sheet (log-uniform or linear-uniform), each fitted
    with the same free-parameter models. Returns (null RMS per model, summary with the sheet's value and one-sided p)."""
    rng = np.random.default_rng(seed)
    t = np.asarray(tones, float)
    lo, hi, n = t.min(), t.max(), len(t)
    rows = []
    for _ in range(n_sets):
        if mode == "log":
            s = np.exp(rng.uniform(math.log(lo), math.log(hi), n))
        else:
            s = rng.uniform(lo, hi, n)
        d = scale_models(s, fast=True)
        d["arithmetic progression in Hz (1 - R^2)"] = 1 - linear_rank_fit(s)["r2"]
        rows.append(d)
    null = pd.DataFrame(rows)
    obs = scale_models(t, fast=True)
    obs["arithmetic progression in Hz (1 - R^2)"] = 1 - linear_rank_fit(t)["r2"]
    summ = []
    for m in null.columns:
        p = (1 + (null[m] <= obs[m]).sum()) / (1 + len(null))
        summ.append({"model": m, "sheet_value": obs[m], "null_median": float(null[m].median()),
                     "null_p05": float(null[m].quantile(0.05)), "p_null_as_good": float(p), "mode": mode})
    return null, pd.DataFrame(summ)


def kendall_inversions_p(order_ranks: list[int]) -> tuple[int, float]:
    """Number of inversions of the printed order vs Hz order, and exact P(inversions <= observed) under a random permutation
    (Mahonian numbers)."""
    inv = sum(1 for i in range(len(order_ranks)) for j in range(i + 1, len(order_ranks)) if order_ranks[i] > order_ranks[j])
    n = len(order_ranks)
    dp = [1]
    for m in range(1, n + 1):
        new = [0] * (len(dp) + m - 1)
        for k, v in enumerate(dp):
            for j in range(m):
                new[k + j] += v
        dp = new
    return inv, sum(dp[: inv + 1]) / math.factorial(n)


# ------------------------------------------------------------------------------------------------
# unit existence / coverage
# ------------------------------------------------------------------------------------------------


def tilings(word: str, units: list[str]) -> tuple[int, int]:
    """(max number of characters of ``word`` covered by non-overlapping unit occurrences, number of complete tilings)."""
    n = len(word)
    cover = [0] * (n + 1)
    ways = [0] * (n + 1)
    ways[0] = 1
    for i in range(1, n + 1):
        cover[i] = cover[i - 1]
        for u in units:
            L = len(u)
            if i >= L and word[i - L:i] == u:
                cover[i] = max(cover[i], cover[i - L] + L)
                ways[i] += ways[i - L]
    return cover[n], ways[n]


def coverage_stats(tokens: list[str], units: list[str]) -> dict:
    types = Counter(tokens)
    n_tok = len(tokens)
    chars = sum(len(w) for w in tokens)
    covered = 0
    full = 0
    contain = 0
    amb = 0
    full_types = 0
    contain_types = 0
    for w, c in types.items():
        cov, ways = tilings(w, units)
        covered += cov * c
        if cov == len(w):
            full += c
            full_types += 1
            if ways > 1:
                amb += c
        if any(u in w for u in units):
            contain += c
            contain_types += 1
    return {"n_tokens": n_tok, "n_types": len(types), "chars": chars,
            "char_cov": covered / chars, "tokens_fully_tileable": full / n_tok, "types_fully_tileable": full_types / len(types),
            "n_types_fully_tileable": full_types, "tokens_containing_a_unit": contain / n_tok,
            "types_containing_a_unit": contain_types / len(types), "ambiguous_tilings_share_of_full": (amb / full) if full else 0.0}


def fully_tileable_words(tokens, units) -> pd.DataFrame:
    rows = []
    for w, c in Counter(tokens).most_common():
        cov, ways = tilings(w, units)
        if cov == len(w):
            rows.append({"word": w, "count": c, "n_tilings": ways})
    return pd.DataFrame(rows)


def line_coverage(folios: list[Folio], units: list[str]) -> dict:
    n = full = full_multi = 0
    for f in folios:
        for ln in f.lines:
            n += 1
            ok = all(tilings(w, units)[0] == len(w) for w in ln)
            full += ok
            full_multi += ok and len(ln) >= 2
    return {"n_lines": n, "lines_fully_tileable": full, "lines_fully_tileable_multiword": full_multi}


def unit_cum_coverage(tokens: list[str], preset: str = "collapsed") -> pd.DataFrame:
    seg = Segmenter.preset(preset)
    cnt = Counter(u for w in tokens for u in seg(w))
    tot = sum(cnt.values())
    rows, cum = [], 0
    for k, (u, c) in enumerate(cnt.most_common(), 1):
        cum += c
        rows.append({"rank": k, "unit": u, "count": c, "cum_share": cum / tot})
    return pd.DataFrame(rows)


def top_k_units_word_coverage(tokens: list[str], k: int = 8, preset: str = "collapsed") -> dict:
    """Reference ceiling: the k most frequent segmentation units (an *optimal-ish* 8-symbol inventory by frequency)."""
    seg = Segmenter.preset(preset)
    cnt = Counter(u for w in tokens for u in seg(w))
    top = {u for u, _ in cnt.most_common(k)}
    segs = [seg(w) for w in tokens]
    tok_full = sum(all(u in top for u in s) for s in segs) / len(segs)
    unit_share = sum(c for u, c in cnt.items() if u in top) / sum(cnt.values())
    return {"top_units": sorted(top), "unit_share": unit_share, "tokens_fully_tileable": tok_full}


# ------------------------------------------------------------------------------------------------
# bigram cohesion / position under a within-word shuffle null
# ------------------------------------------------------------------------------------------------


def pair_obs_exp(tokens: list[str], a: str, b: str) -> dict:
    """Observed count of the adjacent letter pair (a then b) inside words, the exact expected count if the letters of every word
    were shuffled (sum n_a*n_b/L, or n_a(n_a-1)/L if a==b), and the same split by position class (initial / medial / final)."""
    obs = Counter()
    exp = Counter()
    for w in tokens:
        L = len(w)
        if L < 2:
            continue
        na, nb = w.count(a), w.count(b)
        if na == 0 or nb == 0:
            continue
        pairs = na * nb if a != b else na * (na - 1)
        e = pairs / L                           # total expected adjacent a->b pairs; spread uniformly over the L-1 start slots
        slot = e / (L - 1)
        exp["all"] += e
        exp["initial"] += slot
        exp["final"] += slot
        exp["medial"] += slot * max(L - 3, 0)
        if L == 2:
            exp["initial"] -= slot            # a single slot is both initial and final: count it once, as 'whole'
            exp["final"] -= slot
            exp["whole"] += slot
    for w in tokens:
        L = len(w)
        i = w.find(a + b)
        while i != -1:
            obs["all"] += 1
            if L == 2:
                obs["whole"] += 1
            elif i == 0:
                obs["initial"] += 1
            elif i + 2 == L:
                obs["final"] += 1
            else:
                obs["medial"] += 1
            i = w.find(a + b, i + 1)
    return {"obs": dict(obs), "exp": dict(exp)}


def unit_table(tokens: list[str], units: list[str], folios: list[Folio] | None = None, n_boot: int = 500, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    letters = Counter(c for w in tokens for c in w)
    n_letters = sum(letters.values())
    # adjacent in-word pair total and unigram marginals for the pointwise-mutual-information expectation
    left, right, npairs = Counter(), Counter(), 0
    for w in tokens:
        for x, y in zip(w, w[1:]):
            left[x] += 1
            right[y] += 1
            npairs += 1
    rows = []
    for u in units:
        a, b = u[0], u[1]
        r = pair_obs_exp(tokens, a, b)
        o, e = r["obs"].get("all", 0), r["exp"].get("all", 0.0)
        e_pmi = left[a] * right[b] / npairs
        whole = sum(1 for w in tokens if w == u)
        n_a_nonfinal = left[a]
        n_b_noninitial = right[b]
        row = {"unit": u, "tokens_containing": sum(1 for w in tokens if u in w), "occurrences": o,
               "share_of_all_letters_pct": 100 * 2 * o / n_letters, "whole_word_tokens": whole,
               "expected_if_letters_shuffled_in_word": e, "obs_over_exp_shuffle": o / e if e else float("nan"),
               "pmi_bits": math.log2(o / e_pmi) if o and e_pmi else float("-inf"),
               "p_b_follows_a": o / letters[a] if letters[a] else float("nan"),
               "p_a_precedes_b": o / letters[b] if letters[b] else float("nan"),
               "letter_a_count": letters[a], "letter_b_count": letters[b]}
        for pos in ("initial", "medial", "final", "whole"):
            row[f"obs_{pos}"] = r["obs"].get(pos, 0)
            row[f"exp_{pos}"] = r["exp"].get(pos, 0.0)
        rows.append(row)
    df = pd.DataFrame(rows)
    if folios is not None and n_boot:
        # bootstrap CI of obs/exp over folios
        per_f = []
        for f in folios:
            tk = f.tokens
            d = {}
            for u in units:
                r = pair_obs_exp(tk, u[0], u[1])
                d[u] = (r["obs"].get("all", 0), r["exp"].get("all", 0.0))
            per_f.append(d)
        lo, hi = [], []
        n = len(per_f)
        for u in units:
            ob = np.array([d[u][0] for d in per_f], float)
            ex = np.array([d[u][1] for d in per_f], float)
            rs = []
            for _ in range(n_boot):
                idx = rng.integers(0, n, n)
                s_e = ex[idx].sum()
                rs.append(ob[idx].sum() / s_e if s_e > 0 else np.nan)
            lo.append(np.nanpercentile(rs, 2.5))
            hi.append(np.nanpercentile(rs, 97.5))
        df["obs_over_exp_ci_lo"] = lo
        df["obs_over_exp_ci_hi"] = hi
    return df


def cross_boundary_counts(folios: list[Folio], units: list[str]) -> pd.DataFrame:
    """Occurrences of each 2-letter unit in the space-less line stream split into inside a word vs spanning a word break."""
    rows = []
    for u in units:
        inside = span = 0
        for f in folios:
            for ln in f.lines:
                for w in ln:
                    inside += w.count(u)
                for w1, w2 in zip(ln, ln[1:]):
                    if w1.endswith(u[0]) and w2.startswith(u[1]):
                        span += 1
        rows.append({"unit": u, "inside_word": inside, "across_word_break": span})
    return pd.DataFrame(rows)


def order_asymmetry(tokens: list[str], units: list[str]) -> pd.DataFrame:
    """For words containing two different sheet units (non-overlapping), how often each ordering occurs. A free symbol set would show
    both orders; a rigid word grammar shows one."""
    cnt = Counter()
    for w in tokens:
        occ = []
        for u in units:
            i = w.find(u)
            while i != -1:
                occ.append((i, u))
                i = w.find(u, i + 1)
        occ.sort()
        for (i, u), (j, v) in itertools.combinations(occ, 2):
            if u != v and j >= i + len(u):
                cnt[(u, v)] += 1
    rows = []
    for (u, v), c in sorted(cnt.items(), key=lambda kv: -kv[1]):
        rows.append({"first": u, "second": v, "count": c, "reverse_count": cnt.get((v, u), 0)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# neighbour predictive information
# ------------------------------------------------------------------------------------------------


def _mi_binary(x: np.ndarray, y: np.ndarray) -> float:
    n = len(x)
    if n == 0:
        return 0.0
    c = np.zeros((2, 2))
    np.add.at(c, (x, y), 1)
    p = c / n
    px, py = p.sum(1, keepdims=True), p.sum(0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(p > 0, p * np.log2(p / (px * py)), 0.0)
    return float(t.sum())


def adjacent_pairs(folios: list[Folio]) -> list[tuple[str, str]]:
    return [(w1, w2) for f in folios for ln in f.lines for w1, w2 in zip(ln, ln[1:])]


def neighbour_mi(folios: list[Folio], substr: str, n_perm: int = 300, rng=None) -> dict:
    """MI (bits) between 'token contains substr' at position i and i+1 (same line), vs the same after shuffling tokens within
    each folio (destroys neighbour order, keeps folio-level topic/hand/language structure)."""
    rng = rng or np.random.default_rng(0)
    obs_pairs = []
    perm_sets = []
    for f in folios:
        toks_lines = f.lines
        flat = np.array([1 if substr in w else 0 for ln in toks_lines for w in ln], dtype=np.int8)
        lens = [len(ln) for ln in toks_lines]
        perm_sets.append((flat, lens))
    def mi_of(arrs):
        xs, ys = [], []
        for flat, lens in arrs:
            i = 0
            for L in lens:
                seg = flat[i:i + L]
                xs.append(seg[:-1])
                ys.append(seg[1:])
                i += L
        x = np.concatenate(xs) if xs else np.array([], dtype=np.int8)
        y = np.concatenate(ys) if ys else np.array([], dtype=np.int8)
        return _mi_binary(x.astype(int), y.astype(int)), len(x)
    obs, n = mi_of(perm_sets)
    null = []
    for _ in range(n_perm):
        shuf = [(rng.permutation(flat), lens) for flat, lens in perm_sets]
        null.append(mi_of(shuf)[0])
    null = np.array(null)
    return {"mi_bits": obs, "null_mean": float(null.mean()), "null_sd": float(null.std(ddof=1)),
            "z": float((obs - null.mean()) / null.std(ddof=1)) if null.std() > 0 else float("nan"), "n_pairs": n}


# ------------------------------------------------------------------------------------------------
# sections (enrichment, permutation tests)
# ------------------------------------------------------------------------------------------------


def folio_matrix(folios: list[Folio], units: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """(unit occurrence counts per folio [n_folios x n_units], token counts per folio)."""
    X = np.array([[sum(w.count(u) for w in f.tokens) for u in units] for f in folios], float)
    N = np.array([len(f.tokens) for f in folios], float)
    return X, N


def rate_ratio(X, N, mask, smooth: float = 0.5) -> np.ndarray:
    """log2 of (occurrences per token inside mask) / (outside), with additive smoothing, per unit."""
    inside = (X[mask].sum(0) + smooth) / (N[mask].sum() + 2 * smooth)
    outside = (X[~mask].sum(0) + smooth) / (N[~mask].sum() + 2 * smooth)
    return np.log2(inside / outside)


def enrichment_matrix(folios, units, sections, n_perm: int = 5000, seed: int = 11, strata: bool = False) -> pd.DataFrame:
    """For every (unit, section): rate per 1000 tokens inside, outside, log2 ratio, and a permutation p-value obtained by shuffling the
    section labels over folios (token counts per folio kept). ``strata=True`` shuffles only among folios of the same Currier language."""
    rng = np.random.default_rng(seed)
    X, N = folio_matrix(folios, units)
    sec = np.array([f.section for f in folios])
    lang = np.array([f.language for f in folios])
    rows = []
    for s in sections:
        mask = sec == s
        if mask.sum() == 0:
            continue
        obs = rate_ratio(X, N, mask)
        cnt = np.zeros(len(units))
        cnt_low = np.zeros(len(units))
        for _ in range(n_perm):
            if strata:
                perm = sec.copy()
                for L in np.unique(lang):
                    ix = np.where(lang == L)[0]
                    perm[ix] = rng.permutation(sec[ix])
            else:
                perm = rng.permutation(sec)
            r = rate_ratio(X, N, perm == s)
            cnt += r >= obs - 1e-12
            cnt_low += r <= obs + 1e-12
        for j, u in enumerate(units):
            rows.append({"unit": u, "section": s, "n_folios": int(mask.sum()), "tokens_in_section": int(N[mask].sum()),
                         "occurrences_in_section": int(X[mask, j].sum()), "rate_per_1000_in": 1000 * X[mask, j].sum() / N[mask].sum(),
                         "rate_per_1000_out": 1000 * X[~mask, j].sum() / N[~mask].sum(), "log2_ratio": obs[j],
                         "p_enriched": (1 + cnt[j]) / (1 + n_perm), "p_depleted": (1 + cnt_low[j]) / (1 + n_perm),
                         "strata": "language" if strata else "none"})
    return pd.DataFrame(rows)


def holm(ps: list[float]) -> list[float]:
    order = np.argsort(ps)
    m = len(ps)
    adj = np.empty(m)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * ps[i])
        adj[i] = min(1.0, run)
    return list(adj)


def sheet_score(X, N, sec, units, assign: dict[str, list[str]], smooth: float = 0.5) -> float:
    """Mean log2 enrichment of each unit inside the sections its *assigned meaning* predicts, over units that have a prediction."""
    vals = []
    for j, u in enumerate(units):
        secs = assign.get(u, [])
        if not secs:
            continue
        mask = np.isin(sec, secs)
        if mask.sum() == 0 or (~mask).sum() == 0:
            continue
        vals.append(rate_ratio(X, N, mask, smooth)[j])
    return float(np.mean(vals)) if vals else float("nan")


def mapping_permutation_test(folios, units, table_assign: dict[str, list[str]], n_label_perm: int = 3000, seed: int = 5) -> dict:
    # ``units`` may be any subset: the meanings of exactly these units are permuted among exactly these units.
    """(1) Rank of the sheet's unit->meaning pairing among all 8! pairings of the same meanings to the same units.
    (2) Folio-label permutation p-value of the sheet's score."""
    X, N = folio_matrix(folios, units)
    sec = np.array([f.section for f in folios])
    meanings = [table_assign.get(u, []) for u in units]       # prediction attached to the sheet's meaning in row j
    # precompute score contribution of unit j given a section set
    cache: dict[tuple[int, tuple], float] = {}

    def contrib(j, secs):
        key = (j, tuple(secs))
        if key not in cache:
            mask = np.isin(sec, secs)
            cache[key] = float(rate_ratio(X, N, mask)[j]) if secs and mask.sum() and (~mask).sum() else np.nan
        return cache[key]

    def score(perm):
        v = [contrib(j, meanings[perm[j]]) for j in range(len(units))]
        v = [x for x in v if not np.isnan(x)]
        return float(np.mean(v)) if v else float("nan")

    ident = tuple(range(len(units)))
    s_sheet = score(ident)
    allscores = np.array([score(p) for p in itertools.permutations(range(len(units)))])
    p_rank = float((allscores >= s_sheet - 1e-12).mean())
    rng = np.random.default_rng(seed)
    nulls = []
    assign_sheet = {u: table_assign.get(u, []) for u in units}
    for _ in range(n_label_perm):
        nulls.append(sheet_score(X, N, rng.permutation(sec), units, assign_sheet))
    nulls = np.array(nulls)
    return {"sheet_score": s_sheet, "frac_of_8!_pairings_at_least_as_good": p_rank, "n_pairings": len(allscores),
            "max_pairing_score": float(np.nanmax(allscores)), "median_pairing_score": float(np.nanmedian(allscores)),
            "label_perm_p": float((1 + (nulls >= s_sheet - 1e-12).sum()) / (1 + n_label_perm)),
            "label_perm_null_mean": float(np.nanmean(nulls)), "all_scores": allscores}


# ------------------------------------------------------------------------------------------------
# folio classification by unit counts (predictive information)
# ------------------------------------------------------------------------------------------------


def nb_loo(X: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> dict:
    """Leave-one-folio-out multinomial naive Bayes. X = counts per folio [n x k] (plus an 'other' column is added by the caller).
    Returns accuracy and balanced accuracy."""
    classes = np.unique(y)
    n, k = X.shape
    Cc = np.stack([X[y == c].sum(0) for c in classes])            # classes x k
    cnt = np.array([(y == c).sum() for c in classes], float)
    pred = np.empty(n, dtype=y.dtype)
    for i in range(n):
        C = Cc.copy()
        ci = int(np.where(classes == y[i])[0][0])
        C[ci] = C[ci] - X[i]
        prior = cnt.copy()
        prior[ci] -= 1
        if prior[ci] <= 0:
            prior[ci] = 1e-3
        p = (C + alpha) / (C + alpha).sum(1, keepdims=True)
        ll = np.log(prior / prior.sum()) + (X[i][None, :] * np.log(p)).sum(1)
        pred[i] = classes[int(ll.argmax())]
    acc = float((pred == y).mean())
    bal = float(np.mean([(pred[y == c] == c).mean() for c in classes]))
    return {"accuracy": acc, "balanced_accuracy": bal}


def unit_count_features(folios: list[Folio], substrs: list[str]) -> np.ndarray:
    cols = []
    for u in substrs:
        cols.append([sum(w.count(u) for w in f.tokens) for f in folios])
    X = np.array(cols, float).T
    N = np.array([len(f.tokens) for f in folios], float)
    other = np.maximum(N - X.sum(1), 0)[:, None]
    return np.hstack([X, other])


def frequent_bigrams(tokens: list[str], top: int = 60) -> list[str]:
    c = Counter(w[i:i + 2] for w in tokens for i in range(len(w) - 1))
    return [b for b, _ in c.most_common(top)]


def specificity_pool(folios: list[Folio], section: str, pool: list[str], n_perm: int = 2000, seed: int = 21) -> pd.DataFrame:
    """Section enrichment of many ordinary frequent letter pairs, to see how special a sheet unit's enrichment is."""
    return L_enrich(folios, pool, section, n_perm, seed)


def L_enrich(folios, pool, section, n_perm, seed):
    df = enrichment_matrix(folios, pool, [section], n_perm=n_perm, seed=seed)
    return df
