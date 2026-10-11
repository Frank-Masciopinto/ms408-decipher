"""Orchestrate Stage 6 + 7 (word structure) on MS 408 and all controls -> ``reports/word_structure/``.

Per corpus (MS 408 and every control row of :mod:`controls_run`): cross-validated slot-grammar /
bigram / affix metrics (:mod:`word_structure`) and behavioural word-clustering metrics
(:mod:`word_classes`, neighbour features only so that every corpus is treated identically).
MS 408 additionally gets the line / section / Currier / hand feature variants, a block bootstrap
of the headline metrics, cluster tables and a slot-count sweep. Verdicts compare MS 408 with each
hypothesis family through the prediction interval of :mod:`controls_ci`.

MS 408 is undeciphered. Slots and clusters are numbered, unlabelled positions / groups; the only tags
used are behavioural ("line-final-leaning", "herbal-leaning") and never grammatical.
"""
from __future__ import annotations

import math
import os
import random
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from . import controls_ci as CI
from . import controls_run as CR
from . import word_classes as WC
from . import word_structure as WS
from .analysis import md_table
from .controls_text import TARGET_TOKENS
from .paths import reports_dir

CHUNK = 500
MS_ROWS = ["MS408 P (collapsed units)", "MS408 P (raw EVA chars)", "MS408 Currier A (collapsed)", "MS408 Currier B (collapsed)",
           "MS408 P tokens shuffled (collapsed)", "MS408 P letters shuffled in tokens (collapsed)"]
MS_MAIN = CR.MS_MAIN
K_SWEEP = (4, 6, 8, 10, 12, 14)
SWEEP_ROWS = ["plain:la_vulgate", "plain:la_pliny_herbal", "plain:it_manzoni", "plain:he_tanakh", "plain:ar_quran",
              "shuffle_letters:la_vulgate", "slot_grammar_p0.35", "selfcitation_p0.3"]

STRUCT_KEYS = list(WS.STRUCT_INFO)
CLASS_KEYS = list(WC.CLASS_INFO)
ALL_INFO = {**{k: v for k, v in WS.STRUCT_INFO.items()}, **{k: v for k, v in WC.CLASS_INFO.items()}}


# ------------------------------------------------------------------ corpora

def ms_corpora(main_file=None) -> dict:
    """name -> dict(tokens=list[tuple], words=list[str], blocks=list, seg=segmenter, corpus=WC.Corpus) for the MS 408 rows."""
    from .analysis import groups, load_corpus
    from .ivtff import readable
    from .segment import Segmenter
    corpus = load_corpus(main_file)
    grp = groups(corpus, "split")
    coll, raw = Segmenter.preset("collapsed"), Segmenter.preset("raw")

    def build(lines, seg, shuffle_tokens=False, shuffle_units=False):
        words, blocks, lids, ps, sec, lang, hand = [], [], [], [], [], [], []
        for ln in lines:
            first = True
            for w in ln.words:
                if not readable(w):
                    continue
                words.append(w)
                blocks.append(ln.page)
                lids.append(ln.locus.locus_id)
                ps.append(bool(first and getattr(ln.locus, "paragraph_start", False)))
                first = False
                sec.append(ln.locus.section or "?")
                lang.append(ln.locus.language or "?")
                hand.append(ln.locus.hand or "?")
        if shuffle_tokens:
            idx = list(range(len(words)))
            random.Random(1).shuffle(idx)
            words = [words[i] for i in idx]       # blocks / lines stay in place: only the words move
        tokens = [tuple(seg(w)) for w in words]
        if shuffle_units:
            rng = random.Random(1)
            tokens = [tuple(rng.sample(list(t), len(t))) for t in tokens]
        meta = {} if (shuffle_tokens or shuffle_units) else {"section": sec, "language": lang, "hand": hand}
        return dict(tokens=tokens, words=words, blocks=blocks, seg=seg,
                    corpus=WC.Corpus(words, blocks, lids, ps, meta))
    P = grp["P"]
    return {
        MS_MAIN: build(P, coll),
        "MS408 P (raw EVA chars)": build(P, raw),
        "MS408 Currier A (collapsed)": build(grp["A"], coll),
        "MS408 Currier B (collapsed)": build(grp["B"], coll),
        "MS408 P tokens shuffled (collapsed)": build(P, coll, shuffle_tokens=True),
        "MS408 P letters shuffled in tokens (collapsed)": build(P, coll, shuffle_units=True),
    }


