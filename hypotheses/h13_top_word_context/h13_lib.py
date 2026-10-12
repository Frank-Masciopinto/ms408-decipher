"""h13: top-100 words: positions, neighbour contexts, spelling variants, image links (PREREG.md). No meaning claims."""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h09_image_context_cribs")); sys.path.insert(0, str(ROOT / "src"))
import h09_lib as H9  # noqa: E402
from msdecipher.segment import Segmenter, PRESETS  # noqa: E402

SEG = Segmenter(PRESETS["collapsed"], name="collapsed")
LOC = re.compile(r"^<(f\d+[rv]\d*)\.(\d+),([@+&*=\-~])([A-Z])(\w)>\s*(.*)$")


def tokens_raw(txt):
    """all tokens of a locus in order with readability flag (unreadable tokens keep their slot)."""
    t = txt.replace("<->", ".")
    para = t.lstrip().startswith("<%>")
    t = re.sub(r"<[^>]*>", "", t); t = re.sub(r"\[([^:\]]*):[^\]]*\]", r"\1", t); t = re.sub(r"\{[^}]*\}|@\d+;", "?", t)
    toks = [w for w in re.split(r"[.,\s]+", t) if w]
    return [(w, not re.search(r"[?*!%$]", w)) for w in toks], para


def token_table():
    q = pd.read_csv(ROOT / "data" / "quires.csv", dtype=str, keep_default_na=False).set_index("page")
    rows = []
    for ln in H9.TR.read_text(encoding="utf-8", errors="replace").splitlines():
        m = LOC.match(ln)
        if not m: continue
        f, n, _, g, s, txt = m.groups(); toks, para = tokens_raw(txt); L = len(toks)
        for i, (w, ok) in enumerate(toks):
            if not ok: continue
            rows.append(dict(folio=f, line=int(n), gtype=g, sub=s, w=w, pos=i, nline=L, line_initial=i == 0 and g == "P",
                             line_final=i == L - 1 and g == "P", para_initial=i == 0 and g == "P" and para,
                             prev=toks[i - 1][0] if i > 0 and toks[i - 1][1] else None, next=toks[i + 1][0] if i < L - 1 and toks[i + 1][1] else None))
    d = pd.DataFrame(rows)
    d["hand"] = d.folio.map(q.lfd_hand).fillna("?").replace("", "?"); d["lang"] = d.folio.map(q.currier_language).fillna("?").replace("", "?")
    d["HL"] = d.hand + d.lang; d["quire"] = d.folio.map(q.quire).fillna("?"); d["section"] = d.folio.map(q.section).fillna("?")
    d["stratum"] = d.quire + "|" + d.HL; d["is_label"] = d.gtype == "L"
    return d


def top_words(d, k=100):
    return [w for w, _ in Counter(d[d.gtype.isin(["P", "C", "R", "L"])].w).most_common(k)]


# ------------------------------------------------------------------ 1 positions
def positions(d, top):
    from scipy.stats import poisson
    rows = []
    P = d[d.gtype == "P"]
    for col in ("line_initial", "line_final", "para_initial"):
        base = P.groupby("HL")[col].mean()
        for w in top:
            t = P[P.w == w]; obs = int(t[col].sum()); exp = float(t.HL.map(base).sum())
            p = 2 * min(poisson.cdf(obs, exp), poisson.sf(obs - 1, exp)) if exp > 0 else 1.0
            rows.append(dict(word=w, position=col, n=len(t), obs=obs, exp=exp, ratio=(obs + .5) / (exp + .5), p=min(1, p)))
    A = d[d.gtype.isin(["P", "C", "R", "L"])]; base = A.groupby("HL").is_label.mean()
    for w in top:
        t = A[A.w == w]; obs = int(t.is_label.sum()); exp = float(t.HL.map(base).sum())
        p = 2 * min(poisson.cdf(obs, exp), poisson.sf(obs - 1, exp)) if exp > 0 else 1.0
        rows.append(dict(word=w, position="label", n=len(t), obs=obs, exp=exp, ratio=(obs + .5) / (exp + .5), p=min(1, p)))
    r = pd.DataFrame(rows); r["p_holm"] = H9.holm(r.p.values); return r


