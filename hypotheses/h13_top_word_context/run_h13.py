"""Run h13 (see PREREG.md). Writes results/, figures/, cards/."""
import json
from itertools import combinations

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import h13_lib as L
from h13_lib import H9, HERE

rng = np.random.default_rng(13)
R, F, C = HERE / "results", HERE / "figures", HERE / "cards"
d = L.token_table(); top = L.top_words(d); freq = d[d.gtype.isin(["P", "C", "R", "L"])].w.value_counts()
out = {"n_tokens": int(len(d)), "n_top": len(top)}

# 1 positions
pos = L.positions(d, top); pos.to_csv(R / "positions.csv", index=False)
sig = pos[pos.p_holm < 0.05]
out["pos_sig"] = {f"{p}_{dirn}": sorted(sig[(sig.position == p) & ((sig.ratio > 1) == (dirn == "enriched"))].word) for p in ["line_initial", "line_final", "para_initial", "label"] for dirn in ["enriched", "depleted"]}

# 2 contexts + clusters
V = L.ppmi(L.context_matrix(d, top)); lab, D = L.cluster(V); sil = L.silhouette(D, lab)
null_sil = []
for i in range(20):
    e = L.shuffled_contexts(d, rng); Vn = L.ppmi(L.context_matrix(e, top)); ln, Dn = L.cluster(Vn); null_sil.append(L.silhouette(Dn, ln))
out["silhouette"] = sil; out["silhouette_null_mean"] = float(np.mean(null_sil)); out["silhouette_null_max"] = float(np.max(null_sil))
out["silhouette_p"] = float((1 + sum(s >= sil for s in null_sil)) / 21)
from scipy.stats import spearmanr
cl = pd.DataFrame({"word": top, "cluster": lab, "freq": [int(freq[w]) for w in top], "rank": range(1, 101)})
# frequency-band check: Kruskal-Wallis of log freq across clusters, and per-cluster rank range
from scipy.stats import kruskal
groups = [np.log(cl[cl.cluster == k].freq) for k in sorted(cl.cluster.unique()) if (cl.cluster == k).sum() > 1]
out["cluster_freq_kruskal_p"] = float(kruskal(*groups).pvalue) if len(groups) > 1 else None
HLs = d[d.gtype == "P"].groupby("HL").size(); HLs = HLs[HLs > 1000].index.tolist()
hlshare = d[d.gtype == "P"].groupby(["w", "HL"]).size().unstack(fill_value=0)[HLs]; hlshare = hlshare.div(hlshare.sum(1), axis=0)
summ = []
for k, g in cl.groupby("cluster"):
    sh = hlshare.loc[g.word].mean(); dom = sh.idxmax()
    summ.append(dict(cluster=int(k), n=len(g), rank_min=int(g["rank"].min()), rank_median=float(g["rank"].median()), rank_max=int(g["rank"].max()),
                     top_HL=dom, top_HL_share=float(sh.max()), members=" ".join(g.word)))
cs = pd.DataFrame(summ); cs.to_csv(R / "clusters.csv", index=False); cl.to_csv(R / "cluster_membership.csv", index=False)
out["clusters"] = summ
U, S, Vt = np.linalg.svd(V - V.mean(0), full_matrices=False); XY = U[:, :2] * S[:2]
fig, ax = plt.subplots(figsize=(10, 8))
for k in sorted(set(lab)):
    m = lab == k; ax.scatter(XY[m, 0], XY[m, 1], s=np.sqrt(cl.freq[m]) * 2, label=f"class {k}", alpha=.6)
for (x, y), w in zip(XY, top): ax.annotate(w, (x, y), fontsize=6)
ax.legend(fontsize=7); ax.set_title(f"h13 top-100 words: PPMI neighbour contexts, SVD 2-D, average-linkage k=8 (silhouette {sil:.3f} vs null {np.mean(null_sil):.3f})")
fig.tight_layout(); fig.savefig(F / "clusters_svd.png", dpi=130); plt.close(fig)

# spelling variants
S = L.cosine(V); idx = {w: i for i, w in enumerate(top)}
pairs = []
for a, b in combinations(top, 2):
    ed = L.unit_edit(a, b)
    if ed <= 2: pairs.append(dict(a=a, b=b, ed=ed, cos=float(S[idx[a], idx[b]])))
pp = pd.DataFrame(pairs); rp = L.rule_pairs(top); rset = {(a, b) for a, b, _ in rp} | {(b, a) for a, b, _ in rp}
pp["rule"] = [(a, b) in rset for a, b in zip(pp.a, pp.b)]
out["n_rule_pairs"] = int(pp.rule.sum()); out["n_ed2_pairs"] = len(pp)
obs = pp[pp.rule].cos.mean() - pp[~pp.rule].cos.mean(); null = []
for _ in range(5000):
    m = rng.permutation(pp.rule.values); null.append(pp.cos[m].mean() - pp.cos[~m].mean())
