"""Clustering of glyph crops, comparison with the EVA catalogue, QA metrics, overlays and the report.

Everything here is descriptive and best effort. MS 408 is undeciphered; image clusters are NOT
decoded letters, and agreement with EVA letters says something about how well *a transcriber's*
alphabet matches visual shape, not about what the text means.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .paths import repo_root, glyphs_dir, reports_dir
from . import glyph_stage as gs

MIN_UNIT_N = 40          # EVA units with fewer labelled crops are left out of agreement metrics
K_LIST = (8, 12, 16, 24, 32, 40)
K_MAIN = 24              # presentation choice for sheets/tables (EVA has ~20-25 frequent symbols); sweep reported


def image_report_dir() -> Path:
    return reports_dir() / "image_stage"


def image_glyph_dir() -> Path:
    return glyphs_dir() / "image"


# ----------------------------------------------------------------------------- loading

def load_stage(out: Path | None = None):
    out = out or gs.processed_dir()
    pages = pd.read_csv(out / "pages.csv")
    words = pd.read_csv(out / "words.csv", keep_default_na=False)
    glyphs = pd.read_csv(out / "glyphs.csv", keep_default_na=False)
    crops = np.load(out / "crops.npy")
    meta = json.loads((out / "run.json").read_text())
    return pages, words, glyphs, crops, meta


# ----------------------------------------------------------------------------- QA metrics

def qa_metrics(pages: pd.DataFrame, words: pd.DataFrame, glyphs: pd.DataFrame, seed: int = 1) -> dict:
    rng = np.random.RandomState(seed)
    m: dict = {}
    p = pages[pages.lines_transcribed > 0]
    d = p.lines_detected - p.lines_transcribed
    m["pages"] = int(len(p))
    m["lines_detected_total"] = int(p.lines_detected.sum())
    m["lines_transcribed_total"] = int(p.lines_transcribed.sum())
    m["pages_line_count_within_1"] = float((d.abs() <= 1).mean())
    m["pages_line_count_within_3"] = float((d.abs() <= 3).mean())
    m["pages_line_count_exact"] = float((d == 0).mean())
    m["median_abs_line_diff"] = float(d.abs().median())
    m["mean_rel_line_error"] = float((d.abs() / p.lines_transcribed).mean())
    m["lines_aligned_share_of_transcribed"] = float(p.lines_aligned.sum() / p.lines_transcribed.sum())
    m["lines_words_unsup_share_of_aligned"] = float(p.lines_words_unsup.sum() / max(p.lines_aligned.sum(), 1))
    m["lines_words_guided_share_of_aligned"] = float(p.lines_words_guided.sum() / max(p.lines_aligned.sum(), 1))
    m["lines_rejected_share_of_aligned"] = float(p.lines_rejected.sum() / max(p.lines_aligned.sum(), 1))
    # word-count agreement of the plain gap threshold (all aligned lines, before guidance)
    m["words_detected_total"] = int(p.words_detected.sum())
    m["words_transcribed_total"] = int(p.words_transcribed.sum())
    # independent plausibility check: word width (px) vs transcribed length (characters)
    acc = words[(words.word_source != "") & (words.tr_chars > 0)].copy()
    acc["wpx"] = acc.x1 - acc.x0
    if len(acc) > 20:
        r = float(np.corrcoef(acc.wpx, acc.tr_chars)[0, 1])
        shuf = []
        for _ in range(20):
            shuf.append(np.corrcoef(acc.wpx.values, rng.permutation(acc.tr_chars.values))[0, 1])
        m["word_width_vs_chars_r"] = r
        m["word_width_vs_chars_r_shuffled"] = float(np.mean(shuf))
        m["accepted_words"] = int(len(acc))
    g = words[words.tr_units > 0]
    if len(g):
        dd = g.n_cand - g.tr_units
        m["glyph_words"] = int(len(g))
        m["glyph_count_exact"] = float((dd == 0).mean())
        m["glyph_count_within_1"] = float((dd.abs() <= 1).mean())
        m["glyph_count_mean_diff"] = float(dd.mean())
        m["glyph_count_mae"] = float(dd.abs().mean())
        m["glyph_count_corr"] = float(np.corrcoef(g.n_cand, g.tr_units)[0, 1])
    for src in ("cand", "forced", "randcut"):
        m[f"n_{src}"] = int((glyphs.source == src).sum())
    m["n_strict_labelled"] = int((glyphs.unit_strict != "").sum())
    return m


# ----------------------------------------------------------------------------- features

def hog_features(crops: np.ndarray) -> np.ndarray:
    from skimage.feature import hog
    out = [hog(c.astype(np.float32) / 255.0, orientations=9, pixels_per_cell=(6, 6), cells_per_block=(2, 2),
               feature_vector=True) for c in crops]
    return np.asarray(out, np.float32)


def build_features(crops: np.ndarray, geom: np.ndarray, n_pca: int = 40, seed: int = 1, fit_idx=None):
    """HOG(24x24 black-hat crop) + 3 geometry features (w, h, y-centre in x-heights) -> standardised PCA."""
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    H = hog_features(crops)
    G = np.clip(geom, -4, 4) * 2.0
    X = np.hstack([H, G]).astype(np.float32)
    fit = X if fit_idx is None else X[fit_idx]
    sc = StandardScaler().fit(fit)
    pca = PCA(n_components=min(n_pca, X.shape[1]), random_state=seed).fit(sc.transform(fit))
    return pca.transform(sc.transform(X)), (sc, pca)


# ----------------------------------------------------------------------------- agreement metrics

def agreement(labels: np.ndarray, clusters: np.ndarray, seed: int = 1) -> dict:
    from sklearn import metrics as M
    rng = np.random.RandomState(seed)
    out = {"nmi": M.normalized_mutual_info_score(labels, clusters),
           "ari": M.adjusted_rand_score(labels, clusters),
           "homogeneity": M.homogeneity_score(labels, clusters),
           "completeness": M.completeness_score(labels, clusters)}
    ct = pd.crosstab(clusters, labels)
    out["purity"] = float(ct.max(axis=1).sum() / ct.values.sum())
    base = [M.normalized_mutual_info_score(rng.permutation(labels), clusters) for _ in range(5)]
    out["nmi_shuffled"] = float(np.mean(base))
    return {k: float(v) for k, v in out.items()}


def knn_cv(X: np.ndarray, y: np.ndarray, groups: np.ndarray, cap_per_class: int = 500, seed: int = 1, k: int = 7):
    """Group-k-fold (by PDF page) kNN accuracy; classes capped to balance. Returns metrics, labels, predictions."""
    from sklearn.model_selection import GroupKFold
    from sklearn.neighbors import KNeighborsClassifier
    rng = np.random.RandomState(seed)
    keep = []
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        keep.extend(rng.choice(idx, min(len(idx), cap_per_class), replace=False))
    keep = np.sort(np.array(keep))
    Xs, ys, gs_ = X[keep], y[keep], groups[keep]
    n_groups = len(np.unique(gs_))
    pred = np.empty(len(ys), dtype=object)
    for tr, te in GroupKFold(n_splits=min(5, n_groups)).split(Xs, ys, gs_):
        clf = KNeighborsClassifier(n_neighbors=k).fit(Xs[tr], ys[tr])
        pred[te] = clf.predict(Xs[te])
    classes = np.unique(ys)
    recalls = {c: float((pred[ys == c] == c).mean()) for c in classes}
    res = {"accuracy": float((pred == ys).mean()), "macro_recall": float(np.mean(list(recalls.values()))),
           "chance": float(1.0 / len(classes)), "n": int(len(ys)), "classes": int(len(classes))}
    return res, ys, pred, recalls


def confusable_pairs(y: np.ndarray, pred: np.ndarray, top: int = 15) -> pd.DataFrame:
    classes = sorted(set(y))
    idx = {c: i for i, c in enumerate(classes)}
    C = np.zeros((len(classes), len(classes)))
    for a, b in zip(y, pred):
        C[idx[a], idx[b]] += 1
    n = C.sum(axis=1)
    rows = []
    for i in range(len(classes)):
        for j in range(i + 1, len(classes)):
            rows.append((classes[i], classes[j], (C[i, j] + C[j, i]) / (n[i] + n[j]), C[i, j] / n[i], C[j, i] / n[j]))
    df = pd.DataFrame(rows, columns=["unit_a", "unit_b", "confusion_rate", "a_as_b", "b_as_a"])
    return df.sort_values("confusion_rate", ascending=False).head(top).reset_index(drop=True), C, classes


# ----------------------------------------------------------------------------- figures

def _sheet(crops_by_row: list[list[np.ndarray]], labels: list[str], path: Path, scale: int = 3, per_row: int = 16):
    import cv2
    cs = gs.CROP * scale
    label_w = 230
    W = label_w + per_row * cs
    H = len(crops_by_row) * cs
    img = np.full((H, W), 255, np.uint8)
    for r, (row, lab) in enumerate(zip(crops_by_row, labels)):
        cv2.putText(img, lab, (4, r * cs + cs // 2 + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, 0, 1, cv2.LINE_AA)
        for c, cr in enumerate(row[:per_row]):
            big = cv2.resize(255 - cr, (cs, cs), interpolation=cv2.INTER_CUBIC)
            img[r * cs:(r + 1) * cs, label_w + c * cs:label_w + (c + 1) * cs] = big
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])


def overlay_page(pdf_page: int, folio: str, path: Path, crop=(80, 60, 1240, 560)) -> None:
    """Annotated crop of a page: lines (red), words (blue), glyph candidates (alternating green/orange)."""
    import cv2
    from PIL import Image
    seg = gs.segment_page(gs.page_image_path(pdf_page), pdf_page, folio)
    vis = cv2.cvtColor(seg.gray, cv2.COLOR_GRAY2BGR)
    for li, ln in enumerate(seg.lines):
        cv2.rectangle(vis, (ln.x0, ln.y0), (ln.x1, ln.y1), (0, 0, 255), 1)
        for wi, w in enumerate(seg.words[li]):
            cv2.rectangle(vis, (w.x0, w.y0 - 2), (w.x1, w.y1 + 2), (255, 80, 0), 1)
            for gi, g in enumerate(seg.glyphs[li][wi]):
                cv2.rectangle(vis, (g.x0, g.y0), (g.x1, g.y1), [(0, 170, 0), (0, 140, 255)][gi % 2], 1)
    x0, y0, x1, y1 = crop
    im = Image.fromarray(cv2.cvtColor(vis[y0:y1, x0:x1], cv2.COLOR_BGR2RGB))
    im = im.resize((int(im.width * 1.25), int(im.height * 1.25)), Image.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.quantize(colors=48, method=Image.MEDIANCUT).save(path, optimize=True)


def _plot_sweep(sweep: pd.DataFrame, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 3.6))
    for name, g in sweep.groupby("set"):
        ax.plot(g.k, g.nmi, marker="o", label=f"{name}")
    ax.plot(sweep.groupby("k").nmi_shuffled.mean().index, sweep.groupby("k").nmi_shuffled.mean().values, "k:", label="shuffled labels")
    ax.set_xlabel("k-means clusters"); ax.set_ylabel("NMI(cluster, EVA unit)"); ax.legend(fontsize=8)
    ax.set_title("Image clusters vs EVA units (strict / forced / random-cut)", fontsize=9)
    fig.tight_layout(); path.parent.mkdir(parents=True, exist_ok=True); fig.savefig(path, dpi=110); plt.close(fig)


def _plot_confusion(C: np.ndarray, classes: list[str], path: Path, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    Cn = C / np.maximum(C.sum(axis=1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.imshow(Cn, cmap="viridis", vmin=0, vmax=max(0.5, Cn.max()))
    ax.set_xticks(range(len(classes))); ax.set_xticklabels(classes, rotation=90, fontsize=7)
    ax.set_yticks(range(len(classes))); ax.set_yticklabels(classes, fontsize=7)
    ax.set_xlabel("predicted from image"); ax.set_ylabel("EVA unit"); ax.set_title(title, fontsize=9)
    fig.tight_layout(); path.parent.mkdir(parents=True, exist_ok=True); fig.savefig(path, dpi=100); plt.close(fig)


# ----------------------------------------------------------------------------- main analysis

def analyse(out: Path | None = None, seed: int = 1, verbose: bool = True) -> dict:
    from sklearn.cluster import KMeans, HDBSCAN
    from sklearn.metrics import silhouette_score
    rng = np.random.RandomState(seed)
    pages, words, glyphs, crops, meta = load_stage(out)
    res: dict = {"meta": meta, "qa": qa_metrics(pages, words, glyphs, seed)}
    geom_cols = ["w_xh", "h_xh", "yc_xh"]

    # --- crop selection (cap sizes; keep every strictly labelled crop) -------------------------------
    ok_size = (glyphs.w_xh.between(0.12, 3.5)) & (glyphs.h_xh.between(0.25, 4.0))
    cand = glyphs[(glyphs.source == "cand") & ok_size]
    strict = cand[cand.unit_strict != ""]
    unl = cand[cand.unit_strict == ""]
    unl = unl.sample(min(len(unl), 25000), random_state=seed)
    forced = glyphs[(glyphs.source == "forced") & ok_size]
    forced = forced.sample(min(len(forced), 20000), random_state=seed)
    rand = glyphs[(glyphs.source == "randcut") & ok_size]
    rand = rand.sample(min(len(rand), 20000), random_state=seed)
    use = pd.concat([strict.assign(_set="strict"), unl.assign(_set="unlabelled"),
                     forced.assign(_set="forced"), rand.assign(_set="random")], ignore_index=True)
    if verbose:
        print(f"features for {len(use)} crops (strict {len(strict)}, forced {len(forced)}, random {len(rand)})")
    X, _ = build_features(crops[use.crop.values], use[geom_cols].values, seed=seed,
                          fit_idx=np.where(use._set.isin(["strict", "unlabelled"]))[0])
    use["_i"] = np.arange(len(use))

    # --- inventory: cluster the candidate crops (CC/valley candidates, no transcription used) ---------
    Uidx = use.index[use._set.isin(["strict", "unlabelled"])].values
    XU = X[Uidx]
    sub = rng.choice(len(XU), min(len(XU), 6000), replace=False)
    sweep_rows, models = [], {}
    for k in K_LIST:
        km = KMeans(n_clusters=k, n_init=3, random_state=seed).fit(XU)
        models[k] = km
        sil = float(silhouette_score(XU[sub], km.labels_[sub])) if k > 1 else float("nan")
        res.setdefault("silhouette", {})[k] = sil
        for name, sset in (("strict", "strict"), ("forced", "forced"), ("random-cut", "random")):
            g = use[use._set == sset]
            vc = g.unit_strict if sset == "strict" else g.unit_forced
            keep_units = vc.value_counts()
            keep_units = keep_units[keep_units >= MIN_UNIT_N].index
            gg = g[vc.isin(keep_units)]
            if len(gg) < 100 or vc.loc[gg.index].nunique() < 4:
                continue
            lab = vc.loc[gg.index].values
            pred = km.predict(X[gg._i.values])
            a = agreement(lab, pred, seed)
            sweep_rows.append({"k": k, "set": name, "n": len(gg), "units": int(len(keep_units)), **a})
    sweep = pd.DataFrame(sweep_rows)
    res["sweep"] = sweep
    # HDBSCAN (density based) for an inventory size not fixed in advance
    hs = rng.choice(len(XU), min(len(XU), 15000), replace=False)
    hdb = HDBSCAN(min_cluster_size=80, min_samples=10).fit(XU[hs][:, :20])
    nl = hdb.labels_
    res["hdbscan"] = {"clusters": int(len(set(nl)) - (1 if -1 in nl else 0)), "noise_share": float((nl == -1).mean()),
                      "n": int(len(hs))}
    res["kmeans_k_best_silhouette"] = int(max(res["silhouette"], key=lambda k: res["silhouette"][k]))

    # --- supervised separability of EVA units (kNN, grouped by page) and confusable pairs ---------------
    sep = {}
    conf = {}
    per_unit = {}
    for name, sset in (("strict", "strict"), ("forced", "forced"), ("random-cut", "random")):
        g = use[use._set == sset]
        lab = (g.unit_strict if sset == "strict" else g.unit_forced).values
        cnt = pd.Series(lab).value_counts()
        keepu = set(cnt[cnt >= MIN_UNIT_N].index)
        msk = np.array([l in keepu for l in lab])
        if msk.sum() < 100 or len(keepu) < 4:
            continue
        r, ys, pr, rec = knn_cv(X[g._i.values[msk]], lab[msk], g.pdf_page.values[msk], seed=seed)
        sep[name] = r
        per_unit[name] = rec
        pairs, C, classes = confusable_pairs(ys, pr)
        conf[name] = (pairs, C, classes)
    res["knn"] = sep
    res["confusable"] = {k: v[0] for k, v in conf.items()}
    res["_conf"] = conf
    res["per_unit_recall"] = per_unit

    # --- main model (k = K_MAIN): cluster <-> EVA table ---------------------------------------------------
    km = models[K_MAIN] if K_MAIN in models else models[K_LIST[len(K_LIST) // 2]]
    use["cluster"] = km.predict(X)
    res["k_main"] = int(km.n_clusters)
    S = use[use._set == "strict"]
    rows = []
    for c in range(km.n_clusters):
        mem = use[(use.cluster == c) & use._set.isin(["strict", "unlabelled"])]
        lab = S[S.cluster == c].unit_strict.value_counts()
        top = ", ".join(f"{u} {v / lab.sum():.0%}" for u, v in lab.head(3).items()) if len(lab) else ""
        rows.append({"cluster": c, "n_candidates": len(mem), "n_strict_labelled": int(lab.sum()),
                     "top_eva_units": top, "purity": float(lab.iloc[0] / lab.sum()) if len(lab) else float("nan"),
                     "median_w_xh": float(mem.w_xh.median()), "median_h_xh": float(mem.h_xh.median()),
                     "median_yc_xh": float(mem.yc_xh.median())})
    res["clusters"] = pd.DataFrame(rows)
    ct = pd.crosstab(S.cluster, S.unit_strict)
    res["contingency"] = ct
    use["_cl"] = use.cluster
    res["use"] = use
    res["X"] = X
    res["crops"] = crops
    res["glyph_df"] = glyphs
    res["pages_df"], res["words_df"] = pages, words
    return res


def eva_comparison(res: dict) -> pd.DataFrame:
    """Per EVA unit: catalogue share, labelled crop counts, kNN recall per set, dominant cluster/spread."""
    use = res["use"]
    cat_path = glyphs_dir() / "catalog.csv"
    cat = pd.read_csv(cat_path) if cat_path.exists() else pd.DataFrame(columns=["glyph", "share", "group"])
    cat = cat[cat.get("group", "P") == "P"] if "group" in cat else cat
    share = dict(zip(cat.glyph, cat.share)) if len(cat) else {}
    S = use[use._set == "strict"]
    F = use[use._set == "forced"]
    units = sorted(set(S.unit_strict) | set(F.unit_forced) - {""})
    rows = []
    ct = res["contingency"]
    for u in units:
        if u == "":
            continue
        n_s, n_f = int((S.unit_strict == u).sum()), int((F.unit_forced == u).sum())
        if n_s + n_f < 20:
            continue
        rows.append({"eva_unit": u, "catalogue_share": share.get(u, float("nan")),
                     "n_strict": n_s, "n_forced": n_f,
                     "recall_strict": res["per_unit_recall"].get("strict", {}).get(u, float("nan")),
                     "recall_forced": res["per_unit_recall"].get("forced", {}).get(u, float("nan")),
                     "recall_random_cut": res["per_unit_recall"].get("random-cut", {}).get(u, float("nan")),
                     "main_cluster": int(ct[u].idxmax()) if u in ct else -1,
                     "main_cluster_share": float(ct[u].max() / ct[u].sum()) if u in ct and ct[u].sum() else float("nan")})
    return pd.DataFrame(rows).sort_values("n_forced", ascending=False).reset_index(drop=True)


# ----------------------------------------------------------------------------- outputs

def write_outputs(res: dict, seed: int = 1, overlays=((190, "f106r"), (138, "f76r"), (4, "f1r"))) -> dict:
    import cv2
    rep, gd = image_report_dir(), image_glyph_dir()
    rep.mkdir(parents=True, exist_ok=True)
    gd.mkdir(parents=True, exist_ok=True)
    rng = np.random.RandomState(seed)
    use, crops = res["use"], res["crops"]
    qa = res["qa"]

    # tables
    (rep / "qa_metrics.json").write_text(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in qa.items()},
                                                    indent=1))
    res["pages_df"].to_csv(rep / "pages.csv", index=False)
    res["sweep"].round(4).to_csv(rep / "cluster_agreement_sweep.csv", index=False)
    res["clusters"].round(3).to_csv(gd / f"image_inventory_k{res['k_main']}.csv", index=False)
    res["contingency"].to_csv(rep / "cluster_vs_eva_contingency_strict.csv")
    cmp_ = eva_comparison(res)
    cmp_.round(3).to_csv(rep / "eva_vs_image.csv", index=False)
    for name, df in res["confusable"].items():
        df.round(3).to_csv(rep / f"confusable_pairs_{name}.csv", index=False)
    knn = pd.DataFrame(res["knn"]).T
    knn.round(4).to_csv(rep / "knn_separability.csv")

    # figures
    _plot_sweep(res["sweep"], rep / "cluster_agreement_sweep.png")
    for name in ("strict", "forced"):
        if name in res["_conf"]:
            _, C, classes = res["_conf"][name]
            _plot_confusion(C, classes, rep / f"confusion_{name}.png", f"kNN confusion, {name} labels (rows: EVA unit)")
    # cluster sheet
    rows, labels = [], []
    cl = res["clusters"]
    for _, r in cl.iterrows():
        mem = use[(use.cluster == r.cluster) & use._set.isin(["strict", "unlabelled"])]
        pick = mem.sample(min(len(mem), 16), random_state=seed)
        rows.append([crops[i] for i in pick.crop.values])
        labels.append(f"c{int(r.cluster):02d} n={int(r.n_candidates)} {r.top_eva_units}"[:40])
    _sheet(rows, labels, rep / f"cluster_sheet_k{res['k_main']}.png", scale=2)
    # EVA unit sheet (strict crops)
    S = use[use._set == "strict"]
    top_units = S.unit_strict.value_counts().head(24).index
    rows, labels = [], []
    for u in top_units:
        g = S[S.unit_strict == u]
        pick = g.sample(min(len(g), 16), random_state=seed)
        rows.append([crops[i] for i in pick.crop.values])
        labels.append(f"EVA '{u}' n={len(g)}")
    _sheet(rows, labels, rep / "eva_units_strict_sheet.png", scale=2)
    # overlays
    done = []
    for pg, fol in overlays:
        try:
            overlay_page(pg, fol, rep / f"overlay_p{pg:03d}_{fol}.png")
            done.append(f"overlay_p{pg:03d}_{fol}.png")
        except FileNotFoundError:
            pass

    # small representative sample of crops in git (tiny 24x24 PNGs) + metadata
    sdir = gd / "sample"
    if sdir.exists():
        for f in sdir.glob("*.png"):
            f.unlink()
    sdir.mkdir(parents=True, exist_ok=True)
    pieces = []
    for u in top_units:
        g = S[S.unit_strict == u]
        pieces.append(g.sample(min(len(g), 6), random_state=seed))
    U = use[use._set == "unlabelled"]
    pieces.append(U.sample(min(len(U), 60), random_state=seed))
    sample = pd.concat(pieces)
    names = []
    for _, r in sample.iterrows():
        name = f"p{int(r.pdf_page):03d}_l{int(r.line):02d}_w{int(r.word):02d}_g{int(r.idx):02d}.png"
        cv2.imwrite(str(sdir / name), 255 - crops[int(r.crop)])
        names.append(name)
    sample = sample.assign(file=names)[["file", "pdf_page", "folio", "hand", "line", "word", "idx", "x0", "y0", "x1", "y1",
                                       "w_xh", "h_xh", "yc_xh", "cluster", "unit_strict", "aligned_word"]]
    sample.to_csv(gd / "sample_metadata.csv", index=False)
    res["sample_files"] = len(sample)
    res["overlays"] = done
    res["eva_cmp"] = cmp_
    return res


def _pct(x) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.0f}%"


def write_markdown(res: dict) -> Path:
    qa, sw, knn = res["qa"], res["sweep"], res["knn"]
    k_main = res["k_main"]

    def sw_row(k, s):
        r = sw[(sw.k == k) & (sw.set == s)]
        return r.iloc[0] if len(r) else None

    lines = []
    A = lines.append
    A("# Image glyph stage: QA report (best effort)\n")
    A("> **MS 408 is undeciphered. This stage does not decode anything.** It tries to find lines, words and glyph "
      "candidates in the page scans and to compare visual clusters with the *transcriber's* EVA alphabet. All "
      "accuracy numbers below are **proxies** measured against that transcription (there is no hand-annotated "
      "ground truth), on the same 28 pages that were used to choose the parameters, so they are optimistic.\n")
    A("## What was run\n")
    A(f"- Pages: {qa['pages']} text-dominant single-folio pages (stars/recipes section f103-f116 plus f1r, f58, f66r, f76r), "
      "chosen from `data/page_index.csv` (`text_page_candidate`). Herbal/zodiac/biological pages with drawings were not attempted.")
    A("- Input: native scans extracted from the PDF (about 1500x2000 px, 220 ppi; letter x-height is only ~11-12 px).")
    A("- Method: black-hat ink extraction, projection-profile deskew, row-profile line detection, column-gap word "
      "splitting, connected-component + valley glyph candidates, HOG + geometry features, k-means / HDBSCAN.\n")
    A("## Accuracy proxies\n")
    A("| Stage | Metric | Value |\n|---|---|---|")
    A(f"| Lines | detected / transcribed P-lines (all pages) | {qa['lines_detected_total']} / {qa['lines_transcribed_total']} |")
    A(f"| Lines | pages with exact / within ±1 / within ±3 line count | {_pct(qa['pages_line_count_exact'])} / "
      f"{_pct(qa['pages_line_count_within_1'])} / {_pct(qa['pages_line_count_within_3'])} |")
    A(f"| Lines | mean relative line-count error per page | {_pct(qa['mean_rel_line_error'])} |")
    A(f"| Lines | transcribed lines that got a detected partner (DP alignment) | {_pct(qa['lines_aligned_share_of_transcribed'])} |")
    A(f"| Words | detected / transcribed words (plain gap threshold, all pages) | {qa['words_detected_total']} / {qa['words_transcribed_total']} |")
    A(f"| Words | aligned lines where the plain threshold reproduces the exact word count | {_pct(qa['lines_words_unsup_share_of_aligned'])} |")
    A(f"| Words | aligned lines needing guided splitting / rejected as ambiguous | {_pct(qa['lines_words_guided_share_of_aligned'])} / {_pct(qa['lines_rejected_share_of_aligned'])} |")
    A(f"| Words | correlation image word width vs transcribed length (n={qa.get('accepted_words', 0)}; shuffled control {qa.get('word_width_vs_chars_r_shuffled', float('nan')):.2f}) | {qa.get('word_width_vs_chars_r', float('nan')):.2f} |")
    A(f"| Glyphs | candidate count equals transcribed unit count (n={qa.get('glyph_words', 0)} words) | {_pct(qa.get('glyph_count_exact'))} |")
    A(f"| Glyphs | candidate count within ±1 of unit count | {_pct(qa.get('glyph_count_within_1'))} |")
    A(f"| Glyphs | mean (candidates - units), MAE, correlation | {qa.get('glyph_count_mean_diff', float('nan')):+.2f}, {qa.get('glyph_count_mae', float('nan')):.2f}, {qa.get('glyph_count_corr', float('nan')):.2f} |")
    A("")
    A("Reading: line detection is decent on clean text pages (±1 line on about half the pages), word splitting by gaps "
      "is poor (the pen often joins neighbouring words and letters), and glyph candidates match the transcribed unit "
      "count exactly for only about a quarter of the words. The cursive, touching strokes and a ~11 px x-height are the "
      "limiting factors; a higher-resolution source image would help more than any clustering trick.\n")
    A("## Label provenance (so the EVA comparison is not circular)\n")
    A("Crops are cut from the image using ink structure only. The transcription supplies (a) which detected line belongs "
      "to which transcribed line (widths + word counts), (b) the *number* of words in the line, and (c) the number of "
      f"units in a word. EVA letter identity is never used for cutting. Three labelled sets exist:\n")
    A(f"- **strict** ({qa['n_strict_labelled']} crops): word where the number of image candidates equals the number of transcribed units; the i-th candidate gets the i-th unit. Biased towards easily segmented words.")
    A(f"- **forced** ({qa['n_forced']} crops): words where the counts differ are cut at ink valleys into exactly the transcribed number of pieces. Noisy.")
    A(f"- **random-cut control** ({qa['n_randcut']} crops): same words and counts, cut positions drawn at random. Anything the forced set shows above this control is signal from the image.\n")
    A("## Image-derived inventory vs EVA\n")
    A(f"- k-means silhouette is flat (about 0.08 to 0.09 for k = 8 to 40; best k = {res['kmeans_k_best_silhouette']}): the crops "
      "form a continuum, not well-separated classes. HDBSCAN finds "
      f"{res['hdbscan']['clusters']} dense clusters and labels {_pct(res['hdbscan']['noise_share'])} of crops as noise.")
    cat_path = glyphs_dir() / "catalog.csv"
    if cat_path.exists():
        cat = pd.read_csv(cat_path)
        cat = cat[cat.group == "P"] if "group" in cat else cat
        n1, n05 = int((cat.share >= 0.01).sum()), int((cat.share >= 0.005).sum())
        A(f"- The transcription-derived EVA catalogue (`glyphs/catalog.csv`, running text) has {n1} symbols with share >= 1% and {n05} with share >= 0.5%.")
    A("- So the image data **does not support a specific inventory size**. It neither confirms nor refutes the ~15-17 frequent EVA symbols.\n")
    A("Agreement between k-means clusters (fitted on unlabelled candidate crops) and EVA units, restricted to units with at least "
      f"{MIN_UNIT_N} labelled crops:\n")
    A("| k | set | units | NMI | ARI | purity | NMI with shuffled labels |\n|---|---|---|---|---|---|---|")
    for k in K_LIST:
        for s in ("strict", "forced", "random-cut"):
            r = sw_row(k, s)
            if r is not None:
                A(f"| {k} | {s} | {int(r.units)} | {r.nmi:.3f} | {r.ari:.3f} | {r.purity:.2f} | {r.nmi_shuffled:.3f} |")
    A("")
    A("kNN separability of EVA units from crop features (grouped 5-fold by page, classes capped at 500):\n")
    A("| set | classes | accuracy | macro recall | chance |\n|---|---|---|---|---|")
    for s, r in knn.items():
        A(f"| {s} | {r['classes']} | {r['accuracy']:.2f} | {r['macro_recall']:.2f} | {r['chance']:.2f} |")
    A("")
    A("Reading: on the strict set the crops carry real information about the EVA unit (several times chance), but clusters "
      "are far from one-to-one with EVA letters (NMI ~0.15). On the forced set the gain over the random-cut control is small, "
      "so the forced labels are mostly noise: do not treat them as evidence about glyph identity. Because the strict set "
      "is selected by count agreement, it is not a representative sample of the manuscript.\n")
    for s in ("strict", "forced"):
        if s in res["confusable"]:
            A(f"### Most confusable EVA pairs ({s} set, kNN)\n")
            A("| unit A | unit B | pair confusion rate | A read as B | B read as A |\n|---|---|---|---|---|")
            for _, r in res["confusable"][s].head(8).iterrows():
                A(f"| {r.unit_a} | {r.unit_b} | {r.confusion_rate:.2f} | {r.a_as_b:.2f} | {r.b_as_a:.2f} |")
            A("")
    A("Pairs that stay confusable in the strict set (for example a/e, a/i, n/y, e/k) are candidates for 'EVA distinguishes them, the "
      "image at this resolution barely does'. That points at transcription/resolution limits, not at a finding about the script.\n")
    A("## Files\n")
    A("- `qa_metrics.json`, `pages.csv` (per page), `cluster_agreement_sweep.csv`, `knn_separability.csv`, `eva_vs_image.csv`, "
      "`confusable_pairs_*.csv`, `cluster_vs_eva_contingency_strict.csv`")
    A(f"- Figures: `cluster_sheet_k{k_main}.png`, `eva_units_strict_sheet.png`, `confusion_*.png`, `cluster_agreement_sweep.png`")
    A("- Overlays (red = line, blue = word, green/orange = glyph candidates): " + ", ".join(f"`{o}`" for o in res["overlays"]))
    A(f"- `glyphs/image/`: `image_inventory_k{k_main}.csv`, `sample_metadata.csv` and {res['sample_files']} tiny sample crops. "
      "The full crop array (about 77,000 crops) and metadata are in `data/processed/glyph_stage/` (git-ignored).\n")
    A("## Limitations\n")
    A("- No ground-truth boxes; accuracy is inferred from agreement with a transcription that itself has errors and uncertain spaces.")
    A("- Parameters (line smoothing, word-gap fraction, glyph width, merge size) were tuned for count agreement on these same pages. No held-out set.")
    A("- Only 28 text-dominant pages and a few scribal hands; no per-hand or per-quire analysis. Drawings, pigment and bleed-through are not handled; red star marks at line starts are sometimes detected as 'words'.")
    A("- Image resolution (x-height ~11 px) is too low to separate fine stroke differences; the Yale PDF only contains these ~220 ppi scans.")
    A("- Clusters are unlabelled shapes; matching an EVA letter does not mean the glyph is a letter, and nothing here says what the text is.")
    A("- Page-image rights: check Yale's usage statement before redistributing. Only tiny 24x24 crops and three annotated page excerpts are committed.\n")
    path = image_report_dir() / "REPORT.md"
    path.write_text("\n".join(lines))
    return path


def run_image_stage(pages=None, mode: str = "text", units: str = "collapsed", report: bool = True, seed: int = 1) -> dict:
    from .images import extract_native
    from .pageindex import build_index, index_path
    if not index_path().exists():
        build_index()
    extract_native()                      # skips pages already extracted
    out = gs.run_segmentation(pages=pages, mode=mode, units=units)
    print(f"segmented {len(out['pages'])} pages: {len(out['glyphs'])} crops -> {gs.processed_dir()}")
    if not report:
        return out
    res = analyse(seed=seed)
    write_outputs(res, seed)
    path = write_markdown(res)
    print(f"report: {path}")
    return res
