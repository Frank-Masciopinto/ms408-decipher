"""Step 1 of the hybrid test: fit hybrid generators on *training folios* of MS 408, evaluate on *held-out folios* and fresh seeds
with the full 35-metric suite (prediction-interval verdicts), against the parent mechanisms, with a parameter-count-penalised comparison.

Protocol (all numbers in ``reports/mechanisms/hybrid/``):
* MS 408 'P' running text split into 3 folds **by folio** (folio *i* of the manuscript order -> fold *i mod 3*, so every fold spans all
  sections and both Currier languages).  For each fold: fit on the other two folds' text, evaluate on the held-out fold's text.
* Fit objective ``D`` = RMS z over :data:`FIT_SET` (9 lexicon metrics + the 3 letter entropies H1, h2, h3), scale per metric
  ``sqrt(SE_jackknife^2 + (2 % |value|)^2)``; mean of 2 generator seeds per candidate; random search (:data:`N_RANDOM`) + local
  refinement; **the structure metrics (within-word shuffle, positional skew, slot grammar, suffix, cluster stability, word-length SD,
  coverage) are never fitted** -- they are the genuinely held-out-in-kind tests.
* Evaluation: the best parameters, **fresh seeds** (>= 100) and 11 plaintexts (7 Latin, 4 Italian), generated at the held-out fold's
  size, through the full suite; MS 408 held-out SEs = delete-one-group jackknife on the held-out fold.
* Parents are run through exactly the same protocol: Naibbe (no fitted parameters; plaintexts), Timm-Schinner Java generator (parameters
  fitted on *all* of MS 408 earlier -> in-sample, an advantage to the parent), slot-conditioned bigram grammar (fitted on the training folds).
* Parameter-count-penalised comparison: ``AIC = chi2_train(fit metrics) + 2 k`` (k = fitted parameters incl. grammar parameters used to
  draw codewords), and the held-out ``chi2`` / unfitted-metric RMS z (capped at 10).
"""
from __future__ import annotations

import json
import math
import random
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

from . import controls_ci as CI
from . import mech_grammars as G
from . import mech_hybrid as H
from . import mech_naibbe as N
from . import mech_selfcitation as S
from . import mechanisms_run as R
from . import stats as ST
from . import word_structure_run as WSR
from .paths import reports_dir

SEG = R.SEG
FIT_PLAIN = ["la_pliny_herbal", "la_celsus", "it_sidrach", "la_isidore"]       # plaintexts used while fitting (one per seed)
EVAL_PLAIN = R.NAIBBE_LATIN + R.NAIBBE_ITALIAN
FIT_SET = R.FIT_METRICS + ["unit_H1", "unit_h2", "unit_h3"]
N_RANDOM, N_LOCAL_TOP, N_LOCAL_EACH = 120, 3, 30
FIT_SEEDS = (11, 12)
N_FOLDS = 3
HYBRID_VARIANTS = OrderedDict([
    ("A1 Naibbe tokens + copy-modify", dict(enc="naibbe", plain_edit=False)),
    ("A2 whole-word codebook + copy-modify", dict(enc="codebook", plain_edit=False)),
    ("B reverse: copy-modify base, plaintext-driven edits", dict(enc="naibbe", plain_edit=True)),
    ("C0 control: grammar innovations + copy-modify (no plaintext)", dict(enc="grammar", plain_edit=False)),
])
PARENTS = ["Naibbe cipher (parent)", "Self-citation, authors' defaults (parent)", "Self-citation, fitted on all MS 408 (parent, in-sample)",
           "Slot-conditioned bigram (trained on training folios; parent grammar)"]

_PT: dict[str, list[str]] = {}


PLAIN_WORDS = 40000          # a codebook consumes one plaintext word per innovation (up to ~35k): never wrap around within a run


def plaintext(cid: str) -> list[str]:
    if cid not in _PT:
        from .controls_text import load_tokens
        _PT[cid] = load_tokens(cid, PLAIN_WORDS)
    return _PT[cid]


# ------------------------------------------------------------------ MS 408 data and folds

def ms_data(main_file=None) -> dict:
    ms = WSR.ms_corpora(main_file)
    c = ms[WSR.MS_MAIN]
    meta = c["corpus"].meta
    return dict(words=c["words"], pages=list(c["blocks"]), section=list(meta["section"]), language=list(meta["language"]), corp=c)


def folds_by_folio(pages: list, k: int = N_FOLDS) -> list[int]:
    order = list(OrderedDict.fromkeys(pages))
    fold_of = {p: i % k for i, p in enumerate(order)}
    return [fold_of[p] for p in pages]


