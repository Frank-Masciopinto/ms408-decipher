"""Figures for h05 from results/*.csv (run after run_h05.py)."""
import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import h05_lib as L

warnings.filterwarnings("ignore")
R = L.HERE / "results"
F = L.HERE / "figures"
F.mkdir(exist_ok=True)
S = json.load(open(R / "summary.json"))
loci = pd.read_csv(R / "zodiac_loci.csv")
fol = pd.read_csv(R / "zodiac_folios.csv")
short = [f"{f}\n{L.PAGE_SIGN[f][:4]}" for f in L.FOLIOS]

# 1. labels per page by band + ring words
fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
lab = loci[loci.ltype == "Lz"]
tab = lab.groupby(["folio", "band"]).size().unstack(fill_value=0).reindex(L.FOLIOS)
bottom = np.zeros(len(tab))
for b in [c for c in ["inner", "middle", "outer", "top", "centre"] if c in tab]:
    ax[0].bar(range(len(tab)), tab[b], bottom=bottom, label=b)
    bottom += tab[b].values
ax[0].set_xticks(range(12)); ax[0].set_xticklabels(short, fontsize=7); ax[0].set_ylabel("nymph/star labels"); ax[0].legend(fontsize=7)
ax[0].set_title("299 labels on 12 pages (Aries and Taurus: 15 each; 'top' = overflow nymphs)", fontsize=8)
ax[1].bar(range(12), fol.n_ring_words.values, color="tab:gray")
ax[1].set_xticks(range(12)); ax[1].set_xticklabels(short, fontsize=7); ax[1].set_ylabel("ring-text words (Cc)"); ax[1].set_title("circular text, 2-4 rings per page", fontsize=8)
fig.tight_layout(); fig.savefig(F / "fig1_zodiac_pages_labels.png", dpi=140); plt.close(fig)

# 2. page similarity
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
for a, fn, tt in ((ax[0], "page_similarity_label_unit_bigrams.csv", "label unit-bigram cosine"), (ax[1], "page_similarity_ring_unit_bigrams.csv", "ring-text unit-bigram cosine")):
    M = pd.read_csv(R / fn, index_col=0)
    im = a.imshow(M.values, cmap="viridis")
    a.set_xticks(range(12)); a.set_yticks(range(12)); a.set_xticklabels(L.FOLIOS, rotation=90, fontsize=7); a.set_yticklabels([f"{f} {L.PAGE_SIGN[f][:4]}" for f in L.FOLIOS], fontsize=7)
    a.set_title(tt, fontsize=9); plt.colorbar(im, ax=a, fraction=0.046)
    for (i, j) in ((1, 2), (3, 4)):          # Aries 1-2, Taurus 1-2
        a.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, ec="red", lw=1.5)); a.add_patch(plt.Rectangle((i - .5, j - .5), 1, 1, fill=False, ec="red", lw=1.5))
fig.suptitle("Do the two Aries pages / two Taurus pages (red) look alike? Only as much as neighbouring pages do", fontsize=9)
fig.tight_layout(); fig.savefig(F / "fig2_page_similarity.png", dpi=140); plt.close(fig)

# 3. affix shares
A = pd.read_csv(R / "label_affix_shares_by_page.csv")
fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
for c in ["starts_o", "starts_ot", "starts_ok", "starts_qo"]:
    ax[0].plot(range(12), A[c], marker="o", label=c.replace("starts_", "begins "))
ax[0].set_xticks(range(12)); ax[0].set_xticklabels(short, fontsize=7); ax[0].legend(fontsize=7); ax[0].set_ylabel("share of label words"); ax[0].set_title("label beginnings by page (page order = month order)", fontsize=8)
for c in ["ends_y", "ends_l", "ends_r", "ends_m", "ends_n", "ends_ar_or"]:
    ax[1].plot(range(12), A[c], marker="o", label=c.replace("ends_", "ends -"))
ax[1].set_xticks(range(12)); ax[1].set_xticklabels(short, fontsize=7); ax[1].legend(fontsize=7, ncol=2); ax[1].set_title("label endings by page", fontsize=8)
fig.tight_layout(); fig.savefig(F / "fig3_label_affixes_by_page.png", dpi=140); plt.close(fig)

# 4. length tests
lt = pd.read_csv(R / "length_order_tests.csv")
met = pd.read_csv(R / "sign_label_length_metrics.csv", index_col=0)
nl = L.name_lists()
fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
for a, key in ((ax[0], "sign:latin"), (ax[1], "month:roman_words_on_the_pages")):
    x = [len(n) for n in L.names_by_sign(nl[key])]
    y = met.label_mean_letters.values
    a.scatter(x, y)
    for xi, yi, s in zip(x, y, L.SIGNS):
        a.annotate(s[:4], (xi, yi), fontsize=7, xytext=(2, 2), textcoords="offset points")
    r = lt[(lt.names == key) & (lt.voynich_metric == "label_mean_letters")].iloc[0]
    a.set_title(f"{key}: rho={r.spearman_rho:.2f}, p={r.p_perm_two_sided:.2f}", fontsize=8)
    a.set_xlabel("name length (letters)"); a.set_ylabel("mean label length on that sign's pages (EVA chars)")
