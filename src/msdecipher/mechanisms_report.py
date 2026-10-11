"""Markdown report and figures for :mod:`msdecipher.mechanisms_run`."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import mech_selfcitation as S

GROUP_ORDER = ["letter entropy", "within-word shuffle", "positional skew", "slot grammar", "suffix", "Zipf / Heaps", "word shape",
               "adjacent repeats", "cluster stability", "grammar coverage"]


def _f(v, nd=3):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    if isinstance(v, (float, np.floating)) and math.isinf(v):
        return "+inf" if v > 0 else "-inf"       # zero run-to-run spread (e.g. a deterministic coverage)
    return f"{v:.{nd}f}"


def _md(df: pd.DataFrame, cols=None, nd=3) -> list[str]:
    cols = cols or list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(_f(r[c], nd) if isinstance(r[c], (float, np.floating)) else str(r[c]) for c in cols) + " |")
    return out


SUITE_CLUSTER = ["k5_ari_boot", "k5_ari_split", "sil_k5", "class_mi_excess_k5", "nmi_last_unit_excess_k5"]


def matrix(sc: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for mech, g in sc.groupby("mechanism", sort=False):
        d = {"mechanism": mech}
        tot_ok = tot = 0
        for _, r in g.iterrows():
            d[r["group"]] = f"{r['reproduced']}/{r['n_metrics']}"
            tot_ok += r["reproduced"]
            tot += r["n_metrics"]
        d["all"] = f"{tot_ok}/{tot}"
        rows.append(d)
    df = pd.DataFrame(rows)
    return df[["mechanism"] + [c for c in GROUP_ORDER if c in df.columns] + ["all"]]


def mech_section(tab: pd.DataFrame, mech: str) -> list[str]:
    t = tab[tab.mechanism == mech]
    out = [f"#### {mech}", "", "| metric | MS 408 (±SE) | mechanism mean (SD over runs) | z | verdict |", "|---|---|---|---|---|"]
    for grp in GROUP_ORDER:
        for _, r in t[t.group == grp].iterrows():
            out.append(f"| {r['label']} | {_f(r['ms408'])} ± {_f(r['ms_se'])} | {_f(r['mech_mean'])} ({_f(r['mech_sd'])}) | {_f(r['z'], 1)} | {r['verdict']} |")
    out.append("")
    return out


def _lists(t: pd.DataFrame) -> tuple[list[str], list[str]]:
    ok = [r["label"] for _, r in t.iterrows() if r["verdict"] == "≈"]
    miss = [f"{r['label']} ({r['verdict']}, z={r['z']:.1f})" for _, r in t.reindex(t["z"].abs().sort_values(ascending=False).index).iterrows() if r["verdict"] in ("↑", "↓")]
    return ok, miss


def findings(res: dict) -> list[str]:
    tab, runs = res["table"], res["runs"]
    out = []
    for mech in tab.mechanism.unique():
        t = tab[tab.mechanism == mech]
        ok, miss = _lists(t)
        out.append(f"- **{mech}**: reproduces {len(ok)}/{len(t)} suite metrics within the 95 % prediction interval "
                   f"(MS 408 SE + run-to-run spread). Misses (largest |z| first): {', '.join(miss[:6]) if miss else 'none'}.")
    return out


def sweep_text(res: dict) -> list[str]:
    sw, oat, best = res.get("sweep"), res.get("oat"), res.get("best_params")
    if sw is None:
        return ["_Self-citation sweep not run (no JDK / `--no-sweep`)._", ""]
    d = sw.groupby(["stage", "label"])["distance"].mean().reset_index()
    default = d[d.stage == "default"]["distance"].iloc[0]
    rnd = d[d.stage == "random"]["distance"]
    loc = d[d.stage == "local"]["distance"]
    bestd = d[d.stage != "default"]["distance"].min()
    out = [f"Distance = RMS z over the nine lexicon-level fit metrics ({', '.join(S_FIT())}); scale per metric = sqrt(SE_MS² + (2 % of MS value)²). "
           "Lower is better; 1 ≈ 'within one SE-ish' on average.", "",
           f"* authors' defaults (conf.properties): **{default:.2f}** (mean over {len(S_SEEDS())} sweep seeds)",
           f"* random search, {len(rnd)} parameter vectors inside the documented bounds: median {rnd.median():.2f}, "
           f"min {rnd.min():.2f}, max {rnd.max():.2f}; {int((rnd < default).sum())} of {len(rnd)} beat the defaults",
           f"* local refinement ({len(loc)} vectors around the best three): min {loc.min():.2f}" if len(loc) else "",
           f"* **best vector: {bestd:.2f}**", ""]
    out += ["Best parameters (all inside the documented bounds; unlisted parameters keep the defaults):", "", "| parameter | default | best | documented range |", "|---|---|---|---|"]
    for k in S.SWEPT:
        rng = S.BOUNDS.get(k) or "/".join(S.CHOICES[k])
        out.append(f"| `{k}` | {S.DEFAULTS[k]} | {best.get(k, S.DEFAULTS[k])} | {rng} |")
    out.append("")
    zc = [c for c in sw.columns if c.startswith("z:")]
    zz = sw[sw.label.isin(["authors' defaults"])][zc].mean()
    bl = sw[sw["best"]][zc].mean() if "best" in sw else None
    out += ["Fit quality per fit metric (z against MS 408; sweep seeds):", "", "| metric | z at defaults | z at best |", "|---|---|---|"]
    for c in zc:
        out.append(f"| {c[2:]} | {zz[c]:.1f} | {bl[c]:.1f} |" if bl is not None else f"| {c[2:]} | {zz[c]:.1f} | – |")
    out.append("")
    if oat is not None and len(oat):
        g = oat.groupby(["param", "value"])["distance"].mean().reset_index()
        sens = g.groupby("param")["distance"].agg(["min", "max"]).assign(range=lambda x: x["max"] - x["min"]).sort_values("range", ascending=False)
        out += ["One-at-a-time sweep (all other parameters at the defaults): fit distance range per parameter", "",
                "| parameter | min D | max D | range |", "|---|---|---|---|"]
        for p, r in sens.iterrows():
            out.append(f"| `{p}` | {r['min']:.2f} | {r['max']:.2f} | {r['range']:.2f} |")
        out.append("")
    return out


def size_text(sm) -> list[str]:
    if sm is None or not len(sm):
        return []
    cols = [c for c in sm.columns if c not in ("corpus", "group")]
    g = sm.groupby("group", sort=False)[cols].mean().reset_index()
    sd = sm.groupby("group", sort=False)[cols].std().reset_index()
    out = ["Size-matched check (10,900 tokens, the size of the authors' default 1200-line text; MS 408 = its three consecutive 10,900-token windows, "
           "generator = 5 seeds; mean, and SD across windows/seeds in the last rows):", ""]
    out += _md(g, nd=3) + [""] + ["SD across windows / seeds:", ""] + _md(sd, nd=3) + [""]
    return out


def S_FIT():
    from .mechanisms_run import FIT_METRICS
    return FIT_METRICS


def S_SEEDS():
    from .mechanisms_run import SWEEP_SEEDS
    return SWEEP_SEEDS


def grammar_text(gc: pd.DataFrame) -> list[str]:
    cols = ["bits_tok", "bits_type", "bits_newtype", "cov_tok", "cov_type", "cov_newtype", "mdl_tok", "mdl_type", "mdl_type_params", "mdl_type_structure"]
    g = gc.reset_index()
    out = ["Held-out (4-fold CV by folio) bits per word, coverage (share the hard grammar can generate at all) and full-data MDL, on MS 408 'P' text "
           "(collapsed-EVA units, words of ≤ 12 units). All models are scored as distributions over EVA *strings*, so unit inventories do not matter. "
           "Hand-coded grammars get an escape to the letter-pair model for words they cannot generate (weight = training-uncovered share), so their bits "
           "include the price of every miss. 'tok' = token weighted, 'type' = each held-out type once, 'newtype' = held-out types not seen in training.", ""]
    show = g[["model"] + [c for c in cols if c in g.columns]].copy()
    out += _md(show, nd=3)
    out.append("")
    b = gc.loc[[i for i in gc.index if "letter-pair" in i]].iloc[0]
    for kind in ("tok", "type", "newtype"):
        row = []
        for m, r in gc.iterrows():
            if f"bits_{kind}" in r and not pd.isna(r[f"bits_{kind}"]):
                row.append((r[f"bits_{kind}"], m))
        row.sort()
        out.append(f"* best held-out bits ({kind}): " + "; ".join(f"{m} {v:.2f}" for v, m in row[:3]) + f" — letter-pair baseline {b[f'bits_{kind}']:.2f}")
    out.append("")
    return out


def report_markdown(res: dict) -> str:
    tab, sc, runs, ms, se = res["table"], res["scorecard"], res["runs"], res["ms"], res["se"]
    L = ["# Candidate generating mechanisms vs the measured structure of MS 408", "",
         "_Auto-generated by `python -m msdecipher mechanisms-run`. **MS 408 is undeciphered.** A mechanism that reproduces a metric shows that "
         "the metric does not discriminate that mechanism from MS 408; it does not show that the manuscript was produced by it. A mechanism that "
         "misses a metric is evidence against *that implementation* on *that metric* only._", "",
         "## What was run", "",
         f"* every row below is {res['n_tokens']:,} tokens of generated text pushed through exactly the metric suite used for MS 408 and the controls "
         "(`controls_metrics.metrics` + `word_structure_run.row_metrics`, collapsed-EVA units, 500-token chunks as blocks);",
         "* MS 408 = the 34,977-token 'P' running text; its SEs are the delete-one-block jackknife SEs of `reports/controls/ms408_ci.csv` and "
         "`reports/word_structure/ms408_ci.csv`;",
         "* verdict `≈` = MS 408 inside the 95 % prediction interval of the mechanism's runs (t-interval over runs, widened by MS 408's SE; "
         "`controls_ci.interval_verdict`); `↑`/`↓` = MS 408 is above/below the mechanism;",
         f"* {len(runs[~runs.mechanism.str.startswith('reference')])} mechanism runs "
         f"({runs[~runs.mechanism.str.startswith('reference')].mechanism.nunique()} mechanism variants, multiple seeds each), "
         f"{len(runs[runs.mechanism.str.startswith('reference')])} reference rows.", "",
         "## 1. Scorecard: how many suite metrics each mechanism reproduces", ""]
    L += _md(matrix(sc), nd=3)
    L += ["", "Cells are *reproduced / metrics in the group*. Groups with a single clustering/Zipf metric are noisy; read the per-metric tables below.", "",
          "## 2. Findings (auto-generated from the tables)", ""] + findings(res) + [""]
    ref = runs[runs.mechanism.str.startswith("reference")]
    if len(ref):
        keep = [m for m in ("unit_h2", "shuffle_gap_h2", "pos_skewed_unit_share", "slot_null_gap_type", "affix_suffix_type_share", "zipf_mle_s_r10_1000",
                            "adjacent_identical_rate", "k5_ari_boot", "k5_ari_split", "sil_k5", "class_mi_excess_k5", "nmi_last_unit_excess_k5") if m in ref.columns]
        d = ref[["mechanism"] + keep].copy()
        d["mechanism"] = d["mechanism"].str.replace("reference: ", "")
        d = pd.concat([pd.DataFrame([{"mechanism": "**MS 408**", **{m: ms[m] for m in keep}}]), d], ignore_index=True)
        L += ["### Reference rows: how much does each metric discriminate?", "",
              "Context for the verdicts: MS 408 itself with tokens shuffled / letters shuffled inside tokens, and natural-language plaintext. "
              "A metric on which all of these agree (notably the cluster-stability group) cannot tell mechanisms apart.", ""] + _md(d, nd=3) + [""]
    cl = [m for m in SUITE_CLUSTER if m in runs.columns]
    mm = runs[~runs.mechanism.str.startswith("reference")].groupby("mechanism", sort=False)[cl].mean().reset_index()
    msr = {"mechanism": "**MS 408 (± jackknife SE)**", **{m: f"{ms[m]:.3f} ± {se.get(m, float('nan')):.3f}" for m in cl}}
    mm = pd.concat([pd.DataFrame([msr]), mm], ignore_index=True)
    L += ["### Cluster-stability point estimates (the verdicts for this group have little power)", "",
          "MS 408's jackknife SEs for these metrics are large (0.1-0.15 on ARI), so the prediction intervals are wide and even i.i.d. samplers "
          "(ARI ≈ 0) can sit inside them (`≈`). The point estimates are more informative than the verdicts here:", ""] + _md(mm, nd=3) + [""]
    L += ["## 3. Per-mechanism detail (MS 408 vs mechanism, all suite metrics)", ""]
    for mech in tab.mechanism.unique():
        L += mech_section(tab, mech)
    L += ["## 4. Naibbe cipher", ""]
    ni = res.get("naibbe_info", {})
    if ni:
        L += [f"* decryption check: {ni.get('roundtrip')}", f"* plaintext letters per ciphertext token: {1 / ni.get('tokens_per_letter'):.2f} "
              f"(1 token = 1 or 2 letters); ambiguity retries per bigram: {ni.get('retries_per_bigram'):.2f}",
              f"* table statistics: {ni.get('stats')}", ""]
    per = res.get("naibbe_per_plaintext")
    if per is not None:
        keep = [c for c in ["unit_H1", "unit_h2", "shuffle_gap_h2", "type_token_ratio", "zipf_mle_s_r10_1000", "heaps_beta_in_order",
                            "affix_suffix_type_share", "slot_null_gap_type", "k5_ari_split", "adjacent_identical_rate"] if c in per.columns]
        d = per[keep].reset_index().rename(columns={"base": "plaintext"})
        msrow = {"plaintext": "**MS 408**", **{c: ms[c] for c in keep}}
        L += ["Per-plaintext means (78-card deck, 5 seeds each):", ""] + _md(pd.concat([d, pd.DataFrame([msrow])], ignore_index=True), nd=3) + [""]
    L += ["## 5. Self-citation generator: fit to MS 408 and parameter sweep", ""] + sweep_text(res) + size_text(res.get("size_matched"))
    L += ["## 6. Word grammars: coverage, MDL and held-out fit on MS 408", ""] + grammar_text(res["grammar"])
    L += ["## 7. Faithfulness, limitations and what was not done", ""] + limitations()
    return "\n".join(L) + "\n"


def limitations() -> list[str]:
    return [
        "* **Naibbe**: tables, card weights, respacing probability and the unambiguity rule are the author's (MIT code/tables, Greshko 2025, "
        "commit f2675ec); the full text of the Cryptologia paper sits behind a bot wall and could not be fetched, so details were taken from the "
        "released code and from paper excerpts in search snippets (card-table mapping 5:2:2:2:1:1, 52/78-card decks, unigram/bigram respacing, "
        "Zattera-style slot grammar for affixes). The author's *Voynichesque* model and spreadsheets were not used. No nulls, line or paragraph structure "
        "(the paper lists this as a known limitation); one fresh deck per ~60 plaintext letters (the author's code uses one per plaintext line).",
        "* **Self-citation**: run through the authors' own Java source (JDK 17, log4j 1.2.17), not re-implemented, because the algorithm is defined "
        "by ~5,000 lines of rules; the paper's text (behind a bot wall) was only seen in snippets. Parameters swept are those exposed in `conf.properties` "
        "inside their documented ranges; the `voynich` / `statistic` / `percent` follow rules are excluded as circular. The generator embeds VMS-derived "
        "priors (glyph classes, the f103v seed line, `daiin`/`ol`/`chedy` suggestion types), so a good match is not independent evidence.",
        "* **Zattera**: the 12-slot table is transcribed from Zandbergen's reproduction (voynich.nu/a3_para.html §3.5.4) of Zattera (2022); the paper's own "
        "probabilities and its transliteration alphabet were not available, so the hand-coded part is the slot *structure*; probabilities are EM-fitted here. "
        "Coverage depends on the transcription used here (ZL 3b, collapsed EVA).",
        "* **Stolfi**: the normal-word PCFG with its counts is transcribed from the 2000 note; the abnormal-word lists are not part of the grammar and are "
        "counted as uncovered. The 'published probabilities' variant was fitted by Stolfi on the whole 1998 text, so it is *not* a held-out result; "
        "the re-fitted variant re-estimates rule probabilities on the training folios only.",
        "* **In-sample generators**: the grammar generators (learned slot, slot-conditioned bigram, Zattera, Stolfi) are fitted to all of MS 408 and sampled "
        "i.i.d. They show what a word grammar *alone* can reproduce (an upper bound), not an independent test; they have no memory between words, "
        "so repetition / page-level structure is expected to be missed.",
        "* No metric here is decisive and many are correlated; the scorecard counts are descriptive. Verdict widths depend on the number of runs.",
    ]


# ------------------------------------------------------------------ figures

def make_plots(res: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out = res["out"] / "figures"
    tab = res["table"]
    mechs = list(tab.mechanism.unique())
    mets = [m for m in dict.fromkeys(tab.metric)]
    Z = np.full((len(mechs), len(mets)), np.nan)
    for i, mch in enumerate(mechs):
        t = tab[tab.mechanism == mch].set_index("metric")
        for j, m in enumerate(mets):
            if m in t.index:
                Z[i, j] = np.clip(t.loc[m, "z"], -8, 8)
    fig, ax = plt.subplots(figsize=(max(10, 0.34 * len(mets)), 0.42 * len(mechs) + 3))
    im = ax.imshow(Z, cmap="RdBu_r", vmin=-8, vmax=8, aspect="auto")
    ax.set_xticks(range(len(mets)))
    ax.set_xticklabels([tab[tab.metric == m]["label"].iloc[0] for m in mets], rotation=75, ha="right", fontsize=7)
    ax.set_yticks(range(len(mechs)))
    ax.set_yticklabels(mechs, fontsize=7)
    for i in range(len(mechs)):
        for j in range(len(mets)):
            if not np.isnan(Z[i, j]) and abs(Z[i, j]) <= 2:
                ax.text(j, i, "≈", ha="center", va="center", fontsize=6)
    fig.colorbar(im, ax=ax, label="z = (MS 408 − mechanism) / scale   (red: MS 408 above)", shrink=0.6)
    ax.set_title("Mechanisms vs MS 408 (≈ marks |z| ≤ 2; colour clipped at ±8)")
    fig.tight_layout()
    fig.savefig(out / "mechanism_z_heatmap.png", dpi=140)
    plt.close(fig)

    sw, oat = res.get("sweep"), res.get("oat")
    if sw is not None:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        d = sw.groupby(["stage", "label"])["distance"].mean().reset_index()
        for st, c in (("random", "tab:blue"), ("local", "tab:green")):
            axes[0].hist(d[d.stage == st]["distance"], bins=20, alpha=0.6, label=st, color=c)
        axes[0].axvline(d[d.stage == "default"]["distance"].iloc[0], color="k", ls="--", label="authors' defaults")
        axes[0].set_xlabel("fit distance to MS 408 (lexicon metrics, RMS z)")
        axes[0].set_ylabel("parameter vectors")
        axes[0].legend()
        axes[0].set_title("Self-citation parameter search (documented bounds)")
        if oat is not None and len(oat):
            g = oat.groupby(["param", "value"])["distance"].mean().reset_index()
            sens = g.groupby("param")["distance"].agg(lambda x: x.max() - x.min()).sort_values()
            axes[1].barh([p.split(".", 1)[1] if "." in p else p for p in sens.index], sens.values, color="tab:orange")
            axes[1].set_xlabel("range of fit distance over the parameter's bounds")
            axes[1].set_title("One-at-a-time sensitivity")
            axes[1].tick_params(axis="y", labelsize=6)
        fig.tight_layout()
        fig.savefig(out / "selfcitation_sweep.png", dpi=140)
        plt.close(fig)

    gc = res["grammar"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    names = [n.replace(" (", "\n(") for n in gc.index]
    for ax, col, ttl in ((axes[0], "bits_type", "held-out bits per word type (lower = better)"), (axes[1], "cov_type", "held-out type coverage")):
        colors = ["tab:red" if bool(h) else "tab:blue" for h in gc["hand_coded"]]
        ax.bar(range(len(gc)), gc[col], color=colors)
        ax.set_xticks(range(len(gc)))
        ax.set_xticklabels(names, rotation=70, ha="right", fontsize=6)
        ax.set_title(ttl, fontsize=9)
    fig.suptitle("MS 408: learned (blue) vs hand-coded (red) word grammars")
    fig.tight_layout()
    fig.savefig(out / "grammar_comparison.png", dpi=140)
    plt.close(fig)
