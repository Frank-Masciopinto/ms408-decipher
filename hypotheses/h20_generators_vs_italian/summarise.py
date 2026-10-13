import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
import h20_lib as L
from h20_lib import HERE
R = HERE / "results"
def group(c):
    return "MS" if c.startswith("MS_") else "Italian" if c.startswith("IT_") else "C0 engine" if c.startswith("GEN_C0") else "self-citation" if c.startswith("GEN_SC") else \
        "Naibbe(it)" if "naibbe" in c else "syllabic(it)" if "syll" in c else "no-vowel(it)" if "novowel" in c else "suspension(it)"
rows = []
for f in sorted(R.glob("cell_*.json")):
    m = json.load(open(f)); c = m["cell"]
    for sch in ["bifolium", "quire"]:
        s = m["schemes"][sch]; b = s["bits"]
        d = L.dstats(b, s["glyphs_per_word"], m["crossfit_W5"]["lam"])
        rows.append(dict(cell=c, group=group(c), scheme=sch, **d, lam5_lo=m["crossfit_W5"]["lam_lo"], lam5_hi=m["crossfit_W5"]["lam_hi"], lam100=m["crossfit_W100"]["lam"],
                         **{f"bits_{k}": v for k, v in b.items()}, glyphs_per_word=s["glyphs_per_word"],
                         naibbe_eps=float(np.mean([min(e.get("naibbe_la_eps", 1), e.get("naibbe_it_eps", 1)) for e in s["extras"]])) if "naibbe_la_eps" in s["extras"][0] else np.nan,
                         winner=min([k for k in b if "+ONSET" not in k], key=lambda k: b[k])))
T = pd.DataFrame(rows); out = {}
for sch in ["bifolium", "quire"]:
    S = T[T.scheme == sch].copy(); S = S[[c for c in S.columns if not c.startswith("m_")]]; ms = S[S.group == "MS"][list(L.DELTA)].to_dict("records")
    mm = pd.DataFrame([L.match(r, ms) for r in S[list(L.DELTA)].to_dict("records")], index=S.index); S = pd.concat([S, mm.add_prefix("m_")], axis=1)
    T.loc[S.index, mm.add_prefix("m_").columns] = mm.add_prefix("m_").values
    out[sch] = dict(ms_range={k: [min(r[k] for r in ms), max(r[k] for r in ms)] for k in L.DELTA},
                    reproduces=sorted(S[(S.group != "MS") & (S.m_reproduces == True)].cell), best=S[S.group != "MS"].sort_values("m_distance").cell.head(5).tolist(),
                    group_mean=S.groupby("group")[list(L.DELTA) + ["m_n_match", "m_distance"]].mean().round(3).to_dict("index"))
T.to_csv(R / "fingerprint_table.csv", index=False)
B = T[T.scheme == "bifolium"].set_index("cell"); P = {}
it = B[B.group == "Italian"]; P["P1"] = dict(n_reproduce=int(it.m_reproduces.sum()), all_D1_pos=bool((it.D1 > 0).all()), all_D4_neg=bool((it.D4 < 0).all()), pass_=bool(it.m_reproduces.sum() == 0 and (it.D1 > 0).all() and (it.D4 < 0).all()))
gen = B[B.group.isin(["C0 engine", "self-citation"])]; P["P2"] = dict(max_match=int(gen.m_n_match.max()), best=gen.m_n_match.idxmax(), pass_=bool(gen.m_n_match.max() >= 4))
nb = B[B.group == "Naibbe(it)"]; lo2, lo3 = out["bifolium"]["ms_range"]["D2"][0] - .1, out["bifolium"]["ms_range"]["D3"][0] - .015
P["P3"] = dict(D1=nb.D1.round(3).tolist(), D2=nb.D2.round(3).tolist(), D3=nb.D3.round(3).tolist(), reproduces=int(nb.m_reproduces.sum()),
               pass_=bool((nb.D1 <= .1).all() and (nb.D2 < lo2).all() and (nb.D3 < lo3).all() and nb.m_reproduces.sum() == 0))
sy = B[B.group == "syllabic(it)"]; P["P4"] = dict(D1=sy.D1.round(3).tolist(), pass_=bool((sy.D1 > .3).all() and (~sy.m_D1.astype(bool)).all()))
ab = B[B.group.isin(["no-vowel(it)", "suspension(it)"])]; P["P5"] = dict(D1=ab.D1.round(3).to_dict(), pass_=bool((ab.D1 > .3).all() and (~ab.m_D1.astype(bool)).all()))
nm = B[B.group != "MS"].sort_values("m_distance"); P["P6"] = dict(best=nm.index[0], best_group=nm.group.iloc[0], pass_=nm.group.iloc[0] in ("C0 engine", "self-citation"))
out["predictions"] = P
json.dump(out, open(R / "summary.json", "w"), indent=1, default=float)
cols = ["cell", "D1", "D2", "D3", "lam5_lo", "lam5_hi", "D4", "D5", "m_n_match", "m_distance", "bits_G", "bits_PCLM", "bits_KN1", "bits_KN3", "bits_COPY1", "bits_COPY3", "naibbe_eps", "winner"]
print(B.reset_index()[cols].round(3).to_string()); print(json.dumps({k: v for k, v in out.items()}, indent=1, default=float)[:6000])
# figure: D1 vs D2 and D4
fig, ax = plt.subplots(1, 2, figsize=(13, 5)); cm = dict(zip(sorted(B.group.unique()), plt.cm.tab10.colors))
for g, s in B.groupby("group"):
    ax[0].scatter(s.D1, s.D2, label=g, color=cm[g], s=40); ax[1].scatter(s.D4, s.D5, label=g, color=cm[g], s=40)
r = out["bifolium"]["ms_range"]
for a, (kx, ky) in zip(ax, [("D1", "D2"), ("D4", "D5")]):
    a.add_patch(plt.Rectangle((r[kx][0] - L.DELTA[kx], r[ky][0] - L.DELTA[ky]), r[kx][1] - r[kx][0] + 2 * L.DELTA[kx], r[ky][1] - r[ky][0] + 2 * L.DELTA[ky], fill=False, ls="--"))
    a.set_xlabel({"D1": "D1 n-gram gain (bits/word)", "D4": "D4 char-model dominance (bits/word)"}[kx]); a.set_ylabel({"D2": "D2 cache gain (bits/word)", "D5": "D5 char-model bits/glyph"}[ky])
ax[0].legend(fontsize=7); fig.suptitle("h20: likelihood fingerprint (dashed box = MS 408 range ± δ), bifolium folds"); fig.tight_layout(); fig.savefig(HERE / "figures" / "fingerprint.png", dpi=130)
