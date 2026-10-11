"""Library for h06: (1) section-varying NO-PLAINTEXT generators vs MS 408's section signal, (2) the zodiac pages vs generators.

Nothing here decodes MS 408. The question of part 1 is whether a section signal of MS 408's strength *needs* topic-driven (plaintext) content, or whether a generator whose parameters /
vocabulary pool / favoured units change by section (no plaintext at all) reproduces it -- and at what parameter cost, since a per-section pool of S memorised word types can trivially
carry section vocabulary.

Section-varying generator (SV): the copy-and-modify engine of ``mech_hybrid`` with three section-dependent components, each switchable:
  E  engine parameters per group  (p_copy, window, p_prev, p_exact, p_suffix, p_prefix  [+ p_pool])  -- fitted on the group's training text (lexicon + letter metrics)
  U  favoured units per group     (innovations are importance-resampled from one big grammar sample with weight  prod_u r_g[u]  where r_g[u] = smoothed unit frequency in the
                                   group / global; A-1 parameters per group, estimated, not searched)
  P  vocabulary seed pool per group (the S most frequent word types of the group in the training folios; with probability p_pool an innovation is drawn from the pool instead of the grammar)
Innovations otherwise come from ONE global slot-conditioned-bigram grammar fitted on the training folios (shared by every variant; ~1.4k parameters, also used by the C0 control of the
hybrid stage).  No plaintext enters anywhere.
"""
from __future__ import annotations

import bisect
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
from msdecipher import controls_ci as CI  # noqa: E402
from msdecipher import mech_hybrid as H  # noqa: E402
from msdecipher import mech_hybrid_run as HR  # noqa: E402
from msdecipher import mech_hybrid_topics as T  # noqa: E402
from msdecipher import mechanisms_run as R  # noqa: E402
from msdecipher import word_structure_run as WSR  # noqa: E402

SEG = R.SEG
PARAMS = ("p_copy", "window", "p_prev", "p_exact", "p_suffix", "p_prefix", "p_pool")
BIGPOOL_N = 60000
K_PSEUDO = 200          # pseudo-counts of the unit-tilt smoothing
RESULTS = HERE / "results"
FIG = HERE / "figures"


# ------------------------------------------------------------------ parameters

def sample_params(rng: random.Random, free: tuple, base: dict) -> dict:
    p = dict(base)
    q = H.sample_params(rng)
    for k in free:
        if k == "p_pool":
            p[k] = rng.uniform(0.0, 0.7)
        else:
            p[k] = getattr(q, k)
    return _norm(p)


def _norm(p: dict) -> dict:
    s = p["p_exact"] + p["p_suffix"] + p["p_prefix"]
    if s > 1:
        p = {**p, "p_exact": p["p_exact"] / s, "p_suffix": p["p_suffix"] / s, "p_prefix": p["p_prefix"] / s}
    return p


def perturb_params(rng: random.Random, p: dict, free: tuple) -> dict:
    q = dict(p)
    for k in rng.sample(list(free), min(len(free), rng.randint(1, 3))):
        if k == "window":
            q[k] = int(min(200, max(3, round(q[k] * 10 ** rng.gauss(0, 0.2)))))
        else:
            q[k] = min(1.0 if k != "p_copy" else 0.95, max(0.0, q[k] + rng.gauss(0, 0.15)))
    return _norm(q)


DEFAULT_BASE = dict(p_copy=0.1, window=20, p_prev=0.3, p_exact=0.15, p_suffix=0.3, p_prefix=0.2, p_pool=0.0)


# ------------------------------------------------------------------ group models

@dataclass
class GroupModel:
    params: dict
    pool: list = field(default_factory=list)
    pool_cum: list = field(default_factory=list)
    tilt_cum: list | None = None               # cumulative weights over the big grammar sample
    k_engine: int = 0
    k_tilt: int = 0
    k_pool: int = 0


