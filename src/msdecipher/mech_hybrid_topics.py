"""Step 2 of the hybrid test: is MS 408's section-specific vocabulary more consistent with a topic-structured underlying text than with a pure generator?

**This is a test of what a pipeline could and could not produce; it does not identify a plaintext, and MS 408 stays undeciphered.**

Unit of analysis: the *folio* (the page-level running text of MS 408 'P', label = the folio's illustration section: herbal, recipes ('stars'),
biological, pharmaceutical, cosmological+astronomical merged; text-only pages are generated but not classified).  For MS 408 and for every
generated corpus **laid out on the same folio sequence** (same section and token count per folio) we compute, with identical code:

* **between-section JS divergence** of word distributions (mean over section pairs, bits) and its excess over a label-permutation null
  (folio labels shuffled, class sizes kept; finite-size bias cancels);
* **section-classification accuracy on held-out folios** (balanced accuracy and macro-F1; TF-IDF + logistic regression, and multinomial NB;
  5-fold stratified CV *by folio*, 3 repeats) against a label-permutation null;
* **section-keyword reproducibility**: for each section, top-30 over-represented word types (relative-frequency ratio, min count 5) in two
  random halves of its folios; overlap of the two lists (null: shuffled labels);
* **folio-block uncertainty** for MS 408: bootstrap over folios (and per-folio correctness bootstrap for accuracy).

Generated corpora (``MODELS``): topic-matched hybrids (each section's innovations come from a topical Latin work: herbal <- Pliny XX-XXVII,
pharmaceutical <- Celsus, biological <- Pliny VII-XI, recipes <- Macer, cosmo/astro <- Isidore, text-only <- Augustine -- an arbitrary but
documented assignment that *maximises* topic contrast), the same hybrids with **topic-mixed** plaintext (each folio draws its work at random: no
section <-> topic link, the null for 'topic-structured plaintext'), a **single-work** control, the no-plaintext control C0, the pure Naibbe
cipher (matched / mixed) and the authors' self-citation generator sliced into the folio layout.  Because every generator has local drift
(copying from recent words, continuous plaintext) and sections are contiguous runs of folios, 'topic-mixed' and the pure generators measure how
much section signal drift alone produces.
"""
from __future__ import annotations

import math
import random
from collections import Counter, OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.naive_bayes import MultinomialNB

from . import controls_ci as CI
from . import mech_hybrid as H
from . import mech_hybrid_run as HR
from . import mechanisms_run as R
from . import mech_selfcitation as S
from . import word_structure_run as WSR
from .paths import reports_dir

SECTION_CLASS = {"herbal": "herbal", "stars": "recipes", "biological": "biological", "pharmaceutical": "pharmaceutical",
                 "cosmological": "cosmo-astro", "astronomical": "cosmo-astro"}
CLASSES = ["herbal", "recipes", "biological", "pharmaceutical", "cosmo-astro"]
TOPIC_WORK = {"herbal": "la_pliny_herbal", "pharmaceutical": "la_celsus", "biological": "la_pliny_general", "recipes": "la_macer",
              "cosmo-astro": "la_isidore", "text-only": "la_augustine"}
WORKS = list(TOPIC_WORK.values())
TOPK, MINCOUNT = 30, 5


# ------------------------------------------------------------------ folio documents

def folio_layout(d: dict) -> list[dict]:
    """One entry per folio in manuscript order: folio, class (None for text-only/other), language, tokens."""
    pages: OrderedDict = OrderedDict()
    for w, p, s, lg in zip(d["words"], d["pages"], d["section"], d["language"]):
        e = pages.setdefault(p, {"folio": p, "sections": Counter(), "langs": Counter(), "words": []})
        e["sections"][s] += 1
        e["langs"][lg] += 1
        e["words"].append(w)
    out = []
    for e in pages.values():
        sec = e["sections"].most_common(1)[0][0]
        out.append({"folio": e["folio"], "section": sec, "cls": SECTION_CLASS.get(sec), "lang": e["langs"].most_common(1)[0][0], "words": e["words"]})
    return out


def corpus_from_layout(layout: list[dict], words: list[str]) -> list[dict]:
    """Cut a flat generated word list into folios with the layout's sizes/labels."""
    out, i = [], 0
    for e in layout:
        n = len(e["words"])
        out.append({**{k: e[k] for k in ("folio", "section", "cls", "lang")}, "words": words[i:i + n]})
        i += n
    return out


