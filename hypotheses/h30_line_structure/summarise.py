"""Summarise h30 results: table + L1-L5 verdicts -> results/summary.md, results/summary.json."""
import json, glob, os
T = ["1A", "2B", "3B", "3A", "dante", "ariosto", "macer", "augustine", "manzoni", "sidrach", "cucina"]
PROSE = ["augustine", "manzoni", "sidrach"]
R = {t: json.load(open(f"results/m_{t}.json")) for t in T if os.path.exists(f"results/m_{t}.json")}
def row(t):
    d = R[t]; m6 = d["M6"]
    return dict(text=t, lines=d["n_lines"], wpl=d["M1"]["words_mean"], cv=d["M1"]["words_cv"],
                posTYPE=d["M2"]["TYPE"]["excess"], posTYPE_z=d["M2"]["TYPE"]["z"],
                posEND=d["M2"]["END"]["excess"], posONSET=d["M2"]["ONSET"]["excess"],
                fl_share=d["M2"]["TYPE"]["first_last_share"],
                win_EO=d["M3"]["END>ONSET"]["within_excess"], acr_EO=d["M3"]["END>ONSET"]["across_excess"],
                acr_z=d["M3"]["END>ONSET"]["across_z"], rhyme_z=d["M4"]["z_next"],
                para_js=d["M5"]["onset_js"] if d.get("M5") else None, para_z=d["M5"]["z"] if d.get("M5") else None,
                len_first=d["M5"]["len_first"] if d.get("M5") else None, len_other=d["M5"]["len_other"] if d.get("M5") else None,
                gain_pos=m6["bag"] - m6["positional"], gain_hmm=m6["bag"] - m6["hmm"], gain_bi=m6["bag"] - m6["bigram"])
rows = {t: row(t) for t in R}
pr_pos = sum(rows[p]["posTYPE"] for p in PROSE) / len(PROSE)
pr_gain = max(rows[p]["gain_pos"] for p in PROSE)
ver = {}
for h in ["1A", "2B", "3B", "3A"]:
    r = rows[h]
    L1 = r["cv"] >= 0.25 and r["rhyme_z"] < 3
    L2 = r["posTYPE"] >= 3 * pr_pos and r["posTYPE_z"] > 5
    L3 = r["win_EO"] > 0 and r["acr_EO"] < 0.5 * r["win_EO"]
    L4 = r["para_z"] is not None and r["para_z"] > 5 and r["len_first"] > r["len_other"]
    L5 = r["gain_pos"] >= 0.05 and r["gain_pos"] > pr_gain and r["gain_hmm"] > 0
    cls = "verse-like" if not L1 else ("margin-broken prose" if not L2 else
          ("list/table entry" if L5 and r["fl_share"] >= 0.6 else "structured line (unclassified)"))
    ver[h] = dict(L1=L1, L2=L2, L3=L3, L4=L4, L5=L5, class_=cls)
cols = ["text","lines","wpl","cv","posTYPE","posTYPE_z","fl_share","posEND","posONSET","win_EO","acr_EO","acr_z","rhyme_z","para_js","para_z","len_first","len_other","gain_pos","gain_bi","gain_hmm"]
f = lambda v: "-" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))
out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
out += ["| " + " | ".join(f(rows[t][c]) for c in cols) + " |" for t in rows]
out += ["", f"prose-control positional TYPE excess mean = {pr_pos:.4f}; max prose positional gain = {pr_gain:.4f}", "",
        "| hand | L1 not verse | L2 positional | L3 line-bounded | L4 para-onset | L5 model gain | class |", "|---|---|---|---|---|---|---|"]
out += [f"| {h} | {v['L1']} | {v['L2']} | {v['L3']} | {v['L4']} | {v['L5']} | {v['class_']} |" for h, v in ver.items()]
open("results/summary.md", "w").write("\n".join(out) + "\n")
json.dump(dict(rows=rows, verdicts=ver, prose_pos=pr_pos, prose_gain=pr_gain), open("results/summary.json", "w"), indent=1)
print("\n".join(out))
