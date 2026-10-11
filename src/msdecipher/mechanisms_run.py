"""Run candidate generating mechanisms through the full MS 408 metric suite -> reports/mechanisms/.

Mechanisms (all *tests of whether a mechanism reproduces measured structure*; none of them decodes MS 408):
  1. Naibbe cipher (Greshko 2025) applied to Latin and Italian plaintexts (78- and 52-card variants).
  2. Timm & Schinner self-citation generator (authors' reference code), authors' defaults and parameters fitted to MS 408
     within the documented bounds (random search + local refinement + one-at-a-time sweep; fit on lexicon metrics only,
     then evaluated on fresh seeds on the whole suite).
  3. Hand-coded Zattera slot alphabet and Stolfi grammar, and
  4. slot-conditioned bigram models, as *generators fitted to MS 408* (in-sample: an upper bound on what a word grammar
     alone can reproduce) -- plus the held-out grammar comparison on MS 408.
Every run goes through exactly the metric suite used for MS 408 and the controls (``controls_metrics.metrics`` +
``word_structure_run.row_metrics``), and MS 408's own jackknife SEs are used in prediction-interval verdicts.
"""
from __future__ import annotations

import math
import random
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from . import controls_ci as CI
from . import controls_metrics as CM
from . import mech_grammars as G
from . import mech_naibbe as N
from . import mech_selfcitation as S
from . import word_structure_run as WSR
from .controls_text import load_tokens
from .paths import reports_dir
from .segment import Segmenter

CHUNK = WSR.CHUNK
NAIBBE_LATIN = ["la_vulgate", "la_augustine", "la_pliny_herbal", "la_pliny_general", "la_celsus", "la_isidore", "la_macer"]
NAIBBE_ITALIAN = ["it_dante", "it_manzoni", "it_sidrach", "it_ariosto"]
MAX_PLAIN_WORDS = 14000
SC_SEEDS = [1, 2, 3, 4, 5]
SWEEP_SEEDS = [101, 102]

# metric -> (label, group). The "suite" requested: letter entropy, within-word shuffle, positional skew, slot-grammar
# shuffle penalty, suffix rate, Zipf/Heaps, adjacent repeats, cluster stability (+ word shape and grammar coverage).
SUITE: dict[str, tuple[str, str]] = {
    "unit_H1": ("unit entropy H1 (bits)", "letter entropy"),
    "unit_h2": ("conditional entropy h2 (bits)", "letter entropy"),
    "unit_h3": ("conditional entropy h3 (bits)", "letter entropy"),
    "unit_h2_over_H1": ("h2 / H1", "letter entropy"),
    "shuffle_gap_h2": ("h2 rise after within-word shuffle (bits)", "within-word shuffle"),
    "shuffle_gap_over_H1": ("h2 rise after shuffle / H1", "within-word shuffle"),
    "pos_jsd_initial_final": ("word-initial vs final unit JSD (bits)", "positional skew"),
    "pos_skewed_unit_share": ("share of positionally skewed units", "positional skew"),
    "slot_gain_frac_type": ("slot-grammar gain fraction (types)", "slot grammar"),
    "slot_null_gap_type": ("slot grammar shuffle penalty, types (bits)", "slot grammar"),
    "slot_null_gap_tok": ("slot grammar shuffle penalty, tokens (bits)", "slot grammar"),
    "slot_minus_bigram_type": ("slot minus letter-pair bits (types)", "slot grammar"),
    "cov_slot_type": ("slot-grammar type coverage (held out)", "slot grammar"),
    "affix_suffix_type_share": ("suffix rate (types)", "suffix"),
    "affix_suffix_token_share": ("suffix rate (tokens)", "suffix"),
    "affix_prefix_type_share": ("prefix rate (types)", "suffix"),
    "affix_cores_per_type": ("affix model: cores per type", "suffix"),
    "type_token_ratio": ("type/token ratio", "Zipf / Heaps"),
    "hapax_share_of_types": ("hapax share of types", "Zipf / Heaps"),
    "top10_token_coverage": ("top-10 token coverage", "Zipf / Heaps"),
    "word_entropy_H1": ("word entropy (bits)", "Zipf / Heaps"),
    "zipf_mle_s_r10_1000": ("Zipf exponent s (MLE r10-1000)", "Zipf / Heaps"),
    "heaps_beta_in_order": ("Heaps beta (text order)", "Zipf / Heaps"),
    "heaps_beta_shuffled": ("Heaps beta (shuffled)", "Zipf / Heaps"),
    "mean_word_length_units": ("mean word length (units)", "word shape"),
    "word_length_sd_units": ("word length SD (units)", "word shape"),
    "adjacent_identical_rate": ("adjacent identical-token rate", "adjacent repeats"),
    "adjacent_edit1_rate": ("adjacent edit-distance-1 rate", "adjacent repeats"),
    "k5_ari_boot": ("cluster stability: bootstrap ARI (k=5)", "cluster stability"),
    "k5_ari_split": ("cluster stability: half-split ARI (k=5)", "cluster stability"),
    "sil_k5": ("silhouette (k=5)", "cluster stability"),
    "class_mi_excess_k5": ("class MI excess over null (k=5)", "cluster stability"),
    "nmi_last_unit_excess_k5": ("NMI of classes with last unit, excess", "cluster stability"),
    "cov_zattera_tok": ("Zattera slot-table token coverage", "grammar coverage"),
    "cov_stolfi_tok": ("Stolfi grammar token coverage", "grammar coverage"),
}
# lexicon-level metrics the self-citation authors target: the only ones used to FIT the generator
FIT_METRICS = ["type_token_ratio", "hapax_share_of_types", "top10_token_coverage", "word_entropy_H1", "zipf_mle_s_r10_1000",
               "heaps_beta_in_order", "mean_word_length_units", "adjacent_identical_rate", "adjacent_edit1_rate"]