def control_corpus(words: list[str]) -> dict:
    blocks = [i // CHUNK for i in range(len(words))]
    return dict(tokens=[tuple(w) for w in words], words=list(words), blocks=blocks, seg=lambda w: tuple(w),
                corpus=WC.Corpus(words, blocks))


# ------------------------------------------------------------------ one row

def row_metrics(c: dict, K: int, seed: int = 1, folds: int = 4, boot: int = 12, splits: int = 4,
                null: bool = True, features: str = "neighbour") -> dict:
    warnings.filterwarnings("ignore")
    s = WS.structure_metrics(c["tokens"], c["blocks"], K=K, n_folds=folds, seed=seed, null=null)
    s = {k: v for k, v in s.items() if not k.startswith("_")}
    w = WC.class_metrics(c["corpus"], c["seg"], features=features, B=boot, n_splits=splits, seed=seed)
    return {**s, **w}


def _one_thread():
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[v] = "1"
    try:                                            # env vars set after numpy is imported are ignored: limit the live BLAS/OpenMP pools
        from threadpoolctl import threadpool_limits
        threadpool_limits(1)
    except Exception:
        pass


# ------------------------------------------------------------------ families / verdicts

def family_table(comp: pd.DataFrame, ms_name: str, ms_se: dict | None, metrics: list[str], memberships: dict) -> pd.DataFrame:
    ctrl = CR._expand(comp, memberships)
    rows = []
    for fam, g in ctrl.groupby("family", sort=False):
        for m in metrics:
            if m not in g.columns:
                continue
            vals = g[m].astype(float).values
            v = float(comp.loc[ms_name, m]) if m in comp.columns else float("nan")
            iv = CI.interval_verdict(v, (ms_se or {}).get(m, 0.0), vals)
            rows.append({"family": fam, "metric": m, "group": ALL_INFO.get(m, ("", ""))[1], "ms408": v,
                         "se_ms": (ms_se or {}).get(m, float("nan")), **{k: iv[k] for k in
                         ("n_members", "family_mean", "family_sd", "family_min", "family_max", "z", "pi_lo", "pi_hi", "verdict", "ms_percentile")}})
    return pd.DataFrame(rows)


def verdict_summary(vt: pd.DataFrame) -> pd.DataFrame:
    out = []
    for fam, g in vt.groupby("family", sort=False):
        v = g["verdict"]
        out.append({"family": fam, "n_members": int(g["n_members"].iloc[0]), "inside": int((v == "≈").sum()),
                    "outside": int(v.isin(["↑", "↓"]).sum()), "undetermined": int(v.isin(["?", "–"]).sum()), "n_metrics": len(g),
                    "outside_metrics": "; ".join(f"{m}{x}" for m, x in zip(g["metric"], v) if x in ("↑", "↓"))})
    return pd.DataFrame(out).sort_values(["inside", "n_members"], ascending=False).reset_index(drop=True)


# ------------------------------------------------------------------ MS-only detail

def ms_detail(ms: dict, K: int, out: Path, seed: int = 1, boot: int = 30, log=print) -> dict:
    """Fitted slot grammar / affixes / clusters for MS 408 (full data) -> CSV."""
    res = {}
    r = WS.structure_metrics(ms["tokens"], ms["blocks"], K=K, n_folds=4, seed=seed, null=False, return_models=True)
    slot, big, uni, counts = r["_models"]["type"]
    pd.DataFrame(slot.describe(top=8)).to_csv(out / "ms408_slot_grammar_types.csv", index=False)
    stok = r["_models"]["tok"][0]
    pd.DataFrame(stok.describe(top=8)).to_csv(out / "ms408_slot_grammar_tokens.csv", index=False)
    pd.DataFrame(np.round(slot.P, 4), columns=[str(u) for u in slot.units], index=[f"slot{k + 1}" for k in range(K)]).to_csv(out / "ms408_slot_unit_matrix.csv")
    res["slot"], res["slot_tok"] = slot, stok
    am = r["_models"].get("affix")
    if am is not None:
        pre, suf = am.top_affixes(25)
        pd.DataFrame([{"kind": "prefix", "affix": "".join(a), "prob": p} for a, p in pre] +
                     [{"kind": "suffix", "affix": "".join(a), "prob": p} for a, p in suf]).to_csv(out / "ms408_affixes.csv", index=False)
        res["affix"] = am
    # example words: best / worst explained types
    types = [w for w in counts if len(w) <= K]
    lp = slot.logprob2(types, 1e-3)
    order = np.argsort(-lp)
    pd.DataFrame({"word": ["".join(types[i]) for i in order[:40]], "bits": [-lp[i] for i in order[:40]], "tokens": [counts[types[i]] for i in order[:40]]}).to_csv(out / "ms408_slot_best_types.csv", index=False)
    res["structure"] = {k: v for k, v in r.items() if not k.startswith("_")}
    # slot-count sweep
    sw = []
    for k in K_SWEEP:
        m = WS.structure_metrics(ms["tokens"], ms["blocks"], K=k, n_folds=4, seed=seed, null=True, affix=False)
        sw.append({"corpus": "MS408", "K": k, **{x: m.get(x) for x in ("bits_type_slot", "bits_type_bigram", "slot_minus_bigram_type", "slot_gain_frac_type",
                                                                   "slot_null_gap_type", "mdl_type_slot", "mdl_type_bigram", "mdl_type_slot_null_gap",
                                                                   "bits_tok_slot", "bits_tok_bigram", "slot_null_gap_tok", "share_over_K", "cov_slot_type")}})
        log(f"  K={k}: slot {m['bits_type_slot']:.2f} vs bigram {m['bits_type_bigram']:.2f} bits/type")
    res["sweep"] = sw
    # clustering variants with detail
    cl = {}
    for feats in ("neighbour", "line", "full"):
        m = WC.class_metrics(ms["corpus"], ms["seg"], features=feats, B=boot, n_splits=6, seed=seed, return_detail=True)
        cl[feats] = m
        log(f"  clusters [{feats}]: k_best={m['k_best']} sil_k5={m['sil_k5']:.3f} ARI_boot={m['k5_ari_boot']:.3f} class-MI excess={m['class_mi_excess_k5']:.3f}")
    res["clusters"] = cl
    write_cluster_tables(ms, cl, out)
    return res


def _tags(rates: dict, base: dict) -> list[str]:
    tags = []
    if rates["line_initial"] > 1.5 * base["line_initial"]:
        tags.append("line-initial-leaning")
    if rates["line_final"] > 1.5 * base["line_final"]:
        tags.append("line-final-leaning")
    if rates["line_initial"] < base["line_initial"] / 2:
        tags.append("rarely line-initial")
    if rates["line_final"] < base["line_final"] / 2:
        tags.append("rarely line-final")
    for k in ("section", "language"):
        sh = rates.get(k)
        if sh and sh[1] > 1.5 * base[k][sh[0]]:
            tags.append(f"{sh[0]}-leaning" if k == "section" else f"Currier-{sh[0]}-leaning")
    return tags


def write_cluster_tables(ms: dict, cl: dict, out: Path) -> None:
    c: WC.Corpus = ms["corpus"]
    tok = c.tokens
    n = len(tok)
    L = c.line_ids
    sec, lang = c.meta["section"], c.meta["language"]
    # per-word behaviour over the whole corpus
    info: dict[str, dict] = {}
    for i, w in enumerate(tok):
        d = info.setdefault(w, {"n": 0, "li": 0, "lf": 0, "sec": {}, "lang": {}})
        d["n"] += 1
        d["li"] += int(i == 0 or L[i - 1] != L[i])
        d["lf"] += int(i == n - 1 or L[i + 1] != L[i])
        d["sec"][sec[i]] = d["sec"].get(sec[i], 0) + 1
        d["lang"][lang[i]] = d["lang"].get(lang[i], 0) + 1
    base_sec = pd.Series(sec).value_counts(normalize=True).to_dict()
    base_lang = pd.Series(lang).value_counts(normalize=True).to_dict()
    gl_li = sum(d["li"] for d in info.values()) / n
    gl_lf = sum(d["lf"] for d in info.values()) / n
    base = {"line_initial": gl_li, "line_final": gl_lf, "section": base_sec, "language": base_lang}
    for feats, m in cl.items():
        det = m["_detail"]
        vocab, lab = det["vocab"], det["labels"]
        rows, crows = [], []
        for cid in sorted(set(lab)):
            ws = [w for w, l in zip(vocab, lab) if l == cid]
            tot = sum(info[w]["n"] for w in ws)
            li = sum(info[w]["li"] for w in ws) / tot
            lf = sum(info[w]["lf"] for w in ws) / tot
            secs, langs = {}, {}
            for w in ws:
                for a, b in info[w]["sec"].items():
                    secs[a] = secs.get(a, 0) + b
                for a, b in info[w]["lang"].items():
                    langs[a] = langs.get(a, 0) + b
            topsec = max(secs, key=secs.get)
            toplang = max(langs, key=langs.get)
            rates = {"line_initial": li, "line_final": lf, "section": (topsec, secs[topsec] / tot), "language": (toplang, langs[toplang] / tot)}
            tags = _tags(rates, base)
            crows.append({"cluster": f"C{cid + 1}", "n_words": len(ws), "tokens": tot, "token_share": tot / n, "line_initial_rate": li, "line_final_rate": lf,
                          "top_section": topsec, "top_section_share": secs[topsec] / tot, "top_language": toplang, "top_language_share": langs[toplang] / tot,
                          "behavioural_tags": ", ".join(tags) or "none above thresholds",
                          "top_words": " ".join(sorted(ws, key=lambda x: -info[x]["n"])[:12])})
            for w in ws:
                d = info[w]
                rows.append({"word": w, "cluster": f"C{cid + 1}", "tokens": d["n"], "line_initial_rate": d["li"] / d["n"], "line_final_rate": d["lf"] / d["n"],
                             "top_section": max(d["sec"], key=d["sec"].get), "top_language": max(d["lang"], key=d["lang"].get)})
        pd.DataFrame(rows).sort_values(["cluster", "tokens"], ascending=[True, False]).to_csv(out / f"ms408_clusters_{feats}_words.csv", index=False)
        pd.DataFrame(crows).to_csv(out / f"ms408_clusters_{feats}.csv", index=False)
        # association of clusters with topic metadata (token-weighted NMI of cluster with dominant section / language)
        from sklearn.metrics import normalized_mutual_info_score as nmi
        ws_ = np.array([info[w]["n"] for w in vocab], dtype=float)
        rep = np.maximum(1, np.round(ws_ / ws_.min() / 4)).astype(int)
        for key, getter in (("section", lambda w: max(info[w]["sec"], key=info[w]["sec"].get)), ("language", lambda w: max(info[w]["lang"], key=info[w]["lang"].get))):
            dom = np.repeat(np.array([getter(w) for w in vocab], dtype=object), rep)
            m[f"nmi_with_dominant_{key}"] = float(nmi(np.repeat(lab, rep), dom))


# ------------------------------------------------------------------ main run

HEADLINE = ["slot_gain_frac_type", "slot_minus_bigram_type", "slot_null_gap_type", "newtype_slot_minus_bigram", "slot_gain_frac_tok",
            "slot_null_gap_tok", "cov_slot_type", "cov_slot_minus_bigram_type", "gen_slot_newtype", "mdl_type_slot_minus_bigram",
            "mdl_type_slot_null_gap", "affix_minus_bigram_type", "affix_prefix_type_share", "affix_suffix_type_share",
            "k5_ari_boot", "k5_ari_split", "sil_k5", "class_mi_excess_k5", "class_mi_norm_k5", "nmi_last_unit_excess_k5",
            "nmi_first_unit_excess_k5", "hdbscan_noise_share"]


def run_word_structure(out_dir: Path | None = None, n_tokens: int = TARGET_TOKENS, main_file=None, K: int = 12, jackknife: bool = True,
                       workers: int | None = None, make_plots: bool = True, quiet: bool = False, ms_class_boot: int = 30,
                       do_sweep: bool = True, reuse: bool = False) -> dict:
    out = Path(out_dir) if out_dir else reports_dir() / "word_structure"
    out.mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(exist_ok=True)
    log = (lambda *a: None) if quiet else (lambda *a: print(*a, flush=True))
    _one_thread()
    ms = ms_corpora(main_file)
    plain = CR._word_sets(n_tokens, log)
    ms_train = None
    specs = CR.control_specs(n_tokens, 1, plain, ms_train)
    specs = [sp for sp in specs if sp["family"] != CR.FAMILY_ABJAD_VARIANT]
    log(f"{len(ms)} MS 408 rows + {len(specs)} control rows")
    jobs = [("ms", n) for n in ms] + [("ctl", i) for i in range(len(specs))]

    def run(job):
        _one_thread()
        kind, key = job
        if kind == "ms":
            c = ms[key]
            name, fam, base, win = key, "MS 408", "-", 0
        else:
            sp = specs[key]
            words = sp["build"](1 if sp["stochastic"] else 0)
            c = control_corpus(words)
            name, fam, base, win = sp["name"], sp["family"], sp["base"], sp["window"]
        m = row_metrics(c, K)
        return {"name": name, "family": fam, "base": base, "window": win, "n_tokens": len(c["tokens"]), **m}
    if reuse and (out / "comparison.csv").exists():
        log("re-using", out / "comparison.csv")
        comp = pd.read_csv(out / "comparison.csv").set_index("name")
    else:
        log("analysing every corpus (slot grammar + clustering) ...")
        rows = CI.pmap(run, jobs, workers)
        comp = pd.DataFrame(rows).set_index("name")
        comp.reset_index().to_csv(out / "comparison.csv", index=False)
    memberships = {sp["name"]: sp["memberships"] for sp in specs}

    res = {"comparison": comp, "memberships": memberships, "K": K, "jackknife": jackknife, "n_tokens": n_tokens, "out": out}

    # ---- MS 408: delete-one-block jackknife of the word-structure metrics (8-page blocks)
    ms_se = None
    if jackknife:
        base = ms[MS_MAIN]
        pages = list(dict.fromkeys(base["blocks"]))
        by_page: dict = {}
        for i, b in enumerate(base["blocks"]):
            by_page.setdefault(b, []).append(i)
        nb = CR.BOOT_BLOCK_PAGES
        grp = [[i for p in pages[j:j + nb] for i in by_page[p]] for j in range(0, len(pages), nb)]

        def jack_one(g):
            _one_thread()
            idx = [i for j, gi in enumerate(grp) if j != g for i in gi]
            tokens = [base["tokens"][i] for i in idx]
            words = [base["words"][i] for i in idx]
            bl = [base["blocks"][i] for i in idx]
            c = dict(tokens=tokens, words=words, blocks=bl, seg=base["seg"], corpus=WC.Corpus(words, bl))
            return row_metrics(c, K, seed=1, boot=6, splits=3, null=True)
        log(f"MS 408 delete-one-block jackknife of the word-structure metrics: {len(grp)} replicates")
        if reuse and (out / "ms408_jackknife_replicates.csv").exists():
            jres = pd.read_csv(out / "ms408_jackknife_replicates.csv")
        else:
            jres = pd.DataFrame(CI.pmap(jack_one, range(len(grp)), workers))
            jres.to_csv(out / "ms408_jackknife_replicates.csv", index=False)
        stat = []
        for m in HEADLINE + [k for k in comp.columns if k in ALL_INFO and k not in HEADLINE]:
            if m not in jres.columns:
                continue
            est = float(comp.loc[MS_MAIN, m])
            se = CI.jackknife_se(jres[m].values)
            lo, hi = est - 1.96 * se, est + 1.96 * se
            if m.endswith(("_share", "_type", "_tok")) and ("share" in m or m.startswith("cov_")) or m == "hdbscan_noise_share":
                lo, hi = max(lo, 0.0), min(hi, 1.0)            # proportions cannot leave [0, 1]
            stat.append({"metric": m, "estimate": est, "se_jackknife_block8": se, "ci_lo": lo, "ci_hi": hi, "n_replicates": len(jres)})
        mci = pd.DataFrame(stat)
        mci.to_csv(out / "ms408_ci.csv", index=False)
        ms_se = dict(zip(mci["metric"], mci["se_jackknife_block8"]))
        res["ms_ci"] = mci
    res["ms_se"] = ms_se

    # ---- verdicts
    metrics = [m for m in ALL_INFO if m in comp.columns]
    vt = family_table(comp, MS_MAIN, ms_se, metrics, memberships)
    vt.to_csv(out / "verdicts.csv", index=False)
    vs = verdict_summary(vt)
    vs.to_csv(out / "verdict_summary.csv", index=False)
    res.update(verdicts=vt, summary=vs)

    # ---- MS 408 detail: fitted models, clusters, K sweep
    log("MS 408 detail ...")
    det = ms_detail(ms[MS_MAIN], K, out, boot=ms_class_boot, log=log)
    res["detail"] = det
    sweep = list(det["sweep"])
    if reuse and (out / "slot_count_sweep.csv").exists():
        sweep = pd.read_csv(out / "slot_count_sweep.csv").to_dict("records")
    elif do_sweep:
        sidx = {sp["name"]: i for i, sp in enumerate(specs)}
        sj = [(n, k) for n in SWEEP_ROWS if n in sidx for k in K_SWEEP]

        def sw(job):
            _one_thread()
            n, k = job
            sp = specs[sidx[n]]
            c = control_corpus(sp["build"](1 if sp["stochastic"] else 0))
            m = WS.structure_metrics(c["tokens"], c["blocks"], K=k, n_folds=4, seed=1, null=True, affix=False)
            return {"corpus": n, "K": k, **{x: m.get(x) for x in ("bits_type_slot", "bits_type_bigram", "slot_minus_bigram_type", "slot_gain_frac_type",
                                                              "slot_null_gap_type", "mdl_type_slot", "mdl_type_bigram", "mdl_type_slot_null_gap",
                                                              "bits_tok_slot", "bits_tok_bigram", "slot_null_gap_tok", "share_over_K", "cov_slot_type")}}
        log(f"slot-count sweep on {len(SWEEP_ROWS)} controls x {len(K_SWEEP)} K ...")
        sweep += CI.pmap(sw, sj, workers)
    pd.DataFrame(sweep).to_csv(out / "slot_count_sweep.csv", index=False)
    res["sweep_df"] = pd.DataFrame(sweep)

    (out / "REPORT.md").write_text(report_markdown(res), encoding="utf-8")
    if make_plots:
        from . import word_structure_plots
        word_structure_plots.make_all(res, out / "figures")
    log("wrote", out)
    return res


# ------------------------------------------------------------------ report

SHOW_STRUCT = ["slot_gain_frac_type", "slot_minus_bigram_type", "slot_null_gap_type", "newtype_slot_minus_bigram", "cov_slot_type",
               "mdl_type_slot_minus_bigram", "affix_prefix_type_share", "affix_suffix_type_share"]
SHOW_CLASS = ["k5_ari_boot", "k5_ari_split", "sil_k5", "class_mi_excess_k5", "nmi_last_unit_excess_k5", "nmi_first_unit_excess_k5"]
SHORT = {"slot_gain_frac_type": "slot gain frac", "slot_minus_bigram_type": "slot−bigram", "slot_null_gap_type": "null gap",
         "newtype_slot_minus_bigram": "new-type slot−bigram", "cov_slot_type": "coverage", "mdl_type_slot_minus_bigram": "MDL slot−bigram",
         "affix_prefix_type_share": "prefix share", "affix_suffix_type_share": "suffix share", "k5_ari_boot": "ARI boot", "k5_ari_split": "ARI split",
         "sil_k5": "silhouette", "class_mi_excess_k5": "class MI", "nmi_last_unit_excess_k5": "NMI last", "nmi_first_unit_excess_k5": "NMI first"}


def _fmt(v, nd=3):
    return "n/a" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{nd}f}"


