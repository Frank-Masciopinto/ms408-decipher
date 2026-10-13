"""Summarise h31 cells -> results/summary_table.csv, results/verdicts.json (rules in PREREG.md)."""
import json
import numpy as np
import pandas as pd
from h31_lib import HERE

R = HERE / "results"
rows = []
for f in sorted(R.glob("cell_*.json")):
    d = json.loads(f.read_text()); g = d["cell"].split("_")[0]
    ho = d["heldout_bits_per_word"]
    for m in ("M1", "M2", "M3"):
        x = d[m]
        rows.append(dict(cell=d["cell"], group=g, seg=m, I1=x["I1"], n_suffix=x["n_suffix"], P1=x["P1"], C1=x["C1"], C1z=x["C1z"], R1=x["R1"],
                         A1=x["A1"], A1z=x["A1z"], A1_lastchar=x["A1_lastchar"], L_char=ho["CharLM"], L_morph=min(ho["M1"], ho["M2"], ho["M3"]),
                         L_gap=min(ho["M1"], ho["M2"], ho["M3"]) - ho["CharLM"], L_M1=ho["M1"], L_M2=ho["M2"], L_M3=ho["M3"]))
T = pd.DataFrame(rows); T.to_csv(R / "summary_table.csv", index=False)
MET = ["P1", "C1", "R1", "A1", "I1", "L_gap"]
ver = {}
for m in ("M1", "M2", "M3"):
    S = T[T.seg == m]; ver[m] = {}
    for k in MET:
        nat = S[S.group == "NAT"][k].dropna(); gen = S[S.group == "GEN"][k].dropna(); ms = S[S.group == "MS"][k]
        inn = lambda v, s: len(s) and s.min() <= v <= s.max()
        if ms.isna().any() or not len(nat) or not len(gen): v = "n/a"
        elif all(inn(v, nat) and not inn(v, gen) for v in ms): v = "language-like"
        elif all(inn(v, gen) and not inn(v, nat) for v in ms): v = "generator-like"
        else: v = "neither/overlap"
        ver[m][k] = dict(verdict=v, MS=ms.round(3).tolist(), NAT=[round(nat.min(), 3), round(nat.max(), 3)], GEN=[round(gen.min(), 3), round(gen.max(), 3)])
core = ["P1", "C1", "R1", "A1"]
cnt = {m: dict(lang=sum(ver[m][k]["verdict"] == "language-like" for k in core), gen=sum(ver[m][k]["verdict"] == "generator-like" for k in core)) for m in ver}
Hm = cnt["M1"]["lang"] >= 3 and any(cnt[m]["lang"] >= 3 for m in ("M2", "M3"))
Hd = cnt["M1"]["gen"] >= 3
out = dict(verdicts=ver, counts=cnt, H_morph=bool(Hm), H_decor=bool(Hd))
(R / "verdicts.json").write_text(json.dumps(out, indent=1, default=float))
pd.set_option("display.width", 250)
print(T[["cell", "seg", "I1", "n_suffix", "P1", "C1", "R1", "A1", "A1_lastchar", "L_char", "L_M1", "L_M2", "L_M3", "L_gap"]].round(3).to_string())
for m in ver: print(m, {k: (v["verdict"], v["MS"], v["NAT"], v["GEN"]) for k, v in ver[m].items()})
print(cnt, "H_morph", Hm, "H_decor", Hd)
