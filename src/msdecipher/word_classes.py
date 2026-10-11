"""Stage 7 (behavioural word clustering): which frequent words behave alike, and is that grouping stable?

**Behavioural tags only.** Clusters are groups of word types with similar distribution (neighbour words,
line position, section, Currier A/B, hand). They are *not* parts of speech: nothing here says that a
cluster is a verb, a noun, a name or anything else. A grouping only counts as meaningful here to the extent
that it is stable under resampling and carries more adjacent-word information than a shuffled text.

Features (``N`` most frequent word types, default 200):

* *neighbour profile* (all corpora): counts of the word's left and right neighbours over the ``C``
  (default 150) most frequent words + OTHER (+ line boundary for MS 408 in the line-aware variant);
  PPMI-weighted, SVD-reduced to 15 dims, rows L2-normalised;
* *line behaviour* (MS 408): line-initial and line-final rate (and paragraph-initial for first lines);
* *section / Currier language / hand* (MS 408): share of the word's tokens in each category.

Clustering: k-means (cosine geometry via normalised rows), Ward agglomerative and HDBSCAN. Quality and stability:
silhouette; adjusted Rand index (ARI) between the clustering of the full data and clusterings of block bootstraps
(pages for MS 408, 500-token chunks for controls); ARI between random half-splits; held-out adjacent-class mutual
information (classes learned on half of the blocks, evaluated on the other half, minus the same quantity for a
token-shuffled test half, in bits); and NMI of the clusters with the first / last unit of the word (type-level, token-weighted).
"""
from __future__ import annotations

import math
import random
from collections import Counter
from typing import Callable, Sequence

import numpy as np
from sklearn.cluster import HDBSCAN, KMeans, AgglomerativeClustering
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score
from sklearn.preprocessing import normalize

N_VOCAB = 200
N_CTX = 150
SVD_DIMS = 15
K_FIXED = 5
K_RANGE = range(2, 9)


class Corpus:
    """Tokens (readable words) in running order, block id per token, optional line / metadata arrays."""

    def __init__(self, tokens: Sequence[str], blocks: Sequence, line_ids: Sequence | None = None,
                 para_start: Sequence[bool] | None = None, meta: dict[str, Sequence] | None = None):
        self.tokens = list(tokens)
        self.blocks = list(blocks)
        self.line_ids = list(line_ids) if line_ids is not None else None
        self.para_start = list(para_start) if para_start is not None else None
        self.meta = {k: list(v) for k, v in (meta or {}).items()}
        assert len(self.tokens) == len(self.blocks)

    def __len__(self):
        return len(self.tokens)

    def subset_blocks(self, chosen: Sequence) -> "Corpus":
        """Blocks concatenated in the given order (repeats allowed), for resampling."""
        by: dict = {}
        for i, b in enumerate(self.blocks):
            by.setdefault(b, []).append(i)
        idx = [i for b in chosen for i in by[b]]
        return Corpus([self.tokens[i] for i in idx], [self.blocks[i] for i in idx],
                      [self.line_ids[i] for i in idx] if self.line_ids else None,
                      [self.para_start[i] for i in idx] if self.para_start else None,
                      {k: [v[i] for i in idx] for k, v in self.meta.items()})