out["rule_cos_mean"] = float(pp[pp.rule].cos.mean()); out["other_ed2_cos_mean"] = float(pp[~pp.rule].cos.mean())
out["rule_cos_p_one_sided"] = float((1 + sum(n >= obs for n in null)) / 5001)
# cross-hand: X in 2B vs Y in 1A
V2B = L.ppmi(L.context_matrix(d, top, rows_filter=d.HL == "2B")); V1A = L.ppmi(L.context_matrix(d, top, rows_filter=d.HL == "1A")); X = L.cosine(V2B, V1A)
cross = []
for a, b, r in rp:
    for x, y in ((a, b), (b, a)):
        if V2B[idx[x]].sum() == 0 or V1A[idx[y]].sum() == 0: continue
        others = [j for j, w in enumerate(top) if w not in (x, y) and V1A[j].sum() > 0]
        cross.append(dict(x_2B=x, y_1A=y, rule=r, cos=float(X[idx[x], idx[y]]), random_mean=float(X[idx[x], others].mean()),
                          rank_pct=float((X[idx[x], others] < X[idx[x], idx[y]]).mean())))
cr = pd.DataFrame(cross); cr.to_csv(R / "rule_pairs_cross_hand.csv", index=False); pp.to_csv(R / "edit_pairs_context.csv", index=False)
from scipy.stats import wilcoxon
diff = cr.cos - cr.random_mean
out["cross_n"] = len(cr); out["cross_mean_cos"] = float(cr.cos.mean()); out["cross_random_mean"] = float(cr.random_mean.mean())
out["cross_wilcoxon_p_one_sided"] = float(wilcoxon(diff, alternative="greater").pvalue) if len(cr) > 1 else None
# sign-flip permutation as a second check
fl = [np.mean(diff * rng.choice([-1, 1], len(diff))) for _ in range(5000)]
out["cross_signflip_p"] = float((1 + sum(f >= diff.mean() for f in fl)) / 5001)
out["cross_median_rank_pct"] = float(cr.rank_pct.median())

# 3 image links: page level
tags = pd.read_csv(H9.HERE / "data" / "visual_tags.csv"); T = H9.tag_scores(tags)
Rt, n, meta = L.page_rates(d, top); keep = [f for f in n.index if f in T.index]; ki = [list(n.index).index(f) for f in keep]
Rt = Rt[ki]; meta = meta.loc[keep]; Tm = T.loc[keep]
strata = meta.stratum.values; groups = [np.where(strata == s)[0] for s in np.unique(strata)]
rows = []
for tag in Tm.columns:
    t = Tm[tag].values.astype(float)
    if t.std() == 0: continue
    r = L.corr_cols(t[None, :], Rt)[0]
    P = np.empty((2000, len(t)))
    for i in range(2000):
        tt = t.copy()
        for g in groups: tt[g] = t[rng.permutation(g)]
        P[i] = tt
    rn = L.corr_cols(P, Rt)
    for j, w in enumerate(top):
        nd = rn[:, j]; p = (1 + np.sum(np.abs(nd - nd.mean()) >= abs(r[j] - nd.mean()) - 1e-9)) / 2001
        rows.append(dict(word=w, level="page", target=tag, stat=float(r[j]), null_mean=float(nd.mean()), p=float(p)))
# label level
SUB = {"c": "jar", "f": "plant_part", "n": "nymph", "t": "tube", "s": "star", "z": "zodiac"}
Lb = d[d.gtype == "L"].copy(); Lb["obj"] = Lb["sub"].map(SUB).fillna("other"); lg = [np.where(Lb.stratum.values == s)[0] for s in Lb.stratum.unique()]
objs = Lb.obj.values; NL = np.empty((2000, len(Lb)), dtype=object)
for i in range(2000):
    o = objs.copy()
    for g in lg: o[g] = objs[rng.permutation(g)]
    NL[i] = o
wv = Lb.w.values
for w in top:
    m = wv == w
    if m.sum() < 3: continue
    for ob in SUB.values():
        o = int((objs[m] == ob).sum()); nd = (NL[:, m] == ob).sum(1); e = nd.mean()
        if (objs == ob).sum() == 0: continue
        p = (1 + np.sum(np.abs(nd - e) >= abs(o - e))) / 2001
        rows.append(dict(word=w, level="label", target=ob, stat=o, null_mean=float(e), p=float(p)))
