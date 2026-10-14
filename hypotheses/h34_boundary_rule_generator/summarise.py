"""Summarise h34 -> results/summary.json, summary.md (pass/fail per PREREG)."""
import json

import h34_lib as L
import h20_lib as L20

R = L.HERE / "results"; HANDS = ["1A", "2B", "3B"]; GENS = ["C0", "naibbe_it", "naibbe_nonsense"]
ms = json.loads((R / "ms_targets.json").read_text())
m = {(h, g): json.loads((R / f"m_{h}_{g}.json").read_text()) for h in HANDS for g in GENS}
R20 = L.ROOT / "hypotheses/h20_generators_vs_italian/results"


def fp(f):
    d = json.loads(f.read_text()); s = d["schemes"]["bifolium"]; return L20.dstats(s["bits"], s["glyphs_per_word"], d["crossfit_W5"]["lam"])


msr = [fp(R20 / f"cell_MS_{h}.json") for h in HANDS]; rows = []; P = {}
for (h, g), d in m.items():
    st = d["cells"][f"s{d['s_star']}"]; s0 = d["cells"]["s0.0"]; sh = d["cells"]["shuffled"]; t = ms[h]["test"]
    f0 = fp(R / f"cell_{h}_{g}_s0.json"); f1 = fp(R / f"cell_{h}_{g}_sstar.json")
    n0 = L20.match(f0, msr)["n_match"]; n1 = L20.match(f1, msr)["n_match"]
    rows.append(dict(hand=h, gen=g, s_star=d["s_star"], J_ms=t["J"], J=st["J"], J_s0=s0["J"], J_end=st["J_end"], J_edge_ms=t["J_edge"], J_edge=st["J_edge"],
                     T=st["T"], T_shuf=sh["T"], J_shuf=sh["J"], J_allgaps=d["cells"]["allgaps"]["J"], S_ms=t["S"], S0=s0["S"], S=st["S"],
                     V=st["types5k"] / s0["types5k"], fp_s0=n0, fp_star=n1, **{f"D_{k}": v for k, v in f1.items()}))
w = lambda a, b: abs(a - b) <= .35 * b
P["P1"] = sum(w(r["J"], r["J_ms"]) for r in rows); P["P2"] = sum(r["J"] > r["J_end"] for r in rows)
P["P3"] = sum(r["T"] >= .6 and r["T_shuf"] <= .3 for r in rows); P["P4"] = sum(.75 <= r["S"] <= .82 for r in rows)
P["P5"] = sum(abs(r["V"] - 1) <= .05 for r in rows)
nb = [r for r in rows if r["gen"] == "naibbe_it"]
P["P6_nb5"] = sum(r["fp_star"] == 5 for r in nb); P["P6_maxloss"] = max(r["fp_s0"] - r["fp_star"] for r in rows)
P["P7_ms"] = min(ms[h]["test"]["J_edge"] / ms[h]["test"]["J"] for h in HANDS); P["P7_gen"] = sum(w(r["J_edge"], r["J_edge_ms"]) for r in rows)
V = dict(P1=P["P1"] >= 7, P2=P["P2"] >= 7, P3=P["P3"] >= 7, P4=P["P4"] >= 6, P5=P["P5"] == 9, P6=P["P6_nb5"] >= 2 and P["P6_maxloss"] <= 1,
         P7=P["P7_ms"] >= .5 and P["P7_gen"] >= 6)
V["H_gap"] = V["P1"] and V["P2"] and V["P3"] and V["P6"]
(R / "summary.json").write_text(json.dumps(dict(counts=P, verdicts=V, rows=rows, ms_targets=ms), indent=1, default=float))
k = ["hand", "gen", "J_ms", "J", "J_s0", "J_end", "J_shuf", "T", "T_shuf", "S_ms", "S0", "S", "fp_s0", "fp_star"]
md = ["| " + " | ".join(k) + " |", "|" + "---|" * len(k)]
md += ["| " + " | ".join(f"{r[x]:.3f}" if isinstance(r[x], float) else str(r[x]) for x in k) + " |" for r in rows]
md += ["", "counts: " + json.dumps(P), "verdicts: " + json.dumps(V)]
(R / "summary.md").write_text("\n".join(md) + "\n"); print("\n".join(md))
