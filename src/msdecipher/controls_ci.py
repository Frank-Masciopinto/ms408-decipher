"""Confidence intervals and CI-based verdicts for the control comparison.

* **MS 408**: block bootstrap over *pages* (folios) or over blocks of consecutive pages, so the
  dependence between lines of one page (same hand, same section, same illustration) is kept
  inside a resample. This gives a standard error per metric.
* **Controls**: delete-one-group jackknife over ``G`` contiguous groups of the (possibly transformed) text.
* **Why a jackknife for the SE**: resampling blocks *with replacement* duplicates text, which lowers the
  number of distinct word types, so vocabulary-richness metrics (type/token ratio, hapax share, Heaps beta,
  word entropy, Zipf fit) come out biased and their percentile CIs are not centred on the estimate. The
  delete-one-block jackknife drops data instead of duplicating it and has no such bias, so the jackknife SE
  is the one used in the verdicts (the larger of the delete-one-page and delete-one-8-page-block versions);
  the bootstrap percentile CIs are kept in the CSV for comparison only.
* **Family verdicts** replace the old tolerance-widened min/max bands. For one family and metric
  the members (one per base text x window, seeds averaged) give a mean and between-member SD; MS 408
  is compared with the family through a *prediction interval* that also includes MS 408's own
  bootstrap uncertainty:

      z = (MS - mean) / sqrt(SD^2 * (1 + 1/n) + SE_ms^2),   inside iff |z| <= t(0.975, n - 1)

  Families with fewer than ``MIN_MEMBERS`` members get ``?`` (no honest SD). Members are NOT
  independent draws from "all texts of that family" (a handful of base texts, several windows from
  the same book), so the intervals are optimistic about the family and the verdicts are screens,
  not tests.
* **Per-control z-scores** compare MS 408 with one control row using the two bootstrap SEs only
  (sampling noise of the two texts, nothing about model misspecification).
"""
from __future__ import annotations

import math
import multiprocessing as mp
import os
import random
from typing import Callable, Sequence

import numpy as np
from scipy import stats as sst

MIN_MEMBERS = 3
_JOBS: list = []          # filled before a fork Pool is created (workers inherit it)


# ------------------------------------------------------------------ resampling

def make_blocks(pages: Sequence[Sequence[str]], block: int = 1) -> list[list[str]]:
    """Group consecutive pages into blocks of ``block`` pages (the last block may be shorter);
    each block is one flat word list."""
    out = []
    for i in range(0, len(pages), max(1, block)):
        out.append([w for p in pages[i:i + block] for w in p])
    return out


def make_group_blocks(pages: Sequence[Sequence[str]], keys: Sequence) -> list[list[str]]:
    """Group pages by an arbitrary key (e.g. quire or bifolium, see ``msdecipher.quires``), keeping first-seen
    order; each group is one flat word list. Use with ``resample_blocks`` / ``leave_out`` exactly like
    ``make_blocks`` (h08: quire-level bootstrap / jackknife)."""
    if len(keys) != len(pages):
        raise ValueError("one key per page required")
    groups: dict = {}
    for p, k in zip(pages, keys):
        groups.setdefault(k, []).extend(p)
    return list(groups.values())


def resample_blocks(blocks: Sequence[Sequence[str]], rng: random.Random) -> list[str]:
    """Draw ``len(blocks)`` blocks with replacement and concatenate them."""
    n = len(blocks)
    out: list[str] = []
    for _ in range(n):
        out.extend(blocks[rng.randrange(n)])
    return out


def chunk_blocks(words: Sequence[str], chunk: int = 500) -> list[list[str]]:
    """Contiguous chunks of ``chunk`` tokens (a trailing short chunk is merged into the previous one)."""
    ch = [list(words[i:i + chunk]) for i in range(0, len(words), chunk)]
    if len(ch) > 1 and len(ch[-1]) < chunk // 2:
        ch[-2].extend(ch.pop())
    return ch


def group_split(words: Sequence[str], g: int) -> list[list[str]]:
    """``g`` contiguous, nearly equal groups of tokens."""
    n = len(words)
    g = max(2, min(g, n))
    cuts = [round(i * n / g) for i in range(g + 1)]
    return [list(words[cuts[i]:cuts[i + 1]]) for i in range(g)]


def leave_out(blocks: Sequence[Sequence[str]], i: int) -> list[str]:
    """All blocks except the ``i``-th, concatenated (delete-one-block jackknife replicate)."""
    return [w for j, b in enumerate(blocks) if j != i for w in b]


def jackknife_se(values: Sequence[float]) -> float:
    """Delete-one-group jackknife SE of a statistic from its ``g`` leave-one-group-out values."""
    v = np.asarray([x for x in values if x is not None and not math.isnan(x)], dtype=float)
    g = len(v)
    if g < 2:
        return float("nan")
    return float(math.sqrt((g - 1) / g * ((v - v.mean()) ** 2).sum()))


