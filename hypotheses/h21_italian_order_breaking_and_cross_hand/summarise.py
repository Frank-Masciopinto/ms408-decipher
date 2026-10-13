import json
import sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
import h21_lib as L
from h21_lib import HERE, ROOT, L20
R = HERE / "results"; R20 = ROOT / "hypotheses" / "h20_generators_vs_italian" / "results"
K = list(L20.DELTA)


def row(f, sch="bifolium"):
    m = json.load(open(f)); s = m["schemes"][sch]
    return dict(cell=m["cell"], fit=m.get("fit"), **L20.dstats(s["bits"], s["glyphs_per_word"], m["crossfit_W5"]["lam"]))


def table(sch):
    ms = {c: row(R20 / f"cell_MS_{c}.json", sch) for c in ["1A", "2B", "3B"]}
    same = [row(R20 / f"cell_GEN_C0_{h}.json", sch) | dict(cell=f"B_C0_{h}_s20", fit=dict(train=[h], seed=20)) for h in ["1A", "2B", "3B"]]
    rows = [row(f, sch) for f in sorted(R.glob("cell_*.json"))] + same
    T = pd.DataFrame(rows); msr = list(ms.values())
    mm = pd.DataFrame([L20.match(r, msr) for r in T[K].to_dict("records")]); T = pd.concat([T, mm.add_prefix("m_")], axis=1)
    return T, ms


out = {}
for sch in ["bifolium", "quire"]:
    T, ms = table(sch); T["scheme"] = sch
    A = T[T.cell.str.startswith("A_")].copy()
    A["src"] = [f["src"] for f in A.fit]; A["base"] = [f["base"] for f in A.fit]; A["K"] = [f["K"] for f in A.fit]; A["shuf"] = [f["shuf"] for f in A.fit]; A["r"] = [f["r"] for f in A.fit]
    A["layers"] = [f["layers"] for f in A.fit]; A["null_share"] = [f["null_share"] for f in A.fit]
    B = T[T.cell.str.startswith("B_")].copy(); B["train"] = ["+".join(f["train"]) for f in B.fit]; B["seed"] = [f["seed"] for f in B.fit]
    pm = []
    for _, r in B.iterrows():
        for h, tgt in ms.items():
            p = L.point_match({k: r[k] for k in K}, tgt); pm.append(dict(cell=r.cell, train=r.train, seed=r.seed, target=h, own=h in r.train.split("+"), **{f"p_{k}": v for k, v in p.items()}))
    PM = pd.DataFrame(pm)
    A.drop(columns="fit").to_csv(R / f"partA_{sch}.csv", index=False); B.drop(columns="fit").to_csv(R / f"partB_{sch}.csv", index=False); PM.to_csv(R / f"partB_point_{sch}.csv", index=False)
    out[sch] = dict(A=A, B=B, PM=PM, ms=ms)

A, B, PM = out["bifolium"]["A"], out["bifolium"]["B"], out["bifolium"]["PM"]
grid = A[(A.src == "it_boccaccio") & (A.base == "syll") & ~((A.K == 1))]
grid = grid.sort_values("m_distance"); best = [[r.base, int(r.K), bool(r.shuf), float(r.r)] for r in grid.head(2).itertuples()]
json.dump(best, open(R / "search_best.json", "w"))
basecond = A[A.layers <= 2]; single = A[A.layers == 2]
off = PM[~PM.own & PM.train.str.len().eq(2)]; pooled = PM[PM.train.str.contains(r"\+") & ~PM.own]
P = {}
pl = A[(A.base.isin(["plain", "syll"])) & A.shuf & (A.K == 1) & (A.r == 0)]
P["PA1"] = dict(D1=pl.set_index("cell").D1.round(3).to_dict(), D4=pl.set_index("cell").D4.round(3).to_dict(), n_base_reproduce=int(basecond.m_reproduces.sum()),
               pass_=bool((pl.D1 <= .1).all() and (pl.D4 < -.5).all() and basecond.m_reproduces.sum() == 0))