def report_markdown(res: dict) -> str:
    comp: pd.DataFrame = res["comparison"]
    vt, vs = res["verdicts"], res["summary"]
    ms = comp.loc[MS_MAIN]
    det = res["detail"]
    L = ["# Word structure of MS 408 (Stages 6 and 7): slot grammar, affixes, behavioural clusters", "",
         "> **MS 408 is undeciphered.** This stage measures *structure* (how well a positional grammar fits the vocabulary; whether frequent words "
         "fall into stable behavioural groups) and runs the identical measurements on controls. Slots are numbered positions, clusters are "
         "numbered groups; **no cluster is called a verb, noun, name or anything grammatical**, and a stable grouping is not evidence of "
         "syntax, only of distributional regularity. See [docs/WORD_STRUCTURE.md](../../docs/WORD_STRUCTURE.md).", "",
         f"Setup: MS 408 running text (ZL 3b, collapsed EVA units: ch, sh, cth, ckh, cph, cfh), {int(ms['n_tokens'])} tokens; controls are the same size-matched samples as in `reports/controls/` "
         f"(Latin incl. herbal/medical, Italian, German, Hebrew/Arabic consonantal, ciphers, null generators). Slot grammar K={res['K']}. Cross-validation by block "
         "(folio for MS 408, 500-token chunk for controls), 4 folds. MS 408 CIs: delete-one-block jackknife over 8-page blocks "
         "(`ms408_ci.csv`; estimate ± 1.96 SE).", ""]
    # --- headline numbers
    ci = res.get("ms_ci")
    L += ["## 1. MS 408 headline numbers", ""]
    if ci is not None:
        t = ci[ci["metric"].isin(HEADLINE)].copy()
        t["metric"] = t["metric"].map(lambda m: ALL_INFO.get(m, (m, 'other'))[0])
        t["estimate [95% CI]"] = [f"{r.estimate:.3f} [{r.ci_lo:.3f}, {r.ci_hi:.3f}]" for r in t.itertuples()]
        L += [md_table(t[["metric", "estimate [95% CI]", "se_jackknife_block8"]].rename(columns={"se_jackknife_block8": "SE (8-page-block jackknife)"}), floatfmt="{:.4f}"), ""]
    L += ["## 2. Slot grammar, prefix-core-suffix, MDL", ""] + slot_text(res) + [""]
    L += ["## 3. Behavioural word clusters (MS 408)", ""] + cluster_text(res) + [""]
    L += ["## 4. Controls: is MS 408's structure distinctive?", ""] + comparison_text(res) + [""]
    L += ["## 5. Slot count sweep", "", "Held-out bits per type for slot grammars with K slots vs the unit bigram, on MS 408 and several controls "
          "(`slot_count_sweep.csv`). K = 12 is used everywhere else. **Not comparable across K in absolute bits:** words longer than K units are dropped, so at small K (see `share_over_K`) the evaluated vocabulary is a short-word subset; compare slot vs bigram *within* a K.", "", md_table(res["sweep_df"][["corpus", "K", "bits_type_slot", "bits_type_bigram", "slot_gain_frac_type", "slot_null_gap_type", "share_over_K"]]), ""]
    L += ["## 6. Verdict tables", "",
          "Per family: how many of the metrics MS 408 is inside the 95% prediction interval of (`≈`), above (`↑`), below (`↓`), `?` = fewer than 3 members. "
          "Full metric-by-metric table: `verdicts.csv`.", "", md_table(vs[["family", "n_members", "inside", "outside", "undetermined", "n_metrics"]]), ""]
    L += caveats()
    return "\n".join(L)


