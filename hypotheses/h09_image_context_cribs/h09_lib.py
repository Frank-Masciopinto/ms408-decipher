"""h09: image-context cribs. Labels vs drawn objects, herbal/pharma same-plant pairs, context-word enrichment
against pre-registered visual tags (data/visual_tags.csv, PREREG.md). Quire-aware nulls throughout."""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from msdecipher.quires import load_quires  # noqa: E402

TR = ROOT / "data" / "transcriptions" / "ZL3b-n.txt"
LOC = re.compile(r"^<(f\d+[rv]\d*)\.(\d+),([@+&*=\-~])([A-Z])(\w)>\s*(.*)$")
HDR = re.compile(r"^<(f\d+[rv]\d*)>")
OBJ = {"c": "jar", "f": "plant_part", "n": "nymph", "t": "tube_tub", "s": "star", "z": "zodiac_elem", "a": "astro_elem", "p": "plant"}


def words(raw: str) -> list[str]:
    raw = raw.replace("<->", ".")
    raw = re.sub(r"<[^>]*>", "", raw)
    raw = re.sub(r"\[([^:\]]*):[^\]]*\]", r"\1", raw)
    raw = re.sub(r"\{[^}]*\}|@\d+;", "?", raw)
    return [w for w in re.split(r"[.,\s]+", raw) if w and not re.search(r"[?*!%$]", w)]


def parse(path: Path = TR) -> pd.DataFrame:
    rows = []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = LOC.match(ln)
        if m:
            f, n, _, g, s, txt = m.groups()
            rows.append(dict(folio=f, n=int(n), gtype=g, sub=s, words=words(txt)))
    return pd.DataFrame(rows)


def same_plant_pairs(path: Path = TR) -> list[tuple[str, str, str, bool]]:
    """(herbal folio, pharma folio, source, uncertain) from 'Same plant as ...' header comments (ZL3b).
    Comments follow the page header they describe."""
    out, cur = [], None
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        h = HDR.match(ln)
        if h:
            cur = h.group(1)
        m = re.match(r"#\s*Same plant as (f\d+[rv]\d*)(?:\[[^\]]*\])?\s*(\?)?\s*\(([^)]*)\)", ln)
        if m and cur:
            out.append((cur, m.group(1), m.group(3), bool(m.group(2))))
    return out


def page_bags(loci: pd.DataFrame, gtypes=("P", "C", "R")) -> dict[str, Counter]:
    b = defaultdict(Counter)
    for r in loci.itertuples():
        if r.gtype in gtypes:
            b[r.folio].update(r.words)
    return b


def holm(p):
    p = np.asarray(p, float); o = np.argsort(p); m = len(p); adj = np.empty(m); run = 0
    for i, k in enumerate(o):
        run = max(run, (m - i) * p[k]); adj[k] = min(1, run)
    return adj


def perm_within(groups, rng, n):
    """n permutations (index arrays) that shuffle positions only within the same group."""
    groups = np.asarray(groups); idx = np.arange(len(groups)); out = np.empty((n, len(groups)), int)
    blocks = [np.where(groups == g)[0] for g in np.unique(groups)]
    for k in range(n):
        p = idx.copy()
        for b in blocks:
            p[b] = rng.permutation(b)
        out[k] = p
    return out


# ------------------------------------------------------------------ test 1: label-object vocabulary
def label_table(loci):
    q = load_quires().set_index("page")
    L = loci[(loci.gtype == "L") & loci["sub"].isin(list("cfntsza"))].copy()
    L = L[L.words.map(len) > 0]
    L["obj"] = L["sub"].map(OBJ); L["w"] = L.words.map(lambda ws: max(ws, key=len))
    L["quire"] = L.folio.map(lambda f: q.quire.get(f, -1)); L["section"] = L.folio.map(lambda f: q.section.get(f, "?"))
    return L.reset_index(drop=True)


FEATS = {"pre2": lambda w: w[:2], "suf2": lambda w: w[-2:], "word": lambda w: w, "first": lambda w: w[:1]}


def share_stat(feat_vals, types):
    """(P(share | same type) - P(share | different type)) over all label pairs."""
    f = pd.factorize(feat_vals)[0]; t = pd.factorize(types)[0]
    F = np.zeros((len(f), f.max() + 1)); F[np.arange(len(f)), f] = 1
    T = np.zeros((len(t), t.max() + 1)); T[np.arange(len(t)), t] = 1
    n = len(f)
    tot_pairs = n * (n - 1) / 2
    share_all = ((F.sum(0) ** 2 - F.sum(0)) / 2).sum()
    same = ((T.sum(0) ** 2 - T.sum(0)) / 2).sum()
    FT = F.T @ T  # feature x type counts
    share_same = ((FT ** 2 - FT) / 2).sum()
    return share_same / same - (share_all - share_same) / (tot_pairs - same)