def design(docs: list[dict], classes=CLASSES, lang: str | None = None, min_folios: int = 6):
    """Count matrix and labels of the folios to classify."""
    use = [e for e in docs if e["cls"] in classes and (lang is None or e["lang"] == lang) and len(e["words"]) >= 20]
    cnt = Counter(e["cls"] for e in use)
    keep = {c for c, n in cnt.items() if n >= min_folios}
    use = [e for e in use if e["cls"] in keep]
    cv = CountVectorizer(token_pattern=r"\S+", lowercase=False, min_df=2)
    X = cv.fit_transform([" ".join(e["words"]) for e in use])
    y = np.array([e["cls"] for e in use])
    return X.tocsr(), y, [e["folio"] for e in use], cv.get_feature_names_out()


# ------------------------------------------------------------------ statistics

def mean_pairwise_js(X, y) -> float:
    cls = sorted(set(y))
    P = []
    for c in cls:
        v = np.asarray(X[y == c].sum(axis=0)).ravel().astype(float)
        P.append(v / v.sum())
    P = np.array(P)
    out = []
    for i in range(len(cls)):
        for j in range(i + 1, len(cls)):
            m = 0.5 * (P[i] + P[j])
            with np.errstate(divide="ignore", invalid="ignore"):
                a = np.where(P[i] > 0, P[i] * np.log2(P[i] / m), 0.0).sum()
                b = np.where(P[j] > 0, P[j] * np.log2(P[j] / m), 0.0).sum()
            out.append(0.5 * (a + b))
    return float(np.mean(out))


def cv_predict(X, y, model: str, seed: int = 0, repeats: int = 3, n_splits: int = 5) -> np.ndarray:
    """Pooled held-out predictions (n_docs x repeats) from stratified CV over folios."""
    n_splits = max(2, min(n_splits, min(Counter(y).values())))
    preds = np.empty((len(y), repeats), dtype=object)
    tf = TfidfTransformer(sublinear_tf=True)
    for r in range(repeats):
        skf = StratifiedKFold(n_splits, shuffle=True, random_state=seed * 100 + r)
        for tr, te in skf.split(np.zeros(len(y)), y):
            if model == "nb":
                clf = MultinomialNB(alpha=0.2).fit(X[tr], y[tr])
                preds[te, r] = clf.predict(X[te])
            else:
                Xtr = tf.fit_transform(X[tr])
                clf = LogisticRegression(C=20.0, max_iter=300).fit(Xtr, y[tr])
                preds[te, r] = clf.predict(tf.transform(X[te]))
    return preds


def class_scores(y, preds) -> tuple[float, float]:
    ba = np.mean([balanced_accuracy_score(y, preds[:, r]) for r in range(preds.shape[1])])
    f1 = np.mean([f1_score(y, preds[:, r], average="macro") for r in range(preds.shape[1])])
    return float(ba), float(f1)


