"""Summarise h39 -> results/summary.json, summary.md (pass/fail per PREREG)."""
import json, sys
import h39_lib as S
sys.path.insert(0, str(S.ROOT / "hypotheses/h20_generators_vs_italian"))
import h20_lib as L20  # noqa: E402
R = S.HERE / "results"; HANDS = ["1A", "2B", "3B"]; GENS = ["C0", "naibbe_it", "naibbe_nonsense"]; FEEDS = ["native", "naibbe_it", "naibbe_nonsense"]
H = S.ROOT / "hypotheses"; R20 = H / "h20_generators_vs_italian/results"; R38 = H / "h38_family_respell_and_native_copier/results"
ms = json.loads((H / "h34_boundary_rule_generator/results/ms_targets.json").read_text())
fp = lambda f: (lambda d: L20.dstats(d["schemes"]["bifolium"]["bits"], d["schemes"]["bifolium"]["glyphs_per_word"], d["crossfit_W5"]["lam"]))(json.loads(f.read_text()))
msr = [fp(R20 / f"cell_MS_{h}.json") for h in HANDS]; ld = lambda f: json.loads(f.read_text())
def nfp(f):
    if not f.exists(): return None, None
    mt = L20.match(fp(f), msr); return mt["n_match"], round(fp(f)["D3"], 3)
A = []; B = []
for h in HANDS:
    for g in GENS:
        d = ld(R / f"m_{h}_{g}_graph.json"); sh = ld(R / f"m_{h}_{g}_graphshuf.json"); r38 = ld(R38 / f"m_{h}_{g}_fam.json"); n, d3 = nfp(R / f"cell_{h}_{g}_graph.json")
        A.append(dict(hand=h, gen=g, S_ms=ms[h]["test"]["S"], S=d["m"]["S"], S_shuf=sh["m"]["S"], S_h38=r38["m"]["S"], E=d["E"], E_h38=r38["E"], F=d["F"],
                      J=d["m"]["J"], J_ms=d["J_train_ms"], T=d["m"]["T"], V=d["V_ms"], merged=d["extra"]["merged_types"], fp=n, D3=d3))
    for f in FEEDS:
        d = ld(R / f"m_{h}_{f}_tuned.json"); x = d["extra"]; n, d3 = nfp(R / f"cell_{h}_{f}_tuned.json")
        B.append(dict(hand=h, feed=f, p_fresh=x["p_fresh"], window=x["window"], p0=x["p0"], S_ms=ms[h]["test"]["S"], S=d["m"]["S"], S_tune=x["S"], S_ms_tr=x["S_ms"],
                      C=d["copy_proxy"], C_ms=d["copy_proxy_ms_test"], F=d["F"], J=d["m"]["J"], J_ms=d["J_train_ms"], T=d["m"]["T"], V=d["V_ms"], fp=n, D3=d3))
inr = lambda x: .72 <= x <= .80
P = dict(A1=sum(r["E"] >= .9 for r in A), A2=sum(inr(r["S"]) for r in A), A3=sum(r["fp"] == 5 for r in A), A4=sum(r["F"] <= .05 for r in A),
         A5=sum(abs(r["S_shuf"] - r["S_ms"]) > abs(r["S"] - r["S_ms"]) for r in A),
         B1=sum(inr(r["S"]) for r in B), B2=sum(r["fp"] == 5 for r in B), B3=sum(r["J"] >= .6 * r["J_ms"] and r["T"] >= .85 for r in B),
         B4=sum(abs(r["V"] - 1) <= .25 for r in B),
         B5=sum(abs(next(r["S"] for r in B if r["hand"] == h and r["feed"] == "naibbe_it") - next(r["S"] for r in B if r["hand"] == h and r["feed"] == "naibbe_nonsense")) <= .03 for h in HANDS))
V = dict(A1=P["A1"] >= 7, A2=P["A2"] >= 6, A3=P["A3"] >= 6, A4=P["A4"] >= 7, A5=P["A5"] >= 6, B1=P["B1"] >= 6, B2=P["B2"] >= 6, B3=P["B3"] >= 7, B4=P["B4"] >= 7, B5=P["B5"] == 3)
V["H_A"] = V["A1"] and V["A2"] and V["A3"]; V["H_B"] = V["B1"] and V["B2"] and V["B3"]; V["loop_success"] = V["H_A"] or V["H_B"]
(R / "summary.json").write_text(json.dumps(dict(counts=P, verdicts=V, A=A, B=B), indent=1, default=float))
tab = lambda rows: ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])] + ["| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in r.values()) + " |" for r in rows]
md = ["## Variant A (graph)"] + tab(A) + ["", "## Variant B (tuned)"] + tab(B) + ["", "counts: " + json.dumps(P), "verdicts: " + json.dumps(V)]
(R / "summary.md").write_text("\n".join(md) + "\n"); print("\n".join(md))