def slot_text(res: dict) -> list[str]:
    comp, det = res["comparison"], res["detail"]
    ms = comp.loc[MS_MAIN]
    s = {**ms.to_dict(), **det["structure"]}      # null-model (within-word shuffle) values come from the comparison row
    L = [f"**Slot grammar** ({res['K']} ordered slots; each slot is skipped or emits one unit from its own distribution; fitted by EM, so slots are learned, not hand-written). "
         "Held-out (4-fold by folio) cost, bits:", "",
         md_table(pd.DataFrame([
             {"model": "unit unigram", "bits/type": s["bits_type_unigram"], "bits/token": s["bits_tok_unigram"], "bits/NEW type": s["bits_newtype_unigram"], "shuffled-null bits/type": s["null_bits_type_unigram"]},
             {"model": "within-word unit bigram", "bits/type": s["bits_type_bigram"], "bits/token": s["bits_tok_bigram"], "bits/NEW type": s["bits_newtype_bigram"], "shuffled-null bits/type": s["null_bits_type_bigram"]},
             {"model": f"slot grammar K={res['K']}", "bits/type": s["bits_type_slot"], "bits/token": s["bits_tok_slot"], "bits/NEW type": s["bits_newtype_slot"], "shuffled-null bits/type": s["null_bits_type_slot"]},
             {"model": "prefix-core-suffix", "bits/type": s.get("bits_type_affix"), "bits/token": None, "bits/NEW type": s.get("bits_newtype_affix"), "shuffled-null bits/type": None},
             {"model": "token lexicon (+escape to bigram)", "bits/type": None, "bits/token": s["bits_tok_lexicon"], "bits/NEW type": None, "shuffled-null bits/type": None}]), floatfmt="{:.2f}"), "",
         f"- The slot grammar recovers {s['slot_gain_frac_type']:.0%} of the unigram→bigram information gain (type level) and {s['slot_gain_frac_tok']:.0%} (token level), "
         f"but is still **{s['slot_minus_bigram_type']:.2f} bits/type worse than the within-word bigram** with ~{s['mdl_type_slot_params'] / s['mdl_type_bigram_params']:.0%} as many parameters "
         f"({int(s['mdl_type_slot_params'])} vs {int(s['mdl_type_bigram_params'])}). Description length (data + 0.5·log2 N per parameter): slot {s['mdl_type_slot']:.2f}, bigram {s['mdl_type_bigram']:.2f}, "
         f"unigram {s['mdl_type_unigram']:.2f}, slot on within-word-shuffled MS 408 {s['null_mdl_type_slot']:.2f} bits/type (the shuffled text needs {s['mdl_type_slot_null_gap']:.2f} more).",
         f"- Shuffling units inside words makes the slot grammar {s['slot_null_gap_type']:.2f} bits/type ({s['slot_null_gap_tok']:.2f} bits/token) worse: the positional structure is real in the sense that it compresses.",
         f"- Coverage (pruned grammar can generate the held-out type): slot {s['cov_slot_type']:.1%}, seen-bigram baseline {s['cov_bigram_type']:.1%}; of the {s['oov_type_share']:.0%} of held-out types NEVER seen in training, "
         f"slot grammar generates {s['gen_slot_newtype']:.1%}, bigram baseline {s['gen_bigram_newtype']:.1%}. Coverage is high for both because the pruning threshold is permissive; bits are the sharper measure.",
         f"- Prefix-core-suffix: {s['affix_n_prefixes']} learned prefixes, {s['affix_n_suffixes']} suffixes; {s['affix_prefix_type_share']:.0%} of types get a prefix, {s['affix_suffix_type_share']:.0%} a suffix; "
         f"distinct cores per type {s['affix_cores_per_type']:.2f}; held-out {s.get('bits_type_affix', float('nan')):.2f} bits/type ({s.get('affix_minus_bigram_type', float('nan')):+.2f} vs bigram).", ""]
    sg = pd.read_csv(Path(res.get("out", reports_dir() / "word_structure")) / "ms408_slot_grammar_types.csv") if (Path(res.get("out", reports_dir() / "word_structure")) / "ms408_slot_grammar_types.csv").exists() else None
    if sg is not None:
        L += ["Fitted slots (type-level fit; per slot: probability it emits, top units with their probability within the slot; numbered positions only):", "",
              md_table(sg[["slot", "p_emit", "entropy_bits", "n_units_ge_prune", "top_units"]], floatfmt="{:.2f}"), ""]
    return L


