import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
H = Path(__file__).resolve().parent; R = H / "results"; F = H / "figures"
m = pd.read_csv(R / "heldout_models.csv")
fig, ax = plt.subplots(figsize=(7, 3.8))
for i, (f, g) in enumerate(m.groupby("folds")):
    ax.barh([j + .4 * i for j in range(len(g))], g.gain_vs_M0, .4, label=f"{f} folds")
ax.set_yticks([j + .2 for j in range(len(g))]); ax.set_yticklabels(g.model); ax.invert_yaxis(); ax.set_xlabel("held-out gain over global model (bits/token)"); ax.legend()
fig.tight_layout(); fig.savefig(F / "heldout_models.png", dpi=120)
g = pd.read_csv(R / "rewrite_gap_closure.csv").groupby("comparison").closed.agg(["mean", "std"]).sort_values("mean")
fig, ax = plt.subplots(figsize=(7, 3.5)); ax.barh(g.index, g["mean"], xerr=g["std"], color=["grey" if "noise" in i else ("tab:red" if "hand" in i else "tab:blue") for i in g.index])
ax.set_xlabel("fraction of held-out word-distribution JS closed by ≤10 rewrite rules"); fig.tight_layout(); fig.savefig(F / "rewrite_gap_closure.png", dpi=120)
c = pd.read_csv(R / "residual_section_contrasts.csv")
fig, ax = plt.subplots(figsize=(7, 3.8))
for i, (r, gg) in enumerate(c.groupby("residual")):
    ax.bar([j + .27 * i for j in range(len(gg))], gg.ba - gg.chance, .27, label=r)
ax.set_xticks([j + .27 for j in range(len(gg))]); ax.set_xticklabels(gg.contrast, rotation=20, fontsize=8); ax.set_ylabel("balanced accuracy − chance"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(F / "residual_section_ba.png", dpi=120)
