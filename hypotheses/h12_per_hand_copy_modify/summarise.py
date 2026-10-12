import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
H = Path(__file__).resolve().parent; R = H / "results"
s = pd.read_csv(R / "scores.csv")
piv = s.pivot_table(index=["level", "fold", "cell"], columns="model", values=["rms_z", "top_js"])
out = {}
for metric in ("rms_z", "top_js"):
    t = piv[metric]
    for other in ("POOLED", "SHUF"):
        w = (t["OWN"] < t[other]); out[f"OWN<{other}|{metric}"] = f"{int(w.sum())}/{int(w.notna().sum())} folds"
closure = []
for (lv, f, c), r in piv["top_js"].iterrows():
    for m in r.index:
        if m.startswith("MAPPED"):
            d = m.split()[-1]; cross = r[f"CROSS from {d}"]
            if pd.notna(r[m]):
                closure.append(dict(level=lv, fold=f, pair=f"{c}<-{d}", own=r["OWN"], cross=cross, mapped=r[m], closed=(cross - r[m]) / (cross - r["OWN"])))
cl = pd.DataFrame(closure); cl.to_csv(R / "mapping_closure.csv", index=False)
out["closure_mean"] = cl.groupby(["level", "pair"]).closed.mean().round(3).to_dict()
out["closure_mean"] = {f"{a}|{b}": v for (a, b), v in out["closure_mean"].items()}
p = pd.read_csv(R / "fitted_params.csv"); out["p_copy_range_OWN"] = [float(p[p.model == "OWN"].p_copy.min()), float(p[p.model == "OWN"].p_copy.max())]
out["fit_secs_OWN_median"] = float(p[p.model == "OWN"].secs.median())
mean = s.groupby(["level", "cell", "model"])[["rms_z", "top_js"] + [c for c in s.columns if c.startswith("absz_")]].mean().round(3)
mean.to_csv(R / "scores_mean.csv"); json.dump(out, open(R / "summary.json", "w"), indent=1); print(json.dumps(out, indent=1)); print(cl.round(3).to_string())
g = s[s.level == "bifolium"].copy(); g["m"] = g.model.where(~g.model.str.startswith(("CROSS", "MAPPED")), g.model.str.split().str[0])
g = g.groupby(["cell", "m"]).top_js.mean().unstack()
ax = g[[c for c in ["OWN", "POOLED", "SHUF", "CROSS", "MAPPED"] if c in g]].plot.bar(figsize=(7, 3.6)); ax.set_ylabel("top-100-word JS to held-out text (bits)")
ax.set_title("bifolium folds: lower is better (CROSS/MAPPED averaged over source hands)", fontsize=9); plt.tight_layout(); plt.savefig(H / "figures" / "top_js_by_model.png", dpi=120)
