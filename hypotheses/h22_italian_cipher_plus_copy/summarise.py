import json

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
import h22_lib as L
from h22_lib import HERE, ROOT, L20
R = HERE / "results"; R20 = ROOT / "hypotheses" / "h20_generators_vs_italian" / "results"; R21 = ROOT / "hypotheses" / "h21_italian_order_breaking_and_cross_hand" / "results"
K = list(L20.DELTA); HANDS = ["1A", "2B", "3B"]
J = lambda x: x.item() if hasattr(x, "item") else str(x)  # noqa: E731


def row(f, sch):
    m = json.load(open(f)); s = m["schemes"][sch]
    return dict(cell=m["cell"], fit=m.get("fit"), **L20.dstats(s["bits"], s["glyphs_per_word"], m["crossfit_W5"]["lam"]))


def ms_rows(sch): return {h: row(R20 / f"cell_MS_{h}.json", sch) for h in HANDS}


def add_match(T, ms):
    mm = pd.DataFrame([L20.match(r, list(ms.values())) for r in T[K].to_dict("records")], index=T.index); return pd.concat([T, mm.add_prefix("m_")], axis=1)


out = {}
for sch in ["bifolium", "quire"]:
    ms = ms_rows(sch)
    A = pd.DataFrame([row(f, sch) for f in sorted(R.glob("cell_A_*.json"))]); A = add_match(A, ms)
    for k in ["src", "base", "c", "W", "nulls", "signal_share", "copy_share", "layers", "oracle_acc", "mi_frac"]: A[k] = [f.get(k, np.nan) for f in A.fit]
    Bf = [R / p.name for p in R.glob("cell_B_*.json")] + list(R21.glob("cell_B_C0_*.json"))
    B = [row(f, sch) | dict(cell=json.load(open(f))["cell"]) for f in Bf]
    B = pd.DataFrame(B); B["name"] = [p.stem[5:] for p in Bf]
    B = pd.concat([B, pd.DataFrame([row(R20 / f"cell_GEN_C0_{h}.json", sch) | dict(name=f"B_C0_{h}_s20", fit=dict(train=[h], seed=20)) for h in HANDS])], ignore_index=True)
    B["train"] = ["+".join(f["train"]) for f in B.fit]; B["seed"] = [int(f["seed"]) for f in B.fit]; B = add_match(B, ms)
    PM = pd.DataFrame([dict(name=r.name, train=r.train, seed=r.seed, target=h, saw=h in r.train.split("+"),
                            **{f"p_{k}": v for k, v in L.point_match({k: getattr(r, k) for k in K}, ms[h]).items()}) for r in B.itertuples() for h in HANDS])
    for nm, df in [("partA", A), ("partB", B), ("partB_point", PM)]: df.drop(columns=[c for c in ["fit"] if c in df]).to_csv(R / f"{nm}_{sch}.csv", index=False)
    out[sch] = dict(A=A, B=B, PM=PM, ms=ms)

A, B, PM = out["bifolium"]["A"], out["bifolium"]["B"], out["bifolium"]["PM"]
boc = A[A.src == "it_boccaccio"]; clean = boc[(boc.nulls == "clean") & (boc.c > 0)].sort_values("m_distance")
best = [[r.base, float(r.c), int(r.W)] for r in clean.head(2).itertuples()]; json.dump(best, open(R / "search_best.json", "w"))
P = {}
c0 = boc[(boc.c == 0)]
P["QA1"] = dict(c0=c0.set_index("cell")[["m_n_match", "m_distance"]].round(2).to_dict("index"), pass_=bool(~c0.m_reproduces.any()))
P["QA2"] = dict(best=clean.cell.iloc[0], best_n=int(clean.m_n_match.iloc[0]), max_n=int(clean.m_n_match.max()), n_ge4=int((clean.m_n_match >= 4).sum()), n_5=int((clean.m_n_match == 5).sum()),
               five=clean[clean.m_n_match == 5].cell.tolist(), pass_=bool(clean.m_n_match.max() >= 4))