class Shared:
    """Global grammar sample + global unit frequencies of the training text."""

    def __init__(self, train_words: list[str], seed: int = 0, n_big: int = BIGPOOL_N):
        self.ctx = HR.Ctx(train_words)
        self.big = self.ctx.g_tok.sample(n_big, random.Random(seed + 77))
        self.big_units = [SEG(w) for w in self.big]
        c = Counter(u for w in train_words for u in SEG(w))
        tot = sum(c.values())
        self.unit_p = {u: v / tot for u, v in c.items()}
        self.n_units = len(c)
        self.train_words = train_words


def tilt_weights(sh: Shared, group_words: list[str], top: int | None = None) -> list[float]:
    c = Counter(u for w in group_words for u in SEG(w))
    n = sum(c.values())
    logr = {}
    for u, p in sh.unit_p.items():
        q = (c.get(u, 0) + K_PSEUDO * p) / (n + K_PSEUDO)
        logr[u] = math.log(q / p)
    if top is not None:                      # only the ``top`` units with the largest |log ratio| keep their tilt (the rest = 1)
        keep = set(sorted(logr, key=lambda u: -abs(logr[u]))[:top])
        logr = {u: (v if u in keep else 0.0) for u, v in logr.items()}
    w = np.array([math.exp(max(-6.0, min(6.0, sum(logr.get(u, 0.0) for u in us)))) for us in sh.big_units])
    return np.cumsum(w / w.sum()).tolist()


def make_group_model(sh: Shared, words: list[str], params: dict, S: int, tilt: bool, top: int | None = None) -> GroupModel:
    gm = GroupModel(params=params)
    if S > 0 and words:
        pool = Counter(words).most_common(S)
        gm.pool = [w for w, _ in pool]
        cw = np.cumsum([c for _, c in pool], dtype=float)
        gm.pool_cum = (cw / cw[-1]).tolist()
        gm.k_pool = len(gm.pool)
    if tilt and words:
        gm.tilt_cum = tilt_weights(sh, words, top)
        gm.k_tilt = top if top is not None else sh.n_units - 1
    return gm


# ------------------------------------------------------------------ engine with per-folio group parameters

def _innovate(gm: GroupModel, sh: Shared, rng: random.Random) -> str:
    if gm.pool and rng.random() < gm.params.get("p_pool", 0.0):
        return gm.pool[min(bisect.bisect_left(gm.pool_cum, rng.random()), len(gm.pool) - 1)]
    if gm.tilt_cum is not None:
        return sh.big[min(bisect.bisect_left(gm.tilt_cum, rng.random()), len(sh.big) - 1)]
    return sh.big[rng.randrange(len(sh.big))]


def sv_generate(specs: list[dict], models: dict, sh: Shared, seed: int, scope: str = "window", fallback: dict | None = None,
                extra_pool: list[str] | None = None) -> list[list[str]]:
    """specs = [{'group': g, 'n': tokens, 'page': id}] in order -> list of word lists, one per spec.
    ``scope``: 'window' (copy sources = last ``window`` words, any page), 'page' (history restarts at each spec: copy only within the current spec),
    'global' (uniform over all earlier output, plus ``extra_pool`` if given)."""
    rng = random.Random(seed * 7919 + 13)
    pools = H._Pools()
    out_all: list[str] = []
    result = []
    run = 0
    fb = fallback or {}
    for sp in specs:
        gm = models.get(sp["group"]) or models.get(fb.get(sp["group"], "")) or models["__all__"]
        p = H.Params(**{k: gm.params[k] for k in H.PARAM_NAMES}).normalised()
        hist = [] if scope == "page" else out_all
        cur: list[str] = []
        for _ in range(sp["n"]):
            w = None
            if (hist or (scope == "global" and extra_pool)) and rng.random() < p.p_copy:
                if scope == "global":
                    n_all = len(hist) + (len(extra_pool) if extra_pool else 0)
                    j = rng.randrange(n_all)
                    src = hist[j] if j < len(hist) else extra_pool[j - len(hist)]
                elif not hist:
                    src = None
                else:
                    src = hist[-1] if rng.random() < p.p_prev else hist[-1 - rng.randrange(min(p.window, len(hist)))]
                if src is not None:
                    r = rng.random()
                    op = "exact" if r < p.p_exact else "suffix" if r < p.p_exact + p.p_suffix else "prefix" if r < p.p_exact + p.p_suffix + p.p_prefix else "inner"
                    if op == "exact":
                        w = src
                    else:
                        draw = lambda st: pools.draw({"suffix": "final", "prefix": "init", "unigram": "any"}[st], rng)   # noqa: E731
                        for _t in range(4):
                            e = H._edit(list(SEG(src)), op, draw, rng)
                            if e and 0 < len(e) <= H.MAX_UNITS:
                                w = "".join(e)
                                break
                        if w is None:
                            w = src
                    if hist and w == hist[-1] and run + 1 >= H.MAX_REPEAT:
                        w = None
            if w is None:
                w = _innovate(gm, sh, rng)
                pools.add(w)
            run = run + 1 if (hist and w == hist[-1]) else 0
            hist.append(w)
            if hist is not out_all:
                out_all.append(w)
            cur.append(w)
        result.append(cur)
    return result


