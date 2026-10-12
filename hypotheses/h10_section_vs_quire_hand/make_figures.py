import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
H = Path(__file__).resolve().parent; R = H / "results"; F = H / "figures"; F.mkdir(exist_ok=True)
d = pd.read_csv(R / "contrasts.csv"); col = {"S": "tab:blue", "H": "tab:green", "R": "tab:red"}
fig, ax = plt.subplots(figsize=(8, 5))
ax.barh(d.contrast, d.js_excess_perm, color=[col[b] for b in d.block]); ax.invert_yaxis()
ax.set_xlabel("JS excess over stratified-permutation null (bits)")
ax.set_title("Blue: section within quire×hand | green: section within hand | red: hand/quire within section", fontsize=9)
fig.tight_layout(); fig.savefig(F / "js_excess_by_contrast.png", dpi=120)
v = pd.read_csv(R / "variance_decomposition.csv")
fig, ax = plt.subplots(figsize=(6, 3.5)); x = range(len(v))
ax.bar([i - .2 for i in x], v.alone_R2, .4, label="alone"); ax.bar([i + .2 for i in x], v.unique_R2, .4, label="unique (others held fixed)")
ax.set_xticks(list(x)); ax.set_xticklabels(v.factor); ax.set_ylabel("R² (Hellinger page vectors)"); ax.legend(); fig.tight_layout()
fig.savefig(F / "variance_decomposition.png", dpi=120)