def chunk_corpus(words: Sequence[str], chunk: int = 500) -> Corpus:
    return Corpus(words, [i // chunk for i in range(len(words))])


def vocab_of(c: Corpus, n_vocab: int = N_VOCAB, n_ctx: int = N_CTX):
    cnt = Counter(c.tokens)
    top = [w for w, _ in cnt.most_common(max(n_vocab, n_ctx))]
    return top[:n_vocab], top[:n_ctx], cnt


def _count_blocks(c: Corpus, vocab: list[str], ctx: list[str], line_aware: bool):
    """Per-block neighbour count matrices (n_blocks, N, 2*(C+2)): columns = left [C words, OTHER, BOUND], right [...]."""
    N, C = len(vocab), len(ctx)
    vid = {w: i for i, w in enumerate(vocab)}
    cid = {w: i for i, w in enumerate(ctx)}
    OTHER, BOUND = C, C + 1
    D = C + 2
    ublocks = list(dict.fromkeys(c.blocks))
    bpos = {b: i for i, b in enumerate(ublocks)}
    M = np.zeros((len(ublocks), N, 2 * D))
    T = len(c.tokens)
    cids = np.array([cid.get(w, OTHER) for w in c.tokens])
    vids = np.array([vid.get(w, -1) for w in c.tokens])
    bidx = np.array([bpos[b] for b in c.blocks])
    lines = np.array(c.line_ids, dtype=object) if c.line_ids is not None else None
    for i in range(T):
        v = vids[i]
        if v < 0:
            continue
        if i == 0 or c.blocks[i - 1] != c.blocks[i] or (line_aware and lines is not None and lines[i - 1] != lines[i]):
            l = BOUND
        else:
            l = cids[i - 1]
        if i == T - 1 or c.blocks[i + 1] != c.blocks[i] or (line_aware and lines is not None and lines[i + 1] != lines[i]):
            r = BOUND
        else:
            r = cids[i + 1]
        M[bidx[i], v, l] += 1
        M[bidx[i], v, D + r] += 1
    return M, ublocks


def _line_features(c: Corpus, vocab: list[str]):
    """Per block: counts matrix (n_blocks, N, 4): tokens, line-initial, line-final, paragraph-initial."""
    vid = {w: i for i, w in enumerate(vocab)}
    ublocks = list(dict.fromkeys(c.blocks))
    bpos = {b: i for i, b in enumerate(ublocks)}
    F = np.zeros((len(ublocks), len(vocab), 4))
    L = c.line_ids
    for i, w in enumerate(c.tokens):
        v = vid.get(w)
        if v is None:
            continue
        b = bpos[c.blocks[i]]
        F[b, v, 0] += 1
        if i == 0 or L[i - 1] != L[i]:
            F[b, v, 1] += 1
            if c.para_start and c.para_start[i]:
                F[b, v, 3] += 1
        if i == len(c.tokens) - 1 or L[i + 1] != L[i]:
            F[b, v, 2] += 1
    return F, ublocks


def _cat_features(c: Corpus, vocab: list[str], key: str):
    """Per block: (n_blocks, N, n_categories) token counts by metadata category."""
    vid = {w: i for i, w in enumerate(vocab)}
    cats = sorted({str(x) for x in c.meta[key]})
    cpos = {x: i for i, x in enumerate(cats)}
    ublocks = list(dict.fromkeys(c.blocks))
    bpos = {b: i for i, b in enumerate(ublocks)}
    F = np.zeros((len(ublocks), len(vocab), len(cats)))
    for i, w in enumerate(c.tokens):
        v = vid.get(w)
        if v is not None:
            F[bpos[c.blocks[i]], v, cpos[str(c.meta[key][i])]] += 1
    return F, cats


def ppmi(M: np.ndarray, alpha: float = 0.75) -> np.ndarray:
    """PPMI with context-distribution smoothing; rows = words."""
    tot = M.sum()
    if tot == 0:
        return M
    pw = M.sum(1, keepdims=True) / tot
    pc = M.sum(0, keepdims=True) ** alpha
    pc = pc / pc.sum()
    pwc = M / tot
    with np.errstate(divide="ignore", invalid="ignore"):
        pm = np.log(pwc / (pw * pc))
    pm[~np.isfinite(pm)] = 0
    return np.maximum(pm, 0)


def embed(neigh: np.ndarray, extra: list[np.ndarray] | None = None, dims: int = SVD_DIMS, seed: int = 0) -> np.ndarray:
    """Neighbour counts -> PPMI -> SVD -> L2-normalised rows; ``extra`` blocks (row-normalised profiles) are
    appended after being scaled to the same overall norm and the rows re-normalised."""
    P = ppmi(neigh)
    d = max(2, min(dims, min(P.shape) - 1))
    X = TruncatedSVD(d, random_state=seed).fit_transform(P) if P.any() else np.zeros((P.shape[0], d))
    X = normalize(X)
    parts = [X]
    for E in (extra or []):
        E = np.asarray(E, float)
        E = E - E.mean(0, keepdims=True)
        sd = E.std(0, keepdims=True)
        E = E / np.where(sd > 0, sd, 1)
        n = np.linalg.norm(E, axis=1, keepdims=True).mean() or 1.0
        parts.append(E / n)
    return normalize(np.concatenate(parts, axis=1))


def kmeans_labels(X: np.ndarray, k: int, seed: int = 0) -> np.ndarray:
    return KMeans(k, n_init=10, random_state=seed).fit_predict(X)


def ward_labels(X: np.ndarray, k: int) -> np.ndarray:
    return AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(X)


def hdbscan_labels(X: np.ndarray, min_size: int = 8) -> np.ndarray:
    return HDBSCAN(min_cluster_size=min_size).fit_predict(X)


def best_k(X: np.ndarray, seed: int = 0) -> tuple[int, float, dict[int, float]]:
    sils = {}
    for k in K_RANGE:
        if k >= len(X):
            break
        sils[k] = float(silhouette_score(X, kmeans_labels(X, k, seed)))
    kb = max(sils, key=sils.get)
    return kb, sils[kb], sils


def adjacent_class_mi(tokens: Sequence[str], cls: dict[str, int], blocks: Sequence | None = None) -> tuple[float, float, int]:
    """Plug-in mutual information (bits) between the classes of adjacent in-vocabulary tokens (pairs inside a block,
    both words in the clustered vocabulary), plus H(class) and the number of pairs."""
    pairs = Counter()
    for i in range(len(tokens) - 1):
        a, b = cls.get(tokens[i]), cls.get(tokens[i + 1])
        if a is None or b is None:
            continue
        if blocks is not None and blocks[i] != blocks[i + 1]:
            continue
        pairs[(a, b)] += 1
    n = sum(pairs.values())
    if n == 0:
        return float("nan"), float("nan"), 0
    pa, pb = Counter(), Counter()
    for (a, b), v in pairs.items():
        pa[a] += v
        pb[b] += v
    mi = sum(v / n * math.log2(v * n / (pa[a] * pb[b])) for (a, b), v in pairs.items())
    h = -sum(v / n * math.log2(v / n) for v in pa.values())
    return mi, h, n


def nmi_with_unit(labels: np.ndarray, vocab: list[str], counts: Counter, seg: Callable, where: str, rng: random.Random,
                  n_perm: int = 20) -> tuple[float, float]:
    """(NMI of clusters with the first/last unit of the word, token-weighted; mean NMI after permuting the unit labels)."""
    units = [seg(w)[-1 if where == "last" else 0] for w in vocab]
    w = np.array([counts[v] for v in vocab], dtype=float)
    # token-weighted by repeating proportionally (cap for speed)
    rep = np.maximum(1, np.round(w / w.min() / 4)).astype(int)
    lab = np.repeat(labels, rep)
    un = np.repeat(np.array(units, dtype=object), rep)
    ui = {u: i for i, u in enumerate(dict.fromkeys(units))}
    ua = np.array([ui[u] for u in un])
    nmi = normalized_mutual_info_score(lab, ua)
    perm = []
    base = np.array([ui[u] for u in units])
    for _ in range(n_perm):
        p = base.copy()
        rng.shuffle(p)
        perm.append(normalized_mutual_info_score(lab, np.repeat(p, rep)))
    return float(nmi), float(np.mean(perm))


def _stability(blocks_mats: dict, full_labels: np.ndarray, k: int, B: int, seed: int, build: Callable, ublocks: list) -> dict:
    """ARI of block-bootstrap clusterings against the full-data clustering; ARI between random half-splits."""
    rng = random.Random(seed)
    nb = len(ublocks)
    boot, split = [], []
    for b in range(B):
        counts = np.bincount([rng.randrange(nb) for _ in range(nb)], minlength=nb)
        X = build(counts)
        boot.append(adjusted_rand_score(full_labels, kmeans_labels(X, k, seed + b)))
    for b in range(max(4, B // 3)):
        idx = list(range(nb))
        rng.shuffle(idx)
        h1, h2 = np.zeros(nb), np.zeros(nb)
        h1[idx[: nb // 2]] = 1
        h2[idx[nb // 2:]] = 1
        split.append(adjusted_rand_score(kmeans_labels(build(h1), k, seed + b), kmeans_labels(build(h2), k, seed + 50 + b)))
    return {"ari_boot": float(np.mean(boot)), "ari_boot_sd": float(np.std(boot, ddof=1)) if len(boot) > 1 else float("nan"),
            "ari_split": float(np.mean(split)), "ari_split_sd": float(np.std(split, ddof=1)) if len(split) > 1 else float("nan")}


def class_metrics(c: Corpus, seg: Callable[[str], tuple] | None = None, features: str = "neighbour", k: int = K_FIXED,
                  B: int = 30, seed: int = 1, n_vocab: int = N_VOCAB, n_ctx: int = N_CTX, n_splits: int = 6,
                  return_detail: bool = False) -> dict:
    """Clustering metrics for one corpus. ``features``: ``neighbour`` (flat tokens, comparable across all corpora),
    ``line`` (neighbour + line boundaries + line-initial/final rates; needs ``line_ids``) or ``full`` (line +
    section + Currier language + hand; needs ``meta`` keys section/language/hand)."""
    seg = seg or (lambda w: tuple(w))
    vocab, ctx, cnt = vocab_of(c, n_vocab, n_ctx)
    n_vocab = len(vocab)
    line_aware = features in ("line", "full")
    Mn, ublocks = _count_blocks(c, vocab, ctx, line_aware)
    extras = []
    cat_names: dict = {}
    if line_aware:
        Fl, _ = _line_features(c, vocab)
        extras.append(("line", Fl))
    if features == "full":
        for key in ("section", "language", "hand"):
            if key in c.meta:
                Fc, cats = _cat_features(c, vocab, key)
                extras.append((key, Fc))
                cat_names[key] = cats

    def build(wvec: np.ndarray) -> np.ndarray:
        neigh = np.tensordot(wvec, Mn, axes=(0, 0))
        ex = []
        for name, F in extras:
            S = np.tensordot(wvec, F, axes=(0, 0))
            if name == "line":
                tok = np.maximum(S[:, 0:1], 1)
                ex.append(S[:, 1:4] / tok)
            else:
                ex.append(S / np.maximum(S.sum(1, keepdims=True), 1))
        return embed(neigh, ex, seed=seed)

    X = build(np.ones(len(ublocks)))
    kb, silb, sils = best_k(X, seed)
    lab = kmeans_labels(X, k, seed)
    out = {"n_vocab": n_vocab, "k_best": kb, f"sil_best": silb, "sil_k5": sils.get(k, float("nan")),
           "cluster_size_min_share_k5": float(np.bincount(lab).min() / n_vocab)}
    out.update({f"k5_{a}": b for a, b in _stability(None, lab, k, B, seed, build, ublocks).items()})
    labb = kmeans_labels(X, kb, seed)
    out["ari_boot_best"] = _stability(None, labb, kb, max(8, B // 3), seed + 3, build, ublocks)["ari_boot"]
    # ward / hdbscan agreement and structure
    lw = ward_labels(X, k)
    out["ari_kmeans_vs_ward_k5"] = float(adjusted_rand_score(lab, lw))
    lh = hdbscan_labels(X)
    out["hdbscan_n_clusters"] = int(len(set(lh)) - (1 if -1 in lh else 0))
    out["hdbscan_noise_share"] = float((lh == -1).mean())
    # held-out adjacent-class MI
    rng = random.Random(seed + 11)
    ub = list(ublocks)
    mis, nulls, norm = [], [], []
    for s in range(n_splits):
        rng.shuffle(ub)
        tr = {b: 1.0 for b in ub[: len(ub) // 2]}
        wvec = np.array([tr.get(b, 0.0) for b in ublocks])
        lab_s = kmeans_labels(build(wvec), k, seed + s)
        cls = dict(zip(vocab, lab_s))
        test = c.subset_blocks([b for b in ublocks if b not in tr])
        mi, h, n = adjacent_class_mi(test.tokens, cls, test.blocks)
        sh = list(test.tokens)
        rng.shuffle(sh)
        mi0, _, _ = adjacent_class_mi(sh, cls, None)
        mis.append(mi)
        nulls.append(mi0)
        norm.append(mi / h if h else float("nan"))
    out["class_mi_k5"] = float(np.nanmean(mis))
    out["class_mi_null_k5"] = float(np.nanmean(nulls))
    out["class_mi_excess_k5"] = out["class_mi_k5"] - out["class_mi_null_k5"]
    out["class_mi_norm_k5"] = float(np.nanmean(norm))
    for where in ("last", "first"):
        nmi, nmi0 = nmi_with_unit(lab, vocab, cnt, seg, where, rng)
        out[f"nmi_{where}_unit_k5"] = nmi
        out[f"nmi_{where}_unit_excess_k5"] = nmi - nmi0
    if return_detail:
        out["_detail"] = {"vocab": vocab, "labels": lab, "X": X, "sils": sils, "counts": cnt, "cat_names": cat_names,
                          "extras": extras, "Mn": Mn, "ublocks": ublocks}
    return out


CLASS_INFO: dict[str, tuple[str, str]] = {
    "sil_k5": ("silhouette, k-means k=5", "clustering"),
    "sil_best": ("silhouette at best k (2-8)", "clustering"),
    "k5_ari_boot": ("ARI vs block-bootstrap clusterings (k=5)", "stability"),
    "k5_ari_split": ("ARI between random half-splits (k=5)", "stability"),
    "ari_boot_best": ("ARI vs bootstrap at best k", "stability"),
    "ari_kmeans_vs_ward_k5": ("ARI k-means vs Ward (k=5)", "stability"),
    "hdbscan_n_clusters": ("HDBSCAN clusters", "clustering"),
    "hdbscan_noise_share": ("HDBSCAN noise share", "clustering"),
    "class_mi_excess_k5": ("held-out adjacent-class MI minus shuffled (bits, k=5)", "syntax-like signal"),
    "class_mi_norm_k5": ("adjacent-class MI / H(class)", "syntax-like signal"),
    "nmi_last_unit_excess_k5": ("NMI(cluster, last unit) minus permuted", "form-behaviour link"),
    "nmi_first_unit_excess_k5": ("NMI(cluster, first unit) minus permuted", "form-behaviour link"),
}