tr = A[(A.src != "it_boccaccio")]
t1 = tr[(tr.base == best[0][0]) & (tr.c == best[0][1]) & (tr.W == best[0][2])]
P["QA3"] = dict(transfer={r.cell: [int(r.m_n_match), round(float(r.m_distance), 2)] for r in tr.itertuples()}, pass_=bool((t1.m_n_match >= 4).sum() >= 2) if len(t1) else None)
P["QA4"] = dict(best_clean_dist=float(clean.m_distance.iloc[0]), c0_cross_range=[2.16, 5.95], pass_=bool(clean.m_distance.iloc[0] <= 6.0))
lk = boc[boc.nulls == "leaky"].set_index(["base", "c", "W"]).m_distance; cl = boc[(boc.nulls == "clean")].set_index(["base", "c", "W"]).m_distance
d = (cl.reindex(lk.index) - lk).dropna()
P["QA5"] = dict(mean_clean_minus_leaky=float(d.mean()), mean_abs=float(d.abs().mean()), pass_=bool(d.abs().mean() < 2))
sy = clean[clean.base == "syllNull"]
P["QA6"] = dict(best_syll=sy.cell.iloc[0], oracle_acc=float(sy.oracle_acc.iloc[0]), mi_frac=float(sy.mi_frac.iloc[0]), signal_share=float(sy.signal_share.iloc[0]), pass_=bool(sy.oracle_acc.iloc[0] >= .4))
blind = PM[~PM.saw]
r2b = blind[blind.target == "2B"]; r1a = blind[blind.target == "1A"]; r3b = blind[blind.target == "3B"]
own = PM[PM.saw & (PM.train.str.len() == 2)]
P["QB1"] = dict(blind_ge4_rate={h: float((g.p_n_match >= 4).mean()) for h, g in blind.groupby("target")}, n_blind={h: int(len(g)) for h, g in blind.groupby("target")},
               blind_mean_n={h: float(g.p_n_match.mean()) for h, g in blind.groupby("target")}, own_mean_n={h: float(g.p_n_match.mean()) for h, g in own.groupby("target")},
               blind_mean_dist={h: float(g.p_distance.mean()) for h, g in blind.groupby("target")},
               failing_stats_2B={k: float(1 - r2b[f"p_{k}"].mean()) for k in K},
               pass_=bool((r2b.p_n_match >= 4).mean() <= .2 and (r1a.p_n_match >= 4).mean() >= .6))
P["QB_range"] = dict(n=len(B), n5=int(B.m_reproduces.sum()), n_ge4=int((B.m_n_match >= 4).sum()), dist=[float(B.m_distance.min()), float(B.m_distance.max())])
summ = dict(predictions=P, search_best=best,
            A=A.sort_values("m_distance")[["cell", "m_n_match", "m_distance", "layers", "signal_share", "copy_share", "oracle_acc", "mi_frac"] + K].round(3).to_dict("records"),
            quire_A_5=out["quire"]["A"][out["quire"]["A"].m_reproduces].cell.tolist())
json.dump(summ, open(R / "summary.json", "w"), indent=1, default=J)
pd.set_option("display.width", 250)
print(A.sort_values("m_distance")[["cell", "m_n_match", "m_distance", "signal_share", "oracle_acc", "mi_frac"] + K].round(3).to_string())
print(PM.pivot_table(index="train", columns="target", values="p_n_match", aggfunc=lambda x: "/".join(str(int(v)) for v in x)))
print(json.dumps(P, indent=1, default=J))
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
for b, g in clean.groupby("base"): ax[0].plot(g.sort_values("c").groupby("c").m_distance.min(), "o-", label=b)
ax[0].axhspan(2.16, 5.95, color="g", alpha=.15, label="C0 cross-hand (h21)"); ax[0].set_yscale("log"); ax[0].set_xlabel("copy prob c (best W)"); ax[0].set_ylabel("distance to MS"); ax[0].legend()
for b, g in clean.groupby("base"): ax[1].scatter(g.D3, g.D4, label=b)
ms = out["bifolium"]["ms"]; ax[1].scatter([m["D3"] for m in ms.values()], [m["D4"] for m in ms.values()], c="k", marker="*", s=150, label="MS hands")
ax[1].set_xlabel("D3 = λ5"); ax[1].set_ylabel("D4"); ax[1].legend(); fig.suptitle("h22 Boccaccio, clean nulls, bifolium folds"); fig.tight_layout(); fig.savefig(HERE / "figures" / "copy_layer.png", dpi=130)