im = pd.DataFrame(rows); im["p_holm"] = H9.holm(im.p.values); im.to_csv(R / "image_links.csv", index=False)
surv = im[im.p_holm < 0.05].sort_values("p"); surv.to_csv(R / "image_links_surviving.csv", index=False)
out["n_image_tests"] = len(im); out["n_image_tests_page"] = int((im.level == "page").sum()); out["n_pages"] = len(keep)
out["image_surviving"] = surv[["word", "level", "target", "stat", "null_mean", "p", "p_holm"]].to_dict("records")
out["image_raw_p05"] = int((im.p < 0.05).sum())

# predictions
init = set(out["pos_sig"]["line_initial_enriched"]) | set(out["pos_sig"]["para_initial_enriched"])
out["P1"] = dict(n_initial=len(init), n_final=len(out["pos_sig"]["line_final_enriched"]), pass_=len(init) >= 10 and len(out["pos_sig"]["line_final_enriched"]) >= 5)
nonband = [s for s in summ if s["n"] >= 2 and s["rank_max"] - s["rank_min"] >= 40]
out["P2"] = dict(beats_null=out["silhouette_p"] < 0.05, n_nonband_classes=len(nonband), pass_=out["silhouette_p"] < 0.05 and len(nonband) >= 3)
out["P3"] = dict(p=out["cross_wilcoxon_p_one_sided"], pass_=out["cross_wilcoxon_p_one_sided"] is not None and out["cross_wilcoxon_p_one_sided"] < 0.05)
out["P4"] = dict(n=len(surv), pass_=len(surv) <= 5)
json.dump(out, open(R / "summary.json", "w"), indent=1, default=str)

# cards
cards = []
for w in top:
    p = pos[pos.word == w].set_index("position"); i = idx[w]
    lc = [top[j] for j in np.argsort(-S[i])[1:6]]
    P_ = d[(d.gtype == "P") & (d.w == w)]
    L_, R_ = P_.prev.value_counts().head(5), P_.next.value_counts().head(5)
    vars_ = pp[((pp.a == w) | (pp.b == w))].sort_values("cos", ascending=False).head(5)
    hl = d[d.w == w].HL.value_counts(); sec = d[d.w == w].section.value_counts()
    iw = im[im.word == w].sort_values("p").head(3)
    card = dict(word=w, rank=top.index(w) + 1, count=int(freq[w]), cluster=int(lab[i]),
                **{f"{k}_ratio": round(float(p.loc[k, "ratio"]), 2) for k in p.index}, **{f"{k}_p_holm": float(p.loc[k, "p_holm"]) for k in p.index},
                HL_counts=hl.to_dict(), section_counts=sec.to_dict(), left=L_.to_dict(), right=R_.to_dict(), nearest_context=lc,
                variants=[f"{a if b == w else b} (ed {e}, cos {c:.2f}{', rule' if r else ''})" for a, b, e, c, r in vars_[["a", "b", "ed", "cos", "rule"]].values],
                best_image=[f"{t} {lv} stat {s:.2f} p {pp_:.4f} holm {ph:.3f}" for t, lv, s, pp_, ph in iw[["target", "level", "stat", "p", "p_holm"]].values])
    cards.append(card)
json.dump(cards, open(R / "cards.json", "w"), indent=1, default=str)
pd.DataFrame([{k: (v if not isinstance(v, (dict, list)) else json.dumps(v)) for k, v in c.items()} for c in cards]).to_csv(R / "cards.csv", index=False)
md = ["# h13 word cards (top 100, ZL3b)\n", "Descriptive distributional profiles only; no meanings are claimed. Ratios are observed/expected within hand×language; `*` = Holm p<0.05.\n"]
for c in cards:
    st = lambda k: f"{c[k + '_ratio']}{'*' if c[k + '_p_holm'] < .05 else ''}"
    md += [f"## {c['rank']}. `{c['word']}` (n={c['count']}, class {c['cluster']})",
           f"- position ratios: line-initial {st('line_initial')}, line-final {st('line_final')}, para-initial {st('para_initial')}, label {st('label')}",
           f"- hand×lang: {c['HL_counts']}; sections: {c['section_counts']}",
           f"- left: {c['left']}; right: {c['right']}", f"- nearest by context: {', '.join(c['nearest_context'])}",
           f"- spelling neighbours: {'; '.join(c['variants']) or '-'}", f"- best image tests: {'; '.join(c['best_image']) or '-'}", ""]
(C / "CARDS.md").write_text("\n".join(md))
print(json.dumps({k: v for k, v in out.items() if k not in ("clusters",)}, indent=1, default=str)); print(cs.to_string())
