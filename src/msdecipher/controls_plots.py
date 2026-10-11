"""Figures for the control comparison (Agg backend). Descriptive only."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import stats as S
from .controls_metrics import METRIC_INFO

MS_MAIN = "MS408 P (collapsed units)"


def _save(fig, path: Path) -> str:
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return str(path)


def _colors(families):
    cmap = plt.get_cmap("tab20")
    return {f: cmap(i % 20) for i, f in enumerate(families)}


def scatter_panels(comp, path: Path) -> str:
    pairs = [("unit_H1", "unit_h2"), ("zipf_mle_s_r10_1000", "heaps_beta_shuffled"),
             ("pos_skewed_unit_share", "adjacent_edit1_rate"), ("unit_h3", "shuffle_gap_h2")]
    ctrl = comp[~comp["family"].eq("MS 408")]
    cols = _colors(list(dict.fromkeys(ctrl["family"])))
    fig, axs = plt.subplots(2, 2, figsize=(13, 9.5))
    for ax, (x, y) in zip(axs.flat, pairs):
        for fam, g in ctrl.groupby("family", sort=False):
            ax.scatter(g[x], g[y], color=cols[fam], s=28, label=fam, alpha=0.9, edgecolor="k", linewidth=0.3)
        ms = comp[comp["family"].eq("MS 408")]
        for name, r in ms.iterrows():
            main = name == MS_MAIN
            ax.scatter(r[x], r[y], marker="*" if main else "x", color="k", s=170 if main else 40,
                       zorder=5, label="MS 408 P (collapsed)" if main else None)
        ax.set_xlabel(METRIC_INFO[x][0])
        ax.set_ylabel(METRIC_INFO[y][0])
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=7)
    fig.suptitle("MS 408 (black) vs controls: descriptive statistics, no single panel is decisive", fontsize=10)
    fig.tight_layout(rect=(0, 0.14, 1, 0.97))
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return str(path)


def verdict_heatmap(verd, summ, path: Path) -> str:
    fams = list(summ["family"])
    mets = list(METRIC_INFO)
    mat = np.zeros((len(mets), len(fams)))
    for j, f in enumerate(fams):
        for i, m in enumerate(mets):
            r = verd[(verd["family"] == f) & (verd["metric"] == m)]
            v = r["verdict_collapsed"].iloc[0] if len(r) else "–"
            mat[i, j] = {"≈": 0, "↑": 1, "↓": -1}.get(v, np.nan)
    fig, ax = plt.subplots(figsize=(1 + 0.6 * len(fams), 0.4 * len(mets) + 3.5))
    ax.imshow(mat, cmap="RdYlGn_r", vmin=-1.5, vmax=1.5, aspect="auto")
    for i in range(len(mets)):
        for j in range(len(fams)):
            ax.text(j, i, {0: "≈", 1: "↑", -1: "↓"}.get(mat[i, j], "–"), ha="center", va="center", fontsize=9)
    ax.set_xticks(range(len(fams)))
    ax.set_xticklabels([f if len(f) < 34 else f[:32] + "…" for f in fams], rotation=60, ha="right", fontsize=7)
    ax.set_yticks(range(len(mets)))
    ax.set_yticklabels([METRIC_INFO[m][0] for m in mets], fontsize=8)
    ax.set_title("MS 408 (collapsed units) relative to each family's observed band\n"
                 "≈ inside (yellow), ↑ MS above (red), ↓ MS below (green); coarse screening, tolerance-widened min..max", fontsize=9)
    return _save(fig, path)


def rank_frequency(samples: dict, path: Path) -> str:
    pick = [MS_MAIN, "plain:la_vulgate", "plain:it_manzoni", "plain:de_walther_mhg", "abjad:la_vulgate",
            "vigenere_k6:la_vulgate", "nomenclator:la_vulgate", "verbose_2sym:la_vulgate", "naibbe_like:la_vulgate",
            "selfcitation_p0.3", "markov_o2:la_vulgate", "slot_grammar_p0.35", "shuffle_tokens:la_vulgate"]
    fig, ax = plt.subplots(figsize=(8, 6))
    for k in pick:
        if k not in samples:
            continue
        f = S.rank_frequency(samples[k])
        ax.loglog(np.arange(1, len(f) + 1), f, lw=2.4 if k == MS_MAIN else 1.0, color="k" if k == MS_MAIN else None,
                  label=k, alpha=1 if k == MS_MAIN else 0.8)
    ax.set_xlabel("rank")
    ax.set_ylabel("frequency")
    ax.set_title("Token rank-frequency: MS 408 (black) vs selected controls")
    ax.legend(fontsize=6.5)
    return _save(fig, path)


def strip_plots(comp, path: Path) -> str:
    mets = ["unit_h2", "unit_h3", "shuffle_gap_h2", "zipf_mle_s_r10_1000", "type_token_ratio", "pos_skewed_unit_share"]
    ctrl = comp[~comp["family"].eq("MS 408")]
    fams = list(dict.fromkeys(ctrl["family"]))
    cols = _colors(fams)
    fig, axs = plt.subplots(2, 3, figsize=(15, 9), sharey=True)
    ypos = {f: i for i, f in enumerate(fams)}
    for ax, m in zip(axs.flat, mets):
        for fam, g in ctrl.groupby("family", sort=False):
            ax.scatter(g[m], [ypos[fam]] * len(g), color=cols[fam], s=22, edgecolor="k", linewidth=0.3)
        if MS_MAIN in comp.index:
            ax.axvline(comp.loc[MS_MAIN, m], color="k", lw=1.5)
        ax.set_title(METRIC_INFO[m][0], fontsize=9)
    for ax in axs[:, 0]:
        ax.set_yticks(range(len(fams)))
        ax.set_yticklabels([f if len(f) < 40 else f[:38] + "…" for f in fams], fontsize=7)
    axs[0, 0].invert_yaxis()
    fig.suptitle("Per-family control values (dots) vs MS 408 (black line)", fontsize=10)
    return _save(fig, path)


def make_all(res: dict, samples: dict, fig_dir: Path) -> list[str]:
    fig_dir.mkdir(parents=True, exist_ok=True)
    comp = res["comparison"]
    out = [scatter_panels(comp, fig_dir / "scatter_panels.png"),
           strip_plots(comp, fig_dir / "strip_by_family.png"),
           rank_frequency(samples, fig_dir / "rank_frequency.png")]
    if "verdicts" in res:
        out.append(verdict_heatmap(res["verdicts"], res["summary"], fig_dir / "verdict_heatmap.png"))
    return out
