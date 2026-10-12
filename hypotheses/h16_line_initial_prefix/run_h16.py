import json
import numpy as np, pandas as pd
import h16_lib as L
from h16_lib import L14, HERE
R = HERE / "results"
d0 = L14.table(); out = {"A": {}, "B": {}}; rows = []
for ons_name, ons in [("primary_ds", L.PRIMARY), ("secondary", L.SECONDARY)]:
    d = L.add_attrs(d0, ons)
    for grp, hls in [("2B", ["2B"]), ("3B", ["3B"]), ("2B+3B", ["2B", "3B"]), ("1A", ["1A"])]:
        s = d[d.HL.isin(hls)]; so = s[s.has_on]
        for strat in ["S1", "S1L"]:
            for test, data, attr in [("all:a1_onset", s, "has_on"), ("all:a2_common_stripped", s, "a2"),
                                     ("onset:a2_common_stripped", so, "a2"), ("onset:a3_stripped_eq_next", so, "a3"), ("onset:a4_log_midfreq", so, "a4")]:
                r = L.attr_test(data, attr, "is_init", strat); rows.append(dict(onsets=ons_name, group=grp, null=strat, test=test, **r))
A = pd.DataFrame(rows); A.to_csv(R / "onset_tests.csv", index=False)
P = A[(A.onsets == "primary_ds") & (A.group == "2B+3B")].set_index(["test", "null"])
out["A"]["primary_2B3B"] = {f"{t}|{n}": dict(ratio=r.ratio, z=r.z, p=r.p) for (t, n), r in P.iterrows()}
g = lambda t, n: P.loc[(t, n), "z"]
out["A1"] = dict(pass_=bool(g("all:a1_onset", "S1") > 3 and g("all:a1_onset", "S1L") > 3))
out["A2"] = dict(pass_=bool(all(g(t, n) > 3 for t in ["onset:a2_common_stripped", "onset:a4_log_midfreq"] for n in ["S1", "S1L"])))
out["A3"] = dict(pass_=bool(all(abs(g("onset:a3_stripped_eq_next", n)) < 2 for n in ["S1", "S1L"])))
# examples: initial d/s tokens in 2B+3B, stripped forms
d = L.add_attrs(d0); s = d[d.HL.isin(["2B", "3B"]) & d.has_on]
ex = s.groupby("is_init").apply(lambda x: pd.Series(dict(n=len(x), share_strippable=x.stripped.notna().mean(), share_common=x.a2.mean(), mean_a4=x.a4.mean(), share_eq_next=x.a3.mean())))
ex.to_csv(R / "onset_descriptives_2B3B.csv"); out["A"]["descriptives"] = ex.to_dict("index")
top_init = s[s.is_init].w.value_counts().head(15); out["A"]["top_initial_ds_words"] = top_init.to_dict()
# B
surv = {}
for hl in ["1A", "2B", "3B"]:
    s = d0[d0.HL == hl]; res = {n: L.open_search(s, strat=n) for n in ["S1", "S1L"]}
    m = res["S1"].merge(res["S1L"], on=["word", "slot"], suffixes=("_S1", "_S1L")); m.to_csv(R / f"open_search_{hl}.csv", index=False)
    for slot in ["is_init", "is_final"]:
        for dirn in ["enriched", "depleted"]:
            ok = m[(m.slot == slot) & (m.p_holm_S1 < .05) & (m.p_holm_S1L < .05) & (((m.ratio_S1 > 1) & (m.ratio_S1L > 1)) if dirn == "enriched" else ((m.ratio_S1 < 1) & (m.ratio_S1L < 1)))]
            surv[f"{hl}|{slot}|{dirn}"] = {w: round(r, 2) for w, r in zip(ok.sort_values("ratio_S1", ascending=dirn != "enriched").word, ok.sort_values("ratio_S1", ascending=dirn != "enriched").ratio_S1)}
    out["B"][hl] = dict(n_words=int(m.word.nunique()))
out["B"]["survivors"] = surv
i1A = set(surv["1A|is_init|enriched"]); f1A = set(surv["1A|is_final|enriched"]); iBB = set(surv["2B|is_init|enriched"]) | set(surv["3B|is_init|enriched"])
out["B1"] = dict(n_init=len(i1A), n_final=len(f1A), pass_=len(i1A) >= 3 and len(f1A) >= 3)
out["B2"] = dict(overlap=sorted(i1A & iBB), pass_=len(i1A & iBB) <= 2)
endf = lambda hl: [w for w in surv[f"{hl}|is_final|enriched"] if w.endswith("am") or w.endswith("dy")]
out["B3"] = dict(**{hl: endf(hl) for hl in ["1A", "2B", "3B"]}, pass_=all(endf(hl) for hl in ["1A", "2B", "3B"]))
json.dump(out, open(R / "summary.json", "w"), indent=1, default=float)
print(A[A.onsets == "primary_ds"].round(3).to_string()); print(ex.round(3)); print(json.dumps({k: v for k, v in out.items() if k != "A"}, indent=1, default=float)); print(top_init.to_dict())
# robustness (exploratory, added after first run): exclude the 7 h13 line-initial types
W7 = ["daiin", "dain", "saiin", "sain", "sar", "sol", "y"]
s = d[d.HL.isin(["2B", "3B"]) & d.has_on & ~d.w.isin(W7)]
rob = {n: {a: L.attr_test(s, a, "is_init", n) for a in ["a2", "a4"]} for n in ["S1", "S1L"]}
ini = s[s.is_init]; rob["n_init_tokens"] = int(len(ini)); rob["n_init_types"] = int(ini.w.nunique()); rob["n_init_types_common_stripped"] = int(ini[ini.a2].w.nunique())
rob["top_initial_examples"] = ini[ini.a2].w.value_counts().head(15).to_dict()
out["A"]["robust_excl_7"] = rob; json.dump(out, open(R / "summary.json", "w"), indent=1, default=float)
print(json.dumps(rob, indent=1, default=float))
