"""Summarise h37 -> results/summary.json, summary.md (pass/fail per PREREG)."""
import json, sys
import h37_lib as S
sys.path.insert(0, str(S.ROOT / "hypotheses/h20_generators_vs_italian"))
import h20_lib as L20  # noqa: E402
R = S.HERE / "results"; HANDS = ["1A", "2B", "3B"]; GENS = ["C0", "naibbe_it", "naibbe_nonsense"]
R34 = S.ROOT / "hypotheses/h34_boundary_rule_generator/results"; R20 = S.ROOT / "hypotheses/h20_generators_vs_italian/results"
ms = json.loads((R34 / "ms_targets.json").read_text())
fp = lambda f: (lambda d: L20.dstats(d["schemes"]["bifolium"]["bits"], d["schemes"]["bifolium"]["glyphs_per_word"], d["crossfit_W5"]["lam"]))(json.loads(f.read_text()))
msr = [fp(R20 / f"cell_MS_{h}.json") for h in HANDS]; rows = []
for h in HANDS:
    for g in GENS:
        d = {k: json.loads((R / f"m_{h}_{g}_{k}.json").read_text()) for k in ("off", "copy", "shuf", "h35", "h36pos")}
        row = dict(hand=h, gen=g, S_ms=ms[h]["test"]["S"], J_ms_train=d["copy"]["J_train_ms"])
        for k in d: row[f"S_{k}"] = d[k]["m"]["S"]; row[f"E_{k}"] = d[k]["E"]
        for k in ("copy",):
            row[f"J_{k}"] = d[k]["m"]["J"]; row[f"T_{k}"] = d[k]["m"]["T"]; row[f"V_{k}"] = d[k]["m"]["types5k"] / d["off"]["m"]["types5k"]
            f = R / f"cell_{h}_{g}_{k}.json"; row[f"fp_{k}"] = L20.match(fp(f), msr)["n_match"] if f.exists() else None
        st = d["copy"]["respell_stats"]; row["tree_ok"] = st["derived_ok"] / (st["derived_ok"] + st["derived_fail"]); row["roots"] = st["root"]; row["drivers_copy"] = d["copy"]["drivers"]; rows.append(row)
P = dict(P1=sum(.72 <= r["S_copy"] <= .80 for r in rows), 
         P2=sum(r["J_copy"] >= .6 * r["J_ms_train"] for r in rows), P3=sum(r["T_copy"] >= .85 for r in rows),
         P4=sum(abs(r["V_copy"] - 1) <= .3 for r in rows), P5=sum(r["fp_copy"] == 5 for r in rows),
         P6=sum(r["E_copy"] >= .9 for r in rows), P7=sum(abs(r["S_shuf"] - r["S_ms"]) > abs(r["S_copy"] - r["S_ms"]) for r in rows),
         P8=sum(abs(next(r["S_copy"] for r in rows if r["hand"] == h and r["gen"] == "naibbe_it") - next(r["S_copy"] for r in rows if r["hand"] == h and r["gen"] == "naibbe_nonsense")) <= .03 for h in HANDS))
V = dict(P1=P["P1"] >= 6, P2=P["P2"] >= 7, P3=P["P3"] >= 7, P4=P["P4"] >= 7, P5=P["P5"] >= 6, P6=P["P6"] >= 7, P7=P["P7"] >= 6, P8=P["P8"] == 3)
V["H_copy"] = V["P1"] and V["P5"] and V["P6"]
(R / "summary.json").write_text(json.dumps(dict(counts=P, verdicts=V, rows=rows), indent=1, default=float))
k = ["hand", "gen", "S_ms", "S_off", "S_copy", "S_shuf", "S_h35", "S_h36pos", "E_copy", "E_h35", "E_h36pos", "tree_ok", "roots", "J_ms_train", "J_copy", "T_copy", "V_copy", "fp_copy"]
md = ["| " + " | ".join(k) + " |", "|" + "---|" * len(k)] + ["| " + " | ".join(f"{r[x]:.3f}" if isinstance(r[x], float) else str(r[x]) for x in k) + " |" for r in rows]
md += ["", "Top gap-driving glyphs after `copy` (glyph, weight, P(final|glyph) MS, gen):"] + [f"- {r['hand']} {r['gen']}: {r['drivers_copy'][:4]}" for r in rows]
md += ["", "counts: " + json.dumps(P), "verdicts: " + json.dumps(V)]
(R / "summary.md").write_text("\n".join(md) + "\n"); print("\n".join(md))