ax[2].hist(lt.p_perm_two_sided, bins=np.linspace(0, 1, 11), color="tab:gray", edgecolor="w")
ax[2].axhline(len(lt) / 10, color="r", ls="--", lw=1, label="uniform expectation")
ax[2].set_title(f"{len(lt)} length tests: p-values look uniform (min Holm p = {lt.holm_p.min():.2f})", fontsize=8); ax[2].set_xlabel("permutation p"); ax[2].legend(fontsize=7)
fig.tight_layout(); fig.savefig(F / "fig4_length_order.png", dpi=140); plt.close(fig)

# 5. isomorph + crib null
iso = pd.read_csv(R / "isomorph_name_in_page_tests.csv")
cr = pd.read_csv(R / "crib_drag_summary.csv")
ns = json.load(open(R / "crib_null_store.json"))
fig, ax = plt.subplots(1, 3, figsize=(14, 3.8))
d = iso.sort_values("p_perm")
ax[0].barh([f"{a} ({b})" for a, b in zip(d.names, d["mode"])][:15][::-1], -np.log10(d.p_perm.values[:15][::-1]))
ax[0].axvline(-np.log10(0.05), color="r", ls="--", lw=1); ax[0].axvline(-np.log10(0.05 / len(iso)), color="k", ls=":", lw=1)
ax[0].set_title("isomorph test: 15 smallest p\n(dashed .05, dotted Bonferroni)", fontsize=7); ax[0].set_xlabel("-log10 p"); ax[0].tick_params(axis="y", labelsize=6)
k = "sign:latin"
ax[1].hist(ns[k]["A"], bins=20, alpha=.6, label="names permuted over signs"); ax[1].hist(ns[k]["B"], bins=20, alpha=.6, label="random lexicon words")
ax[1].axvline(ns[k]["obs"], color="r", label=f"true Latin sign names: {ns[k]['obs']}")
ax[1].set_title("crib-drag transfer, Latin sign names:\nlexicon types hit in the rest of MS", fontsize=7); ax[1].legend(fontsize=6)
cr2 = cr.copy()
pa = cr2.rest_hit_types_p_matched_A_perm.fillna(cr2.rest_hit_types_p_ge_A_perm); pb = cr2.rest_hit_types_p_matched_B_random.fillna(cr2.rest_hit_types_p_ge_B_random)
x = np.arange(len(cr2))
ax[2].bar(x - .2, -np.log10(pa), .4, label="vs permuted names"); ax[2].bar(x + .2, -np.log10(pb), .4, label="vs random words")
ax[2].axvline(0, c="k", lw=0)
ax[2].axhline(-np.log10(0.05), color="r", ls="--", lw=1); ax[2].axhline(-np.log10(0.05 / (2 * len(cr2))), color="k", ls=":", lw=1)
ax[2].set_xticks(x); ax[2].set_xticklabels(cr2.names, rotation=75, fontsize=6); ax[2].legend(fontsize=6); ax[2].set_title("crib-drag: matched-coverage p per name list", fontsize=8)
fig.tight_layout(); fig.savefig(F / "fig5_isomorph_and_cribdrag.png", dpi=140); plt.close(fig)

# 6. pitch
lp = pd.read_csv(R / "label_pitch_table.csv")
loc = pd.read_csv(R / "label_tokens.csv")
inv = pd.read_csv(R / "unit_hz_a_slotgrammar_ext.csv")
fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
mh = S["label_pitch"]["mean_hz_by_sign"]
ax[0].bar(range(10), [mh[s] for s in L.SIGNS], color="tab:blue")
ax[0].set_ylim(270, 320); ax[0].set_xticks(range(10)); ax[0].set_xticklabels([s[:5] for s in L.SIGNS], fontsize=8)
ax[0].set_ylabel("mean Hz of label words (a_slotgrammar_ext)")
ax[0].set_title(f"label pitch by sign: eta^2={S['label_pitch']['eta2_sign']:.3f}, perm p={S['label_pitch']['p_perm_eta2']:.3f} (illustration)", fontsize=8)
iv = inv.sort_values("hz_a_slotgrammar_ext")
ax[1].scatter(range(len(iv)), iv.hz_a_slotgrammar_ext, c=np.where(iv.on_sheet, "tab:red", "tab:gray"), s=14)
for i, (u, h) in enumerate(zip(iv.unit, iv.hz_a_slotgrammar_ext)):
    if iv.on_sheet.iloc[i] or i % 4 == 0:
        ax[1].annotate(u, (i, h), fontsize=6, xytext=(1, 2), textcoords="offset points")
ax[1].set_ylabel("Hz"); ax[1].set_title("unit -> Hz under a_slotgrammar_ext (red = sheet's 8 digraphs, fixed at the sheet's values)", fontsize=8)
fig.tight_layout(); fig.savefig(F / "fig6_label_pitch.png", dpi=140); plt.close(fig)
print("figures written")
