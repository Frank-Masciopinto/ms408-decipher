"""Summarise h35 -> results/summary.json, summary.md (pass/fail per PREREG)."""
import json
import h35_lib as S
sys_ = __import__("sys"); sys_.path.insert(0, str(S.ROOT / "hypotheses/h20_generators_vs_italian"))
import h20_lib as L20  # noqa: E402
R = S.HERE / "results"; HANDS = ["1A", "2B", "3B"]; GENS = ["C0", "naibbe_it", "naibbe_nonsense"]
R34 = S.ROOT / "hypotheses/h34_boundary_rule_generator/results"; R20 = S.ROOT / "hypotheses/h20_generators_vs_italian/results"
ms = json.loads((R34 / "ms_targets.json").read_text())
fp = lambda f: (lambda d: L20.dstats(d["schemes"]["bifolium"]["bits"], d["schemes"]["bifolium"]["glyphs_per_word"], d["crossfit_W5"]["lam"]))(json.loads(f.read_text()))
msr = [fp(R20 / f"cell_MS_{h}.json") for h in HANDS]; rows = []
for h in HANDS:
    for g in GENS:
        d = {k: json.loads((R / f"m_{h}_{g}_{k}.json").read_text()) for k in ("off", "on", "shuf")}
        f = R / f"cell_{h}_{g}_on.json"; n = L20.match(fp(f), msr)["n_match"] if f.exists() else None
        rows.append(dict(hand=h, gen=g, S_ms=ms[h]["test"]["S"], S_off=d["off"]["m"]["S"], S_on=d["on"]["m"]["S"], S_shuf=d["shuf"]["m"]["S"],
                         J_ms_train=d["on"]["J_train_ms"], J_on=d["on"]["m"]["J"], T_on=d["on"]["m"]["T"], V=d["on"]["m"]["types5k"] / d["off"]["m"]["types5k"],
                         fp_on=n, drivers_off=d["off"]["drivers"], drivers_on=d["on"]["drivers"]))
P = dict(P1=sum(.72 <= r["S_on"] <= .80 for r in rows), P1_tight=sum(abs(r["S_on"] - r["S_ms"]) <= .04 for r in rows),
         P2=sum(r["J_on"] >= .6 * r["J_ms_train"] for r in rows), P3=sum(r["T_on"] >= .85 for r in rows),
         P4=sum(abs(r["V"] - 1) <= .3 for r in rows), P5=sum(r["fp_on"] == 5 for r in rows),
         P6=sum(abs(r["S_shuf"] - r["S_ms"]) > abs(r["S_on"] - r["S_ms"]) for r in rows),
         P7=sum(abs(next(r["S_on"] for r in rows if r["hand"] == h and r["gen"] == "naibbe_it") - next(r["S_on"] for r in rows if r["hand"] == h and r["gen"] == "naibbe_nonsense")) <= .03 for h in HANDS))
V = dict(P1=P["P1"] >= 6, P2=P["P2"] >= 7, P3=P["P3"] >= 7, P4=P["P4"] >= 7, P5=P["P5"] >= 6, P6=P["P6"] >= 6, P7=P["P7"] == 3)
V["H_shape"] = V["P1"] and V["P2"] and V["P3"] and V["P6"]
(R / "summary.json").write_text(json.dumps(dict(counts=P, verdicts=V, rows=rows), indent=1, default=float))
k = ["hand", "gen", "S_ms", "S_off", "S_on", "S_shuf", "J_ms_train", "J_on", "T_on", "V", "fp_on"]
md = ["| " + " | ".join(k) + " |", "|" + "---|" * len(k)] + ["| " + " | ".join(f"{r[x]:.3f}" if isinstance(r[x], float) else str(r[x]) for x in k) + " |" for r in rows]
md += ["", "Top gap-driving glyphs, shape off (glyph, weight, P(final|glyph) MS, gen):"]
md += [f"- {r['hand']} {r['gen']}: {r['drivers_off'][:4]}" for r in rows]
md += ["", "counts: " + json.dumps(P), "verdicts: " + json.dumps(V)]
(R / "summary.md").write_text("\n".join(md) + "\n"); print("\n".join(md))
