import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
from scipy import stats
import h15_lib as L
from h15_lib import L13, L14, HERE

rng = np.random.default_rng(15); R = HERE / "results"
d = L14.table(); q = pd.read_csv(L.ROOT / "data" / "quires.csv", dtype=str).set_index("page")
d["bif"] = d.folio.map(q.bifolium_id).fillna("?")
BB = d[d.HL.isin(["2B", "3B"])]; A1 = d[d.HL == "1A"]
out = {"A": {}}; rows = []; forest = {}
for name, ws in [("combined", L.WORDS)] + [(w, [w]) for w in L.WORDS]:
    r = {}
    for unit in ["quire", "bif"]:
        t = L.unit_table(BB, ws, unit); t.to_csv(R / f"units_{unit}_{name}.csv", index=False)
        dl = L.dersimonian_laird(t.lr.values, t["var"].values); npos, nu, sp = L.sign_test(t)
        loo = []
        for u in t.unit:
            tt = t[t.unit != u]; loo.append((u, L.dersimonian_laird(tt.lr.values, tt["var"].values)))
        mn = min(loo, key=lambda x: x[1]["ratio"])
        r[unit] = dict(**dl, n_pos=npos, n_units=nu, share_pos=npos / nu, sign_p=sp, loo_min_ratio=mn[1]["ratio"], loo_min_lo=mn[1]["lo"], loo_min_unit=str(mn[0]),
                       loo_all_exclude_1=all(x[1]["lo"] > 1 for x in loo))
        if unit == "quire": forest[name] = t
    o, e, v = L.expected(A1, ws); lr1 = np.log((o + .5) / (e + .5)); v1 = 1 / (o + .5) + 1 / (e + .5)
    pw, e1 = L.power(A1, ws, r["quire"]["ratio"], rng=rng)
    z = (r["quire"]["mu"] - lr1) / np.sqrt(r["quire"]["se"] ** 2 + v1)
    r["1A"] = dict(obs=o, exp=e, ratio=(o + .5) / (e + .5), power_at_BB_ratio=pw, diff_z=float(z), diff_p=float(stats.norm.sf(z)))
    out["A"][name] = r
    rows.append(dict(word=name, **{f"Q_{k}": v for k, v in r["quire"].items()}, **{f"B_{k}": v for k, v in r["bif"].items()}, **{f"1A_{k}": v for k, v in r["1A"].items()}))
pd.DataFrame(rows).to_csv(R / "meta_summary.csv", index=False)
c = out["A"]["combined"]
out["A1"] = dict(pass_=c["quire"]["ratio"] > 1.5 and c["quire"]["lo"] > 1 and c["quire"]["share_pos"] >= .7)
out["A2"] = dict(pass_=c["quire"]["loo_all_exclude_1"])
out["A3"] = dict(I2=c["quire"]["I2"], pass_=c["quire"]["I2"] < .75)
npw = sum(out["A"][w]["1A"]["power_at_BB_ratio"] >= .8 for w in L.WORDS)
out["A4"] = dict(power_combined=c["1A"]["power_at_BB_ratio"], n_words_power80=int(npw), diff_z=c["1A"]["diff_z"], pass_=c["1A"]["power_at_BB_ratio"] >= .8 and npw >= 4 and c["1A"]["diff_z"] > 3)
t = forest["combined"]; fig, ax = plt.subplots(figsize=(6, 5)); y = np.arange(len(t))
ax.errorbar(np.exp(t.lr), y, xerr=[np.exp(t.lr) - np.exp(t.lr - 1.96 * np.sqrt(t["var"])), np.exp(t.lr + 1.96 * np.sqrt(t["var"])) - np.exp(t.lr)], fmt="o")
ax.set_yticks(y); ax.set_yticklabels([f"Q{u}" for u in t.unit]); ax.set_xscale("log"); ax.axvline(1, c="k", lw=.5); ax.axvline(c["quire"]["ratio"], c="r", ls="--")
ax.set_title("h15: 2B/3B line-initial ratio (7 words) per quire"); fig.tight_layout(); fig.savefig(HERE / "figures" / "forest_quire.png", dpi=130)

