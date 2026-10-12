import json
import sys
import numpy as np
import pandas as pd
import h11_lib as L

OUT = L.HERE / "results"
WATER = "qol olkedy qokain qoteedy qokedy".split(); STAR = "cheeo lkaiin oteey al oteedy".split()
ROOT = "ctheol ckhey qoor qokeody qockhey qokeol okeol".split(); TRANS = "chody ckhey oldy qockhey okeeey qokey sol aiin qokol okal".split()


def main(n_perm=2000):
    q, bags = L.load(); S = {}
    # 1 held-out models
    G = (50, 500, 5000, 50000, 500000)
    hm = pd.concat([L.heldout(q, bags, "quire", grid=G), L.heldout(q, bags, "bifolium", grid=G)]); hm.to_csv(OUT / "heldout_models.csv", index=False)
    d, vocab, X, n, Y = L.profiles(q, bags)
    S["R2_HL_alone"] = L.H10.r2(Y - Y.mean(0), L.H10.dummies(d.HL)); S["R2_lang_alone"] = L.H10.r2(Y - Y.mean(0), L.H10.dummies(d.lang))
    S["R2_HL_quire"] = L.H10.r2(Y - Y.mean(0), np.hstack([L.H10.dummies(d.HL), L.H10.dummies(d.quire)]))
    S["R2_section_alone"] = L.H10.r2(Y - Y.mean(0), L.H10.dummies(d.section))
    S["R2_section_given_HL"] = L.H10.r2(Y - Y.mean(0), np.hstack([L.H10.dummies(d.HL), L.H10.dummies(d.section)])) - S["R2_HL_alone"]
    S["R2_full_h10"] = L.H10.r2(Y - Y.mean(0), np.hstack([L.H10.dummies(d.HL), L.H10.dummies(d.quire), L.H10.dummies(d.section)]))
    # 2 residual tests
    RA = L.residualise(Y, d.HL); RB = L.residualise(Y, d.HL, d.quire)
    sec = d.section
    contrasts = {"all sections": sec.isin(["herbal", "pharmaceutical", "biological", "stars", "cosmological", "astronomical", "zodiac"]),
                 "herbal vs pharma": sec.isin(["herbal", "pharmaceutical"]), "herbal vs biological": sec.isin(["herbal", "biological"]),
                 "herbal vs stars": sec.isin(["herbal", "stars"]), "astro/cosmo/zodiac": sec.isin(["astronomical", "cosmological", "zodiac"])}
    rows = []
    for rname, R in [("A: resid HL", RA), ("B: resid HL+quire", RB), ("raw (reference)", Y - Y.mean(0))]:
        for cname, m in contrasts.items():
            rows.append(dict(residual=rname, **L.residual_contrast(R, d, m, n_perm, name=cname)))
    rc = pd.DataFrame(rows)
    for rname in rc.residual.unique():
        mm = rc.residual == rname
        for col in ("p_F_hl_perm", "p_F_hl_drift", "p_ba_hl_perm", "p_ba_hl_drift"):
            rc.loc[mm, "holm_" + col[2:]] = L.holm(rc.loc[mm, col].values)
    rc["survives_both"] = (rc[["holm_F_hl_perm", "holm_F_hl_drift"]].max(axis=1) < .05)
    rc.to_csv(OUT / "residual_section_contrasts.csv", index=False)
    rd = L.residual_decomp(RA, d); rd.to_csv(OUT / "residual_decomposition_A.csv", index=False); S["residual_A_full_R2"] = rd.attrs["full_R2"]
    # image word sets on residuals
    tags = pd.read_csv(L.ROOT / "hypotheses" / "h09_image_context_cribs" / "data" / "visual_tags.csv").set_index("folio")
    d["large_root"] = np.where(d.page.map(tags.root_size).fillna(0) == 2, "yes", "no")
    I = []
    for rname, R in [("A: resid HL", RA), ("B: resid HL+quire", RB)]:
        for name, m, tgt, ws, lab in [("water: bio vs rest", sec != "zzz", "biological", WATER, "section"),
                                      ("star: stars vs rest", sec != "zzz", "stars", STAR, "section"),
                                      ("root/jar: pharma vs rest", sec != "zzz", "pharmaceutical", ROOT, "section"),
                                      ("root/jar: pharma vs herbal", sec.isin(["herbal", "pharmaceutical"]), "pharmaceutical", ROOT, "section"),
                                      ("root transfer: herbal large-root", sec == "herbal", "yes", TRANS, "large_root")]:
            I.append(dict(residual=rname, test=name, **L.wordset_residual(R, d, vocab, X, m, tgt, ws, lab, n_perm)))
    I = pd.DataFrame(I)
    for col in ("p_hl_perm", "p_hl_drift", "p_random_words"):
        I["holm_" + col[2:]] = L.holm(I[col].values)
    I.to_csv(OUT / "residual_image_wordsets.csv", index=False)
    # 3 hand features
    herb = q[q.section == "herbal"]
    cells = {"herbal 1A vs 2B (Q4-7)": (list(herb[(herb.HL == "1A") & herb.quire.isin(list("4567"))].page), list(herb[(herb.HL == "2B") & herb.quire.isin(list("4567"))].page)),
             "herbal 1A vs 2B (all)": (list(herb[herb.HL == "1A"].page), list(herb[herb.HL == "2B"].page)),
             "all 1A vs all 2B": (list(q[q.HL == "1A"].page), list(q[q.HL == "2B"].page)),
             "all 1A vs all 3B": (list(q[q.HL == "1A"].page), list(q[q.HL == "3B"].page))}
    F = []
    for cname, (A, B) in cells.items():
        for kind in ("word", "unit", "prefix", "suffix"):
            F.append(L.discriminate(bags, A, B, kind, n_boot=200 if kind == "word" else 300).assign(contrast=cname))
    pd.concat(F).to_csv(OUT / "hand_discriminating_features.csv", index=False)
    # orthography vs vocabulary
    G = []
    pairs = {"hand gap: herbal 1A vs herbal 2B": ("herbal 1A vs 2B (all)",),
             "hand gap: all 1A vs all 3B": ("all 1A vs all 3B",)}
    comp = {"hand gap: herbal 1A vs herbal 2B": cells["herbal 1A vs 2B (all)"],
            "hand gap: herbal 1A vs herbal 3B": (list(herb[herb.HL == "1A"].page), list(herb[herb.HL == "3B"].page)),
            "section gap: 1A herbal vs 1A pharma": (list(herb[herb.HL == "1A"].page), list(q[(q.HL == "1A") & (q.section == "pharmaceutical")].page)),
            "section gap: 2B herbal vs 2B biological": (list(herb[herb.HL == "2B"].page), list(q[(q.HL == "2B") & (q.section == "biological")].page)),
            "section gap: 3B herbal vs 3B stars": (list(herb[herb.HL == "3B"].page), list(q[(q.HL == "3B") & (q.section == "stars")].page)),
            "noise floor: 1A herbal split": None, "noise floor: 2B biological split": None}
    rng = np.random.default_rng(0)
    for name, ab in comp.items():
        for s in range(5):
            if ab is None:
                base = list(herb[herb.HL == "1A"].page) if "1A" in name else list(q[(q.HL == "2B") & (q.section == "biological")].page)
                base = list(rng.permutation(base)); ab = (base[: len(base) // 2], base[len(base) // 2:])
            G.append(dict(comparison=name, seed=s, **L.gap_closure(bags, ab[0], ab[1], seed=s)))
            if name.startswith("noise"): ab = None
    G = pd.DataFrame(G); G.to_csv(OUT / "rewrite_gap_closure.csv", index=False)
    S["gap_closure_summary"] = {f"{a}|{b}": v for (a, b), v in G.groupby("comparison")[["js_before", "js_after", "closed"]].agg(["mean", "std"]).round(4).to_dict().items()}
    json.dump(S, open(OUT / "summary.json", "w"), indent=1, default=float)
    return hm, S, rc, rd, I, G


if __name__ == "__main__":
    hm, S, rc, rd, I, G = main(int(sys.argv[1]) if len(sys.argv) > 1 else 2000)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 90)
    print(hm.round(4).to_string()); print({k: v for k, v in S.items() if k != "gap_closure_summary"})
    print(rc[["residual", "contrast", "pages", "ba", "chance", "ba_null_hl_perm", "F", "p_F_hl_perm", "p_F_hl_drift", "n_hl_drift", "p_ba_hl_perm", "holm_F_hl_perm", "holm_F_hl_drift", "survives_both"]].round(4).to_string())
    print(rd.round(4).to_string(), rd.attrs); print(I.round(4).to_string())
    print(G.groupby("comparison")[["js_before", "js_after", "closed"]].agg(["mean", "std"]).round(3).to_string())
    print(G[G.seed == 0][["comparison", "rules"]].to_string())
