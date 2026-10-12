import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
import h14_lib as L
from h14_lib import L13, HERE

rng = np.random.default_rng(14); R = HERE / "results"
d = L.table(); out = {"n_lines": int(d.lid.nunique()), "n_tokens": len(d), "n_S1_strata": int(d.S1.nunique()),
                      "share_gapshort_lines": float(d.drop_duplicates("lid").gapshort.mean()), "share_gap_lines": float(d.drop_duplicates("lid").gap.mean())}
tests = [(w, "is_init", "init_enriched") for w in L.INIT] + [(w, "is_final", "final_enriched") for w in L.FINAL] + \
        [(w, "is_init", "init_depleted") for w in L.INIT_DEP] + [(w, "is_final", "final_depleted") for w in L.FINAL_DEP]
rows = []
for null in ["raw", "S1", "S2", "S1L"]:
    for slot in ["is_init", "is_final"]:
        ws = [w for w, s, _ in tests if s == slot]
        if null == "raw": res = L.strat_null(d, ws, slot, "HL", rng=rng)
        elif null == "S2": res = L.line_null(d, ws, slot, rng=rng)
        else: res = L.strat_null(d, ws, slot, null, rng=rng)
        for w, s, grp in tests:
            if s != slot: continue
            o, nl = res[w]; rows.append(dict(null=null, word=w, slot=slot, group=grp, obs=o, null_mean=float(nl.mean()), ratio=(o + .5) / (nl.mean() + .5), p=L.mc_p(o, nl)))
T = pd.DataFrame(rows)
T["p_holm"] = T.groupby("null").p.transform(lambda p: L13.H9.holm(p.values))
T["survives"] = (T.p_holm < .05) & ((T.ratio > 1) == T.group.str.endswith("enriched"))
T.to_csv(R / "position_tests.csv", index=False)
W = T.pivot_table(index=["group", "word"], columns="null", values=["ratio", "survives"], aggfunc="first")
W.columns = [f"{a}_{b}" for a, b in W.columns]; W.to_csv(R / "position_wide.csv")
surv = {g: {n: sorted(T[(T.group == g) & (T.null == n) & T.survives].word) for n in ["raw", "S1", "S2", "S1L"]} for g in T.group.unique()}
out["survivors"] = surv
# subset robustness: S1 on non-first, non-gap/short lines only
sub = d[~d.first_line & ~d.gapshort]
for slot, ws in [("is_init", L.INIT), ("is_final", L.FINAL)]:
    res = L.strat_null(sub, ws, slot, "S1", rng=rng)
    out.setdefault("plain_lines_S1", {}).update({w: dict(obs=res[w][0], ratio=(res[w][0] + .5) / (res[w][1].mean() + .5), p=L.mc_p(*res[w])) for w in ws})
# per-HL S1 ratios for the 10 enriched words
ph = []
for hl in ["1A", "2B", "3B"]:
    s = d[d.HL == hl]
    for slot, ws in [("is_init", L.INIT), ("is_final", L.FINAL)]:
        res = L.strat_null(s, ws, slot, "S1", n=4000, rng=rng)
        for w in ws: ph.append(dict(HL=hl, word=w, slot=slot, obs=res[w][0], null_mean=float(res[w][1].mean()), p=L.mc_p(*res[w])))
pd.DataFrame(ph).to_csv(R / "per_HL_S1.csv", index=False)
# margin squeezing
out["final_length_S1"] = L.final_length(d, "S1"); out["final_length_S2_line"] = L.final_length(d, "lid")
out["init_length_S1"] = (lambda e: L.final_length(e, "S1"))(d.assign(is_final=d.is_init))
out["final_length_by_HL"] = {hl: L.final_length(d, "S1", d.HL == hl) for hl in ["1A", "2B", "3B"]}
lens = d.groupby("is_final").ulen.mean(); out["mean_ulen_final_vs_other"] = [float(lens[True]), float(lens[False])]
# Procrustes
d13 = L13.token_table(); top = L13.top_words(d13); words, ranks, sims = L.procrustes(d13, top)
n = len(words); out["procrustes"] = dict(n=n, top1=float((ranks == 0).mean()), top5=float((ranks < 5).mean()), chance_top1=1 / n, chance_top5=5 / n, median_rank=float(np.median(ranks)))
wi = {w: i for i, w in enumerate(words)}; rp = []
for a, b, r in L13.rule_pairs(top):
    for x, y in ((a, b), (b, a)):
        if x in wi and y in wi:
            s = sims[wi[x]]; others = [j for j in range(n) if j not in (wi[x], wi[y])]
            rp.append(dict(x_2B=x, y_1A=y, rule=r, pct=float((s[others] < s[wi[y]]).mean())))
rp = pd.DataFrame(rp); rp.to_csv(R / "procrustes_rule_pairs.csv", index=False)
dv = rp.pct.values - .5; fl = [np.mean(dv * rng.choice([-1, 1], len(dv))) for _ in range(10000)]
out["procrustes"]["rule_pairs_n"] = len(rp); out["procrustes"]["rule_median_pct"] = float(rp.pct.median())
out["procrustes"]["rule_p_one_sided"] = float((1 + sum(f >= dv.mean() for f in fl)) / 10001)
pd.DataFrame({"word": words, "identity_rank": ranks}).to_csv(R / "procrustes_identity.csv", index=False)
# predictions
both = lambda g, a, b: sorted(set(surv[g][a]) & set(surv[g][b]))
out["P1"] = dict(survive_S1_S2=both("init_enriched", "S1", "S2")); out["P1"]["pass_"] = len(out["P1"]["survive_S1_S2"]) >= 5
out["P2"] = dict(survive_S1_S1L=both("final_enriched", "S1", "S1L")); out["P2"]["pass_"] = len(out["P2"]["survive_S1_S1L"]) >= 2
out["P3"] = dict(squeeze=out["final_length_S1"]["z"] < -2, final_survive_S1L=surv["final_enriched"]["S1L"]); out["P3"]["pass_"] = out["P3"]["squeeze"] and len(surv["final_enriched"]["S1L"]) >= 2
nd = len(L.INIT_DEP) + len(L.FINAL_DEP); ns = len(surv["init_depleted"]["S1"]) + len(surv["final_depleted"]["S1"])
out["P4"] = dict(n=ns, of=nd, pass_=ns >= .6 * nd)
pr = out["procrustes"]; out["P5"] = dict(pass_=pr["top5"] > 3 * pr["chance_top5"] and pr["rule_p_one_sided"] >= .05)
json.dump(out, open(R / "summary.json", "w"), indent=1, default=float)
# figure
fig, ax = plt.subplots(figsize=(11, 5)); E = T[T.group.str.endswith("enriched")]
for k, nl in enumerate(["raw", "S1", "S2", "S1L"]):
    e = E[E.null == nl]; ax.bar(np.arange(len(e)) + k * .2, np.log2(e.ratio), .2, label=nl)
ax.set_xticks(np.arange(len(e)) + .3); ax.set_xticklabels([f"{w}\n{'init' if s == 'is_init' else 'final'}" for w, s in zip(e.word, e.slot)])
ax.axhline(0, c="k", lw=.5); ax.set_ylabel("log2 obs/null"); ax.legend(); ax.set_title("h14: h13 line-position enrichments under layout-controlled nulls")
fig.tight_layout(); fig.savefig(HERE / "figures" / "enrichment_by_null.png", dpi=130)
print(json.dumps(out, indent=1, default=float))