# B
d13 = L13.token_table(); top = L13.top_words(d13); words, ranks, sims = L14.procrustes(d13, top); wi = {w: i for i, w in enumerate(words)}
rp = [(x, y, r) for a, b, r in L13.rule_pairs(top) for x, y in ((a, b), (b, a)) if x in wi and y in wi]
partners = {}
for x, y, _ in rp: partners.setdefault(x, set()).add(y)
ed = {(a, b): L13.unit_edit(a, b) for a in words for b in words}
B = []
for x, y, r in rp:
    i, j = wi[x], wi[y]; s = sims[i]; on = L.onset(x)
    c1 = [wi[z] for z in words if z != x and L.onset(z) == on]
    c2 = [wi[z] for z in words if z != x and ed[(x, z)] == ed[(x, y)] and (z == y or z not in partners[x])]
    B.append(dict(x_2B=x, y_1A=y, rule=r, onset=on, ed=ed[(x, y)], n_stem=len(c1) - 1, n_ed=len(c2) - 1,
                  pct_all=L.pct(s, j, [k for k in range(len(words)) if k != i]), pct_stem=L.pct(s, j, c1), pct_ed=L.pct(s, j, c2)))
B = pd.DataFrame(B); B.to_csv(R / "procrustes_rule_pairs_controlled.csv", index=False)
cal = []
for x in words:
    on = L.onset(x)
    if on is None: continue
    c1 = [wi[z] for z in words if z != x and L.onset(z) == on]
    for z in words:
        if z != x and L.onset(z) == on and z not in partners.get(x, set()):
            cal.append(dict(x=x, z=z, onset=on, pct_stem=L.pct(sims[wi[x]], wi[z], c1)))
cal = pd.DataFrame(cal); cal.to_csv(R / "procrustes_stem_calibration.csv", index=False)
def flip(v):
    v = np.asarray(v)[~np.isnan(v)] - .5; f = [np.mean(v * rng.choice([-1, 1], len(v))) for _ in range(10000)]
    return float((1 + sum(x >= v.mean() for x in f)) / 10001), len(v)
pb = {}
for col in ["pct_all", "pct_stem", "pct_ed"]:
    p, n = flip(B[col]); pb[col] = dict(median=float(B[col].median()), mean=float(B[col].mean()), n=n, signflip_p=p)
mw = stats.mannwhitneyu(B.pct_stem.dropna(), cal.pct_stem.dropna(), alternative="greater")
out["B"] = dict(n_pairs=len(B), **pb, calibration_median=float(cal.pct_stem.median()), calibration_mean=float(cal.pct_stem.mean()), calibration_n=len(cal), mw_p=float(mw.pvalue))
out["B1"] = dict(pass_=pb["pct_stem"]["median"] > .6 and pb["pct_stem"]["signflip_p"] < .05)
out["B2"] = dict(pass_=pb["pct_ed"]["median"] > .6 and pb["pct_ed"]["signflip_p"] < .05)
out["B3"] = dict(pass_=out["B"]["mw_p"] < .05)
json.dump(out, open(R / "summary.json", "w"), indent=1, default=float)
print(json.dumps({k: v for k, v in out.items() if k != "A"}, indent=1, default=float))
print(pd.DataFrame(rows)[["word", "Q_ratio", "Q_lo", "Q_hi", "Q_n_pos", "Q_n_units", "Q_I2", "Q_Q_p", "Q_loo_min_ratio", "Q_loo_min_lo", "B_ratio", "B_lo", "B_n_pos", "B_n_units", "B_I2", "B_loo_min_lo", "1A_obs", "1A_exp", "1A_ratio", "1A_power_at_BB_ratio", "1A_diff_z"]].round(3).to_string())
print(B.round(2).to_string())
