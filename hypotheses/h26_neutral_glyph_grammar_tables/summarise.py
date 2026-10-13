import json

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from h26_lib import HERE, ROOT, L25
L24 = L25.L24; L20 = L24.L20
R = HERE / "results"; R20 = ROOT / "hypotheses" / "h20_generators_vs_italian" / "results"
K = list(L20.DELTA); HANDS = ["1A", "2B", "3B"]; J = lambda x: x.item() if hasattr(x, "item") else str(x)  # noqa: E731
FK = ["src", "grammar", "copy", "seed", "render", "decodable", "signal_share", "H1", "rigidity", "mean_len"]


def row(f, sch):
    m = json.load(open(f)); s = m["schemes"][sch]
    return dict(cell=f.stem[5:], fit=m.get("fit") or {}, **L20.dstats(s["bits"], s["glyphs_per_word"], m["crossfit_W5"]["lam"]))


out = {}
for sch in ["bifolium", "quire"]:
    ms = {h: row(R20 / f"cell_MS_{h}.json", sch) for h in HANDS}
    T = pd.DataFrame([row(f, sch) for f in sorted(R.glob("cell_*.json"))])
    T = pd.concat([T, pd.DataFrame([L20.match(r, list(ms.values())) for r in T[K].to_dict("records")]).add_prefix("m_")], axis=1)
    for k in FK: T[k] = [f.get(k) for f in T.fit]
    T.drop(columns="fit").to_csv(R / f"fingerprints_{sch}.csv", index=False); out[sch] = T


def agg(df, by):
    rows = []
    for k, g in df.groupby(by):
        m, lo, hi = L24.tci(g.m_distance)
        rows.append(dict(zip(by, k), n=len(g), rate5=float(g.m_reproduces.mean()), rate4=float((g.m_n_match >= 4).mean()), nmax=int(g.m_n_match.max()), dist_mean=m, dist_lo=lo, dist_hi=hi,
                         dist_min=float(g.m_distance.min()), **{x: float(g[x].mean()) for x in K + ["decodable", "H1", "rigidity", "mean_len"]}))
    return pd.DataFrame(rows)


T = out["bifolium"]; G = agg(T, ["src", "grammar", "copy", "render"]); G.to_csv(R / "groups_bifolium.csv", index=False); agg(out["quire"], ["src", "grammar", "copy", "render"]).to_csv(R / "groups_quire.csv", index=False)
B = G[(G.src == "it_boccaccio") & (G.render == "eva")]; P = {}
msb = B[B.grammar == "ms"].sort_values("dist_mean").iloc[0]
P["G1"] = dict(ms=B[B.grammar == "ms"][["copy", "rate4", "rate5", "dist_mean", "dist_lo", "dist_hi"]].round(3).to_dict("records"), pass_=bool(msb.rate4 >= .6 and msb.dist_mean <= 10))
neu = B[B.grammar.isin(["rs", "lat"])].sort_values("dist_mean"); nb = neu.iloc[0]
P["G2"] = dict(best_neutral=f"{nb.grammar}/{nb['copy']}", rate4=float(nb.rate4), dist=float(nb.dist_mean), ms_best_dist=float(msb.dist_mean),
               any_orderly_suffices=bool(nb.rate4 >= .6 and nb.dist_mean <= 2 * msb.dist_mean))
allg = B[~B.grammar.isin(["ms", "naibbe"])]
P["G3"] = dict(dist={f"{r.grammar}/{r['copy']}": round(float(r.dist_mean), 2) for _, r in allg.iterrows()}, pass_=bool(((allg["copy"] == "none") & (allg.dist_mean < 75.6) | (allg["copy"] == "swap") & (allg.dist_mean < 67.5)).all()))
bc = T[(T.src == "it_boccaccio") & (T.render == "eva") & (T.grammar != "naibbe")]
rho = {p: float(spearmanr(bc[p], bc.m_distance).correlation) for p in ["H1", "rigidity", "mean_len"]}
P["G4"] = dict(spearman=rho, top=max(rho, key=lambda k: abs(rho[k])), pass_=bool(max(rho, key=lambda k: abs(rho[k])) == "rigidity"))
P["G4"]["spearman_neutral_only"] = {p: float(spearmanr(bc[bc.grammar != "ms"][p], bc[bc.grammar != "ms"].m_distance).correlation) for p in ["H1", "rigidity", "mean_len"]}
P["G5"] = dict(decodable=float(nb.decodable), decodable_best_any=float(B[~B.grammar.isin(["ms", "naibbe"])].sort_values("dist_mean").iloc[0].decodable), pass_=bool(nb.decodable >= .8))
nbest = B[~B.grammar.isin(["ms", "naibbe"])].sort_values("dist_mean").iloc[0]
P["best_neutral_any"] = dict(setting=f"{nbest.grammar}/{nbest['copy']}", dist=float(nbest.dist_mean), rate4=float(nbest.rate4), decodable=float(nbest.decodable))
if not (R / "transfer_settings.json").exists(): json.dump([[nbest.grammar, nbest["copy"]], ["ms", msb["copy"]]], open(R / "transfer_settings.json", "w"))
P["naibbe_anchor"] = B[B.grammar == "naibbe"][["copy", "n", "rate4", "rate5", "dist_mean", "dist_lo", "dist_hi", "D2", "D3", "D4", "D5"]].round(3).to_dict("records")
tr = G[(G.src != "it_boccaccio")]
P["transfer"] = tr[["src", "grammar", "copy", "n", "rate4", "rate5", "dist_mean", "dist_lo", "dist_hi"]].round(3).to_dict("records")
P["char_vs_eva_rs"] = G[(G.grammar == "rs") & (G["copy"] == "none") & (G.src == "it_boccaccio")][["render", "dist_mean", "D4", "D5"]].round(3).to_dict("records")
P["n5_bif"] = int(T.m_reproduces.sum()); P["n5_quire"] = int(out["quire"].m_reproduces.sum()); P["five_bif"] = T[T.m_reproduces].cell.tolist()
json.dump(dict(predictions=P), open(R / "summary.json", "w"), indent=1, default=J)
pd.set_option("display.width", 250)
print(G.round(3).to_string()); print(json.dumps(P, indent=1, default=J))
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
for gname, g in bc.groupby("grammar"): ax[0].scatter(g.rigidity, g.m_distance, label=gname)
ax[0].set_yscale("log"); ax[0].set_xlabel("positional rigidity"); ax[0].set_ylabel("distance to MS"); ax[0].axhline(3.61, c="r", ls="--", lw=1); ax[0].legend(fontsize=8)
for gname, g in bc.groupby("grammar"): ax[1].scatter(g.D4, g.D5, label=gname)
ax[1].scatter([m["D4"] for m in ms.values()], [m["D5"] for m in ms.values()], c="k", marker="*", s=160); ax[1].set_xlabel("D4"); ax[1].set_ylabel("D5"); ax[1].legend(fontsize=8)
fig.tight_layout(); fig.savefig(HERE / "figures" / "grammar_tables.png", dpi=130)