def cluster_text(res: dict) -> list[str]:
    det = res["detail"]["clusters"]
    comp = res["comparison"]
    L = ["Frequent word types (top 200) clustered by distribution. Three feature sets: **neighbour** (left/right neighbour profile, flat tokens; the one used for the control comparison), "
         "**line** (adds line-boundary contexts and line-initial/final rates), **full** (adds section, Currier language, hand). k-means k=5 unless stated.", ""]
    t = pd.DataFrame([{"features": f, "best k": m["k_best"], "silhouette (best k)": m["sil_best"], "silhouette k=5": m["sil_k5"],
                       "ARI bootstrap k=5": m["k5_ari_boot"], "ARI half-split k=5": m["k5_ari_split"], "ARI bootstrap best-k": m["ari_boot_best"],
                       "class-MI excess (bits)": m["class_mi_excess_k5"], "NMI cluster/last unit (excess)": m["nmi_last_unit_excess_k5"],
                       "NMI cluster/first unit (excess)": m["nmi_first_unit_excess_k5"], "NMI with dominant section": m.get("nmi_with_dominant_section"),
                       "NMI with Currier A/B": m.get("nmi_with_dominant_language")} for f, m in det.items()])
    L += [md_table(t, floatfmt="{:.3f}"), ""]
    sh = comp.loc["MS408 P tokens shuffled (collapsed)"]
    L += [f"Reference: the same pipeline on MS 408 with **tokens shuffled** (neighbour features): silhouette k=5 {sh['sil_k5']:.3f}, ARI bootstrap {sh['k5_ari_boot']:.3f}, ARI half-split {sh['k5_ari_split']:.3f}, "
          f"class-MI excess {sh['class_mi_excess_k5']:.3f} bits. Unshuffled MS 408 neighbour features: {det['neighbour']['sil_k5']:.3f}, {det['neighbour']['k5_ari_boot']:.3f}, "
          f"{det['neighbour']['k5_ari_split']:.3f}, {det['neighbour']['class_mi_excess_k5']:.3f}.", ""]
    out = Path(res.get("out", reports_dir() / "word_structure"))
    for f in ("neighbour", "line"):
        p = out / f"ms408_clusters_{f}.csv"
        if p.exists():
            c = pd.read_csv(p)
            L += [f"Clusters, `{f}` features (behavioural tags only; top words are EVA strings):", "",
                  md_table(c[["cluster", "n_words", "token_share", "line_initial_rate", "line_final_rate", "top_section", "top_language", "behavioural_tags", "top_words"]], floatfmt="{:.2f}"), ""]
    return L


