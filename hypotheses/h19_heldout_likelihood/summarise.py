import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
from scipy import stats
from h19_lib import HERE
R = HERE / "results"; rng = np.random.default_rng(19)
BASE = ["G", "SLOT", "KN1", "KN2", "KN3", "COPY1", "COPY3"]; NB = ["NAIBBE_la", "NAIBBE_it"]
rows, rank, out = [], [], {}
cells = sorted(p.stem[5:] for p in R.glob("cell_*.json"))
for c in cells:
    meta = json.load(open(R / f"cell_{c}.json")); out[c] = dict(kind=meta["kind"], n_tokens=meta["n_tokens"], crossfit_copy=meta.get("crossfit_copy"))
    for sch in ["bifolium", "quire"]:
        t = pd.read_csv(R / f"tokens_{c}_{sch}.csv.gz"); ms = [m for m in BASE + NB if m in t]
        gl = t.glyphs.mean()
        bits = {m: float(-t[m].mean()) for m in ms}
        for m in [x for x in t.columns if x.endswith("+ONSET")]: bits[m] = float(-t[m].mean())
        cand = [m for m in BASE + NB if m in t]
        order = sorted(cand, key=lambda m: bits[m]); win, run = order[0], order[1]
        pg = t.groupby("page").apply(lambda g: pd.Series(dict(d=(-g[win] + g[run]).sum(), n=len(g))))
        npos = int((pg.d < 0).sum()); sp = float(stats.binomtest(npos, len(pg), .5, alternative="greater").pvalue)
        bs = [(lambda s: s.d.sum() / s.n.sum())(pg.sample(len(pg), replace=True, random_state=int(rng.integers(1e9)))) for _ in range(1000)]
        ctx = min(bits[m] for m in ["KN2", "KN3", "COPY1", "COPY3"])
        r = dict(cell=c, scheme=sch, kind=meta["kind"], **{f"bits_{m}": v for m, v in bits.items()}, glyphs_per_word=gl, winner=win, runner_up=run,
                 win_minus_run=float(bits[win] - bits[run]), win_ci_lo=float(np.quantile(bs, .025)), win_ci_hi=float(np.quantile(bs, .975)),
                 pages_win_better=npos, n_pages=len(pg), sign_p=sp, gain_ctx=bits["KN1"] - ctx, gain_kn3=bits["KN1"] - bits["KN3"], gain_copy1=bits["KN1"] - bits["COPY1"],
                 gain_copy1_vs_G=bits["G"] - bits["COPY1"], best_ctx=min(["KN2", "KN3", "COPY1", "COPY3"], key=lambda m: bits[m]))
        if "init" in t and t.init.any():
            ti = t[t.init]
            for m in ["KN3", "COPY1", win if win in ["SLOT", "KN1", "KN3", "COPY1", "COPY3"] else "COPY1"]:
                if m + "+ONSET" in t: r[f"onset_gain_init_{m}"] = float(-ti[m].mean() + ti[m + "+ONSET"].mean())
        ex = meta["schemes"][sch]["extras"]
        for k in ["naibbe_la_eps", "naibbe_it_eps", "naibbe_la_decodable_test"]:
            if k in ex[0]: r[k] = float(np.mean([e[k] for e in ex]))
        r["copy1_W"] = [e["copy_par"]["COPY1"]["W"] for e in ex]; r["copy1_lam_inner"] = float(np.mean([e["copy_par"]["COPY1"]["lam"] for e in ex]))
        r["copy3_lam_inner"] = float(np.mean([e["copy_par"]["COPY3"]["lam"] for e in ex]))
        rows.append(r)
S = pd.DataFrame(rows); S.to_csv(R / "summary_table.csv", index=False)
cf = pd.DataFrame([dict(cell=c, **(v["crossfit_copy"] or {})) for c, v in out.items()]); cf.to_csv(R / "copy_rate_crossfit.csv", index=False)
B = S[S.scheme == "bifolium"].set_index("cell"); Q = S[S.scheme == "quire"].set_index("cell")
msc = [c for c in B.index if c.startswith("MS_")]; ctl = [c for c in B.index if c.startswith("CTRL_")]; cph = [c for c in B.index if c.startswith("CIPH_")]
P = {}
g_ms = float(B.loc[msc].gain_ctx.mean()); g_ct = float(B.loc[ctl].gain_ctx.mean())
P["P1"] = dict(ms_gain=g_ms, ctrl_gain=g_ct, ms_gain_quire=float(Q.loc[msc].gain_ctx.mean()), ctrl_gain_quire=float(Q.loc[ctl].gain_ctx.mean()), pass_=g_ct > 2 * g_ms)
cfi = cf.set_index("cell")
P["P2"] = dict(ms={c: [cfi.loc[c, "lam"], cfi.loc[c, "lam_lo"], cfi.loc[c, "lam_hi"]] for c in msc}, ctrl={c: [cfi.loc[c, "lam"], cfi.loc[c, "lam_lo"], cfi.loc[c, "lam_hi"]] for c in ctl + cph},
               synth=[cfi.loc["SYNTH_copy0.2", k] for k in ["lam", "lam_lo", "lam_hi"]])
