import json

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
import h24_lib as L
from h24_lib import HERE, ROOT, L20
R = HERE / "results"; R20 = ROOT / "hypotheses" / "h20_generators_vs_italian" / "results"
K = list(L20.DELTA); HANDS = ["1A", "2B", "3B"]; J = lambda x: x.item() if hasattr(x, "item") else str(x)  # noqa: E731


def row(f, sch):
    m = json.load(open(f)); s = m["schemes"][sch]
    return dict(cell=f.stem[5:], fit=m.get("fit") or {}, **L20.dstats(s["bits"], s["glyphs_per_word"], m["crossfit_W5"]["lam"]))


out = {}
for sch in ["bifolium", "quire"]:
    ms = {h: row(R20 / f"cell_MS_{h}.json", sch) for h in HANDS}
    T = pd.DataFrame([row(f, sch) for f in sorted(R.glob("cell_*.json"))] + [dict(v, cell=f"MS_{h}") for h, v in ms.items()])
    T = pd.concat([T, pd.DataFrame([L20.match(r, list(ms.values())) for r in T[K].to_dict("records")]).add_prefix("m_")], axis=1)
    for k in ["part", "src", "cipher", "variant", "c", "seed", "signal_share", "n_tokens"]: T[k] = [f.get(k, np.nan) for f in T.fit]
    T.drop(columns="fit").to_csv(R / f"fingerprints_{sch}.csv", index=False); out[sch] = T
T = out["bifolium"]; P = {}


def agg(df, by):
    rows = []
    for k, g in df.groupby(by):
        m, lo, hi = L.tci(g.m_distance); rows.append(dict(zip(by, k if isinstance(k, tuple) else (k,)), n=len(g), rate5=float(g.m_reproduces.mean()), rate4=float((g.m_n_match >= 4).mean()),
                                                         dist_mean=m, dist_lo=lo, dist_hi=hi, D4=float(g.D4.mean()), D5=float(g.D5.mean()), D3=float(g.D3.mean()), signal=float(g.signal_share.mean())))
    return pd.DataFrame(rows)


p1 = T[T.part == 1]; A1 = agg(p1, ["variant", "c", "src"]); A1v = agg(p1, ["variant", "c"]); A1.to_csv(R / "part1_by_source.csv", index=False); A1v.to_csv(R / "part1_by_rule.csv", index=False)
sw = p1[p1.variant == "swap"]
P["S1"] = dict(rate5=float(sw.m_reproduces.mean()), n=len(sw), dist=L.tci(sw.m_distance), by_rule=A1v.round(3).to_dict("records"), pass_=bool(sw.m_reproduces.mean() >= .4 and sw.m_distance.mean() <= 4))
p2 = T[(T.part == 2) & (T.src == "it_boccaccio")]; A2 = agg(p2, ["cipher", "variant", "c"]).sort_values("dist_mean"); A2.to_csv(R / "part2_boccaccio.csv", index=False)
nc = p2[p2.c == 0]
P["S2"] = dict(max_n_nocopy=int(nc.m_n_match.max()), pass_=bool(nc.m_n_match.max() < 4))
cp = A2[A2.c > 0]; bestrow = cp.iloc[0]; best = [bestrow.cipher, bestrow.variant, float(bestrow.c)]; json.dump(best, open(R / "neutral_best.json", "w"))
tr = T[(T.part == 2) & (T.src != "it_boccaccio") & (T.cipher == best[0]) & (T.variant == best[1]) & (T.c == best[2])]
trs = agg(tr, ["src"]) if len(tr) else pd.DataFrame()
any5 = p2[(p2.c > 0)].groupby(["cipher", "variant", "c"]).m_reproduces.sum()
P["S3"] = dict(best=best, best_dist=[float(bestrow.dist_mean), float(bestrow.dist_lo), float(bestrow.dist_hi)], best_rate5=float(bestrow.rate5), best_rate4=float(bestrow.rate4),
               settings_with_5of5=[list(k) for k, v in any5.items() if v > 0],
               transfer=trs.round(3).to_dict("records") if len(trs) else "phase2 pending",
               survives=bool(len(trs) and bestrow.dist_mean <= 6 and (trs.rate4 > .5).sum() >= 2), any5=bool((any5 > 0).any()))
P["S3"]["pass_"] = bool(P["S3"]["any5"])
fam = A2.assign(fam=A2.cipher.str[:4]).groupby("fam").dist_mean.min()
P["S4"] = dict(min_dist_by_family=fam.round(2).to_dict(), pass_=bool(fam.get("verb", 1e9) < fam.get("homo", 1e9)))
H = T[T.part == 3].set_index("cell"); b = lambda k: float(H.D5[k])  # noqa: E731
herb1a = np.mean([b("H_1A_herbS0"), b("H_1A_herbS1")])
P["S5"] = dict(D5=H.D5.round(3).to_dict(), D1=H.D1.round(3).to_dict(), n_tokens=H.n_tokens.to_dict(), herb_2B_minus_1A=float(b("H_2B_herb") - herb1a),
               section_effect=bool(abs(b("H_2B_herb") - herb1a) <= .05 and b("H_2B_bio") == H.D5.min()),
               hand_effect=bool(b("H_2B_herb") < herb1a - .05 and b("H_2B_nonbio") < np.mean([b("H_1A_herb0")]) - .05))
json.dump(dict(predictions=P), open(R / "summary.json", "w"), indent=1, default=J)
pd.set_option("display.width", 250)
print(A1v.round(3).to_string()); print(A1.round(3).to_string()); print(A2.round(3).to_string()); print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "by_rule"} for k, v in P.items()}, indent=1, default=J))
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
for (v, c), g in p1.groupby(["variant", "c"]): ax[0].scatter(g.D4, g.D3, label=f"Naibbe {v} c={c}", alpha=.6)
for (ci), g in p2[p2.c > 0].groupby("cipher"): ax[0].scatter(g.D4, g.D3, marker="x", label=f"{ci} +copy")
ms = T[T.cell.str.startswith("MS_")]; ax[0].scatter(ms.D4, ms.D3, c="k", marker="*", s=180, label="MS hands")
ax[0].axvspan(-.07, .18, color="g", alpha=.1); ax[0].set_xlabel("D4"); ax[0].set_ylabel("D3 = λ5"); ax[0].legend(fontsize=7); ax[0].set_xlim(-2.5, .4)
hh = T[T.part == 3].sort_values("D5"); ax[1].barh(hh.cell, hh.D5); ax[1].set_xlim(1.6, 2.1); ax[1].set_xlabel("D5 bits/glyph"); ax[1].set_title("hand vs section")
fig.tight_layout(); fig.savefig(HERE / "figures" / "robustness.png", dpi=130)
