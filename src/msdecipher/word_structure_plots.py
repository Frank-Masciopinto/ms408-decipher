"""Figures for the word-structure stage (Agg backend). Descriptive only."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .word_structure import STRUCT_INFO
from .word_classes import CLASS_INFO

MS_MAIN = "MS408 P (collapsed units)"
ALL = {**STRUCT_INFO, **CLASS_INFO}


def _save(fig, path: Path) -> str:
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return str(path)


def slot_matrix(res: dict, path: Path) -> str:
    slot = res["detail"]["slot"]
    act = slot.e >= slot.min_emit
    mass = (slot.P * slot.e[:, None]).sum(0)
    order = np.argsort(-mass)[:34]                      # the 34 most used units (the rest are rare symbols)
    P = slot.P[:, order]
    fig, ax = plt.subplots(figsize=(0.45 * P.shape[1] + 3, 0.45 * P.shape[0] + 2))
    im = ax.imshow(P, cmap="viridis", aspect="auto")
    ax.set_xticks(range(P.shape[1]))
    ax.set_xticklabels([str(slot.units[i]) for i in order], rotation=90, fontsize=8)
    ax.set_yticks(range(slot.K))
    ax.set_yticklabels([f"slot {k + 1}  (p_emit {slot.e[k]:.2f})" for k in range(slot.K)], fontsize=8)
    fig.colorbar(im, ax=ax, label="P(unit | slot)")
    ax.set_title(f"MS 408 learned slot grammar (K={slot.K}, type-level fit): numbered positions, no labels")
    return _save(fig, path)


def _cols(families):
    cmap = plt.get_cmap("tab20")
    return {f: cmap(i % 20) for i, f in enumerate(families)}


def strips(res: dict, path: Path) -> str:
    comp = res["comparison"]
    mets = ["slot_gain_frac_type", "slot_null_gap_type", "mdl_type_slot_minus_bigram", "k5_ari_boot", "class_mi_excess_k5", "nmi_last_unit_excess_k5"]
    ctrl = comp[~comp["family"].eq("MS 408")]
    fams = list(dict.fromkeys(ctrl["family"]))
    cols = _cols(fams)
    fig, axs = plt.subplots(2, 3, figsize=(16, 10), sharey=True)
    ypos = {f: i for i, f in enumerate(fams)}
    se = res.get("ms_se") or {}
    for ax, m in zip(axs.flat, mets):
        for fam, g in ctrl.groupby("family", sort=False):
            ax.scatter(g[m], [ypos[fam]] * len(g), color=cols[fam], s=22, edgecolor="k", linewidth=0.3)
        v = comp.loc[MS_MAIN, m]
        ax.axvline(v, color="k", lw=1.5)
        if se.get(m) == se.get(m) and se.get(m):
            ax.axvspan(v - 1.96 * se[m], v + 1.96 * se[m], color="k", alpha=0.15)
        ax.set_title(ALL[m][0], fontsize=9)
    for ax in axs[:, 0]:
        ax.set_yticks(range(len(fams)))
        ax.set_yticklabels([f if len(f) < 42 else f[:40] + "…" for f in fams], fontsize=7)
    axs[0, 0].invert_yaxis()
    fig.suptitle("Word-structure metrics: controls (dots) vs MS 408 (black line, grey = 95% block-jackknife CI)", fontsize=10)
    return _save(fig, path)


def stability_scatter(res: dict, path: Path) -> str:
    comp = res["comparison"]
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.5))
    ctrl = comp[~comp["family"].eq("MS 408")]
    cols = _cols(list(dict.fromkeys(ctrl["family"])))
    for ax, (x, y) in zip(axs, [("k5_ari_boot", "class_mi_excess_k5"), ("slot_gain_frac_type", "slot_null_gap_type")]):
        for fam, g in ctrl.groupby("family", sort=False):
            ax.scatter(g[x], g[y], color=cols[fam], s=26, edgecolor="k", linewidth=0.3, label=fam if len(fam) < 40 else fam[:38] + "…")
        for name, r in comp[comp["family"].eq("MS 408")].iterrows():
            main = name == MS_MAIN
            ax.scatter(r[x], r[y], marker="*" if main else "x", color="k", s=200 if main else 40, zorder=5,
                       label="MS 408 P (collapsed)" if main else None)
        ax.set_xlabel(ALL[x][0])
        ax.set_ylabel(ALL[y][0])
    axs[0].legend(fontsize=5.5, ncol=2)
    fig.suptitle("MS 408 (star) and variants (x) vs controls", fontsize=10)
    return _save(fig, path)


def clusters_plot(res: dict, path: Path) -> str:
    cl = res["detail"]["clusters"]
    fig, axs = plt.subplots(1, 3, figsize=(20, 7))
    for ax, feats in zip(axs, ("neighbour", "line", "full")):
        d = cl[feats]["_detail"]
        X, lab, vocab, cnt = d["X"], d["labels"], d["vocab"], d["counts"]
        Xc = X - X.mean(0)
        u, s, vt = np.linalg.svd(Xc, full_matrices=False)
        Y = Xc @ vt[:2].T
        cmap = plt.get_cmap("tab10")
        for c in sorted(set(lab)):
            m = lab == c
            ax.scatter(Y[m, 0], Y[m, 1], color=cmap(c), s=[8 + 60 * np.sqrt(cnt[w] / max(cnt.values())) for w, k in zip(vocab, m) if k], alpha=0.8, label=f"C{c + 1}")
        top = sorted(range(len(vocab)), key=lambda i: -cnt[vocab[i]])[:25]
        for i in top:
            ax.annotate(vocab[i], (Y[i, 0], Y[i, 1]), fontsize=6.5)
        ax.set_title(f"{feats} features: k-means k=5 (PCA of embedding)\nsil={cl[feats]['sil_k5']:.2f}, ARI boot={cl[feats]['k5_ari_boot']:.2f}", fontsize=9)
        ax.legend(fontsize=7)
    fig.suptitle("MS 408 behavioural clusters of the 200 most frequent word types (numbered groups, not word classes)", fontsize=10)
    return _save(fig, path)


def sweep_plot(res: dict, path: Path) -> str:
    sw = res["sweep_df"]
    names = list(dict.fromkeys(sw["corpus"]))
    fig, axs = plt.subplots(2, 4, figsize=(18, 8), sharex=True)
    for ax, n in zip(axs.flat, names):
        g = sw[sw["corpus"] == n].sort_values("K")
        ax.plot(g["K"], g["bits_type_slot"], "o-", label="slot grammar")
        ax.plot(g["K"], g["bits_type_bigram"], "s--", label="unit bigram")
        ax.set_title(n, fontsize=9)
        ax.set_xlabel("K slots")
        ax.set_ylabel("held-out bits/type")
    axs.flat[0].legend(fontsize=7)
    fig.suptitle("Held-out bits per word type vs number of slots", fontsize=10)
    return _save(fig, path)


def verdict_heatmap(res: dict, path: Path) -> str:
    vt = res["verdicts"]
    summ = res["summary"]
    fams = list(summ["family"])
    mets = list(dict.fromkeys(vt["metric"]))
    mat = np.full((len(mets), len(fams)), np.nan)
    for j, f in enumerate(fams):
        for i, m in enumerate(mets):
            r = vt[(vt["family"] == f) & (vt["metric"] == m)]
            if len(r):
                mat[i, j] = {"≈": 0, "↑": 1, "↓": -1}.get(r["verdict"].iloc[0], np.nan)
    fig, ax = plt.subplots(figsize=(1 + 0.6 * len(fams), 0.32 * len(mets) + 3.5))
    ax.imshow(mat, cmap="RdYlGn_r", vmin=-1.5, vmax=1.5, aspect="auto")
    for i in range(len(mets)):
        for j in range(len(fams)):
            ax.text(j, i, {0: "≈", 1: "↑", -1: "↓"}.get(mat[i, j], "?"), ha="center", va="center", fontsize=8)
    ax.set_xticks(range(len(fams)))
    ax.set_xticklabels([f if len(f) < 34 else f[:32] + "…" for f in fams], rotation=60, ha="right", fontsize=7)
    ax.set_yticks(range(len(mets)))
    ax.set_yticklabels([ALL[m][0][:60] for m in mets], fontsize=7)
    ax.set_title("MS 408 vs each family's 95% prediction interval (≈ inside, ↑ above, ↓ below, ? <3 members)", fontsize=9)
    return _save(fig, path)


def make_all(res: dict, fig_dir: Path) -> list[str]:
    fig_dir.mkdir(parents=True, exist_ok=True)
    return [slot_matrix(res, fig_dir / "ms408_slot_matrix.png"), strips(res, fig_dir / "strip_by_family.png"),
            stability_scatter(res, fig_dir / "scatter_structure.png"), clusters_plot(res, fig_dir / "ms408_clusters.png"),
            sweep_plot(res, fig_dir / "slot_count_sweep.png"), verdict_heatmap(res, fig_dir / "verdict_heatmap.png")]