def test_label_objects(L, n_perm=2000, seed=0):
    rng = np.random.default_rng(seed); rows = []
    for null, grp in [("global", np.zeros(len(L))), ("within_quire", L.quire.values)]:
        P = perm_within(grp, rng, n_perm)
        for fn, f in FEATS.items():
            vals = L.w.map(f).values; obs = share_stat(vals, L.obj.values)
            nul = np.array([share_stat(vals, L.obj.values[p]) for p in P])
            rows.append(dict(null=null, feature=fn, obs=obs, null_mean=nul.mean(), null_sd=nul.std(),
                             z=(obs - nul.mean()) / (nul.std() + 1e-12), p=(1 + (nul >= obs).sum()) / (n_perm + 1)))
    d = pd.DataFrame(rows); d["p_holm"] = holm(d.p); return d


def per_type_profile(L):
    rows = []
    for o, g in L.groupby("obj"):
        c1 = Counter(g.w.str[:2]); c2 = Counter(g.w.str[-2:])
        rows.append(dict(obj=o, n=len(g), folios=g.folio.nunique(), quires=g.quire.nunique(),
                         top_pre2=", ".join(f"{k}:{v}" for k, v in c1.most_common(3)),
                         top_suf2=", ".join(f"{k}:{v}" for k, v in c2.most_common(3)),
                         o_initial=round((g.w.str[0] == "o").mean(), 3), mean_len=round(g.w.str.len().mean(), 2),
                         repeated_words=int((g.w.value_counts() > 1).sum())))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ test 2: same-plant pairs
def jacc(a: set, b: set):
    return len(a & b) / max(1, len(a | b))


def test_same_plant(loci, pairs, n_perm=5000, seed=0):
    q = load_quires().set_index("page")
    bags = page_bags(loci, ("P", "L"))
    def pharma_set(f):
        fs = [f] if f in q.index else [x for x in q.index if re.fullmatch(f + r"\d", x)]
        return {w for r in loci[loci.folio.isin(fs) & (loci.gtype == "L")].itertuples() for w in r.words if len(w) >= 3}
    herb = [p for p in q.index if q.section.get(p) == "herbal" and p in bags]
    rows = []
    for h, t, src, unc in pairs:
        if h not in bags or q.section.get(t, 'pharmaceutical') != 'pharmaceutical':
            continue
        ps = pharma_set(t)
        if not ps:
            continue
        sims = {hh: jacc({w for w in bags[hh] if len(w) >= 3}, ps) for hh in herb}
        obs = sims[h]; vals = np.array(list(sims.values()))
        rows.append(dict(herbal=h, pharma=t, source=src, uncertain=unc, n_pharma_labels=len(ps), jaccard=obs,
                         mean_other=vals.mean(), rank_pct=(vals < obs).mean() + 0.5 * (vals == obs).mean(),
                         shared=" ".join(sorted({w for w in bags[h] if len(w) >= 3} & ps))))
    d = pd.DataFrame(rows)
    if len(d):
        # combined: mean rank percentile vs uniform (permutation of partner within all herbal pages)
        rng = np.random.default_rng(seed)
        null = rng.random((n_perm, len(d))).mean(1)  # rank percentile of random partner ~ U(0,1)
        d.attrs["mean_rank_pct"] = d.rank_pct.mean(); d.attrs["p"] = (1 + (null >= d.rank_pct.mean()).sum()) / (n_perm + 1)
    return d


# ------------------------------------------------------------------ test 3: label words in own page text
def test_label_in_text(L, loci, n_perm=5000, seed=0):
    bags = page_bags(loci, ("P", "C", "R"))
    Lw = L[L.w.str.len() >= 3].copy()
    Lw = Lw[Lw.folio.isin(bags.keys())].reset_index(drop=True)
    def hits(folios):
        return np.array([bags[f][w] > 0 for f, w in zip(folios, Lw.w)]).sum()
    obs = hits(Lw.folio.values); rng = np.random.default_rng(seed); res = {}
    for null, grp in [("within_quire", Lw.quire.values), ("within_object_type", Lw.obj.values)]:
        P = perm_within(grp, rng, n_perm)
        nul = np.array([hits(Lw.folio.values[p]) for p in P])
        res[null] = dict(obs=int(obs), n_labels=len(Lw), null_mean=float(nul.mean()), ratio=float(obs / nul.mean()),
                         p=float((1 + (nul >= obs).sum()) / (n_perm + 1)))
    by = Lw.assign(hit=[bags[f][w] > 0 for f, w in zip(Lw.folio, Lw.w)]).groupby("obj").hit.agg(["sum", "count"])
    return res, by


# ------------------------------------------------------------------ test 4/5: context words
def tag_scores(tags):
    t = tags.set_index("folio")
    return pd.DataFrame({
        "water": t.nymphs.clip(upper=30) / 30 + t.pools + t.pipes / 2 + t.green_water + t.blue_water,
        "star": t.stars.clip(upper=30),
        "root": t.roots + 0 * t.jars,
        "jar": t.jars,
        "nymph": t.nymphs,
        "large_root": (t.root_size == 2).astype(float),
        "blue_flower": t.blue_flower.astype(float),
    })