def keyword_overlap(X, y, rng: random.Random, splits: int = 4, topk: int = TOPK) -> float:
    """Mean over sections and random folio splits of |top-k(half 1) ∩ top-k(half 2)| / k, top-k by relative-frequency ratio vs the other sections."""
    Xd = np.asarray(X.todense(), float)
    tot = Xd.sum(axis=0)
    vals = []
    for c in sorted(set(y)):
        idx = np.where(y == c)[0]
        if len(idx) < 6:
            continue
        for _ in range(splits):
            perm = list(idx)
            rng.shuffle(perm)
            halves = [perm[: len(perm) // 2], perm[len(perm) // 2:]]
            tops = []
            for h in halves:
                sec = Xd[h].sum(axis=0)
                rest = tot - sec
                ratio = (sec / max(sec.sum(), 1)) / ((rest + 0.5) / max(rest.sum(), 1))
                ratio = np.where(sec >= MINCOUNT, ratio, -1)
                tops.append(set(np.argsort(-ratio)[:topk]))
            vals.append(len(tops[0] & tops[1]) / topk)
    return float(np.mean(vals)) if vals else float("nan")


def perm_stat(fn, y, n_perm: int, seed: int = 0):
    rng = np.random.default_rng(seed)
    obs = fn(y)
    null = np.array([fn(rng.permutation(y)) for _ in range(n_perm)])
    return obs, null


def p_upper(obs: float, null: np.ndarray) -> float:
    return float((1 + (null >= obs).sum()) / (1 + len(null)))


def stats_for(docs: list[dict], n_perm: int = 200, seed: int = 0, lr: bool = True) -> dict:
    X, y, _, _ = design(docs)
    out = {"n_folios": len(y)}
    js_obs, js_null = perm_stat(lambda yy: mean_pairwise_js(X, yy), y, n_perm, seed)
    out.update(js=js_obs, js_null_mean=float(js_null.mean()), js_excess=js_obs - float(js_null.mean()),
               js_z=(js_obs - js_null.mean()) / (js_null.std(ddof=1) or 1e-9), js_p=p_upper(js_obs, js_null))
    nb_obs, nb_null = perm_stat(lambda yy: class_scores(yy, cv_predict(X, yy, "nb", seed, repeats=1))[0], y, n_perm, seed + 1)
    nb_ba, nb_f1 = class_scores(y, cv_predict(X, y, "nb", seed))
    out.update(nb_bal_acc=nb_ba, nb_macro_f1=nb_f1, nb_null_mean=float(nb_null.mean()), nb_p=p_upper(nb_obs, nb_null),
               nb_z=(nb_obs - nb_null.mean()) / (nb_null.std(ddof=1) or 1e-9))
    if lr:
        pr = cv_predict(X, y, "lr", seed)
        out["lr_bal_acc"], out["lr_macro_f1"] = class_scores(y, pr)
    ko, kn = perm_stat(lambda yy: keyword_overlap(X, yy, random.Random(7), splits=2), y, max(20, n_perm // 4), seed + 2)
    out.update(keyword_overlap=keyword_overlap(X, y, random.Random(seed + 5)), keyword_null_mean=float(kn.mean()), keyword_p=p_upper(ko, kn))
    return out


def shift_null(X, y, seed: int = 0, min_shift: int = 10, stride: int = 1) -> dict:
    """Drift-aware null: labels circularly shifted along the folio order (contiguous section runs preserved, section<->content link broken)."""
    n = len(y)
    ks = [k for k in range(min_shift, n - min_shift, stride)]
    js = np.array([mean_pairwise_js(X, np.roll(y, k)) for k in ks])
    nb = np.array([class_scores(np.roll(y, k), cv_predict(X, np.roll(y, k), "nb", seed, repeats=1))[0] for k in ks])
    js_obs = mean_pairwise_js(X, y)
    nb_obs = class_scores(y, cv_predict(X, y, "nb", seed, repeats=1))[0]
    return {"n_shifts": len(ks), "js_shift_null_mean": float(js.mean()), "js_shift_p": p_upper(js_obs, js),
            "nb_shift_null_mean": float(nb.mean()), "nb_shift_null_max": float(nb.max()), "nb_shift_p": p_upper(nb_obs, nb)}


def within_language_nb(docs: list[dict], lg: str, seed: int = 0) -> float:
    try:
        X, y, _, _ = design(docs, lang=lg)
        if len(set(y)) < 2:
            return float("nan")
        return class_scores(y, cv_predict(X, y, "nb", seed))[0]
    except ValueError:
        return float("nan")


def ms_uncertainty(docs: list[dict], n_boot: int = 300, seed: int = 0) -> dict:
    """Folio-block bootstrap SEs / CIs for MS 408 (folios resampled with replacement within the whole corpus)."""
    X, y, _, _ = design(docs)
    rng = np.random.default_rng(seed)
    js, kw = [], []
    n = len(y)
    for _ in range(n_boot):
        ix = rng.integers(0, n, n)
        yy = y[ix]
        if len(set(yy)) < len(set(y)):
            continue
        js.append(mean_pairwise_js(X[ix], yy))
        kw.append(keyword_overlap(X[ix], yy, random.Random(int(rng.integers(1 << 30))), splits=1))
    # per-folio correctness bootstrap for accuracy (pooled CV predictions, NB and LR)
    res = {"js_se": float(np.std(js, ddof=1)), "js_ci": (float(np.quantile(js, .025)), float(np.quantile(js, .975))),
           "keyword_se": float(np.nanstd(kw, ddof=1)), "keyword_ci": (float(np.nanquantile(kw, .025)), float(np.nanquantile(kw, .975)))}
    for model in ("nb", "lr"):
        pr = cv_predict(X, y, model, seed)
        corr = np.array([[1.0 if pr[i, r] == y[i] else 0.0 for r in range(pr.shape[1])] for i in range(n)]).mean(axis=1)
        accs = []
        for _ in range(n_boot):
            ix = rng.integers(0, n, n)
            yy = y[ix]
            accs.append(np.mean([balanced_accuracy_score(yy, pr[ix, r]) for r in range(pr.shape[1])]))
        res[f"{model}_bal_acc_se"] = float(np.std(accs, ddof=1))
        res[f"{model}_bal_acc_ci"] = (float(np.quantile(accs, .025)), float(np.quantile(accs, .975)))
    return res


def top_words(docs: list[dict], k: int = 8) -> pd.DataFrame:
    X, y, _, names = design(docs)
    Xd = np.asarray(X.todense(), float)
    tot = Xd.sum(axis=0)
    rows = {}
    for c in CLASSES:
        sec = Xd[y == c].sum(axis=0)
        rest = tot - sec
        ratio = (sec / sec.sum()) / ((rest + 0.5) / rest.sum())
        ratio = np.where(sec >= 15, ratio, -1)
        rows[c] = " ".join(names[i] for i in np.argsort(-ratio)[:k])
    return pd.DataFrame({"section": list(rows), "top over-represented words (ratio, count ≥ 15)": list(rows.values())})


# ------------------------------------------------------------------ generated corpora on the folio layout

def _enc_for(kind: str, pl: list[str], seed: int, ctx):
    return HR.make_encoder(kind, pl, seed, ctx)


def generated_words(model: str, layout: list[dict], params: dict, ctx, seed: int, rng_mix: random.Random) -> list[str]:
    """Flat word list of ``sum(len)`` tokens laid out on ``layout`` for one named model/seed."""
    n_tot = sum(len(e["words"]) for e in layout)
    kind, topic = model.rsplit("|", 1) if "|" in model else (model, "none")
    if kind == "SC defaults" or kind == "SC fitted":
        return S.generate({} if kind == "SC defaults" else params["__sc__"], ((seed - 1) % 5) + 1, 35000, tag="default" if kind == "SC defaults" else "fitted")[:n_tot]
    if kind == "Naibbe pure":
        # pure cipher, no copying: p_copy = 0
        p = H.Params(p_copy=0.0)
        v = "A1 Naibbe tokens + copy-modify"
        return _hybrid(v, p, topic, layout, ctx, seed, rng_mix)
    v = {"A1": "A1 Naibbe tokens + copy-modify", "A2": "A2 whole-word codebook + copy-modify", "B": "B reverse: copy-modify base, plaintext-driven edits",
         "C0": "C0 control: grammar innovations + copy-modify (no plaintext)"}[kind]
    return _hybrid(v, H.Params(**params[v]) if kind != "Naibbe pure" else H.Params(p_copy=0.0), topic, layout, ctx, seed, rng_mix)


def _hybrid(variant: str, p: H.Params, topic: str, layout: list[dict], ctx, seed: int, rng_mix: random.Random) -> list[str]:
    spec = HR.HYBRID_VARIANTS[variant]
    steps, encs = [], {}
    for i, e in enumerate(layout):
        sec = e["cls"] or "text-only"
        if topic == "matched":
            work = TOPIC_WORK[sec]
        elif topic == "mixed":
            work = rng_mix.choice(WORKS)
        elif topic == "single":
            work = "la_pliny_herbal"
        else:
            work = "la_pliny_herbal"          # C0: the encoder ignores plaintext
        key = work
        if key not in encs:
            encs[key] = _enc_for(spec["enc"], HR.plaintext(work), seed * 31 + len(encs), ctx)
        steps.append((key, len(e["words"])))
    return H.generate(None, p, 0, seed, plain_edit=spec["plain_edit"], section_encoders=encs, layout=steps)


MODELS = ["A1|matched", "A1|mixed", "A1|single", "A2|matched", "A2|mixed", "B|matched", "B|mixed", "C0|none",
          "Naibbe pure|matched", "Naibbe pure|mixed", "SC defaults", "SC fitted"]
LABEL = {"A1|matched": "A1 hybrid, topic-matched plaintext", "A1|mixed": "A1 hybrid, topic-mixed plaintext", "A1|single": "A1 hybrid, single work",
         "A2|matched": "A2 codebook hybrid, topic-matched", "A2|mixed": "A2 codebook hybrid, topic-mixed", "B|matched": "B reverse hybrid, topic-matched",
         "B|mixed": "B reverse hybrid, topic-mixed", "C0|none": "C0 no-plaintext control", "Naibbe pure|matched": "Naibbe cipher, topic-matched (p_copy = 0)",
         "Naibbe pure|mixed": "Naibbe cipher, topic-mixed", "SC defaults": "Self-citation (Java), defaults", "SC fitted": "Self-citation (Java), fitted"}
_G: dict = {}


def _model_job(job):
    WSR._one_thread()
    model, seed = job
    layout, params, ctx, n_perm = _G["layout"], _G["params"], _G["ctx"], _G["n_perm"]
    w = generated_words(model, layout, params, ctx, seed, random.Random(seed * 17 + 3))
    docs = corpus_from_layout(layout, w)
    st = stats_for(docs, n_perm=n_perm, seed=seed)
    st["nb_langA"] = within_language_nb(docs, "A", seed)
    st["nb_langB"] = within_language_nb(docs, "B", seed)
    return {"model": model, "seed": seed, **st}


def run_topics(out_dir: Path | None = None, n_perm: int = 1000, n_seeds: int = 10, workers: int | None = None, quiet: bool = False,
               main_file=None, n_perm_gen: int = 100) -> dict:
    import json
    from . import mech_hybrid_topics_report as TR
    out = Path(out_dir) if out_dir else reports_dir() / "mechanisms" / "hybrid" / "topics"
    out.mkdir(parents=True, exist_ok=True)
    log = (lambda *a: None) if quiet else (lambda *a: print(*a, flush=True))
    WSR._one_thread()
    d = HR.ms_data(main_file)
    layout = folio_layout(d)
    pj = reports_dir() / "mechanisms" / "hybrid" / "hybrid_params_all_ms408.json"
    params = json.loads(pj.read_text())
    bj = reports_dir() / "mechanisms" / "selfcitation_best_params.json"
    params["__sc__"] = json.loads(bj.read_text()) if bj.exists() else {}
    ctx = HR.Ctx(d["words"])
    log("MS 408 folio statistics (permutations, bootstrap) ...")
    msdocs = [{**{k: e[k] for k in ("folio", "section", "cls", "lang")}, "words": e["words"]} for e in layout]
    ms = stats_for(msdocs, n_perm=n_perm, seed=0)
    unc = ms_uncertainty(msdocs, 300)
    X, y, folios, _ = design(msdocs)
    ms.update(shift_null(X, y, 0))
    ms["nb_langA"], ms["nb_langB"] = within_language_nb(msdocs, "A"), within_language_nb(msdocs, "B")
    classes = pd.Series(y).value_counts().to_dict()
    # within-language diagnostics (does the section signal survive inside a Currier language?)
    within = []
    for lg in ("A", "B"):
        dd = [e for e in msdocs if e["lang"] == lg]
        try:
            X2, y2, _, _ = design(dd, lang=lg)
            if len(set(y2)) >= 2:
                st = stats_for(dd, n_perm=min(n_perm, 300), seed=1) if False else None
                js_obs, js_null = perm_stat(lambda yy: mean_pairwise_js(X2, yy), y2, 300, 3)
                nb_obs, nb_null = perm_stat(lambda yy: class_scores(yy, cv_predict(X2, yy, "nb", 0, repeats=1))[0], y2, 300, 4)
                ba, f1 = class_scores(y2, cv_predict(X2, y2, "nb", 0))
                within.append({"language": lg, "classes": ", ".join(f"{k}:{v}" for k, v in Counter(y2).items()), "n_folios": len(y2), "js": js_obs,
                               "js_null_mean": float(js_null.mean()), "js_p": p_upper(js_obs, js_null), "nb_bal_acc": ba, "nb_null_mean": float(nb_null.mean()),
                               "nb_p": p_upper(nb_obs, nb_null), "chance": 1 / len(set(y2))})
        except ValueError:
            pass
    pd.DataFrame(within).to_csv(out / "ms408_within_language.csv", index=False)
    tw = top_words(msdocs)
    tw.to_csv(out / "ms408_top_words.csv", index=False)
    _G.update(layout=layout, params=params, ctx=ctx, n_perm=n_perm_gen)
    jobs = [(m, s) for m in MODELS for s in range(1, n_seeds + 1)]
    log(f"{len(jobs)} generated corpora on the MS 408 folio layout ...")
    rows = CI.pmap(_model_job, jobs, workers)
    gen = pd.DataFrame(rows)
    gen.to_csv(out / "generated_section_stats.csv", index=False)
    pd.DataFrame([{**ms, **{f"unc_{k}": v for k, v in unc.items()}}]).to_csv(out / "ms408_section_stats.csv", index=False)
    # one example of top words for topic-matched A2
    ex = generated_words("A2|matched", layout, params, ctx, 1, random.Random(3))
    top_words(corpus_from_layout(layout, ex)).to_csv(out / "a2_matched_top_words.csv", index=False)
    res = {"ms": ms, "unc": unc, "gen": gen, "within": pd.DataFrame(within), "top": tw, "classes": classes, "out": out, "params": params,
           "n_perm": n_perm, "n_seeds": n_seeds, "n_folios": len(y)}
    (out / "REPORT.md").write_text(TR.report_markdown(res), encoding="utf-8")
    log("wrote", out)
    return res
