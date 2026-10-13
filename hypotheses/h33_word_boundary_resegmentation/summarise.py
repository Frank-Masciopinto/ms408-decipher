"""Summarise h33 results -> results/summary.md + summary.json (verdicts per PREREG.md)."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent / "results"
C = {p.stem[2:]: json.loads(p.read_text()) for p in sorted(R.glob("c_*.json"))}
T = ["orig", "join2", "shift+1", "shift+2", "shift-1", "shift-2", "morf"]; SH = ["shift+1", "shift+2", "shift-1", "shift-2"]
out = ["# h33 summary", ""]; ver = {}
for var in ("full", "interior"):
    out += [f"## {var}", "", "| corpus | grp | space ent. removed | F1 | " + " | ".join(f"{t} M4 / M1 / M5" for t in T) + " |", "|" + "---|" * (4 + len(T))]
    for n, c in C.items():
        d = c[var]; out.append(f"| {n} | {c['group']} | {d['space']['entropy_removed']:.3f} | {d['space']['f1']:.3f} | " +
                              " | ".join(f"{d[t]['M4_ngram_gain']:.3f} / {d[t]['M1_ttr']:.3f} / {d[t]['M5_junction']:.3f}" for t in T) + " |")
    out.append("")
nat = [n for n, c in C.items() if c["group"] == "NAT"]; ms = [n for n, c in C.items() if c["group"] == "MS"]
f = lambda n, v, t, m: C[n][v][t][m]
ver["P1"] = all(f(n, "full", t, "M4_ngram_gain") < f(n, "full", "orig", "M4_ngram_gain") and f(n, "full", t, "M1_ttr") > f(n, "full", "orig", "M1_ttr") for n in nat for t in ("shift+1", "shift-1"))
minrise = {t: min(f(n, "interior", t, "M1_ttr") - f(n, "interior", "orig", "M1_ttr") for n in nat) for t in SH + ["morf"]}
hs = {}
for h in ms:
    o = C[h]["interior"]["orig"]
    hs[h] = [t for t in SH + ["morf"] if C[h]["interior"][t]["M4_ngram_gain"] >= o["M4_ngram_gain"] and C[h]["interior"][t]["M5_junction"] <= .5 * o["M5_junction"]
             and C[h]["interior"][t]["M1_ttr"] - o["M1_ttr"] <= minrise[t]]
ver["H_straddle_passing_transforms"] = hs; ver["H_straddle"] = sum(bool(v) for v in hs.values()) >= 2
ver["H_true_space"] = sum(all(f(h, "full", t, "M4_ngram_gain") < f(h, "full", "orig", "M4_ngram_gain") for t in SH) for h in ms) >= 2
mx = max(C[n]["full"]["space"]["entropy_removed"] for n in nat)
ver["S1"] = sum(C[h]["full"]["space"]["entropy_removed"] > mx for h in ms) >= 2; ver["S1_nat_max"] = mx
out += ["## Verdicts", "", "```", json.dumps(ver, indent=1), "```"]
(R / "summary.md").write_text("\n".join(out)); (R / "summary.json").write_text(json.dumps(ver, indent=1)); print("\n".join(out))