def comparison_text(res: dict) -> list[str]:
    comp, vt = res["comparison"], res["verdicts"]
    ms = comp.loc[MS_MAIN]
    cols = SHOW_STRUCT + SHOW_CLASS
    fam_rows = []
    for fam in [CR.FAMILY_PLAIN, CR.FAMILY_PLAIN_LATIN, CR.FAMILY_PLAIN_HERBAL, CR.FAMILY_ABJAD]:
        g = vt[vt["family"] == fam]
        if g.empty:
            continue
        r = {"family": f"{fam} (n={int(g['n_members'].iloc[0])})"}
        for m in cols:
            x = g[g["metric"] == m]
            if len(x):
                r[SHORT[m]] = f"{x['family_mean'].iloc[0]:.2f}±{x['family_sd'].iloc[0]:.2f}"
        fam_rows.append(r)
    r = {"family": "**MS 408**"}
    for m in cols:
        r[SHORT[m]] = f"{ms[m]:.2f}"
    fam_rows.append(r)
    L = ["Mean ± between-member SD of each natural-text family against MS 408 (key metrics):", "", md_table(pd.DataFrame(fam_rows)), ""]
    # z for natural families
    L += ["z-scores of MS 408 against families (prediction-interval scale; |z| > t-limit ≈ outside; `?` = <3 members):", ""]
    zr = []
    fams = [CR.FAMILY_PLAIN, CR.FAMILY_PLAIN_LATIN, CR.FAMILY_PLAIN_HERBAL, CR.FAMILY_ABJAD, "slot-grammar generator", "self-citation generator", "letters shuffled inside words", "shuffled tokens",
            "nomenclator-like syllable code", "verbose cipher (letter -> 2 symbols)"]
    for m in cols:
        r = {"metric": SHORT[m], "MS 408": ms[m]}
        for fam in fams:
            g = vt[(vt["family"] == fam) & (vt["metric"] == m)]
            if len(g):
                z = g["z"].iloc[0]
                r[fam.split(" (")[0][:26]] = f"{z:+.1f}{g['verdict'].iloc[0]}" if not math.isnan(z) else "?"
        zr.append(r)
    L += [md_table(pd.DataFrame(zr), floatfmt="{:.3f}"), ""]
    # per-row table of the main contrasts
    t = comp.reset_index()
    t = t[t["window"] == 0][["name", "family"] + SHOW_STRUCT[:6] + SHOW_CLASS[:4]].rename(columns=SHORT)
    L += ["All corpora (window 0), key metrics (`comparison.csv` has everything, all windows):", "", md_table(t, floatfmt="{:.2f}"), ""]
    L += auto_findings(res)
    return L


