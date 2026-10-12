"""h07 leave-one-section-out.  ``python run_h07.py predict`` (fits on training sections, writes predictions + manifest; never reads held-out text),
then ``python run_h07.py score`` (refuses to run unless the manifest matches; computes the real held-out statistics and scores)."""
from __future__ import annotations

import json
import random
import sys
import time

import numpy as np
import pandas as pd

import h07_lib as L
from h07_lib import HR, H, T, CI, L6, CLASSES

N_SEEDS = L.PREREG["seeds"]
WORKS = [w for w in T.WORKS if w != "la_augustine"]
GEN_ROWS = {   # name -> (family, description)
    "C0g global copy-modify (baseline)": ("baseline", "one global engine, no section dependence"),
    "SV P50 nearest": ("a: setting switch", "per-section pool of 50 types; held-out = nearest section's settings"),
    "SV P50 pooled": ("a: setting switch", "held-out = pool fitted on all training text"),
    "SV U nearest": ("a: setting switch", "per-section unit tilt (all units); nearest rule"),
    "SV U pooled": ("a: setting switch", "unit tilt of all training text"),
    "SV EUP25 nearest": ("a: setting switch", "per-section engine+units+pool 25; nearest rule"),
    "SV EUP25 pooled": ("a: setting switch", "engine+units+pool 25 fitted on all training text"),
    "SV EUP25 random-section (null)": ("null model", "held-out uses a random training section's EUP25 settings"),
    "A1 topic-matched": ("b: topic plaintext", "Naibbe-token hybrid; held-out encodes its topical Latin work"),
    "A2 topic-matched": ("b: topic plaintext", "whole-word codebook hybrid; held-out encodes its topical Latin work"),
    "A2 random-topic (null)": ("null model", "codebook hybrid; held-out encodes a random other work"),
}
SV_SPECS = {"P50": dict(E=False, U=False, S=50), "U": dict(E=False, U=True, S=0), "EUP25": dict(E=True, U=True, S=25)}


def fit_sv(sh, words, spec, gm_all, seed):
    base = dict(gm_all.params)
    if spec["S"] > 0:
        base["p_pool"] = 0.2
    free = L6.PARAMS if (spec["E"] and spec["S"]) else ("p_pool",) if spec["S"] else ()
    gm, _ = L6.fit_group(sh, words, spec["S"], spec["U"], free, base, seed=seed)
    return gm, len(free) + gm.k_tilt + gm.k_pool


def hybrid_words(variant, p, layout, ctx, seed, held, held_work):
    spec = HR.HYBRID_VARIANTS[variant]
    encs, steps = {}, []
    for e in layout:
        sec = e["cls"] or "text-only"
        work = held_work if sec == held else T.TOPIC_WORK[sec]
        if work not in encs:
            encs[work] = HR.make_encoder(spec["enc"], HR.plaintext(work), seed * 31 + len(encs), ctx)
        steps.append((work, len(e["words"])))
    return H.generate(None, p, 0, seed, plain_edit=spec["plain_edit"], section_encoders=encs, layout=steps)


