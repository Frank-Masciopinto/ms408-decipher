import json

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
from h25_lib import HERE, ROOT, L24
L20 = L24.L20
R = HERE / "results"; R20 = ROOT / "hypotheses" / "h20_generators_vs_italian" / "results"
K = list(L20.DELTA); HANDS = ["1A", "2B", "3B"]; J = lambda x: x.item() if hasattr(x, "item") else str(x)  # noqa: E731


def row(f, sch):
    m = json.load(open(f)); s = m["schemes"][sch]
    return dict(cell=f.stem[5:], fit=m.get("fit") or {}, **L20.dstats(s["bits"], s["glyphs_per_word"], m["crossfit_W5"]["lam"]))


out = {}
for sch in ["bifolium", "quire"]:
    ms = {h: row(R20 / f"cell_MS_{h}.json", sch) for h in HANDS}
    T = pd.DataFrame([row(f, sch) for f in sorted(R.glob("cell_*.json"))])
    T = pd.concat([T, pd.DataFrame([L20.match(r, list(ms.values())) for r in T[K].to_dict("records")]).add_prefix("m_")], axis=1)
    for k in ["src", "variant", "copy", "seed", "render", "signal_share", "decodable"]: T[k] = [f.get(k) for f in T.fit]
    T.drop(columns="fit").to_csv(R / f"fingerprints_{sch}.csv", index=False); out[sch] = T
MSMEAN = {k: np.mean([r[k] for r in ms.values()]) for k in K}


def agg(df, by):
    rows = []
    for k, g in df.groupby(by):
        m, lo, hi = L24.tci(g.m_distance)
        rows.append(dict(zip(by, k if isinstance(k, tuple) else (k,)), n=len(g), rate5=float(g.m_reproduces.mean()), rate4=float((g.m_n_match >= 4).mean()), nmax=int(g.m_n_match.max()),
                         dist_mean=m, dist_lo=lo, dist_hi=hi, dist_min=float(g.m_distance.min()), **{k2: float(g[k2].mean()) for k2 in K}, decodable=float(g.decodable.mean()), signal=float(g.signal_share.mean())))
    return pd.DataFrame(rows)


T = out["bifolium"]; Q = out["quire"]
G = agg(T, ["src", "variant", "copy", "render"]); G.to_csv(R / "groups_bifolium.csv", index=False); agg(Q, ["src", "variant", "copy", "render"]).to_csv(R / "groups_quire.csv", index=False)
boc = G[G.src == "it_boccaccio"]; g = lambda v, c, r, df=boc: df[(df.variant == v) & (df["copy"] == c) & (df.render == r)].iloc[0]  # noqa: E731
P = {}
bs = [g("base", "swap", r) for r in ("char", "eva")]
P["T1"] = dict(base_swap={r: dict(rate4=float(x.rate4), rate5=float(x.rate5), dist=[float(x.dist_mean), float(x.dist_lo), float(x.dist_hi)], dist_min=float(x.dist_min)) for r, x in zip(("char", "eva"), bs)},
               any5_NH_copy=int(T[(T["copy"] != "none")].m_reproduces.sum()), five_cells=T[(T["copy"] != "none") & T.m_reproduces].cell.tolist())
P["T1"]["T1_holds"] = bool(any(x.rate4 >= .5 and x.dist_mean <= 10 for x in bs)); P["T1"]["design_enough"] = bool(P["T1"]["T1_holds"] and P["T1"]["any5_NH_copy"] >= 1)
nc = G[(G["copy"] == "none")]
P["T2"] = dict(nocopy=nc[["src", "variant", "render", "dist_mean", "nmax"]].round(2).to_dict("records"), pass_=bool(g("base", "none", "char").dist_mean < 89 or g("base", "none", "eva").dist_mean < 89))
e = T[(T.src == "it_boccaccio") & (T.variant == "base")].pivot_table(index=["copy", "seed"], columns="render", values="D5").dropna()
P["T3"] = dict(absdiff_D5=dict(char=float((e.char - MSMEAN["D5"]).abs().mean()), eva=float((e.eva - MSMEAN["D5"]).abs().mean())), D5=dict(char=float(e.char.mean()), eva=float(e.eva.mean())),
               pass_=bool((e.eva - MSMEAN["D5"]).abs().mean() < (e.char - MSMEAN["D5"]).abs().mean()))
sens = boc[(boc.render == "char") & (boc["copy"].isin(["none", "swap"]))].pivot_table(index="variant", columns="copy", values="dist_mean")
base_d = sens.loc["base"]; eff = (np.log(sens) - np.log(base_d)).abs().mean(axis=1).drop("base")
grp = {"A15": "alphabet", "A25": "alphabet", "short": "code length", "long": "code length", "T1": "tables", "T3": "tables", "uniform": "card weights", "p30": "p_unigram", "p70": "p_unigram"}
byp = eff.groupby(eff.index.map(grp)).max().sort_values(ascending=False)
P["T4"] = dict(dist=sens.round(2).to_dict("index"), log_effect=eff.round(3).to_dict(), by_parameter=byp.round(3).to_dict(), top=byp.index[0], pass_=bool(byp.index[0] in ("code length", "p_unigram")))
bestv = boc[(boc.render == "char") & (boc["copy"] == "swap")].sort_values("dist_mean").iloc[0].variant; json.dump(bestv, open(R / "best_variant.json", "w"))
bx = boc[(boc["copy"] != "none")].sort_values("dist_mean").iloc[0]
P["T5"] = dict(best=f"{bx.variant}/{bx["copy"]}/{bx.render}", decodable=float(bx.decodable), signal=float(bx.signal), pass_=bool(bx.decodable >= .8))
P["best_variant_for_eva_transfer"] = bestv
P["eva_transfer"] = G[(G.variant == bestv) & (G.render == "eva") & (G["copy"] == "swap")][["src", "n", "rate4", "rate5", "dist_mean", "dist_lo", "dist_hi"]].round(3).to_dict("records")
P["transfer_base_char"] = G[(G.variant == "base") & (G.render == "char")][["src", "copy", "rate4", "rate5", "dist_mean", "nmax"]].round(3).to_dict("records")
P["quire_any5"] = Q[Q.m_reproduces].cell.tolist()[:40]; P["quire_n5"] = int(Q.m_reproduces.sum())
json.dump(dict(predictions=P), open(R / "summary.json", "w"), indent=1, default=J)
pd.set_option("display.width", 250)
print(G.round(3).drop(columns=["signal"]).to_string()); print(json.dumps(P, indent=1, default=J))
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
sens.plot.barh(ax=ax[0], logx=True); ax[0].axvline(3.61, c="r", ls="--", label="Naibbe+swap (h24)"); ax[0].axvline(89, c="grey", ls=":", label="best h24 neutral"); ax[0].set_xlabel("mean distance (Boccaccio, char seg)"); ax[0].legend(fontsize=8)
for r, gg in T[(T.variant == "base") & (T.src == "it_boccaccio")].groupby("render"): ax[1].scatter(gg.D4, gg.D5, label=f"NH base ({r})")
ax[1].scatter([m["D4"] for m in ms.values()], [m["D5"] for m in ms.values()], c="k", marker="*", s=160, label="MS hands"); ax[1].set_xlabel("D4"); ax[1].set_ylabel("D5"); ax[1].legend()
fig.tight_layout(); fig.savefig(HERE / "figures" / "nh_sensitivity.png", dpi=130)