P["P2"]["pass_"] = bool(all(cfi.loc[c, "lam_hi"] - cfi.loc[c, "lam_lo"] < .1 and .01 <= cfi.loc[c, "lam"] <= .2 for c in msc) and min(cfi.loc[msc, "lam"]) > max(cfi.loc[ctl, "lam"]) and abs(cfi.loc["SYNTH_copy0.2", "lam"] - .2) <= .05)
nb = lambda c, D: min(D.loc[c, "bits_NAIBBE_la"], D.loc[c, "bits_NAIBBE_it"])
P["P3"] = dict(ciph={c: dict(naibbe=nb(c, B), slot=B.loc[c, "bits_SLOT"]) for c in cph}, ms={c: dict(naibbe=nb(c, B), slot=B.loc[c, "bits_SLOT"], G=B.loc[c, "bits_G"]) for c in msc})
P["P3"]["pass_"] = bool(all(nb(c, B) < B.loc[c, "bits_SLOT"] for c in cph) and all(nb(c, D) >= D.loc[c, "bits_SLOT"] for c in msc for D in (B, Q)))
P["P4"] = dict(winners={c: [B.loc[c, "winner"], Q.loc[c, "winner"]] for c in msc}, kn3_gain={c: B.loc[c, "gain_kn3"] for c in msc})
P["P4"]["pass_"] = bool(all(B.loc[c, "winner"] in ("KN1", "COPY1", "SLOT") and Q.loc[c, "winner"] in ("KN1", "COPY1", "SLOT") and B.loc[c, "gain_kn3"] < .3 for c in msc))
og = {c: B.loc[c].get("onset_gain_init_KN3") for c in msc}
P["P5"] = dict(onset_gain_init_KN3=og, onset_gain_init_COPY1={c: B.loc[c].get("onset_gain_init_COPY1") for c in msc})
P["P5"]["pass_"] = bool(og["MS_2B"] > .3 and og["MS_3B"] > .3 and og["MS_1A"] < .1)
V = {}
V["language_like"] = bool(g_ms >= .5 * g_ct)
V["copy_like"] = {c: bool(B.loc[c, "bits_COPY1"] < B.loc[c, "bits_KN3"] and cfi.loc[c, "lam_lo"] > .05) for c in msc}
V["cipher_like_rule"] = {c: bool(nb(c, B) < B.loc[c, "bits_SLOT"] and nb(c, B) < B.loc[c, "bits_KN1"]) for c in msc}
V["naibbe_mean_eps_ms"] = {c: [B.loc[c, "naibbe_la_eps"], B.loc[c, "naibbe_it_eps"]] for c in msc}
V["naibbe_mean_eps_ciph"] = {c: [B.loc[c, "naibbe_la_eps"], B.loc[c, "naibbe_it_eps"]] for c in cph}
json.dump(dict(predictions=P, verdict=V), open(R / "summary.json", "w"), indent=1, default=float)
cols = ["cell", "scheme", "bits_G", "bits_SLOT", "bits_KN1", "bits_KN2", "bits_KN3", "bits_COPY1", "bits_COPY3", "bits_NAIBBE_la", "bits_NAIBBE_it", "winner", "runner_up", "win_minus_run", "win_ci_lo", "win_ci_hi", "pages_win_better", "n_pages", "gain_ctx", "gain_kn3", "gain_copy1", "gain_copy1_vs_G", "glyphs_per_word"]
print(S[[c for c in cols if c in S]].round(3).to_string()); print(cf.round(3).to_string()); print(json.dumps(dict(P=P, V=V), indent=1, default=float))
# figure
fig, ax = plt.subplots(figsize=(11, 5)); xs = np.arange(len(B))
for k, m in enumerate(["G", "KN1", "KN3", "COPY1", "SLOT", "NAIBBE_la"]):
    ax.bar(xs + k * .13, B[f"bits_{m}"].values / B.glyphs_per_word.values, .13, label=m)
ax.set_xticks(xs + .3); ax.set_xticklabels(B.index, rotation=30, ha="right", fontsize=8); ax.set_ylabel("held-out bits / glyph (bifolium folds)"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(HERE / "figures" / "bits_per_glyph.png", dpi=130)
