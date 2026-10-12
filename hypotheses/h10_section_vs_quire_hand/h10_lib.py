"""h10: section vs quire / hand / Currier-language effects (see PREREG.md)."""
from __future__ import annotations

import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h09_image_context_cribs")); sys.path.insert(0, str(HERE))
import h09_lib as H9  # noqa: E402
from inventory import pages  # noqa: E402


def load():
    q = pages(); lo = H9.parse(); bags = H9.page_bags(lo, ("P", "C", "R"))
    q = q[q.tokens > 0].reset_index(drop=True)
    return q, bags


def matrix(bags, pg, min_count=2):
    tot = Counter(); [tot.update(bags[p]) for p in pg]
    vocab = sorted(w for w, c in tot.items() if c >= min_count)
    X = np.array([[bags[p][w] for w in vocab] for p in pg], float)
    return X, vocab


def js_classes(X, y):
    """mean pairwise JS (bits) between pooled class distributions."""
    cls = np.unique(y); P = [X[y == c].sum(0) for c in cls]; P = [p / p.sum() for p in P]
    def js(a, b):
        m = (a + b) / 2
        f = lambda u: np.sum(u[u > 0] * np.log2(u[u > 0] / m[u > 0]))
        return 0.5 * f(a) + 0.5 * f(b)
    return float(np.mean([js(a, b) for a, b in combinations(P, 2)]))


def nb_ba(X, y, groups, alpha=0.5):
    """multinomial NB, leave-one-group(bifolium)-out, balanced accuracy."""
    cls = np.unique(y); pred = np.empty(len(y), dtype=object)
    for g in np.unique(groups):
        te = groups == g; tr = ~te
        if len(np.unique(y[tr])) < len(cls):   # conjugate leaves carry the only other page of a class: fall back to leave-one-page-out
            for i in np.where(te)[0]:
                tr1 = np.ones(len(y), bool); tr1[i] = False
                lp1 = [np.log((X[tr1 & (y == c)].sum(0) + alpha) / (X[tr1 & (y == c)].sum(0) + alpha).sum()) for c in cls]
                pr1 = np.log([max(1e-9, np.mean(y[tr1] == c)) for c in cls])
                pred[i] = cls[np.argmax(X[i] @ np.array(lp1).T + pr1)]
            continue
        lp = []
        for c in cls:
            cnt = X[tr & (y == c)].sum(0) + alpha; lp.append(np.log(cnt / cnt.sum()))
        prior = np.log([np.mean(y[tr] == c) for c in cls])
        s = X[te] @ np.array(lp).T + prior
        pred[te] = cls[np.argmax(s, 1)]
    ok = pred != None  # noqa: E711
    return float(np.mean([np.mean(pred[ok & (y == c)] == c) for c in cls if (ok & (y == c)).any()]))


def strat_perms(strata, rng, n):
    strata = np.asarray(strata); out = []
    blocks = [np.where(strata == s)[0] for s in np.unique(strata)]
    for _ in range(n):
        p = np.arange(len(strata))
        for b in blocks:
            p[b] = rng.permutation(b)
        out.append(p)
    return out


def rotations(strata, order):
    """all joint non-identity cyclic rotations of labels along page order within each stratum (up to 200)."""
    strata = np.asarray(strata); blocks = [np.where(strata == s)[0] for s in np.unique(strata)]
    blocks = [b[np.argsort(order[b])] for b in blocks]
    L = max(len(b) for b in blocks); out = []
    for k in range(1, L):
        p = np.arange(len(strata))
        for b in blocks:
            p[b] = np.roll(b, k % len(b))
        if not (p == np.arange(len(p))).all():
            out.append(p)
    return out


def contrast(q, bags, mask, label_col, strata_col="stratum", n_perm=2000, seed=0, name=""):
    d = q[mask].reset_index(drop=True)
    y = d[label_col].values; st = d[strata_col].values; grp = d.bifolium_id.values; order = d.order.values.astype(int)
    X, vocab = matrix(bags, d.page)
    # weight per stratum: statistic computed within strata that contain >1 class, token-weighted
    strata_ok = [s for s in np.unique(st) if len(np.unique(y[st == s])) > 1]
    def stat(yy):
        js = ba = wt = 0.0
        for s in strata_ok:
            m = st == s
            if len(np.unique(yy[m])) < 2: continue
            w = X[m].sum(); js += w * js_classes(X[m], yy[m]); ba += w * nb_ba(X[m], yy[m], grp[m]); wt += w
        return js / wt, ba / wt
    obs = stat(y); rng = np.random.default_rng(seed)
    res = dict(contrast=name, classes=" vs ".join(f"{c}({(y == c).sum()}p/{int(X[y == c].sum())}t)" for c in np.unique(y)),
               strata=len(strata_ok), pages=len(d), tokens=int(X.sum()), js=obs[0], ba=obs[1], ba_chance=1 / len(np.unique(y)))
    for nn, P in [("perm", strat_perms(st, rng, n_perm)), ("drift", rotations(st, order))]:
        nul = np.array([stat(y[p]) for p in P])
        res[f"js_null_{nn}"] = nul[:, 0].mean(); res[f"js_excess_{nn}"] = obs[0] - nul[:, 0].mean()
        res[f"ba_null_{nn}"] = nul[:, 1].mean()
        res[f"p_js_{nn}"] = (1 + (nul[:, 0] >= obs[0] - 1e-12).sum()) / (len(P) + 1)
        res[f"p_ba_{nn}"] = (1 + (nul[:, 1] >= obs[1] - 1e-12).sum()) / (len(P) + 1)
        res[f"n_{nn}"] = len(P)
    # jackknife by bifolium (statistic and JS excess against the perm-null mean)
    jk = []
    for g in np.unique(grp):
        keep = grp != g
        if all(len(np.unique(y[keep & (st == s)])) > 1 for s in strata_ok):
            sub = dict(X=X[keep]); Xs, ys, sts, gs = X[keep], y[keep], st[keep], grp[keep]
            js = ba = wt = 0.0
            for s in strata_ok:
                m = sts == s; w = Xs[m].sum(); js += w * js_classes(Xs[m], ys[m]); ba += w * nb_ba(Xs[m], ys[m], gs[m]); wt += w
            jk.append((js / wt, ba / wt))
    jk = np.array(jk); n = len(jk)
    if n > 2:
        se = np.sqrt((n - 1) / n * ((jk - jk.mean(0)) ** 2).sum(0))
        res["js_se"], res["ba_se"] = se
        res["ba_ci"] = f"{obs[1] - 1.96 * se[1]:.3f}–{obs[1] + 1.96 * se[1]:.3f}"
        res["js_excess_ci"] = f"{res['js_excess_perm'] - 1.96 * se[0]:.3f}–{res['js_excess_perm'] + 1.96 * se[0]:.3f}"
    return res


