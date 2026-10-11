"""Run the statistics suite on MS 408 and on every control; write comparison tables and plots.

Outputs (``reports/controls/``): ``comparison.csv`` (one row per control / MS variant: mean over
seeds), ``comparison_sd.csv`` (SD over seeds for stochastic controls), ``comparison_runs.csv``
(every run), ``family_ranges.csv`` + ``verdicts.csv`` + ``verdict_summary.csv`` (does MS 408 fall
inside each hypothesis family's observed range, metric by metric), ``size_sensitivity.csv``,
``comparison.md`` and ``figures/*.png``.

Reading the output: a family "range" is the min..max over its members (often only 2-3
controls built from 1-2 base texts), widened by an arbitrary tolerance per metric. That is a
coarse screening device, not a hypothesis test. MS 408 is undeciphered; falling inside or
outside a family's band says nothing decisive about what the text is.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from . import controls_transforms as T
from .analysis import md_table
from .controls_metrics import METRIC_INFO, metrics, verdict
from .controls_text import TARGET_TOKENS, load_tokens
from .paths import reports_dir

PLAIN = ["la_vulgate", "la_augustine", "it_dante", "it_manzoni", "de_walther_mhg"]
BASES = ["la_vulgate", "it_manzoni"]     # texts the transformations are applied to
SEED_DEFAULT = 3

# transformation name -> hypothesis family
TRANSFORM_FAMILY = {
    "abjad": "abjad (vowels removed)",
    "monoalphabetic": "monoalphabetic substitution",
    "caesar3": "monoalphabetic substitution",
    "vigenere_k3": "polyalphabetic (Vigenere)",
    "vigenere_k6": "polyalphabetic (Vigenere)",
    "nomenclator": "nomenclator-like syllable code",
    "verbose_2sym": "verbose cipher (letter -> 2 symbols)",
    "naibbe_like": "Naibbe-inspired homophonic tiles",
    "reverse_words": "word reversal",
    "alphagram": "anagram (alphagram)",
    "shuffle_letters": "letters shuffled inside words",
    "shuffle_tokens": "shuffled tokens",
}
STOCHASTIC_TRANSFORMS = {"monoalphabetic", "vigenere_k3", "vigenere_k6", "nomenclator", "verbose_2sym",
                         "naibbe_like", "shuffle_letters", "shuffle_tokens"}
FAMILY_PLAIN = "natural-language plaintext (Latin/Italian/MHG)"
FAMILY_MS_MARKOV = "Markov o2 TRAINED ON MS 408 (matches by construction)"


def _word_sets(n_tokens: int) -> dict[str, list[str]]:
    return {cid: load_tokens(cid, n_tokens) for cid in PLAIN}


def control_specs(n_tokens: int, seeds: int, plain: dict[str, list[str]], ms_train: list[str] | None):
    """Yield (name, family, base, stochastic, builder(seed)->words)."""
    specs = []
    for cid in PLAIN:
        specs.append((f"plain:{cid}", FAMILY_PLAIN, cid, False, lambda s, c=cid: plain[c]))
    for tr, fam in TRANSFORM_FAMILY.items():
        for b in BASES:
            specs.append((f"{tr}:{b}", fam, b, tr in STOCHASTIC_TRANSFORMS,
                          lambda s, tr=tr, b=b: T.TRANSFORMS[tr](plain[b], s)))
    for b in BASES:
        specs.append((f"markov_o2:{b}", "Markov character gibberish", b, True,
                      lambda s, b=b: T.markov_char(plain[b], n_tokens, 2, s)))
        specs.append((f"markov_o1:{b}", "Markov character gibberish", b, True,
                      lambda s, b=b: T.markov_char(plain[b], n_tokens, 1, s)))
        specs.append((f"iid_letters:{b}", "iid letters (no structure)", b, True,
                      lambda s, b=b: T.iid_letters(plain[b], n_tokens, s)))
    for p in (0.15, 0.3, 0.5):
        specs.append((f"selfcitation_p{p}", "self-citation generator", "-", True,
                      lambda s, p=p: T.selfcitation(n_tokens, s, p_mutate=p)))
    for p in (0.2, 0.35, 0.5):
        specs.append((f"slot_grammar_p{p}", "slot-grammar generator", "-", True,
                      lambda s, p=p: T.slot_grammar(n_tokens, s, p_second_core=p)))
    if ms_train:
        specs.append(("markov_o2:ms408", FAMILY_MS_MARKOV, "ms408", True,
                      lambda s: T.markov_char(ms_train, n_tokens, 2, s)))
    return specs


def ms_variants(main_file=None, uncertain: str = "split"):
    """Word lists + segmenters for MS 408 (target) rows. Returns (rows, train_words) or ({}, None)."""
    from .analysis import groups, load_corpus
    from .corpus_view import readable_words
    from .segment import Segmenter
    try:
        corpus = load_corpus(main_file)
    except FileNotFoundError:
        return {}, None
    grp = groups(corpus, uncertain)
    coll = Segmenter.preset("collapsed")
    raw = Segmenter.preset("raw")
    P = readable_words(grp["P"])
    rows = {
        "MS408 P (collapsed units)": (P, coll),
        "MS408 P (raw EVA chars)": (P, raw),
        "MS408 Currier A (collapsed)": (readable_words(grp["A"]), coll),
        "MS408 Currier B (collapsed)": (readable_words(grp["B"]), coll),
        "MS408 P tokens shuffled (collapsed)": (T.shuffle_tokens(P, 1), coll),
        "MS408 P letters shuffled in tokens (collapsed)": (_shuffle_units_in_tokens(P, coll, 1), coll),
    }
    # single-char encoding of the collapsed units, for the Markov-trained-on-MS control
    comps = {}
    train = []
    for w in P:
        u = coll(w)
        train.append("".join(comps.setdefault(x, x if len(x) == 1 else chr(0x100 + len(comps))) for x in u))
    return rows, train


def _shuffle_units_in_tokens(words, seg, seed):
    import random
    rng = random.Random(seed)
    out = []
    for w in words:
        u = list(seg(w))
        rng.shuffle(u)
        out.append("".join(u))
    return out


def run_controls(n_tokens: int = TARGET_TOKENS, seeds: int = SEED_DEFAULT, out_dir: Path | None = None,
                 main_file=None, make_plots: bool = True, quiet: bool = False) -> dict:
    out = Path(out_dir) if out_dir else reports_dir() / "controls"
    out.mkdir(parents=True, exist_ok=True)
    log = (lambda *a: None) if quiet else (lambda *a: print(*a, flush=True))
    plain = _word_sets(n_tokens)
    ms_rows, ms_train = ms_variants(main_file)
    if not ms_rows:
        log("MS 408 transcription not found (python -m msdecipher fetch): controls only, no verdicts")
    runs, meta, samples = [], {}, {}
    # MS rows
    for name, (w, seg) in ms_rows.items():
        m = metrics(w, seg, seed=1)
        runs.append({"name": name, "family": "MS 408", "base": "-", "seed": 0, **m})
        meta[name] = ("MS 408", "-", False)
        samples[name] = w
        log("ms", name)
    for name, fam, base, stoch, build in control_specs(n_tokens, seeds, plain, ms_train):
        for s in (range(1, seeds + 1) if stoch else [0]):
            w = build(s)
            m = metrics(w, None, seed=s)
            runs.append({"name": name, "family": fam, "base": base, "seed": s, **m})
            if s <= 1:
                samples[name] = w
        meta[name] = (fam, base, stoch)
        log("ctrl", name, "tokens", len(w))
    runs_df = pd.DataFrame(runs)
    runs_df.to_csv(out / "comparison_runs.csv", index=False)
    mcols = [c for c in runs_df.columns if c not in ("name", "family", "base", "seed")]
    order = list(dict.fromkeys(runs_df["name"]))
    grp = runs_df.groupby("name", sort=False)
    mean_df = grp[mcols].mean().loc[order]
    sd_df = grp[mcols].std(ddof=0).loc[order]
    info = pd.DataFrame({"name": order, "family": [meta[n][0] for n in order],
                         "base": [meta[n][1] for n in order],
                         "n_runs": [int((runs_df["name"] == n).sum()) for n in order]}).set_index("name")
    comp = info.join(mean_df)
    comp.reset_index().to_csv(out / "comparison.csv", index=False)
    info.join(sd_df).reset_index().to_csv(out / "comparison_sd.csv", index=False)

    res = {"comparison": comp, "sd": sd_df, "n_tokens": n_tokens, "seeds": seeds}
    if ms_rows:
        ranges, verd, summ = family_verdicts(comp)
        ranges.to_csv(out / "family_ranges.csv", index=False)
        verd.to_csv(out / "verdicts.csv", index=False)
        summ.to_csv(out / "verdict_summary.csv", index=False)
        res.update(ranges=ranges, verdicts=verd, summary=summ)
        size = size_sensitivity(ms_rows, plain)
        size.to_csv(out / "size_sensitivity.csv", index=False)
        res["size"] = size
    (out / "comparison.md").write_text(report_markdown(res, out), encoding="utf-8")
    if make_plots:
        from . import controls_plots
        controls_plots.make_all(res, samples, out / "figures")
    log("wrote", out)
    return res


# ------------------------------------------------------------------ family screening

MS_MAIN = "MS408 P (collapsed units)"
MS_RAW = "MS408 P (raw EVA chars)"


def family_verdicts(comp: pd.DataFrame):
    """Per family and metric: min/max over member means, MS value, verdict (collapsed and raw EVA)."""
    ctrl = comp[~comp["family"].isin(["MS 408", FAMILY_MS_MARKOV])]
    ranges, verd = [], []
    for fam, g in ctrl.groupby("family", sort=False):
        for m, (label, tol, group) in METRIC_INFO.items():
            vals = g[m].astype(float)
            lo, hi = float(vals.min()), float(vals.max())
            ranges.append({"family": fam, "metric": m, "n_members": len(g), "min": lo, "max": hi})
            row = {"family": fam, "metric": m, "group": group, "tolerance": tol, "family_min": lo, "family_max": hi,
                   "n_members": len(g)}
            for tag, key in (("collapsed", MS_MAIN), ("raw", MS_RAW)):
                v = float(comp.loc[key, m])
                row[f"ms_{tag}"] = v
                row[f"verdict_{tag}"] = verdict(v, lo, hi, tol)
            verd.append(row)
    ranges_df, verd_df = pd.DataFrame(ranges), pd.DataFrame(verd)
    summ = []
    for fam, g in verd_df.groupby("family", sort=False):
        row = {"family": fam, "n_members": int(g["n_members"].iloc[0])}
        for tag in ("collapsed", "raw"):
            v = g[f"verdict_{tag}"]
            row[f"within_{tag}"] = int((v == "≈").sum())
            row[f"outside_{tag}"] = int(v.isin(["↑", "↓"]).sum())
        row["n_metrics"] = len(g)
        row["outside_metrics_collapsed"] = "; ".join(f"{m}{v}" for m, v in zip(g["metric"], g["verdict_collapsed"]) if v in "↑↓")
        summ.append(row)
    summ_df = pd.DataFrame(summ).sort_values("within_collapsed", ascending=False).reset_index(drop=True)
    return ranges_df, verd_df, summ_df


def size_sensitivity(ms_rows, plain, n_small: int = 9000) -> pd.DataFrame:
    """Same metrics on the first ``n_small`` tokens of MS 408 (manuscript order) and of the plain
    controls, to show how much each number moves with sample size alone."""
    rows = []
    P, coll = ms_rows[MS_MAIN]
    for name, w, seg in [("MS408 P first %d" % n_small, P[:n_small], coll)] + \
                        [(f"plain:{c} first {n_small}", plain[c][:n_small], None) for c in PLAIN]:
        m = metrics(w, seg, seed=1)
        rows.append({"name": name, **{k: m[k] for k in ("n_tokens", "type_token_ratio", "zipf_mle_s_r10_1000",
                                                      "heaps_beta_in_order", "unit_H1", "unit_h2", "unit_h3",
                                                      "shuffle_gap_h2", "pos_skewed_unit_share")}})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ markdown

SHOW = ["n_tokens", "type_token_ratio", "zipf_mle_s_r10_1000", "heaps_beta_shuffled", "mean_word_length_units",
        "unit_H1", "unit_h2", "unit_h3", "shuffle_gap_h2", "sukhotin_vowel_like_share", "pos_skewed_unit_share",
        "adjacent_edit1_rate"]
SHORT = {"n_tokens": "tokens", "type_token_ratio": "TTR", "zipf_mle_s_r10_1000": "Zipf s", "heaps_beta_shuffled": "Heaps β",
         "mean_word_length_units": "len", "unit_H1": "H1", "unit_h2": "h2", "unit_h3": "h3", "shuffle_gap_h2": "Δh2 shuf",
         "sukhotin_vowel_like_share": "vowel-like", "pos_skewed_unit_share": "pos-skew", "adjacent_edit1_rate": "adj-edit1"}


def report_markdown(res: dict, out: Path) -> str:
    comp: pd.DataFrame = res["comparison"]
    L = ["# Control comparison: MS 408 vs controls", "",
         "> **MS 408 is undeciphered.** This is a screening comparison of descriptive statistics, not a decipherment, "
         "and no single metric is decisive. Controls are small in number and built from a few base texts (Latin, Italian, "
         "one small Middle High German text); transformations are simplified illustrations of each family, NOT reproductions "
         "of published ciphers; generators are not fitted to MS 408. See [docs/CONTROLS.md](../../docs/CONTROLS.md).", "",
         f"Target size {res['n_tokens']} tokens per control (MS 408 running text: "
         f"{int(comp.loc[MS_MAIN, 'n_tokens']) if MS_MAIN in comp.index else 'n/a'} readable tokens); "
         f"stochastic controls are means over {res['seeds']} seeds. Controls use single characters as units; MS 408 uses the "
         "collapsed EVA segmentation (ch, sh, cth, ckh, cph, cfh as single units) unless marked raw. Tables: "
         "`comparison.csv` (means), `comparison_sd.csv`, `comparison_runs.csv`.", ""]
    t = comp.reset_index()[["name", "family"] + SHOW].rename(columns=SHORT)
    L += ["## 1. All corpora, selected metrics", "", md_table(t), ""]
    if "verdicts" in res:
        verd, summ = res["verdicts"], res["summary"]
        L += ["## 2. Which hypothesis families does MS 408 fall inside?", "",
              "For every family the band is [min, max] of its members' means, widened by a per-metric tolerance (see "
              "`controls_metrics.METRIC_INFO`; round numbers, not confidence intervals). `≈` MS 408 inside the band, `↑` above, "
              "`↓` below. The `Markov o2 trained on MS 408` control is excluded: it is built from MS 408 itself.", ""]
        piv = verd.pivot(index="metric", columns="family", values="verdict_collapsed")
        cols = list(summ["family"])
        piv = piv.loc[list(METRIC_INFO), cols]
        piv.index = [METRIC_INFO[m][0] for m in piv.index]
        short_cols = {c: (c if len(c) < 22 else c[:20] + "…") for c in cols}
        t2 = piv.rename(columns=short_cols).reset_index().rename(columns={"index": "metric"})
        L += [md_table(t2), "", "Column order = number of metrics inside the band (highest first):", ""]
        L += [f"{i + 1}. {c}" for i, c in enumerate(cols)] + [""]
        s2 = summ[["family", "n_members", "within_collapsed", "outside_collapsed", "within_raw", "outside_raw", "n_metrics"]]
        s2 = s2.rename(columns={"within_collapsed": "inside (collapsed units)", "outside_collapsed": "outside (collapsed)",
                                "within_raw": "inside (raw EVA)", "outside_raw": "outside (raw)"})
        L += ["### Summary per family", "", md_table(s2), ""]
        L += ["### Metrics where MS 408 falls OUTSIDE each family (collapsed units)", ""]
        for _, r in summ.iterrows():
            L.append(f"- **{r['family']}** ({int(r['within_collapsed'])}/{int(r['n_metrics'])} inside): "
                     f"{r['outside_metrics_collapsed'] or 'none'}")
        L += [""] + interpretation(res) + [""]
        L += ["## 3. Sample-size sensitivity (first 9,000 tokens of each)", "", md_table(res["size"]), "",
              "The first 9,000 tokens of MS 408 are mostly herbal-section text in manuscript order; the point is only how far "
              "TTR, Zipf, Heaps and entropies move when the sample shrinks to the size of the small Middle High German control.", ""]
    L += ["## Caveats", "",
          "- Few controls per family (2-3, from 1-2 base texts), so family bands are crude and partly reflect the base text.",
          "- Tokenization is a free choice: controls are normalised to a-z with diacritics folded; MS 408 uses a transcription (ZL 3b) with uncertain spaces split and unreadable tokens dropped, and unit segmentation (collapsed vs raw) changes unit-level metrics (see the `raw` columns in `verdict_summary.csv`).",
          "- Poetry (Dante, Walther) and prose (Augustine, Manzoni) differ; MS 408 pages are not independent samples (sections, hands, Currier A/B).",
          "- `Markov o2 trained on MS 408` reproduces h2 by construction and is not a hypothesis. The slot-grammar generator's inventories were written with published descriptions of Voynichese in mind (see `controls_transforms.slot_grammar`), so its match is expected, not independent evidence.",
          "- The verbose / Naibbe-inspired controls are measured on single symbols; the cipher's natural unit (a 2-3 symbol group) would give different unit statistics. The self-citation generator here is a simple copy-and-mutate toy (parameters 0.15/0.3/0.5, not fitted), far from the published Timm-Schinner generator.",
          "- Ranking families by the count of metrics inside the band is only a convenience for ordering columns; the metrics are strongly correlated, so the count is not a likelihood.",
          "- Tolerances are arbitrary round numbers; `≈` means 'not clearly separated', not 'consistent with'.",
          "- No metric here is decisive; several hypotheses (self-citation generators, verbose ciphers) are known to reproduce parts of the profile.", ""]
    return "\n".join(L)


KEY = ["unit_h2", "unit_h3", "shuffle_gap_h2", "zipf_mle_s_r10_1000", "type_token_ratio", "pos_skewed_unit_share",
       "adjacent_edit1_rate"]


def interpretation(res: dict) -> list[str]:
    """Data-driven, hedged reading of the verdict matrix."""
    verd, comp = res["verdicts"], res["comparison"]
    ms = comp.loc[MS_MAIN]
    L = ["### Reading the matrix (auto-generated from the numbers above; hedged)", "",
         f"MS 408 (collapsed units): h2 = {ms['unit_h2']:.2f} bits, h3 = {ms['unit_h3']:.2f}, h2 rise after within-word "
         f"shuffle = {ms['shuffle_gap_h2']:.2f} bits, Zipf s = {ms['zipf_mle_s_r10_1000']:.2f}, TTR = {ms['type_token_ratio']:.2f}, "
         f"{ms['pos_skewed_unit_share']:.0%} of units positionally skewed, adjacent edit-distance-1 rate {ms['adjacent_edit1_rate']:.3f}.", ""]
    for m in KEY:
        g = verd[verd["metric"] == m]
        inside = list(g.loc[g["verdict_collapsed"] == "≈", "family"])
        lab = METRIC_INFO[m][0]
        L.append(f"- **{lab}**: MS 408 is inside the band of " + (", ".join(inside) if inside else "**no** control family") + ".")
    allm = verd.groupby("metric")["verdict_collapsed"].apply(lambda v: (v == "≈").all())
    nonm = [METRIC_INFO[m][0] for m in METRIC_INFO if allm.get(m, False)]
    none_in = verd.groupby("metric")["verdict_collapsed"].apply(lambda v: (v == "≈").sum() == 0)
    outm = [METRIC_INFO[m][0] for m in METRIC_INFO if none_in.get(m, False)]
    L += ["", "- Metrics where MS 408 is inside **every** family band (non-discriminating here): " + (", ".join(nonm) or "none") + ".",
          "- Metrics where MS 408 is outside **every** family band (no control family reproduces it with these settings): "
          + (", ".join(outm) or "none") + ".", "",
          "What this does and does not say: the table shows which simplified control families have statistics near MS 408's on each "
          "metric. No family matches on all metrics, and the families that match on the most metrics (e.g. the slot-grammar generator) "
          "were designed with Voynichese structure in mind, so their match is not independent evidence. Matching on many metrics "
          "is not proof of a mechanism, and mismatching is not refutation: the controls are crude, tolerances arbitrary and "
          "several families (verbose/homophonic ciphers, self-citation generators) have parameters that could be tuned toward MS 408."]
    return L