P["PA2"] = dict(max_match_single=int(single.m_n_match.max()), best_single=single.sort_values("m_n_match", ascending=False).cell.iloc[0], pass_=bool(single.m_n_match.max() < 4))
tr = A[A.cell.isin([c for c in A.cell]) & (A.src != "it_boccaccio")]
trb = tr[[ [r.base, int(r.K), bool(r.shuf), float(r.r)] in best for r in tr.itertuples()]]
P["PA3"] = dict(grid_max_match=int(grid.m_n_match.max()), grid_best=grid.cell.iloc[0], grid_best_layers=int(grid.layers.iloc[0]), grid_best_null_share=float(grid.null_share.iloc[0]),
               five_of_five=grid[grid.m_n_match == 5].cell.tolist(), min_layers_5=int(grid[grid.m_n_match == 5].layers.min()) if (grid.m_n_match == 5).any() else None,
               transfer=trb.set_index("cell").m_n_match.to_dict() if len(trb) else "phase2 pending")
P["PA3"]["pass_"] = bool(grid.m_n_match.max() >= 4 and (P["PA3"]["min_layers_5"] is None or P["PA3"]["min_layers_5"] >= 3) and len(trb) and (trb.groupby("src").m_n_match.max() >= 4).sum() >= 2)
P["PB1"] = dict(off_diag={f"{a}->{b}_s{s}": int(v) for a, b, s, v in zip(off.train, off.target, off.seed, off.p_n_match)}, per_seed={int(s): int((g.p_n_match >= 4).sum()) for s, g in off.groupby("seed")}, n_ge4=int((off.p_n_match >= 4).sum()), n=len(off), pass_=bool((off.groupby("seed").p_n_match.apply(lambda x: (x >= 4).sum()) >= 4).all()))
P["PB2"] = dict(pooled={f"{a}->{b}": int(v) for a, b, v in zip(pooled.cell, pooled.target, pooled.p_n_match)}, pass_=bool((pooled.p_n_match >= 4).all()))
crossd = B[B.train.str.contains(r"\+")].m_distance.min(); bestA = A.m_distance.min()
P["PB3"] = dict(pooled_min_dist=float(crossd), pooled_max_dist=float(B[B.train.str.contains(r"\+")].m_distance.max()), single_offhand_max_dist=float(B[~B.train.str.contains(r"\+")].m_distance.max()), best_A_dist=float(bestA), pass_=bool(crossd < bestA))
summ = dict(predictions=P, search_best=best,
            A_top=A.sort_values("m_distance")[["cell", "m_n_match", "m_distance", "layers", "null_share"] + K].head(12).round(3).to_dict("records"),
            B_range=B[["cell", "train", "seed", "m_n_match", "m_distance"] + K].round(3).to_dict("records"),
            quire_A_reproduce=out["quire"]["A"][out["quire"]["A"].m_reproduces == True].cell.tolist(),
            quire_B_reproduce=out["quire"]["B"][out["quire"]["B"].m_reproduces == True].cell.tolist())
json.dump(summ, open(R / "summary.json", "w"), indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x))
pd.set_option("display.width", 250)
print(A.sort_values("m_distance")[["cell", "m_n_match", "m_distance", "layers", "null_share"] + K].round(3).to_string())
print(B[["cell", "m_n_match", "m_distance"] + K].round(3).to_string()); print(PM.pivot_table(index="cell", columns="target", values="p_n_match"))
print(json.dumps(P, indent=1, default=str))
fig, ax = plt.subplots(1, 2, figsize=(13, 5)); rr = {k: [min(v[k] for v in out["bifolium"]["ms"].values()), max(v[k] for v in out["bifolium"]["ms"].values())] for k in K}
for lab, s, c in [("A base", A[A.layers <= 2], "tab:blue"), ("A combos", A[A.layers > 2], "tab:orange"), ("B C0 cross/pooled", B, "tab:green")]:
    ax[0].scatter(s.D1, s.D2, label=lab, color=c, s=30); ax[1].scatter(s.D4, s.D5, color=c, s=30)
for a, (kx, ky) in zip(ax, [("D1", "D2"), ("D4", "D5")]):
    a.add_patch(plt.Rectangle((rr[kx][0] - L20.DELTA[kx], rr[ky][0] - L20.DELTA[ky]), rr[kx][1] - rr[kx][0] + 2 * L20.DELTA[kx], rr[ky][1] - rr[ky][0] + 2 * L20.DELTA[ky], fill=False, ls="--")); a.set_xlabel(kx); a.set_ylabel(ky)
ax[0].legend(); fig.suptitle("h21 fingerprint (dashed = MS range ± δ), bifolium folds"); fig.tight_layout(); fig.savefig(HERE / "figures" / "fingerprint.png", dpi=130)