# ------------------------------------------------------------------ variance decomposition
def hellinger(X):
    R = X / X.sum(1, keepdims=True); return np.sqrt(R)


def dummies(v):
    v = pd.Series(v).astype(str); return pd.get_dummies(v, drop_first=True).values.astype(float)


def r2(Y, Z):
    Yc = Y - Y.mean(0)
    if Z.shape[1] == 0: return 0.0
    Zc = Z - Z.mean(0); B, *_ = np.linalg.lstsq(Zc, Yc, rcond=None)
    return float(((Zc @ B) ** 2).sum() / (Yc ** 2).sum())


def decompose(q, bags, top=300, min_tokens=50, n_perm=999, seed=0):
    d = q[(q.tokens >= min_tokens)].reset_index(drop=True)
    tot = Counter(); [tot.update(bags[p]) for p in d.page]
    vocab = [w for w, _ in tot.most_common(top)]
    X = np.array([[bags[p][w] for w in vocab] for p in d.page], float) + 1e-9
    Y = hellinger(X); o = d.order.values.astype(float); o = (o - o.mean()) / o.std()
    F = {"section": dummies(d.section), "quire": dummies(d.quire), "hand": dummies(d.hand), "language": dummies(d.lang),
         "page_order": np.c_[o, o ** 2, o ** 3]}
    full = np.hstack(list(F.values())); R2f = r2(Y, full); rng = np.random.default_rng(seed); rows = []
    for k, Z in F.items():
        red = np.hstack([v for kk, v in F.items() if kk != k]); R2r = r2(Y, red); uniq = R2f - R2r
        # Freedman-Lane: permute residuals of reduced model
        Yc = Y - Y.mean(0); redc = red - red.mean(0); B, *_ = np.linalg.lstsq(redc, Yc, rcond=None)
        fit = redc @ B; res = Yc - fit; cnt = 0
        for _ in range(n_perm):
            Yp = fit + res[rng.permutation(len(res))]
            cnt += (r2(Yp, full) - r2(Yp, red)) >= uniq - 1e-12
        rows.append(dict(factor=k, df=Z.shape[1], alone_R2=r2(Y, Z), unique_R2=uniq, p_unique=(1 + cnt) / (n_perm + 1)))
    out = pd.DataFrame(rows); out.attrs.update(full_R2=R2f, pages=len(d), words=top)
    # section+quire+hand shared fraction
    sqh = r2(Y, np.hstack([F["section"], F["quire"], F["hand"], F["language"]]))
    out.attrs["shared_section_quire_hand_lang"] = sqh - sum(out.set_index("factor").unique_R2[["section", "quire", "hand", "language"]])
    return out


# ------------------------------------------------------------------ word-set enrichment within strata
def wordset_contrast(q, bags, mask, label_col, target, words, n_perm=2000, seed=0, strata_col="stratum"):
    d = q[mask].reset_index(drop=True); y = (d[label_col].values == target); st = d[strata_col].values
    tot = Counter(); [tot.update(bags[p]) for p in d.page]
    n = np.array([sum(bags[p].values()) for p in d.page], float)
    def cnt(ws): return np.array([sum(bags[p][w] for w in ws) for p in d.page], float)
    c = cnt(words)
    def lrr(c, yy): return float(np.log((c[yy].sum() / n[yy].sum() + 1e-6) / (c[~yy].sum() / n[~yy].sum() + 1e-6)))
    obs = lrr(c, y); rng = np.random.default_rng(seed)
    P = strat_perms(st, rng, n_perm); nl = np.array([lrr(c, y[p]) for p in P])
    # frequency-matched random word sets
    allw = list(tot); f = np.array([tot[w] for w in allw]); lg = np.log(f)
    rw = []
    for _ in range(n_perm):
        ws = [allw[int(np.argmin(np.abs(lg - np.log(max(1, tot[w]))) + rng.random(len(allw)) * 0.3))] for w in words]
        rw.append(lrr(cnt(ws), y))
    rw = np.array(rw)
    return dict(target=target, n_words=len(words), words_present=sum(tot[w] > 0 for w in words), word_tokens=int(c.sum()),
                log_rate_ratio=obs, p_label_perm=float((1 + (nl >= obs).sum()) / (n_perm + 1)),
                p_random_words=float((1 + (rw >= obs).sum()) / (n_perm + 1)), pages=len(d))
