import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
H = Path(__file__).resolve().parent; R = H / "results"; F = H / "figures"; F.mkdir(exist_ok=True)
s = json.load(open(R / "summary.json"))
qb = s["t4_quire_block_null"]
fig, ax = plt.subplots(figsize=(7, 4))
for i, (t, v) in enumerate(qb.items()):
    ax.scatter(np.full(len(v["quire_block_null"]), i) + np.random.uniform(-.15, .15, len(v["quire_block_null"])), v["quire_block_null"], c="grey", s=10)
    ax.scatter(i, v["observed_global_holm05"], c="red", s=80, marker="D")
ax.set_xticks(range(len(qb))); ax.set_xticklabels(list(qb)); ax.set_ylabel("words enriched (Holm p<0.05)")
ax.set_title("Context-word enrichment: real visual tag (red) vs random quire-aligned tags (grey)")
fig.tight_layout(); fig.savefig(F / "enrichment_vs_quire_block_null.png", dpi=120)
t1 = pd.read_csv(R / "t1_label_object_sharing.csv")
fig, ax = plt.subplots(figsize=(6, 3.5))
for j, (nl, g) in enumerate(t1.groupby("null")):
    ax.bar(np.arange(len(g)) + j * .4, g.z, .4, label=nl)
ax.set_xticks(np.arange(4) + .2); ax.set_xticklabels(t1.feature.unique()); ax.axhline(1.64, ls="--", c="k", lw=.8)
ax.set_ylabel("z vs permutation null"); ax.legend(); ax.set_title("Same-object labels share features?")
fig.tight_layout(); fig.savefig(F / "label_object_sharing.png", dpi=120)
rob = s["t5_root_robustness"]; ks = [5, 10, 20, 30]
fig, ax = plt.subplots(figsize=(6, 3.5))
for key, lab in [("", "all"), ("|lang=A", "Currier A"), ("|lang=B", "Currier B")]:
    ax.plot(ks, [-np.log10(rob[f"k={k}{key}"]["p_random_tags"]) for k in ks], "o-", label=lab)
ax.axhline(-np.log10(.05), ls="--", c="k", lw=.8); ax.set_xlabel("number of pharma 'root' candidate words"); ax.set_ylabel("-log10 p (within-quire tag null)")
ax.legend(); ax.set_title("Transfer: pharma root words -> herbal large-root pages"); fig.tight_layout(); fig.savefig(F / "root_transfer_robustness.png", dpi=120)