def rate_matrix(loci, folios, min_count=10):
    bags = page_bags(loci, ("P", "C", "R"))
    folios = [f for f in folios if sum(bags[f].values()) >= 20]
    tot = Counter(); [tot.update(bags[f]) for f in folios]
    vocab = [w for w, c in tot.items() if c >= min_count]
    M = np.array([[bags[f][w] for w in vocab] for f in folios], float)
    n = np.array([sum(bags[f].values()) for f in folios], float)
    return folios, vocab, M, n


def _corr(T, R):
    """rows of T (perm x pages) vs columns of R (pages x words): Pearson."""
    Tz = (T - T.mean(1, keepdims=True)) / (T.std(1, keepdims=True) + 1e-12)
    Rz = (R - R.mean(0)) / (R.std(0) + 1e-12)
    return Tz @ Rz / R.shape[0]


def enrichment(folios, vocab, M, n, score, groups, n_perm=2000, seed=0):
    rng = np.random.default_rng(seed)
    R = np.log1p(M / n[:, None] * 1000)
    s = score.reindex(folios).fillna(0).values[None, :]
    obs = _corr(s, R)[0]
    P = perm_within(groups, rng, n_perm)
    nul = _corr(s[0][P], R)
    p_emp = (1 + (nul >= obs[None, :] - 1e-9).sum(0)) / (n_perm + 1)
    from scipy.stats import norm
    z = (obs - nul.mean(0)) / (nul.std(0) + 1e-9)
    p = np.where(nul.std(0) < 1e-6, 1.0, norm.sf(z))  # normal approx to the permutation null (resolution below 1/n_perm)
    d = pd.DataFrame(dict(word=vocab, r=obs, z=z, p=p, p_emp=p_emp, count=M.sum(0).astype(int)))
    # rate ratio top-quartile-tag pages vs rest
    hi = s[0] > np.quantile(s[0], 0.75) if (s[0] > 0).mean() > 0.25 else s[0] > 0
    d["rate_hi"] = M[hi].sum(0) / n[hi].sum() * 1000; d["rate_lo"] = M[~hi].sum(0) / n[~hi].sum() * 1000
    d["rate_ratio"] = (d.rate_hi + 0.05) / (d.rate_lo + 0.05)
    d["p_holm"] = holm(d.p)
    return d.sort_values("p")


def transfer(folios, vocab, M, n, cand, target_mask, groups, k=None, n_rand=2000, seed=0):
    """Combined rate of candidate words on target-tagged vs untagged pages (within a set of pages).
    Nulls: (a) frequency-matched random word sets, (b) within-quire permutation of the target tag."""
    rng = np.random.default_rng(seed); vi = {w: i for i, w in enumerate(vocab)}
    ci = [vi[w] for w in cand if w in vi]
    def stat(cols, mask):
        a = M[mask][:, cols].sum() / n[mask].sum(); b = M[~mask][:, cols].sum() / n[~mask].sum()
        return np.log((a + 1e-6) / (b + 1e-6))
    obs = stat(ci, target_mask)
    tot = M.sum(0); dec = pd.qcut(np.log(tot + 1), 10, labels=False, duplicates="drop")
    pool = defaultdict(list); [pool[d].append(i) for i, d in enumerate(dec)]
    nr = np.array([stat([rng.choice(pool[dec[c]]) for c in ci], target_mask) for _ in range(n_rand)])
    P = perm_within(groups, rng, n_rand)
    nt = np.array([stat(ci, target_mask[p]) for p in P])
    return dict(n_cand=len(ci), log_rate_ratio=float(obs), p_random_words=float((1 + (nr >= obs).sum()) / (n_rand + 1)),
                p_random_tags=float((1 + (nt >= obs).sum()) / (n_rand + 1)), n_target_pages=int(target_mask.sum()), n_pages=len(target_mask))


# ------------------------------------------------------------------ test 6: speculative 'star' word check
STAR = {"latin": "stella", "italian": "stella", "german": "stern", "hebrew": "kokhav", "arabic": "najm", "greek": "aster",
        "occitan": "estela", "czech": "hvezda"}
NULL_CONCEPTS = {"latin": "aqua terra radix folium flos herba sol luna caelum ignis aer vas balneum mulier semen oleum".split(),
                 "italian": "acqua terra radice foglia fiore erba sole luna cielo fuoco aria vaso bagno donna seme olio".split(),
                 "german": "wasser erde wurzel blatt blume kraut sonne mond himmel feuer luft gefass bad frau samen ol".split()}


def pattern(w):
    m = {}; return tuple(m.setdefault(c, len(m)) for c in w)


def struct_score(v, cand):
    """Toy structural consistency: 1 if same length and identical repeat pattern, 0.5 if length +-1, else 0."""
    if len(v) == len(cand) and pattern(v) == pattern(cand):
        return 1.0
    return 0.5 if abs(len(v) - len(cand)) <= 1 else 0.0
