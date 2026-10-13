import json
import sys

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
from h23_lib import HERE, ROOT, L20
sys.path.insert(0, str(ROOT / "hypotheses" / "h19_heldout_likelihood")); import run_h19  # noqa: E402,F401
import h14_lib as L14  # noqa: E402
R = HERE / "results"; R20 = ROOT / "hypotheses" / "h20_generators_vs_italian" / "results"
K = list(L20.DELTA); HANDS = ["1A", "2B", "3B"]; J = lambda x: x.item() if hasattr(x, "item") else str(x)  # noqa: E731


def row(f, sch):
    m = json.load(open(f)); s = m["schemes"][sch]
    return dict(cell=m["cell"] if not f.stem.startswith("cell_B") else f.stem[5:], fit=m.get("fit") or {}, **L20.dstats(s["bits"], s["glyphs_per_word"], m["crossfit_W5"]["lam"]))


out = {}
for sch in ["bifolium", "quire"]:
    ms = {h: row(R20 / f"cell_MS_{h}.json", sch) for h in HANDS}; msr = list(ms.values())
    T = pd.DataFrame([row(f, sch) for f in sorted(R.glob("cell_*.json"))] + [dict(v, cell=f"MS_{h}") for h, v in ms.items()])
    T = pd.concat([T, pd.DataFrame([L20.match(r, msr) for r in T[K].to_dict("records")]).add_prefix("m_")], axis=1)
    for k in ["src", "base", "variant", "c", "signal_share", "oracle_acc", "mi_frac", "n_tokens"]: T[k] = [f.get(k, np.nan) for f in T.fit]
    T.drop(columns="fit").to_csv(R / f"fingerprints_{sch}.csv", index=False); out[sch] = T
T = out["bifolium"]; A = T[T.cell.str.startswith("A_")]; B = T[~T.cell.str.startswith("A_")]
nb = A[(A.base == "naibbe") & (A.src == "it_boccaccio")]; nbc = nb[nb.c > 0].sort_values("m_distance")
best = [[r.variant, float(r.c)] for r in nbc.head(2).itertuples()]; json.dump(best, open(R / "search_best.json", "w"))
P = {}
ok = nbc[(nbc.D4 >= -0.07) & (nbc.D3 >= 0.022)]
P["RA1"] = dict(cells=ok.cell.tolist(), max_D4_with_lam=float(nbc[nbc.D3 >= .022].D4.max()) if (nbc.D3 >= .022).any() else None, pass_=bool(len(ok)))
P["RA2"] = dict(five=nbc[nbc.m_reproduces].cell.tolist(), best=nbc.cell.iloc[0], best_n=int(nbc.m_n_match.iloc[0]), best_dist=float(nbc.m_distance.iloc[0]), pass_=bool(nbc.m_reproduces.any()))
tr = A[(A.src != "it_boccaccio") & (A.base == "naibbe")]
t1 = tr[(tr.variant == best[0][0]) & (tr.c == best[0][1])]
P["RA3"] = dict(transfer={r.cell: [int(r.m_n_match), round(float(r.m_distance), 2)] for r in tr.itertuples()},
               pass_=(bool((t1.m_n_match >= 4).all() and len(t1) == 3 and (not P["RA2"]["pass_"] or (t1.m_n_match == 5).sum() >= 2)) if len(t1) else None))
P["RA4"] = dict(signal_share=float(nbc.signal_share.iloc[0]), pass_=bool(nbc.signal_share.iloc[0] >= .9))
pv = nb.pivot_table(index="c", columns="variant", values="D4")
P["RA5"] = dict(D4=pv.round(3).to_dict(), pass_=bool(((pv["unit"] > pv["ref"]) & (pv["swap"] > pv["ref"])).loc[[c for c in pv.index if c > 0]].all()))
sy = A[A.base == "syll"].sort_values("m_distance")
P["syll"] = sy[["cell", "m_n_match", "m_distance", "D4", "oracle_acc", "mi_frac"]].round(3).to_dict("records")
# Part B descriptives
d = L14.table(); d = d[d.HL.isin(HANDS)]; desc = {}
for h, g in d.groupby("HL"):
    w = g.w; vc = w.value_counts(); ini = g[g.is_init].w.str[0].value_counts(normalize=True)
    desc[h] = dict(n=int(len(w)), types=int(len(vc)), top50=float(vc.head(50).sum() / len(w)), edy=float(w.str.endswith("edy").mean()), qo=float(w.str.startswith("qo").mean()),
                   mean_len=float(w.str.len().mean()), sections=g.section.value_counts(normalize=True).round(3).to_dict(), init_top=ini.head(4).round(3).to_dict())
P["RB1"] = dict(D5={r.cell: round(float(r.D5), 3) for r in B.itertuples() if "sub" in r.cell or "bio" in r.cell},
               pass_=bool(max(B.set_index("cell").D5[["B_2B_bio", "B_2B_nonbio"]]) < min(B.set_index("cell").D5[["B_1A_sub", "B_3B_sub"]])))
b = B.set_index("cell")
P["RB2"] = dict(dD5=float(b.D5["B_2B_noedy"] - b.D5["MS_2B"]), dD1=float(b.D1["B_2B_noedy"] - b.D1["MS_2B"]), dD5_3B=float(b.D5["B_3B_noedy"] - b.D5["MS_3B"]),
               pass_=bool(b.D5["B_2B_noedy"] - b.D5["MS_2B"] >= .05 and b.D1["B_2B_noedy"] < b.D1["MS_2B"]))
summ = dict(predictions=P, search_best=best, partB_descriptives=desc, partB_fingerprints=B[["cell", "n_tokens"] + K].round(3).to_dict("records"),
            naibbe=nb.sort_values("m_distance")[["cell", "m_n_match", "m_distance", "signal_share"] + K].round(3).to_dict("records"),
            quire_A_5=out["quire"][out["quire"].cell.str.startswith("A_") & out["quire"].m_reproduces].cell.tolist())
json.dump(summ, open(R / "summary.json", "w"), indent=1, default=J)
pd.set_option("display.width", 250)
print(A.sort_values("m_distance")[["cell", "m_n_match", "m_distance", "signal_share"] + K].round(3).to_string()); print(B[["cell", "n_tokens"] + K].round(3).to_string())
print(json.dumps(P, indent=1, default=J)); print(json.dumps(desc, indent=1))
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
for v, g in nb[nb.c > 0].groupby("variant"): ax[0].plot(g.D3, g.D4, "o-", label=v)
for h, m in ((h, b.loc[f"MS_{h}"]) for h in HANDS): ax[0].scatter(m.D3, m.D4, marker="*", s=160, c="k")
ax[0].axhspan(-.07, .18, color="g", alpha=.12); ax[0].set_xlabel("D3 = λ5"); ax[0].set_ylabel("D4"); ax[0].legend(fontsize=8); ax[0].set_title("Naibbe-Boccaccio copy variants (c = .03/.05/.10)")
bb = B.sort_values("D5"); ax[1].barh(bb.cell, bb.D5); ax[1].set_xlabel("D5 bits/glyph"); ax[1].set_title("hand 2B diagnostics"); ax[1].set_xlim(1.6, 2.1)
fig.tight_layout(); fig.savefig(HERE / "figures" / "copy_variants.png", dpi=130)