def auto_findings(res: dict) -> list[str]:
    comp, vt = res["comparison"], res["verdicts"]
    ms = comp.loc[MS_MAIN]
    L = ["### Reading the comparison (auto-generated, hedged)", ""]
    nat = comp[comp["family"].isin([CR.FAMILY_PLAIN, CR.FAMILY_ABJAD])]
    for m in ("slot_gain_frac_type", "slot_null_gap_type", "mdl_type_slot_minus_bigram", "k5_ari_boot", "class_mi_excess_k5", "nmi_last_unit_excess_k5"):
        lo, hi, med = nat[m].min(), nat[m].max(), nat[m].median()
        rank = int((nat[m] < ms[m]).sum())
        ci = ""
        mci = res.get("ms_ci")
        if mci is not None and m in set(mci["metric"]):
            r = mci[mci["metric"] == m].iloc[0]
            ci = f" (95% CI {r.ci_lo:.3f} to {r.ci_hi:.3f})"
        L.append(f"- **{ALL_INFO.get(m, (m, 'other'))[0]}**: MS 408 {ms[m]:.3f}{ci}; natural texts (n={len(nat)}) range {lo:.3f}-{hi:.3f}, median {med:.3f}; MS 408 is above {rank} of {len(nat)} of them. "
                 + ("The CI overlaps the natural median: not distinguishable on this metric." if ci and r.ci_lo <= med <= r.ci_hi else ""))
    for fam in ("slot-grammar generator", "self-citation generator", "letters shuffled inside words", "shuffled tokens"):
        g = vt[vt["family"] == fam]
        if len(g):
            ins = g[g["verdict"] == "≈"]
            L.append(f"- **{fam}** (n={int(g['n_members'].iloc[0])}): MS 408 inside the interval on {len(ins)} of {len(g)} word-structure metrics" +
                     (f"; outside on: {', '.join(ALL_INFO.get(m, (m, 'other'))[0] for m in g[g['verdict'].isin(['↑', '↓'])]['metric'][:6])}" if (g['verdict'].isin(['↑', '↓'])).any() else "") + ".")
    return L


