"""h11: explicit hand x Currier-language models; residual section / image tests; hand-effect characterisation (PREREG.md)."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h10_section_vs_quire_hand")); sys.path.insert(0, str(ROOT / "src"))
import h10_lib as H10  # noqa: E402
from msdecipher.quires import group_folds, load_quires  # noqa: E402
from msdecipher.segment import Segmenter, PRESETS  # noqa: E402

holm = H10.H9.holm
SEG = Segmenter(PRESETS["collapsed"], name="collapsed")


def load():
    q, bags = H10.load(); q["HL"] = q.hand + q.lang
    return q, bags


# ------------------------------------------------------------------ 1 hierarchical back-off unigram models
MODELS = {"M0 global": [], "M1 +language": ["lang"], "M2 +hand×lang": ["lang", "HL"], "M3 +HL+quire": ["lang", "HL", "quire"],
          "M4 +HL+section": ["lang", "HL", "section"], "M5 +HL+quire+section": ["lang", "HL", "quire", "section"],
          "M6 +section only": ["section"]}


def fit_predict(q, bags, train, test, levels, a, vocab_size):
    tr = q.iloc[train]; glob = Counter(); [glob.update(bags[p]) for p in tr.page]
    G = sum(glob.values())
    def p_glob(w): return (glob[w] + 0.5) / (G + 0.5 * vocab_size)
    # counts per level key (nested: key = tuple of values up to that level)
    cnt = [dict() for _ in levels]
    for r in tr.itertuples():
        key = ()
        for i, lv in enumerate(levels):
            key = key + (getattr(r, lv),); c = cnt[i].setdefault(key, Counter()); c.update(bags[r.page])
    tot = [{k: sum(v.values()) for k, v in c.items()} for c in cnt]
    ll = 0.0; n = 0
    for r in q.iloc[test].itertuples():
        keys = []; key = ()
        for lv in levels:
            key = key + (getattr(r, lv),); keys.append(key)
        for w, c in bags[r.page].items():
            p = p_glob(w)
            for i, k in enumerate(keys):
                if k in cnt[i]:
                    p = (cnt[i][k][w] + a * p) / (tot[i][k] + a)
            ll += c * np.log2(p); n += c
    return -ll / n, n


def heldout(q, bags, level="quire", k=5, grid=(50, 200, 1000, 5000), seed=0):
    allw = Counter(); [allw.update(bags[p]) for p in q.page]; V = len(allw) * 2
    folds = group_folds(list(q.page), load_quires(), k=k, level=level, seed=seed)
    rows = []
    for name, lv in MODELS.items():
        best = None
        for a in grid:  # choose a by inner score on training folds (cheap: use first fold's training split re-folded)
            s = 0.0
            for tr, te in folds:
                inner = group_folds(list(q.page.iloc[tr]), load_quires(), k=3, level=level, seed=seed + 1)
                tr_i, te_i = inner[0]
                b, _ = fit_predict(q, bags, np.array(tr)[tr_i], np.array(tr)[te_i], lv, a, V); s += b
            if best is None or s < best[1]: best = (a, s)
        a = best[0]; bits = []; ns = []
        for tr, te in folds:
            b, n = fit_predict(q, bags, tr, te, lv, a, V); bits.append(b); ns.append(n)
        bits = np.array(bits); ns = np.array(ns)
        rows.append(dict(model=name, folds=level, a=a, bits_per_token=float((bits * ns).sum() / ns.sum()), fold_bits=" ".join(f"{b:.3f}" for b in bits)))
    d = pd.DataFrame(rows); d["gain_vs_M0"] = d.bits_per_token.iloc[0] - d.bits_per_token
    return d


# ------------------------------------------------------------------ 2 Hellinger profiles and residuals
def profiles(q, bags, top=300, min_tokens=50):
    d = q[q.tokens >= min_tokens].reset_index(drop=True)
    tot = Counter(); [tot.update(bags[p]) for p in d.page]
    vocab = [w for w, _ in tot.most_common(top)]
    X = np.array([[bags[p][w] for w in vocab] for p in d.page], float)
    n = np.array([sum(bags[p].values()) for p in d.page], float)
    Y = np.sqrt(X / n[:, None])
    return d, vocab, X, n, Y


def residualise(Y, *cols):
    Z = np.hstack([H10.dummies(c) for c in cols]) if cols else np.zeros((len(Y), 0))
    Yc = Y - Y.mean(0)
    if Z.shape[1] == 0: return Yc
    Zc = Z - Z.mean(0); B, *_ = np.linalg.lstsq(Zc, Yc, rcond=None)
    return Yc - Zc @ B


def centroid_ba(R, y, groups):
    cls = np.unique(y); pred = np.empty(len(y), dtype=object)
    Rn = R / (np.linalg.norm(R, axis=1, keepdims=True) + 1e-12)
    for g in np.unique(groups):
        te = groups == g; tr = ~te
        C = []
        for c in cls:
            m = tr & (y == c)
            C.append(R[m].mean(0) if m.any() else np.full(R.shape[1], np.nan))
        C = np.array(C); C = C / (np.linalg.norm(C, axis=1, keepdims=True) + 1e-12)
        s = np.nan_to_num(Rn[te] @ C.T, nan=-9); pred[te] = cls[np.argmax(s, 1)]
    return float(np.mean([np.mean(pred[y == c] == c) for c in cls]))


def pseudo_F(R, y):
    cls = np.unique(y); mu = R.mean(0)
    B = sum((y == c).sum() * ((R[y == c].mean(0) - mu) ** 2).sum() for c in cls)
    W = sum(((R[y == c] - R[y == c].mean(0)) ** 2).sum() for c in cls)
    return float((B / (len(cls) - 1)) / (W / (len(y) - len(cls))))


def residual_contrast(R, d, mask, n_perm=2000, seed=0, name="", label="section"):
    m = mask.values if hasattr(mask, "values") else mask
    Rm = R[m]; dd = d[m].reset_index(drop=True); y = dd[label].values; st = dd.HL.values; grp = dd.bifolium_id.values
    order = dd.order.values.astype(int)
    obs_ba = centroid_ba(Rm, y, grp); obs_F = pseudo_F(Rm, y); rng = np.random.default_rng(seed)
    out = dict(contrast=name, classes=" vs ".join(f"{c}({(y == c).sum()}p)" for c in np.unique(y)), pages=len(y),
               ba=obs_ba, chance=1 / len(np.unique(y)), F=obs_F)
    for nn, P in [("hl_perm", H10.strat_perms(st, rng, n_perm)), ("hl_drift", H10.rotations(st, order))]:
        # perm null of F (cheap); BA null on a subsample of perms
        nF = np.array([pseudo_F(Rm, y[p]) for p in P])
        Pb = P[:300] if len(P) > 300 else P
        nB = np.array([centroid_ba(Rm, y[p], grp) for p in Pb])
        out[f"p_F_{nn}"] = float((1 + (nF >= obs_F - 1e-12).sum()) / (len(P) + 1))
        out[f"p_ba_{nn}"] = float((1 + (nB >= obs_ba - 1e-12).sum()) / (len(Pb) + 1))
        out[f"ba_null_{nn}"] = float(nB.mean()); out[f"n_{nn}"] = len(P)
    return out


def residual_decomp(R, d, n_perm=499, seed=0):
    o = d.order.values.astype(float); o = (o - o.mean()) / o.std()
    F = {"section": H10.dummies(d.section), "quire": H10.dummies(d.quire), "page_order": np.c_[o, o ** 2, o ** 3]}
    full = np.hstack(list(F.values())); R2f = H10.r2(R, full); rng = np.random.default_rng(seed); rows = []
    for k, Z in F.items():
        red = np.hstack([v for kk, v in F.items() if kk != k]); uniq = R2f - H10.r2(R, red)
        Rc = R - R.mean(0); redc = red - red.mean(0); B, *_ = np.linalg.lstsq(redc, Rc, rcond=None); fit = redc @ B; res = Rc - fit
        c = 0
        for _ in range(n_perm):
            Rp = fit + res[rng.permutation(len(res))]
            c += (H10.r2(Rp, full) - H10.r2(Rp, red)) >= uniq - 1e-12
        rows.append(dict(factor=k, alone_R2=H10.r2(R, Z), unique_R2=uniq, p_unique=(1 + c) / (n_perm + 1)))
    out = pd.DataFrame(rows); out.attrs["full_R2"] = R2f; return out


def wordset_residual(R, d, vocab, X, mask, target, words, label="section", n_perm=2000, seed=0):
    m = mask.values if hasattr(mask, "values") else mask
    vi = {w: i for i, w in enumerate(vocab)}; idx = [vi[w] for w in words if w in vi]
    Rm = R[m]; dd = d[m].reset_index(drop=True); y = dd[label].values == target; st = dd.HL.values; order = dd.order.values.astype(int)
    def stat(cols, yy): s = Rm[:, cols].sum(1); return float(s[yy].mean() - s[~yy].mean())
    obs = stat(idx, y); rng = np.random.default_rng(seed)
    P = H10.strat_perms(st, rng, n_perm); nP = np.array([stat(idx, y[p]) for p in P])
    D = H10.rotations(st, order); nD = np.array([stat(idx, y[p]) for p in D]) if D else np.array([np.inf])
    freq = X.sum(0); dec = pd.qcut(np.log(freq + 1), 10, labels=False, duplicates="drop")
    pool = {k: np.where(dec == k)[0] for k in np.unique(dec)}
    nW = np.array([stat([rng.choice(pool[dec[i]]) for i in idx], y) for _ in range(n_perm)])
    return dict(n_words_in_vocab=len(idx), target_pages=int(y.sum()), pages=len(y), effect=obs,
                p_hl_perm=float((1 + (nP >= obs).sum()) / (n_perm + 1)), p_hl_drift=float((1 + (nD >= obs).sum()) / (len(D) + 1)),
                n_drift=len(D), p_random_words=float((1 + (nW >= obs).sum()) / (n_perm + 1)))


# ------------------------------------------------------------------ 3 hand features
def log_odds(c1: Counter, c2: Counter, prior: Counter, a0=None):
    """Monroe et al. 2008 log-odds with informative Dirichlet prior; returns DataFrame word, delta, z."""
    n1, n2 = sum(c1.values()), sum(c2.values()); P = sum(prior.values()); a0 = a0 or 0.1 * P
    rows = []
    for w, pc in prior.items():
        a = a0 * pc / P; y1, y2 = c1[w], c2[w]
        d = np.log((y1 + a) / (n1 + a0 - y1 - a)) - np.log((y2 + a) / (n2 + a0 - y2 - a))
        v = 1 / (y1 + a) + 1 / (y2 + a); rows.append((w, d, d / np.sqrt(v), y1, y2))
    return pd.DataFrame(rows, columns=["feature", "delta", "z", "n1", "n2"])


def features(bags, pg, kind):
    c = Counter()
    for p in pg:
        for w, k in bags[p].items():
            if kind == "word": c[w] += k
            else:
                u = SEG(w)
                if kind == "unit": [c.update({x: k}) for x in u]
                elif kind == "prefix": c[u[0] + "-"] += k
                elif kind == "suffix": c["-" + u[-1]] += k
    return c


def discriminate(bags, A, B, kind, top=15, n_boot=300, seed=0):
    cA, cB = features(bags, A, kind), features(bags, B, kind); pr = cA + cB
    pr = Counter({w: v for w, v in pr.items() if v >= 5})
    d = log_odds(cA, cB, pr); rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        bA = list(rng.choice(A, len(A))); bB = list(rng.choice(B, len(B)))
        boots.append(log_odds(features(bags, bA, kind), features(bags, bB, kind), pr).set_index("feature").delta)
    Bt = pd.concat(boots, axis=1)
    d["ci_lo"] = d.feature.map(Bt.quantile(.025, axis=1)); d["ci_hi"] = d.feature.map(Bt.quantile(.975, axis=1))
    d = d.sort_values("z"); return pd.concat([d.head(top), d.tail(top)]).assign(kind=kind)


# ------------------------------------------------------------------ orthography vs vocabulary: greedy rewrite rules
def jsd(c1: Counter, c2: Counter):
    keys = set(c1) | set(c2); n1, n2 = sum(c1.values()), sum(c2.values())
    a = np.array([c1[k] / n1 for k in keys]); b = np.array([c2[k] / n2 for k in keys]); m = (a + b) / 2
    f = lambda u: np.sum(u[u > 0] * np.log2(u[u > 0] / m[u > 0]))
    return 0.5 * f(a) + 0.5 * f(b)


def apply_rule(w, rule):
    pos, s, t = rule
    if pos == "end": return w[: -len(s)] + t if w.endswith(s) else w
    if pos == "start": return t + w[len(s):] if w.startswith(s) else w
    return w.replace(s, t)


def rewrite(c: Counter, rules):
    out = Counter()
    for w, k in c.items():
        for r in rules: w = apply_rule(w, r)
        out[w] += k
    return out


def candidate_rules(cB: Counter, cA: Counter, maxlen=3, top=25):
    def grams(c, pos):
        g = Counter()
        for w, k in c.items():
            for L in range(1, maxlen + 1):
                if len(w) <= L: continue
                if pos == "end": g[w[-L:]] += k
                elif pos == "start": g[w[:L]] += k
                else:
                    for i in range(len(w) - L + 1): g[w[i:i + L]] += k
        return g
    rules = []
    for pos in ("end", "start", "any"):
        gB, gA = grams(cB, pos), grams(cA, pos)
        S = [s for s, _ in gB.most_common(top)]; T = [t for t, _ in gA.most_common(top)] + [""]
        rules += [(pos, s, t) for s in S for t in T if s != t]
    return rules


def greedy_rules(cB_tr, cA_tr, max_rules=10):
    cand = candidate_rules(cB_tr, cA_tr); rules = []; cur = cB_tr; base = jsd(cur, cA_tr)
    for _ in range(max_rules):
        best = None
        for r in cand:
            v = jsd(rewrite(cur, [r]), cA_tr)
            if best is None or v < best[1]: best = (r, v)
        if best is None or best[1] >= base - 1e-4: break
        rules.append(best[0]); cur = rewrite(cur, [best[0]]); base = best[1]
    return rules


def gap_closure(bags, A, B, seed=0, max_rules=10):
    """learn rules on half of the pages of each side, score on the other half."""
    rng = np.random.default_rng(seed); A = list(rng.permutation(A)); B = list(rng.permutation(B))
    A1, A2 = A[: len(A) // 2], A[len(A) // 2:]; B1, B2 = B[: len(B) // 2], B[len(B) // 2:]
    cnt = lambda pg: sum((bags[p] for p in pg), Counter())
    rules = greedy_rules(cnt(B1), cnt(A1), max_rules)
    before = jsd(cnt(B2), cnt(A2)); after = jsd(rewrite(cnt(B2), rules), cnt(A2))
    return dict(js_before=before, js_after=after, closed=(before - after) / before, rules=" ; ".join(f"{p}:{s}->{t or '∅'}" for p, s, t in rules))