# ------------------------------------------------------------------ fitting a group's parameters

_G: dict = {}


def _cand_job(job):
    WSR._one_thread()
    params, label = job
    sh, gm_base, n, ref, sc, seeds = _G["sh"], _G["gm"], _G["n"], _G["ref"], _G["sc"], _G["seeds"]
    gm = GroupModel(params=params, pool=gm_base.pool, pool_cum=gm_base.pool_cum, tilt_cum=gm_base.tilt_cum)
    ms = []
    for s in seeds:
        w = sv_generate([{"group": "g", "n": n, "page": 0}], {"g": gm, "__all__": gm}, sh, s)[0]
        ms.append(HR.fit_vector(w, s))
    m = {k: float(np.mean([x[k] for x in ms])) for k in ms[0]}
    z = HR.zvec(m, ref, sc)
    return {"label": label, "chi2": HR.chi2(z), **{f"p:{k}": v for k, v in params.items()}}


def fit_group(sh: Shared, words: list[str], S: int, tilt: bool, free: tuple, base: dict, seed: int = 0, n_random: int = 40, n_local: int = 10,
              workers: int | None = None, top: int | None = None) -> tuple[GroupModel, float]:
    """Search ``free`` parameters on the lexicon + letter metrics of ``words`` (the group's training text). Returns (model, chi2)."""
    if len(words) < 150 or not free:
        gm = make_group_model(sh, words, dict(base), S, tilt, top)
        return gm, float("nan")
    ref = HR.fit_vector(words)
    se = HR.jackknife_se(words, g=5)
    sc = HR.scales(ref, se, floor_rel=0.05)
    gm0 = make_group_model(sh, words, dict(base), S, tilt, top)
    _G.update(sh=sh, gm=gm0, n=len(words), ref=ref, sc=sc, seeds=(seed + 1, seed + 2))
    rng = random.Random(seed)
    cands = [dict(base)] + [sample_params(rng, free, base) for _ in range(n_random)]
    rows = CI.pmap(_cand_job, [(p, f"r{i}") for i, p in enumerate(cands)], workers)
    best = sorted(range(len(rows)), key=lambda i: rows[i]["chi2"])[:3]
    jobs = [(perturb_params(rng, cands[i], free), f"l{i}~{j}") for i in best for j in range(n_local)]
    rows2 = CI.pmap(_cand_job, jobs, workers)
    allp = cands + [j[0] for j in jobs]
    allr = rows + rows2
    ib = min(range(len(allr)), key=lambda i: allr[i]["chi2"])
    gm0.params = allp[ib]
    gm0.k_engine = len(free)
    return gm0, float(allr[ib]["chi2"])
