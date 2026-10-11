"""Matplotlib figures (Agg backend). All plots are descriptive."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import stats as S


def _save(fig, path: Path) -> str:
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return str(path)


def zipf_plot(words, path: Path) -> str:
    f = S.rank_frequency(words)
    r = np.arange(1, len(f) + 1)
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.loglog(r, f, ".", ms=3, label="tokens (all P text)")
    slope = S.zipf_ols_slope(f, 10, 1000)
    s = S.zipf_mle_exponent(f, 10, 1000)
    if not np.isnan(slope):
        rr = np.arange(10, min(1000, len(f)) + 1)
        c = np.log10(f[9:len(rr) + 9]).mean() - slope * np.log10(rr).mean()
        ax.loglog(rr, 10 ** (c + slope * np.log10(rr)), "r-", lw=1.2,
                  label=f"OLS ranks 10-1000: slope {slope:.2f} (MLE s={s:.2f})")
    ax.set_xlabel("rank")
    ax.set_ylabel("frequency")
    ax.set_title("Token rank-frequency (descriptive, not a language test)")
    ax.legend(fontsize=8)
    return _save(fig, path)


def heaps_plot(words, path: Path) -> str:
    import random
    n, v = S.heaps_curve(words)
    sw = list(words)
    random.Random(1).shuffle(sw)
    n2, v2 = S.heaps_curve(sw)
    b1, _ = S.heaps_exponent(words)
    b2, _ = S.heaps_exponent(words, shuffled=True)
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.loglog(n, v, "o-", ms=3, label=f"manuscript order (beta={b1:.2f})")
    ax.loglog(n2, v2, "s--", ms=3, label=f"shuffled tokens (beta={b2:.2f})")
    ax.set_xlabel("tokens read")
    ax.set_ylabel("distinct tokens")
    ax.set_title("Vocabulary growth (Heaps)")
    ax.legend(fontsize=8)
    return _save(fig, path)


def unit_ab_plot(uf_df, path: Path, top: int = 28) -> str:
    d = uf_df.head(top)
    x = np.arange(len(d))
    tA, tB = d["count_A"].sum(), d["count_B"].sum()
    nA, nB = uf_df["count_A"].sum(), uf_df["count_B"].sum()
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar(x - 0.2, d["count_A"] / nA, 0.4, label="Currier A")
    ax.bar(x + 0.2, d["count_B"] / nB, 0.4, label="Currier B")
    ax.set_xticks(x)
    ax.set_xticklabels(d["unit"], rotation=60, fontsize=8)
    ax.set_ylabel("share of units")
    ax.set_title("Unit shares, Currier A vs B (segmented units)")
    ax.legend()
    return _save(fig, path)


def positional_heatmap(pos_df, path: Path, top: int = 25) -> str:
    d = pos_df[pos_df["subset"] == "P"].head(top)
    cols = ["initial_share", "medial_share", "final_share", "sole_share"]
    M = d[cols].to_numpy(dtype=float)
    # line-level columns as share of the unit's occurrences
    extra = np.vstack([
        d["line_initial_n"].to_numpy(float) / d["n_in_words"].to_numpy(float),
        d["line_final_n"].to_numpy(float) / d["n_in_words"].to_numpy(float),
        d["para_initial_n"].to_numpy(float) / d["n_in_words"].to_numpy(float)]).T
    M = np.hstack([M, extra])
    names = ["word start", "word middle", "word end", "1-unit word", "line start", "line end", "para start"]
    fig, ax = plt.subplots(figsize=(7, 8))
    im = ax.imshow(M, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d["unit"])
    fig.colorbar(im, label="share of the unit's occurrences")
    ax.set_title("Positional distribution of the most frequent units (P text)")
    return _save(fig, path)


def entropy_plot(summary, path: Path) -> str:
    subsets = [s for s in ("P (all running text)", "Currier A", "Currier B") if s in summary.index]
    labels = ["P", "A", "B"][:len(subsets)]
    keys = [("unit_H1", "H1"), ("unit_h2", "h2"), ("unit_h3", "h3"), ("unit_h2_within_word_shuffle", "h2 after\nwithin-token shuffle")]
    x = np.arange(len(keys))
    fig, ax = plt.subplots(figsize=(7, 4.2))
    w = 0.8 / len(subsets)
    for i, (s, lab) in enumerate(zip(subsets, labels)):
        ax.bar(x + i * w - 0.4 + w / 2, [summary.loc[s, k] for k, _ in keys], w, label=lab)
    ax.set_xticks(x)
    ax.set_xticklabels([k[1] for k in keys])
    ax.set_ylabel("bits")
    ax.set_title("Unit entropies (plug-in; not size-matched)")
    ax.legend()
    return _save(fig, path)


def make_all(res: dict, outdir: Path, P, A, B, seg, words) -> list[str]:
    outdir.mkdir(parents=True, exist_ok=True)
    return [
        zipf_plot(words, outdir / "zipf_words.png"),
        heaps_plot(words, outdir / "heaps.png"),
        unit_ab_plot(res["unit_freq"], outdir / "unit_frequencies_ab.png"),
        positional_heatmap(res["positional"], outdir / "positional_heatmap.png"),
        entropy_plot(res["summary"], outdir / "entropies.png"),
    ]