def caveats() -> list[str]:
    return ["## Caveats", "",
            "- **Undeciphered.** Distinctive statistics do not identify a mechanism, a language or a meaning; the same numbers may arise from several processes (including the generators here, whose inventories were written with Voynichese in mind).",
            "- The slot grammar is *one* positional model (independent emissions per slot, one unit per slot, K=12). A bigger or different model (slot-conditioned bigrams, Zattera's exact slot table, Stolfi's crust-mantle-core) could fit better; the unit bigram is only a baseline, not a ceiling.",
            "- Words longer than K=12 units are dropped from every model (share reported as `share_over_K`; large for verbose/nomenclator-style ciphers, which therefore are not like-for-like).",
            "- Units differ: MS 408 uses collapsed EVA units (ch, sh, cth, ckh, cph, cfh); controls use single characters (Hebrew/Arabic one native letter). Alphabet sizes differ (~22 vs 23-33), which shifts absolute bits; ratios (`slot gain frac`, null gaps) are less sensitive but not immune.",
            "- Cross-validation folds are blocks (folios / 500-token chunks), not independent texts: MS 408 pages share hand, section, and vocabulary. Held-out numbers are optimistic for within-section generalisation and say nothing about unseen sections.",
            "- Clusters use only the 200 most frequent word types; ARI/silhouette depend on that cut-off, k and the SVD dimension. Behavioural tags are descriptive thresholds (1.5× baseline), nothing more.",
            "- Control rows are one sample each (stochastic controls: seed 1); family prediction intervals mix base texts and are optimistic about 'all texts of that kind'. MS 408 SEs are a delete-one-8-page-block jackknife (no quire map; sampling noise only).",
            "- Neighbour features treat MS 408 as flat running text (line breaks ignored) for the control comparison; the `line`/`full` variants use line and metadata information controls do not have, so they are reported for MS 408 only.", ""]