def summarize(values: Sequence[float], level: float = 0.95) -> dict:
    """Mean, SD (the bootstrap SE), percentile CI of bootstrap replicates (NaN-safe)."""
    v = np.asarray([x for x in values if x is not None and not math.isnan(x)], dtype=float)
    if len(v) < 2:
        return {"mean": float("nan"), "se": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": len(v)}
    a = (1 - level) / 2
    return {"mean": float(v.mean()), "se": float(v.std(ddof=1)),
            "lo": float(np.quantile(v, a)), "hi": float(np.quantile(v, 1 - a)), "n": len(v)}


# ------------------------------------------------------------------ parallel map (fork)

def default_workers() -> int:
    return max(1, min(8, (os.cpu_count() or 2) - 0))


def pmap(fn: Callable, jobs: Sequence, workers: int | None = None) -> list:
    """``[fn(job) for job in jobs]`` on a fork Pool; ``fn`` and everything it needs may be closures /
    module state because workers are forked after the call. Falls back to serial for workers <= 1."""
    workers = default_workers() if workers is None else workers
    jobs = list(jobs)
    if workers <= 1 or len(jobs) <= 1:
        return [fn(j) for j in jobs]
    global _JOBS
    _JOBS = [fn]
    try:
        ctx = mp.get_context("fork")
        with ctx.Pool(min(workers, len(jobs))) as pool:
            return pool.map(_call_job, jobs, chunksize=1)
    finally:
        _JOBS = []


def _call_job(job):
    return _JOBS[0](job)


# ------------------------------------------------------------------ verdicts

def interval_verdict(ms: float, se_ms: float, members: Sequence[float], alpha: float = 0.05,
                     min_members: int = MIN_MEMBERS) -> dict:
    """Prediction-interval verdict of MS 408 against one family's member values (see module docstring).
    ``verdict`` is ``≈`` (inside), ``↑`` / ``↓`` (above / below), ``?`` (too few members) or ``–`` (undefined)."""
    x = np.asarray([v for v in members if not math.isnan(v)], dtype=float)
    n = len(x)
    base = {"n_members": n, "family_mean": float(x.mean()) if n else float("nan"),
            "family_sd": float(x.std(ddof=1)) if n > 1 else float("nan"),
            "family_min": float(x.min()) if n else float("nan"), "family_max": float(x.max()) if n else float("nan")}
    if math.isnan(ms) or n == 0:
        return {**base, "z": float("nan"), "pi_lo": float("nan"), "pi_hi": float("nan"), "verdict": "–",
                "ms_percentile": float("nan")}
    se = 0.0 if (se_ms is None or math.isnan(se_ms)) else se_ms
    pct = float((x < ms).sum() + 0.5 * (x == ms).sum()) / n
    if n < min_members:
        return {**base, "z": float("nan"), "pi_lo": float("nan"), "pi_hi": float("nan"), "verdict": "?",
                "ms_percentile": pct}
    sd = base["family_sd"]
    scale = math.sqrt(sd ** 2 * (1 + 1 / n) + se ** 2)
    tcrit = float(sst.t.ppf(1 - alpha / 2, n - 1))
    if scale == 0:
        z = 0.0 if ms == base["family_mean"] else math.copysign(math.inf, ms - base["family_mean"])
    else:
        z = (ms - base["family_mean"]) / scale
    verdict = "≈" if abs(z) <= tcrit else ("↑" if z > 0 else "↓")
    return {**base, "z": float(z), "pi_lo": base["family_mean"] - tcrit * scale,
            "pi_hi": base["family_mean"] + tcrit * scale, "verdict": verdict, "ms_percentile": pct}


def control_z(ms: float, se_ms: float, c: float, se_c: float) -> float:
    """z of the MS 408 - control difference from the two bootstrap SEs (sampling noise only)."""
    d = math.sqrt((se_ms or 0.0) ** 2 + (se_c or 0.0) ** 2)
    if math.isnan(ms) or math.isnan(c):
        return float("nan")
    if d == 0:
        return 0.0 if ms == c else math.copysign(math.inf, ms - c)
    return (ms - c) / d


def alphabet_adjusted(x: Sequence[float], y: Sequence[float], x_ms: float, y_ms: float, se_ms: float = 0.0,
                      alpha: float = 0.05) -> dict:
    """Regress a metric ``y`` on ``x`` = log2(alphabet size) over natural-language rows (OLS) and ask
    whether MS 408's value is inside the prediction interval at MS 408's own alphabet size.
    Returns slope, intercept, r, prediction, z, verdict."""
    xs, ys = np.asarray(x, float), np.asarray(y, float)
    ok = ~(np.isnan(xs) | np.isnan(ys))
    xs, ys = xs[ok], ys[ok]
    n = len(xs)
    if n < 4 or np.ptp(xs) == 0 or math.isnan(x_ms) or math.isnan(y_ms):
        return {"n": n, "slope": float("nan"), "intercept": float("nan"), "r": float("nan"),
                "pred": float("nan"), "z": float("nan"), "verdict": "?"}
    b, a = np.polyfit(xs, ys, 1)
    res = ys - (a + b * xs)
    s = math.sqrt((res ** 2).sum() / (n - 2))
    sxx = ((xs - xs.mean()) ** 2).sum()
    pred = a + b * x_ms
    se_pred = math.sqrt(s ** 2 * (1 + 1 / n + (x_ms - xs.mean()) ** 2 / sxx) + (se_ms or 0.0) ** 2)
    z = (y_ms - pred) / se_pred if se_pred else float("nan")
    tcrit = float(sst.t.ppf(1 - alpha / 2, n - 2))
    r = float(np.corrcoef(xs, ys)[0, 1])
    return {"n": n, "slope": float(b), "intercept": float(a), "r": r, "pred": float(pred), "z": float(z),
            "verdict": "≈" if abs(z) <= tcrit else ("↑" if z > 0 else "↓"),
            "extrapolated": bool(x_ms < xs.min() or x_ms > xs.max())}