def select(words: list[str], fold: list[int], keep) -> list[str]:
    return [w for w, f in zip(words, fold) if keep(f)]


# ------------------------------------------------------------------ fit metrics and objective

def fit_vector(words: list[str], seed: int = 1) -> dict:
    m = R.light_metrics(words, seed)
    seqs = [tuple(SEG(w)) for w in words]
    ep = ST.entropy_profile(seqs, seed, n_shuffles=1)
    m.update({"unit_H1": ep["H1"], "unit_h2": ep["h2"], "unit_h3": ep["h3"]})
    return m


def jackknife_se(words: list[str], g: int = 8, fn=fit_vector) -> dict:
    parts = CI.group_split(words, g)
    vals = [fn(CI.leave_out(parts, i)) for i in range(g)]
    keys = vals[0].keys()
    return {k: CI.jackknife_se([v[k] for v in vals]) for k in keys}


def scales(ref: dict, se: dict, floor_rel: float = 0.02) -> dict:
    return {k: math.sqrt((se.get(k) or 0.0) ** 2 + (floor_rel * abs(ref[k])) ** 2) or 1e-9 for k in FIT_SET}


def zvec(m: dict, ref: dict, sc: dict) -> dict:
    return {k: (m[k] - ref[k]) / sc[k] for k in FIT_SET}


def chi2(z: dict) -> float:
    return float(sum(v * v for v in z.values()))


# ------------------------------------------------------------------ generator context and builders

class Ctx:
    """Grammars fitted on a body of MS 408 text (used for codebook words and the no-plaintext control)."""

    def __init__(self, train_words: list[str], K: int = 12):
        seg = lambda w: tuple(SEG(w))                                    # noqa: E731
        self.n_grammar_params = None
        self.g_type = G.LearnedUnit(seg, "slotbi", K)
        self.g_type.fit({w: 1.0 for w in set(train_words)}, 0)
        self.g_tok = G.LearnedUnit(seg, "slotbi", K)
        self.g_tok.fit({w: float(c) for w, c in __import__("collections").Counter(train_words).items()}, 0)
        self.train_words = train_words

    def n_params(self) -> int:
        try:
            return int(self.g_type.n_params())
        except Exception:
            return 1617


def make_encoder(kind: str, pl: list[str], seed: int, ctx: Ctx):
    if kind == "naibbe":
        return H.NaibbeLive(pl, seed)
    if kind == "codebook":
        return H.Codebook(pl, lambda n, rng: ctx.g_type.sample(n, rng), seed)
    if kind == "grammar":
        return H.GrammarInnovator(lambda n, rng: ctx.g_tok.sample(n, rng), seed)
    raise ValueError(kind)


def variant_words(variant: str, params: H.Params, plain_id: str, seed: int, n: int, ctx: Ctx) -> list[str]:
    v = HYBRID_VARIANTS[variant]
    enc = make_encoder(v["enc"], plaintext(plain_id), seed, ctx)
    return H.generate(enc, params, n, seed, plain_edit=v["plain_edit"])


def n_fitted(variant: str, ctx: Ctx | None = None) -> int:
    """Free parameters fitted to MS 408: the 6 engine parameters, plus the grammar's parameters when MS-fitted codewords/innovations are used."""
    k = H.N_FREE_PARAMS
    kind = HYBRID_VARIANTS[variant]["enc"]
    if kind in ("codebook", "grammar"):
        k += ctx.n_params() if ctx else 1617
    return k


# ------------------------------------------------------------------ fitting

_G: dict = {}          # fork-shared state for worker processes (grammar objects hold lambdas and cannot be pickled)


def _eval_candidate(job):
    WSR._one_thread()
    variant, params, n, label = job
    ref, sc, ctx = _G["ref"], _G["sc"], _G["ctx"]
    ms = []
    for i, s in enumerate(FIT_SEEDS):
        w = variant_words(variant, params, FIT_PLAIN[(s + i) % len(FIT_PLAIN)], s, n, ctx)
        ms.append(fit_vector(w, s))
    m = {k: float(np.mean([x[k] for x in ms])) for k in ms[0]}
    z = zvec(m, ref, sc)
    return {"label": label, "distance": math.sqrt(chi2(z) / len(z)), "chi2": chi2(z), **params.as_dict(), **{f"z:{k}": v for k, v in z.items()}}