def predict(quick=False):
    t0 = time.time()
    entries = T.folio_layout(HR.ms_data())
    # metadata only for the nearest rule (language labels, folio counts) -- no text
    near = {c: L.nearest_section(entries, c) for c in CLASSES}
    prereg = {**L.PREREG, "resolved_nearest": near, "generators": {k: list(v) for k, v in GEN_ROWS.items()}, "stats": L.STATS,
              "written": time.strftime("%Y-%m-%d %H:%M:%S %Z")}
    (L.RESULTS / "prereg.json").write_text(json.dumps(prereg, indent=1))
    nr, nl = (8, 2) if quick else (30, 8)
    rows, krows = [], []
    seeds = range(1, (3 if quick else N_SEEDS) + 1)
    for held in CLASSES:
        tr = [i for i, e in enumerate(entries) if e["cls"] != held]
        train_words = [w for i in tr for w in entries[i]["words"]]
        groups = {}
        for i in tr:
            groups.setdefault(entries[i]["cls"] or "other", []).extend(entries[i]["words"])
        # placeholder layout: training folios with their real cls, held-out folios with token COUNTS only (words replaced)
        layout = [e if e["cls"] != held else {**e, "words": [""] * len(e["words"])} for e in entries]
        sh = L6.Shared(train_words, seed=7)
        gm_all, _ = L6.fit_group(sh, train_words, 0, False, L6.PARAMS[:6], L6.DEFAULT_BASE, seed=7, n_random=nr, n_local=nl)
        krows.append({"held_out": held, "generator": "C0g global copy-modify (baseline)", "k_specific": 0, "k_global_engine": 6})
        gens = {"C0g global copy-modify (baseline)": lambda s: L6.sv_generate([{"group": "__all__", "n": len(e["words"]), "page": i} for i, e in enumerate(layout)],
                                                                             {"__all__": gm_all}, sh, s)}
        for vn, spec in SV_SPECS.items():
            models = {"__all__": gm_all}
            k = 0
            for g, ws in sorted(groups.items()):
                models[g], kg = fit_sv(sh, ws, spec, gm_all, seed=11)
                k += kg
            pooled, kp = fit_sv(sh, train_words, spec, gm_all, seed=13)

            def mk(rule, models=models, pooled=pooled):
                def f(s):
                    ms = dict(models)
                    if rule == "nearest":
                        ms[held] = models[near[held]]
                    elif rule == "pooled":
                        ms[held] = pooled
                    else:
                        ms[held] = models[random.Random(s * 101).choice([c for c in CLASSES if c != held])]
                    return L6.sv_generate([{"group": e["cls"] or "other", "n": len(e["words"]), "page": i} for i, e in enumerate(layout)], ms, sh, s)
                return f
            gens[f"SV {vn} nearest"] = mk("nearest")
            gens[f"SV {vn} pooled"] = mk("pooled")
            krows += [{"held_out": held, "generator": f"SV {vn} nearest", "k_specific": k, "k_global_engine": 6},
                      {"held_out": held, "generator": f"SV {vn} pooled", "k_specific": k + kp, "k_global_engine": 6}]
            if vn == "EUP25":
                gens["SV EUP25 random-section (null)"] = mk("random")
                krows.append({"held_out": held, "generator": "SV EUP25 random-section (null)", "k_specific": k, "k_global_engine": 6})
        ctx = HR.Ctx(train_words)
        for short, variant in (("A1", "A1 Naibbe tokens + copy-modify"), ("A2", "A2 whole-word codebook + copy-modify")):
            p, _, _ = HR.fit_variant(variant, train_words, ctx, seed=17, n_random=nr, n_local=nl, log=lambda *a: None)
            gens[f"{short} topic-matched"] = (lambda s, v=variant, p=p: hybrid_words(v, p, layout, ctx, s, held, T.TOPIC_WORK[held]))
            kg = len(H.PARAM_NAMES)
            krows.append({"held_out": held, "generator": f"{short} topic-matched", "k_specific": 0, "k_global_engine": kg,
                          "note": "engine params + fixed plaintext choice; codebook/grammar fitted on training text"})
            if short == "A2":
                gens["A2 random-topic (null)"] = (lambda s, v=variant, p=p: hybrid_words(
                    v, p, layout, ctx, s, held, random.Random(s * 37).choice([w for w in WORKS if w != T.TOPIC_WORK[held]])))
                krows.append({"held_out": held, "generator": "A2 random-topic (null)", "k_specific": 0, "k_global_engine": kg})
        for name, f in gens.items():
            for s in seeds:
                out = f(1000 * s + CLASSES.index(held))
                flat = [w for ws in out for w in ws] if out and isinstance(out[0], list) else list(out)
                docs = T.corpus_from_layout(layout, flat)
                rows.append({"held_out": held, "generator": name, "family": GEN_ROWS[name][0], "seed": s, **L.section_stats(docs, held)})
        print(f"{held}: done ({time.time() - t0:.0f}s)", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(L.RESULTS / "predictions_runs.csv", index=False)
    pd.DataFrame(krows).to_csv(L.RESULTS / "parameter_counts.csv", index=False)
    man = {f: L.sha256(L.RESULTS / f) for f in ("prereg.json", "predictions_runs.csv")}
    man["written"] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    (L.RESULTS / "predictions_manifest.json").write_text(json.dumps(man, indent=1))
    print("predictions written + manifest", man)


def score():
    man = json.loads((L.RESULTS / "predictions_manifest.json").read_text())
    for f in ("prereg.json", "predictions_runs.csv"):
        assert L.sha256(L.RESULTS / f) == man[f], f"{f} changed after the manifest was written"
    pr = pd.read_csv(L.RESULTS / "predictions_runs.csv", keep_default_na=False, na_values=[""])
    entries = T.folio_layout(HR.ms_data())
    real_rows, se_rows = [], []
    for held in CLASSES:
        real_rows.append({"held_out": held, **L.section_stats(entries, held)})
        se_rows.append({"held_out": held, **L.jackknife_blocks(entries, held)})
    real, se = pd.DataFrame(real_rows).set_index("held_out"), pd.DataFrame(se_rows).set_index("held_out")
    real.reset_index().to_csv(L.RESULTS / "ms408_heldout_stats.csv", index=False)
    se.reset_index().to_csv(L.RESULTS / "ms408_heldout_jackknife_se.csv", index=False)
    js_cols = [f"js_to_{c}" for c in CLASSES]
    rows = []
    for (held, gen), g in pr.groupby(["held_out", "generator"], sort=False):
        n = len(g)
        for st in L.STATS:
            m, sd = g[st].mean(), g[st].std(ddof=1)
            tot = np.sqrt(sd ** 2 * (1 + 1 / n) + se.loc[held, st] ** 2)
            z = (m - real.loc[held, st]) / tot
            rows.append({"held_out": held, "generator": gen, "family": g["family"].iloc[0], "stat": st, "gen_mean": m, "gen_sd": sd, "ms408": real.loc[held, st],
                         "ms408_se": se.loc[held, st], "z": z, "inside_95": abs(z) <= 1.96})
        # JS shift pattern: correlation of predicted vs real JS vector over the 4 other sections
        cols = [c for c in js_cols if c != f"js_to_{held}"]
        pv, rv = g[cols].mean().values, real.loc[held, cols].values.astype(float)
        rows.append({"held_out": held, "generator": gen, "family": g["family"].iloc[0], "stat": "js_pattern_pearson",
                     "gen_mean": float(np.corrcoef(pv, rv)[0, 1]), "ms408": 1.0, "z": np.nan, "inside_95": np.nan,
                     "gen_sd": float(np.sqrt(np.mean((pv - rv) ** 2))), "ms408_se": np.nan})
    sc = pd.DataFrame(rows)
    sc.to_csv(L.RESULTS / "scores_long.csv", index=False)
    zz = sc[sc.stat.isin(L.STATS)].copy()
    zz["inside_95"] = zz["inside_95"].astype(bool)
    zz["absz"] = zz["z"].abs().clip(upper=10)
    # spread-free error: a mixture null has a wide seed spread that shrinks |z|, so also report the error of the mean in MS-408 SE units
    zz["abs_err_se"] = ((zz["gen_mean"] - zz["ms408"]).abs() / zz["ms408_se"]).clip(upper=50)
    zz["abs_rel_err"] = (zz["gen_mean"] - zz["ms408"]).abs() / zz["ms408"].abs()
    kc = pd.read_csv(L.RESULTS / "parameter_counts.csv").groupby("generator")[["k_specific", "k_global_engine"]].mean()
    pat = sc[sc.stat == "js_pattern_pearson"].groupby("generator")
    summ = zz.groupby(["generator", "family"]).agg(mean_absz=("absz", "mean"), median_absz=("absz", "median"), mean_abs_err_se=("abs_err_se", "mean"),
                                                   mean_abs_rel_err=("abs_rel_err", "mean"), n_inside=("inside_95", "sum"),
                                                   n_cells=("inside_95", "size")).reset_index()
    summ["js_pattern_r_mean"] = summ.generator.map(pat["gen_mean"].mean())
    summ["js_pattern_rmse_mean"] = summ.generator.map(pat["gen_sd"].mean())
    summ = summ.join(kc, on="generator").sort_values("mean_absz")
    summ.to_csv(L.RESULTS / "summary_by_generator.csv", index=False)
    per_sec = zz.groupby(["generator", "held_out"])["absz"].mean().unstack()
    per_sec.to_csv(L.RESULTS / "mean_absz_by_section.csv")
    # paired comparisons (primary + secondary), Wilcoxon over (section, stat) cells
    from scipy.stats import wilcoxon
    piv = zz.pivot_table(index=["held_out", "stat"], columns="generator", values="absz")
    piv2 = zz.pivot_table(index=["held_out", "stat"], columns="generator", values="abs_rel_err")
    comps = []
    pairs = [("SV P50 nearest", "A2 topic-matched", "primary")] + [(a, b, "secondary") for a in GEN_ROWS for b in GEN_ROWS
                                                                 if a < b and (a, b) != ("SV P50 nearest", "A2 topic-matched")]
    for a, b, kind in pairs:
        d = (piv[a] - piv[b]).dropna()
        p = wilcoxon(d).pvalue if (d != 0).any() else 1.0
        comps.append({"a": a, "b": b, "kind": kind, "mean_absz_a": piv[a].mean(), "mean_absz_b": piv[b].mean(), "median_diff_a_minus_b": d.median(),
                      "a_better_cells": int((d < 0).sum()), "b_better_cells": int((d > 0).sum()), "wilcoxon_p": p,
                      "relerr_a": piv2[a].mean(), "relerr_b": piv2[b].mean(), "relerr_wilcoxon_p": wilcoxon((piv2[a] - piv2[b]).dropna()).pvalue})
    cp = pd.DataFrame(comps)
    cp["holm_p_secondary"] = np.nan
    sec = cp.kind == "secondary"
    cp.loc[sec, "holm_p_secondary"] = CI_holm(cp.loc[sec, "wilcoxon_p"].values)
    cp.to_csv(L.RESULTS / "paired_comparisons.csv", index=False)
    print(summ.round(3).to_string(index=False))
    print(cp[cp.kind == "primary"].to_string(index=False))
    plots(zz, summ, real, pr)


def CI_holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0.0
    for r, i in enumerate(o):
        run = max(run, min(1.0, (m - r) * p[i]))
        adj[i] = run
    return adj


def plots(zz, summ, real, pr):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    order = list(summ.generator)
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {"baseline": "grey", "a: setting switch": "tab:blue", "b: topic plaintext": "tab:orange", "null model": "tab:red"}
    ax.barh(order[::-1], summ.mean_absz[::-1], color=[colors[f] for f in summ.family[::-1]])
    ax.axvline(1.0, ls=":", c="k")
    ax.set_xlabel("mean |z| over 5 held-out sections x 10 statistics (lower = better prediction)")
    ax.set_title("h07 leave-one-section-out: prediction error by generator")
    fig.tight_layout()
    fig.savefig(L.FIG / "fig1_mean_absz_by_generator.png", dpi=130)
    plt.close(fig)
    hm = zz.pivot_table(index="generator", columns=["held_out"], values="absz").loc[order]
    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(hm.values, cmap="viridis_r", vmin=0, vmax=6)
    ax.set_xticks(range(hm.shape[1]), hm.columns, rotation=30)
    ax.set_yticks(range(hm.shape[0]), hm.index)
    for i in range(hm.shape[0]):
        for j in range(hm.shape[1]):
            ax.text(j, i, f"{hm.values[i, j]:.1f}", ha="center", va="center", fontsize=7, color="w")
    fig.colorbar(im, label="mean |z| (clipped 10)")
    ax.set_title("mean |z| per held-out section")
    fig.tight_layout()
    fig.savefig(L.FIG / "fig2_absz_heatmap_sections.png", dpi=130)
    plt.close(fig)
    sts = ["overlap_tokens", "new_type_rate", "hapax_share", "js_mean_to_others"]
    sel = ["C0g global copy-modify (baseline)", "SV P50 nearest", "SV EUP25 nearest", "A1 topic-matched", "A2 topic-matched", "A2 random-topic (null)"]
    fig, axs = plt.subplots(1, 4, figsize=(15, 4))
    for ax, st in zip(axs, sts):
        x = np.arange(len(CLASSES))
        for j, g in enumerate(sel):
            m = pr[pr.generator == g].groupby("held_out")[st].mean().reindex(CLASSES)
            ax.plot(x, m.values, "o-", label=g, alpha=.8)
        ax.plot(x, real.loc[CLASSES, st].values, "k*-", ms=12, label="MS 408 (real)")
        ax.set_xticks(x, CLASSES, rotation=30)
        ax.set_title(st)
    axs[0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(L.FIG / "fig3_predicted_vs_real.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    {"predict": lambda: predict("--quick" in sys.argv), "score": score}[sys.argv[1]]()