SEG = Segmenter.preset("collapsed")


# ------------------------------------------------------------------ evaluation of one word list

def corpus_of(words: list[str]) -> dict:
    from .word_classes import Corpus
    blocks = [i // CHUNK for i in range(len(words))]
    return dict(tokens=[tuple(SEG(w)) for w in words], words=list(words), blocks=blocks, seg=SEG,
                corpus=Corpus(words, blocks))


def grammar_coverage(words: list[str]) -> dict:
    """Token share generated by Zattera's 12-slot table and by Stolfi's normal-word grammar (hard coverage)."""
    st = _stolfi()
    ty = Counter(words)
    n = len(words)
    return {"cov_zattera_tok": sum(c for w, c in ty.items() if G.zattera_covered(w)) / n,
            "cov_stolfi_tok": sum(c for w, c in ty.items() if st.covers(w)) / n}


_ST = None


def _stolfi():
    global _ST
    if _ST is None:
        _ST = G.StolfiGrammar()
    return _ST


def evaluate(words: list[str], K: int = 12, seed: int = 1) -> dict:
    """The complete metric suite for one corpus (same code path as MS 408)."""
    WSR._one_thread()
    words = [w for w in words if w]
    m = CM.metrics(words, SEG, seed=seed)
    m.update(WSR.row_metrics(corpus_of(words), K, seed=seed))
    m.update(grammar_coverage(words))
    return m


# ------------------------------------------------------------------ MS 408 reference

def ms_reference(K: int = 12, main_file=None) -> tuple[dict, dict, dict]:
    """(metrics, se, corpora) of MS 408 'P' running text in the collapsed units; SEs from the committed jackknife reports."""
    ms = WSR.ms_corpora(main_file)
    c = ms[WSR.MS_MAIN]
    m = evaluate(c["words"], K)
    se: dict[str, float] = {}
    rd = reports_dir()
    f1, f2 = rd / "controls" / "ms408_ci.csv", rd / "word_structure" / "ms408_ci.csv"
    if f1.exists():
        d = pd.read_csv(f1)
        d = d[d["units"] == "collapsed"]
        se.update(dict(zip(d["metric"], d["se_used"])))
    if f2.exists():
        d = pd.read_csv(f2)
        se.update({k: v for k, v in zip(d["metric"], d["se_jackknife_block8"])})
    return m, se, ms


# ------------------------------------------------------------------ run specifications

def plaintext_words(cid: str) -> list[str]:
    return load_tokens(cid, MAX_PLAIN_WORDS)


def naibbe_words(cid: str, deck: int, seed: int, n_tokens: int, p_uni: float = N.P_UNIGRAM_STANDARD) -> list[str]:
    cipher = N.NaibbeCipher(deck=deck, p_unigram=p_uni)
    return cipher.encrypt(plaintext_words(cid), seed=seed, n_words_out=n_tokens)


def fit_generators(ms_words: list[str], K: int = 12) -> dict[str, G.Adapter]:
    """Grammar generators fitted (token-weighted) on all of MS 408 -- in-sample by construction."""
    seg = lambda w: tuple(SEG(w))                                        # noqa: E731
    wts = dict(Counter(ms_words))
    gens = {
        "Learned slot grammar K=12 (EM, MS 408)": G.LearnedUnit(seg, "slot", K),
        "Learned slot-conditioned bigram K=12 (MS 408)": G.LearnedUnit(seg, "slotbi", K),
        "Zattera slot alphabet (hand-coded slots, EM probs on MS 408)": G.Escaped(seg, "zattera"),
        "Zattera slots + slot-conditioned bigram (MS 408)": G.Escaped(seg, "zattera_bi"),
        "Stolfi grammar (rule probs re-fitted on MS 408)": G.Escaped(seg, "stolfi"),
        "Stolfi grammar (published rule probs)": G.Escaped(seg, "stolfi_pub"),
    }
    for g in gens.values():
        g.fit(wts, 0)
    return gens


def grammar_words(g: G.Adapter, seed: int, n_tokens: int) -> list[str]:
    rng = random.Random(seed)
    if isinstance(g, G.Escaped):
        # normal-word grammars generate only covered words (the escape to the letter-pair model is a scoring device, not a generator)
        return g.sample(n_tokens, rng)
    return g.sample(n_tokens, rng)


def build_specs(n_tokens: int, gens: dict, seeds: int = 5, fitted_params: dict | None = None) -> list[dict]:
    specs: list[dict] = []

    def add(mech, variant, seed, build, base=""):
        specs.append(dict(mechanism=mech, variant=variant, seed=seed, build=build, base=base))
    for cid in NAIBBE_LATIN + NAIBBE_ITALIAN:
        lang = "Latin" if cid in NAIBBE_LATIN else "Italian"
        for s in range(1, seeds + 1):
            add("Naibbe cipher, 78-card deck", f"{cid} s{s}", s, (lambda c=cid, s=s: naibbe_words(c, 78, s, n_tokens)), cid)
        add("Naibbe cipher, 52-card deck", f"{cid} s1", 1, (lambda c=cid: naibbe_words(c, 52, 1, n_tokens)), cid)
        if cid in ("la_vulgate", "it_dante"):
            for s in range(1, 4):
                add("Naibbe cipher, 78-card deck, 50:50 respacing", f"{cid} s{s}", s,
                    (lambda c=cid, s=s: naibbe_words(c, 78, s, n_tokens, N.P_UNIGRAM_BALANCED)), cid)
    for s in SC_SEEDS[:seeds]:
        add("Self-citation (authors' defaults)", f"seed {s}", s, (lambda s=s: S.generate({}, s, n_tokens, tag="default")))
        if fitted_params is not None:
            add("Self-citation (fitted within documented bounds)", f"seed {s}", s,
                (lambda s=s: S.generate(fitted_params, s, n_tokens, tag="fitted")))
    for name, g in gens.items():
        for s in range(1, seeds + 1):
            add(name, f"sample {s}", s, (lambda g=g, s=s: grammar_words(g, s, n_tokens)))
    return specs


def _run_spec(sp: dict) -> dict:
    WSR._one_thread()
    t = time.time()
    w = sp["build"]()
    m = evaluate(w, seed=max(sp["seed"], 1))
    return {"mechanism": sp["mechanism"], "variant": sp["variant"], "base": sp["base"], "seed": sp["seed"],
            "n_tokens": len(w), "seconds": time.time() - t, **m}


# ------------------------------------------------------------------ self-citation fit

def light_metrics(words: list[str], seed: int = 1) -> dict:
    from . import stats as ST
    ws = ST.word_stats(words, SEG, seed)
    lens = np.array([len(SEG(w)) for w in words], float)
    ident, near = CM.repeat_rates(words)
    return {**{k: ws[k] for k in ("type_token_ratio", "hapax_share_of_types", "top10_token_coverage", "word_entropy_H1",
                                  "zipf_mle_s_r10_1000", "heaps_beta_in_order")},
            "mean_word_length_units": float(lens.mean()), "adjacent_identical_rate": ident, "adjacent_edit1_rate": near}


def fit_distance(m: dict, ms: dict, se: dict, floor_rel: float = 0.02) -> tuple[float, dict]:
    """RMS z over :data:`FIT_METRICS`; scale = sqrt(se_MS^2 + (floor_rel |MS|)^2) so tiny MS SEs do not dominate."""
    z = {}
    for k in FIT_METRICS:
        scale = math.sqrt((se.get(k) or 0.0) ** 2 + (floor_rel * abs(ms[k])) ** 2) or 1e-9
        z[k] = (m[k] - ms[k]) / scale
    return float(math.sqrt(np.mean([v * v for v in z.values()]))), z


def _sweep_eval(job):
    WSR._one_thread()
    stage, label, params, seed, n_tokens, ms, se = job
    w = S.generate(params, seed, n_tokens, use_cache=False)
    m = light_metrics(w, seed)
    d, z = fit_distance(m, ms, se)
    return {"stage": stage, "label": label, "seed": seed, "distance": d, **{f"p:{k}": v for k, v in params.items() if k in S.SWEPT},
            **{f"m:{k}": v for k, v in m.items()}, **{f"z:{k}": v for k, v in z.items()}}


def _perturb(rng: random.Random, p: dict) -> dict:
    q = dict(p)
    for k in rng.sample(S.SWEPT, rng.randint(1, 3)):
        if k in S.BOUNDS:
            lo, hi = S.BOUNDS[k]
            q[k] = int(min(hi, max(lo, round(q.get(k, S.DEFAULTS[k]) + rng.gauss(0, 0.2 * (hi - lo))))))
        else:
            q[k] = rng.choice(S.CHOICES[k])
    return q


def selfcitation_fit(n_tokens: int, ms: dict, se: dict, n_random: int = 60, n_local: int = 24, workers=None,
                     seed: int = 0, log=print) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Random search + local refinement + one-at-a-time sweep inside the documented bounds. Returns (best params, sweep table, OAT table)."""
    rng = random.Random(seed)
    jobs = [("default", "authors' defaults", {}, s, n_tokens, ms, se) for s in SWEEP_SEEDS]
    cands = [sample_with_defaults(rng) for _ in range(n_random)]
    jobs += [("random", f"r{i}", p, s, n_tokens, ms, se) for i, p in enumerate(cands) for s in SWEEP_SEEDS]
    log(f"self-citation sweep: {len(jobs)} generator runs (random search)")
    rows = CI.pmap(_sweep_eval, jobs, workers)
    df = pd.DataFrame(rows)
    key = lambda d: d.groupby("label")["distance"].mean().sort_values()          # noqa: E731
    top = [l for l in key(df[df.stage == "random"]).index[:3]]
    byl = {f"r{i}": p for i, p in enumerate(cands)}
    jobs2 = []
    for t in top:
        for j in range(n_local):
            q = _perturb(rng, byl[t])
            jobs2 += [("local", f"{t}~{j}", q, s, n_tokens, ms, se) for s in SWEEP_SEEDS]
            byl[f"{t}~{j}"] = q
    log(f"local refinement around {top}: {len(jobs2)} runs")
    df2 = pd.DataFrame(CI.pmap(_sweep_eval, jobs2, workers))
    all_df = pd.concat([df, df2], ignore_index=True)
    rank = key(all_df[all_df.stage != "default"])
    best_label = rank.index[0]
    best = byl[best_label]
    # one-at-a-time sweep around the authors' defaults
    oat_jobs = []
    for k, (lo, hi) in S.BOUNDS.items():
        for v in sorted({lo, lo + (hi - lo) // 4, lo + (hi - lo) // 2, lo + 3 * (hi - lo) // 4, hi, S.DEFAULTS[k]}):
            oat_jobs += [("oat", f"{k}={v}", {k: v}, s, n_tokens, ms, se) for s in SWEEP_SEEDS]
    for k, ch in S.CHOICES.items():
        for v in ch:
            oat_jobs += [("oat", f"{k}={v}", {k: v}, s, n_tokens, ms, se) for s in SWEEP_SEEDS]
    log(f"one-at-a-time sweep: {len(oat_jobs)} runs")
    oat = pd.DataFrame(CI.pmap(_sweep_eval, oat_jobs, workers))
    oat["param"] = oat["label"].str.split("=").str[0]
    oat["value"] = oat["label"].str.split("=").str[1]
    all_df["best"] = all_df["label"] == best_label
    return best, all_df, oat


def sample_with_defaults(rng: random.Random) -> dict:
    p = S.sample_params(rng)
    return p


# ------------------------------------------------------------------ verdicts / scorecards

def mechanism_table(runs: pd.DataFrame, ms: dict, se: dict, metrics: list[str] | None = None,
                    groups: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame:
    metrics = metrics or [m for m in SUITE if m in runs.columns]
    rows = []
    sets = groups or {k: g for k, g in runs.groupby("mechanism", sort=False)}
    for mech, g in sets.items():
        if len(g) < CI.MIN_MEMBERS:               # no honest SD from < 3 runs: raw rows stay in runs.csv
            continue
        for m in metrics:
            v = CI.interval_verdict(float(ms.get(m, float("nan"))), se.get(m), g[m].astype(float).tolist())
            rows.append({"mechanism": mech, "metric": m, "label": SUITE[m][0], "group": SUITE[m][1], "ms408": ms.get(m),
                         "ms_se": se.get(m, float("nan")), "mech_mean": v["family_mean"], "mech_sd": v["family_sd"],
                         "n_runs": v["n_members"], "z": v["z"], "pi_lo": v["pi_lo"], "pi_hi": v["pi_hi"], "verdict": v["verdict"]})
    return pd.DataFrame(rows)


def scorecard(tab: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (mech, grp), g in tab.groupby(["mechanism", "group"], sort=False):
        rows.append({"mechanism": mech, "group": grp, "n_metrics": len(g), "reproduced": int((g.verdict == "≈").sum()),
                     "too_high": int((g.verdict == "↑").sum()), "too_low": int((g.verdict == "↓").sum())})
    sc = pd.DataFrame(rows)
    return sc


def size_matched(ms_words: list[str], best: dict | None, n: int = 10900, seeds: int = 5) -> pd.DataFrame:
    """The reference generator was published on a ~10.9k-token text (1200 lines); compare it with MS 408 windows of the same size
    (type-token statistics depend on length, so the 35k comparison alone could be unfair to the authors' default text)."""
    if not S.available():
        return pd.DataFrame()
    rows = []
    for i in range(0, len(ms_words) - n + 1, n):
        rows.append({"corpus": f"MS 408 window {i // n + 1}", **light_metrics(ms_words[i:i + n])})
    for name, params in (("self-citation defaults", {}), ("self-citation fitted", best)):
        if params is None:
            continue
        for s in range(1, seeds + 1):
            rows.append({"corpus": f"{name} (seed {s})", **light_metrics(S.generate(params, s, n, use_cache=False))})
    df = pd.DataFrame(rows)
    df["group"] = df["corpus"].str.replace(r" \(seed \d+\)| window \d+", "", regex=True)
    return df


def naibbe_info() -> dict:
    """Decryption round trip and cost statistics of the cipher on 3,000 words of the Vulgate."""
    c = N.NaibbeCipher(deck=78)
    pt = plaintext_words("la_vulgate")[:3000]
    ct = c.encrypt(pt, seed=7)
    plain = N.clean_plaintext(" ".join(pt))
    ok = c.decrypt(ct) == plain
    return {"roundtrip": f"decrypt(encrypt(x)) == x for {len(plain):,} plaintext letters / {len(ct):,} ciphertext words: {ok}",
            "tokens_per_letter": len(ct) / len(plain), "retries_per_bigram": c.retries / max(c.bigrams, 1), "stats": c.stats()}


def run_mechanisms(out_dir: Path | None = None, n_tokens: int = 35000, seeds: int = 5, workers: int | None = None, sweep: bool = True,
                   reuse: bool = False, make_plots: bool = True, quiet: bool = False, K: int = 12, main_file=None) -> dict:
    from . import mechanisms_report as R
    out = Path(out_dir) if out_dir else reports_dir() / "mechanisms"
    out.mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(exist_ok=True)
    log = (lambda *a: None) if quiet else (lambda *a: print(*a, flush=True))
    WSR._one_thread()
    log("MS 408 reference ...")
    ms, se, msc = ms_reference(K, main_file)
    ms_words = msc[WSR.MS_MAIN]["words"]
    n_tokens = len(ms_words) if n_tokens <= 0 else n_tokens
    pd.DataFrame([{"metric": k, "ms408": ms.get(k), "se": se.get(k)} for k in SUITE]).to_csv(out / "ms408_reference.csv", index=False)

    # ---- 2. self-citation: sweep + fit (lexicon metrics only)
    sweep_df = oat_df = None
    best = None
    if S.available() or (out / "selfcitation_best_params.json").exists():
        import json
        pf = out / "selfcitation_best_params.json"
        if reuse and pf.exists():
            best = json.loads(pf.read_text())
            sweep_df = pd.read_csv(out / "selfcitation_sweep.csv") if (out / "selfcitation_sweep.csv").exists() else None
            oat_df = pd.read_csv(out / "selfcitation_oat.csv") if (out / "selfcitation_oat.csv").exists() else None
        elif sweep and S.available():
            best, sweep_df, oat_df = selfcitation_fit(n_tokens, ms, se, workers=workers, log=log)
            sweep_df.to_csv(out / "selfcitation_sweep.csv", index=False)
            oat_df.to_csv(out / "selfcitation_oat.csv", index=False)
            pf.write_text(json.dumps(best, indent=1))
        elif pf.exists():
            best = json.loads(pf.read_text())
    # ---- grammar generators (in-sample, fitted on MS 408)
    log("fitting grammar generators on MS 408 ...")
    gens = fit_generators(ms_words, K)
    # parse cache for the Stolfi grammar must exist before forking (it is shared by every worker)
    st = _stolfi()
    for w in set(ms_words):
        st.covers(w)

    runs_file = out / "runs.csv"
    if reuse and runs_file.exists():
        runs = pd.read_csv(runs_file)
    else:
        specs = build_specs(n_tokens, gens, seeds, best)
        log(f"{len(specs)} mechanism runs through the full suite ...")
        rows = CI.pmap(lambda i: _run_spec(specs[i]), range(len(specs)), workers)   # jobs are indices (lambdas are not picklable)
        runs = pd.DataFrame(rows)
        # reference rows: MS 408 variants and natural Latin
        refs = []
        for nm in ("MS408 P tokens shuffled (collapsed)", "MS408 P letters shuffled in tokens (collapsed)"):
            if nm in msc:
                m = evaluate(msc[nm]["words"], K) if "letters" not in nm else evaluate(["".join(t) for t in msc[nm]["tokens"]], K)
                refs.append({"mechanism": "reference: " + nm, "variant": "-", "base": "-", "seed": 0, "n_tokens": len(msc[nm]["words"]), **m})
        for cid in ("la_vulgate", "la_pliny_herbal", "it_dante"):
            try:
                w = load_tokens(cid, n_tokens)
            except FileNotFoundError:
                continue
            refs.append({"mechanism": "reference: plaintext " + cid, "variant": "-", "base": cid, "seed": 0, "n_tokens": len(w), **evaluate(w, K)})
        runs = pd.concat([runs, pd.DataFrame(refs)], ignore_index=True)
        runs.to_csv(runs_file, index=False)

    # ---- grouped verdicts
    mech_runs = runs[~runs.mechanism.str.startswith("reference")]
    groups = {k: g for k, g in mech_runs.groupby("mechanism", sort=False)}
    nb = mech_runs[mech_runs.mechanism == "Naibbe cipher, 78-card deck"]
    groups["Naibbe 78-card, Latin plaintexts only"] = nb[nb.base.isin(NAIBBE_LATIN)]
    groups["Naibbe 78-card, Italian plaintexts only"] = nb[nb.base.isin(NAIBBE_ITALIAN)]
    tab = mechanism_table(mech_runs, ms, se, groups=groups)
    tab.to_csv(out / "mechanism_verdicts.csv", index=False)
    sc = scorecard(tab)
    sc.to_csv(out / "mechanism_scorecard.csv", index=False)
    # Naibbe per plaintext (mean over seeds)
    per = nb.groupby("base")[[m for m in SUITE if m in nb.columns]].mean()
    per.to_csv(out / "naibbe_per_plaintext.csv")

    # ---- held-out grammar comparison on MS 408
    gcf = out / "grammar_comparison_ms408.csv"
    if reuse and gcf.exists():
        gcdf = pd.read_csv(gcf, index_col="model")
    else:
        log("held-out grammar comparison on MS 408 ...")
        gc = G.compare_grammars(ms_words, msc[WSR.MS_MAIN]["blocks"], lambda w: tuple(SEG(w)), K=K, n_folds=4, seed=1)
        gcdf = pd.DataFrame(gc).T
        gcdf.index.name = "model"
        gcdf.to_csv(gcf)

    ni = naibbe_info()
    sm = size_matched(ms_words, best)
    if len(sm):
        sm.to_csv(out / "selfcitation_size_matched.csv", index=False)
    res = {"naibbe_info": ni, "size_matched": sm, "ms": ms, "se": se, "runs": runs, "table": tab, "scorecard": sc, "grammar": gcdf, "best_params": best,
           "sweep": sweep_df, "oat": oat_df, "out": out, "n_tokens": n_tokens, "naibbe_per_plaintext": per}
    (out / "REPORT.md").write_text(R.report_markdown(res), encoding="utf-8")
    if make_plots:
        R.make_plots(res)
    log("wrote", out)
    return res