def fit_variant(variant: str, train_words: list[str], ctx: Ctx, seed: int = 0, workers=None, log=print,
                n_random: int = N_RANDOM, n_local: int = N_LOCAL_EACH) -> tuple[H.Params, pd.DataFrame, dict]:
    ref = fit_vector(train_words)
    se = jackknife_se(train_words)
    sc = scales(ref, se)
    rng = random.Random(seed)
    pv = "plain_edit" if HYBRID_VARIANTS[variant]["plain_edit"] else "naibbe"
    n = len(train_words)
    cands = [H.Params().normalised()] + [H.sample_params(rng, pv) for _ in range(n_random)]
    _G.update(ref=ref, sc=sc, ctx=ctx)
    jobs = [(variant, p, n, f"r{i}") for i, p in enumerate(cands)]
    df = pd.DataFrame(CI.pmap(_eval_candidate, jobs, workers)).assign(stage="random")
    top = df.sort_values("distance").head(N_LOCAL_TOP)
    jobs2 = []
    for _, r in top.iterrows():
        p0 = H.Params(**{k: (int(r[k]) if k == "window" else float(r[k])) for k in H.PARAM_NAMES})
        for j in range(n_local):
            jobs2.append((variant, H.perturb(rng, p0, pv), n, f"{r['label']}~{j}"))
    df2 = pd.DataFrame(CI.pmap(_eval_candidate, jobs2, workers)).assign(stage="local")
    all_df = pd.concat([df, df2], ignore_index=True).sort_values("distance").reset_index(drop=True)
    b = all_df.iloc[0]
    best = H.Params(**{k: (int(b[k]) if k == "window" else float(b[k])) for k in H.PARAM_NAMES})
    return best, all_df, {"ref": ref, "se": se, "scale": sc}


# ------------------------------------------------------------------ evaluation of one fold

def _suite_job(job):
    WSR._one_thread()
    name, i, build = job
    w = build()
    m = R.evaluate(w, seed=1 + i)
    return {"model": name, "run": i, **m}


def parent_builders(name: str, n: int, ctx: Ctx, seeds: list[int], sc_best: dict | None) -> list:
    if name == PARENTS[0]:
        return [(lambda cid=cid, s=s: R.naibbe_words(cid, 78, s, n)) for cid, s in zip(EVAL_PLAIN, seeds)]
    if name == PARENTS[1]:
        return [(lambda s=s: S.generate({}, ((s - 1) % 5) + 1, 35000, tag="default")[:n]) for s in seeds]
    if name == PARENTS[2]:
        return [(lambda s=s: S.generate(sc_best, ((s - 1) % 5) + 1, 35000, tag="fitted")[:n]) for s in seeds]
    if name == PARENTS[3]:
        return [(lambda s=s: ctx.g_tok.sample(n, random.Random(s))) for s in seeds]
    raise ValueError(name)


def evaluate_fold(fold_idx: int, train_words: list[str], test_words: list[str], params: dict[str, H.Params], ctx: Ctx, sc_best: dict | None,
                  n_runs: int = 5, workers=None, log=print) -> dict:
    """Full-suite runs of hybrids (fresh seeds) and parents at the held-out fold's size + the target's jackknife SEs."""
    n = len(test_words)
    jobs = []
    for vname, p in params.items():
        for i in range(n_runs):
            cid = EVAL_PLAIN[(i * 3 + fold_idx) % len(EVAL_PLAIN)]
            jobs.append((vname, i, (lambda vname=vname, p=p, cid=cid, i=i: variant_words(vname, p, cid, 100 + 10 * fold_idx + i, n, ctx))))
    for pn in PARENTS:
        if pn == PARENTS[2] and sc_best is None:
            continue
        if pn in (PARENTS[1], PARENTS[2]) and not S.available():
            continue
        for i, b in enumerate(parent_builders(pn, n, ctx, [100 + i + 1 for i in range(n_runs)], sc_best)):
            jobs.append((pn, i, b))
    # target jackknife: 8 leave-group-out evaluations of the held-out fold
    parts = CI.group_split(test_words, 8)
    tjobs = [("__target_jk__", i, (lambda i=i: CI.leave_out(parts, i))) for i in range(8)]
    alljobs = jobs + tjobs + [("__target__", 0, (lambda: test_words))]
    rows = CI.pmap(lambda i: _suite_job(alljobs[i]), range(len(alljobs)), workers)
    df = pd.DataFrame(rows)
    tgt = df[df.model == "__target__"].iloc[0]
    jk = df[df.model == "__target_jk__"]
    metrics = [m for m in R.SUITE if m in df.columns]
    se = {m: CI.jackknife_se(jk[m].astype(float).tolist()) for m in metrics}
    ms = {m: float(tgt[m]) for m in metrics}
    runs = df[~df.model.str.startswith("__")]
    return {"runs": runs, "ms": ms, "se": se}