# ------------------------------------------------------------------ 2 contexts
def context_matrix(d, words, ctx_k=300, rows_filter=None):
    P = d[d.gtype == "P"] if rows_filter is None else d[(d.gtype == "P") & rows_filter]
    ctx = [w for w, _ in Counter(d[d.gtype == "P"].w).most_common(ctx_k)]; ci = {w: i for i, w in enumerate(ctx)}; wi = {w: i for i, w in enumerate(words)}
    M = np.zeros((len(words), 2 * len(ctx)))
    for w, a, b in zip(P.w, P.prev, P.next):
        if w not in wi: continue
        if a in ci: M[wi[w], ci[a]] += 1
        if b in ci: M[wi[w], len(ctx) + ci[b]] += 1
    return M


def ppmi(M):
    tot = M.sum()
    if tot == 0: return M
    r = M.sum(1, keepdims=True); c = M.sum(0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        pmi = np.log((M * tot) / (r @ c))
    return np.nan_to_num(np.maximum(pmi, 0), nan=0, posinf=0, neginf=0)


def cosine(A, B=None):
    B = A if B is None else B
    An = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-12); Bn = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-12)
    return An @ Bn.T


def cluster(V, k=8):
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import pdist
    D = pdist(V, "cosine"); D = np.nan_to_num(D, nan=1.0)
    Z = linkage(D, "average"); lab = fcluster(Z, k, "maxclust")
    return lab, D


def silhouette(D, lab):
    from sklearn.metrics import silhouette_score
    from scipy.spatial.distance import squareform
    if len(set(lab)) < 2: return 0.0
    return float(silhouette_score(squareform(D), lab, metric="precomputed"))


def shuffled_contexts(d, rng):
    """neighbours shuffled within HL (keeps each cell's neighbour distribution, breaks word-neighbour association)."""
    e = d.copy(); P = e.gtype == "P"
    for hl, idx in e[P].groupby("HL").groups.items():
        idx = list(idx); e.loc[idx, "prev"] = rng.permutation(e.loc[idx, "prev"].values); e.loc[idx, "next"] = rng.permutation(e.loc[idx, "next"].values)
    return e


def unit_edit(a, b):
    a, b = SEG(a), SEG(b); D = np.arange(len(b) + 1)
    for i in range(1, len(a) + 1):
        prev = D.copy(); D[0] = i
        for j in range(1, len(b) + 1):
            D[j] = min(prev[j] + 1, D[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
    return int(D[-1])


RULES = [("edy", "ol"), ("edy", "or"), ("dy", "ol")]  # pre-registered h11/h12 rule pairs


def rule_pairs(top):
    s = set(top); out = []
    for w in top:
        for a, b in RULES:
            if w.endswith(a):
                v = w[: -len(a)] + b
                if v in s: out.append((w, v, f"-{a}/-{b}"))
    return out


# ------------------------------------------------------------------ 3 image links
def page_rates(d, words, min_tokens=20):
    A = d[d.gtype.isin(["P", "C", "R"])]
    n = A.groupby("folio").size(); n = n[n >= min_tokens]
    C = A[A.w.isin(words)].groupby(["folio", "w"]).size().unstack(fill_value=0).reindex(index=n.index, columns=words, fill_value=0)
    meta = A.drop_duplicates("folio").set_index("folio").loc[n.index, ["HL", "quire", "stratum", "section"]]
    return np.log1p(C.values / n.values[:, None] * 1000), n, meta


def corr_cols(T, R):
    Tz = (T - T.mean(1, keepdims=True)) / (T.std(1, keepdims=True) + 1e-12); Rz = (R - R.mean(0)) / (R.std(0) + 1e-12)
    return Tz @ Rz / R.shape[0]