# ------------------------------------------------------------------ parent chi2 on the training fold

def parent_chi2(name: str, ctx: Ctx, n: int, ref: dict, sc: dict, sc_best: dict | None) -> float | None:
    if name == PARENTS[2] and sc_best is None:
        return None
    if name in (PARENTS[1], PARENTS[2]) and not S.available():
        return None
    bs = parent_builders(name, n, ctx, list(FIT_SEEDS), sc_best)
    ms = [fit_vector(b(), s) for b, s in zip(bs, FIT_SEEDS)]
    m = {k: float(np.mean([x[k] for x in ms])) for k in ms[0]}
    return chi2(zvec(m, ref, sc))


def parent_k(name: str, ctx: Ctx) -> int:
    """Fitted parameters of each parent (discrete design choices counted): Naibbe 0 (deck/respacing fixed by the paper), self-citation 0 for
    its defaults, 15 swept options when fitted, slot-conditioned bigram = its probability parameters."""
    return {PARENTS[0]: 0, PARENTS[1]: 0, PARENTS[2]: 15, PARENTS[3]: ctx.n_params()}[name]


# ------------------------------------------------------------------ orchestration

def run_hybrid(out_dir: Path | None = None, n_runs: int = 5, workers: int | None = None, reuse: bool = False, quiet: bool = False,
               main_file=None) -> dict:
    from . import mech_hybrid_report as HRep
    out = Path(out_dir) if out_dir else reports_dir() / "mechanisms" / "hybrid"
    out.mkdir(parents=True, exist_ok=True)
    log = (lambda *a: None) if quiet else (lambda *a: print(*a, flush=True))
    WSR._one_thread()
    if reuse and (out / "full35k_verdicts.csv").exists():
        res = dict(fits=pd.read_csv(out / "fits_by_fold.csv"), verdicts=pd.read_csv(out / "heldout_verdicts.csv"), penalised=pd.read_csv(out / "penalised_comparison.csv"),
                   full_fits=pd.read_csv(out / "fits_all_ms408.csv"), full_verdicts=pd.read_csv(out / "full35k_verdicts.csv"), n_runs=n_runs, out=out)
        (out / "REPORT.md").write_text(HRep.report_markdown(res), encoding="utf-8")
        return res
    d = ms_data(main_file)
    fold = folds_by_folio(d["pages"])
    best_f = reports_dir() / "mechanisms" / "selfcitation_best_params.json"
    sc_best = json.loads(best_f.read_text()) if best_f.exists() else None
    res: dict = {"folds": [], "out": out}
    fit_rows, run_rows, verdict_rows, pen_rows = [], [], [], []
    for k in range(N_FOLDS):
        train = select(d["words"], fold, lambda f, k=k: f != k)
        test = select(d["words"], fold, lambda f, k=k: f == k)
        ctx = Ctx(train)
        fits, params = {}, {}
        ref = fit_vector(train)
        sc = scales(ref, jackknife_se(train))
        for v in HYBRID_VARIANTS:
            log(f"fold {k}: fitting {v} on {len(train):,} training tokens ...")
            best, df, info = fit_variant(v, train, ctx, seed=k, workers=workers, log=log)
            df.assign(fold=k, variant=v).to_csv(out / f"fit_trace_fold{k}_{v[:2].strip()}.csv", index=False)
            params[v] = best
            fits[v] = df.iloc[0]
            fit_rows.append({"fold": k, "variant": v, "n_train": len(train), "k_fitted": n_fitted(v, ctx), "distance": df.iloc[0]["distance"],
                             "chi2_train": df.iloc[0]["chi2"], "median_random_distance": float(df[df.stage == "random"].distance.median()),
                             **best.as_dict(), **{f"z:{m}": df.iloc[0][f"z:{m}"] for m in FIT_SET}})
        log(f"fold {k}: full-suite evaluation on {len(test):,} held-out tokens ...")
        ev = evaluate_fold(k, train, test, params, ctx, sc_best, n_runs, workers, log)
        runs = ev["runs"].assign(fold=k)
        run_rows.append(runs)
        groups = {m: g for m, g in runs.groupby("model", sort=False)}
        tab = R.mechanism_table(runs, ev["ms"], ev["se"], groups=groups).assign(fold=k)
        verdict_rows.append(tab)
        # penalised comparison inputs
        held = {m: {x: float(g[x].mean()) for x in FIT_SET if x in g.columns} for m, g in groups.items()}
        hsc = scales({x: ev["ms"][x] for x in FIT_SET}, ev["se"])
        for mname, mm in held.items():
            hz = zvec(mm, {x: ev["ms"][x] for x in FIT_SET}, hsc)
            if mname in HYBRID_VARIANTS:
                kk, c2t = n_fitted(mname, ctx), float(fits[mname]["chi2"])
            else:
                kk = parent_k(mname, ctx)
                c2t = parent_chi2(mname, ctx, len(train), ref, sc, sc_best)
            t = tab[tab.mechanism == mname]
            unf = t[~t.metric.isin(FIT_SET)]
            zc = unf.z.astype(float).clip(-10, 10)
            pen_rows.append({"fold": k, "model": mname, "k_fitted": kk, "chi2_train_fitset": c2t,
                             "AIC_train": (c2t + 2 * kk) if c2t is not None else None, "chi2_heldout_fitset": chi2(hz),
                             "repro_all": int((t.verdict == "≈").sum()), "n_all": len(t), "repro_unfitted": int((unf.verdict == "≈").sum()),
                             "n_unfitted": len(unf), "rms_z_unfitted_cap10": float(np.sqrt(np.nanmean(zc ** 2))),
                             "n_runs": int(len(groups[mname]))})
    fits_df, runs_df = pd.DataFrame(fit_rows), pd.concat(run_rows, ignore_index=True)
    ver_df, pen_df = pd.concat(verdict_rows, ignore_index=True), pd.DataFrame(pen_rows)
    fits_df.to_csv(out / "fits_by_fold.csv", index=False)
    runs_df.to_csv(out / "heldout_runs.csv", index=False)
    ver_df.to_csv(out / "heldout_verdicts.csv", index=False)
    pen_df.to_csv(out / "penalised_comparison.csv", index=False)

    # ---- fit on all of MS 408 (parameters used by step 2) and the 35k-token comparison with the mechanisms-stage rows
    log("fitting on all of MS 408 ...")
    ctx_all = Ctx(d["words"])
    full_params, full_rows = {}, []
    for v in HYBRID_VARIANTS:
        best, df, info = fit_variant(v, d["words"], ctx_all, seed=99, workers=workers, log=log)
        full_params[v] = best.as_dict()
        full_rows.append({"variant": v, "k_fitted": n_fitted(v, ctx_all), "distance": df.iloc[0]["distance"], "chi2_train": df.iloc[0]["chi2"],
                          **best.as_dict()})
        df.to_csv(out / f"fit_trace_all_{v[:2].strip()}.csv", index=False)
    (out / "hybrid_params_all_ms408.json").write_text(json.dumps(full_params, indent=1))
    pd.DataFrame(full_rows).to_csv(out / "fits_all_ms408.csv", index=False)
    msref = pd.read_csv(reports_dir() / "mechanisms" / "ms408_reference.csv")
    ms35 = dict(zip(msref.metric, msref.ms408))
    se35 = dict(zip(msref.metric, msref.se))
    n35 = len(d["words"])
    alljobs = []
    for v, p in full_params.items():
        for i in range(n_runs):
            cid = EVAL_PLAIN[(i * 2) % len(EVAL_PLAIN)]
            alljobs.append((v, i, (lambda v=v, p=H.Params(**p), cid=cid, i=i: variant_words(v, p, cid, 200 + i, n35, ctx_all))))
    rows = CI.pmap(lambda i: _suite_job(alljobs[i]), range(len(alljobs)), workers)
    full_runs = pd.DataFrame(rows)
    full_runs.to_csv(out / "full_runs_35k.csv", index=False)
    old = pd.read_csv(reports_dir() / "mechanisms" / "runs.csv")
    old = old[old.mechanism.isin(["Naibbe cipher, 78-card deck", "Self-citation (fitted within documented bounds)", "Self-citation (authors' defaults)",
                                  "Learned slot-conditioned bigram K=12 (MS 408)"])].rename(columns={"mechanism": "model"})
    both = pd.concat([full_runs, old], ignore_index=True)
    ft = R.mechanism_table(both, ms35, se35, groups={m: g for m, g in both.groupby("model", sort=False)})
    ft.to_csv(out / "full35k_verdicts.csv", index=False)
    res.update(fits=fits_df, runs=runs_df, verdicts=ver_df, penalised=pen_df, full_fits=pd.DataFrame(full_rows), full_verdicts=ft, ms35=ms35, se35=se35,
               full_params=full_params, n_runs=n_runs)
    (out / "REPORT.md").write_text(HRep.report_markdown(res), encoding="utf-8")
    log("wrote", out)
    return res
