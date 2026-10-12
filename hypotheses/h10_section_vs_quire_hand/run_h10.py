import json
import numpy as np
import pandas as pd
import h10_lib as L

OUT = L.HERE / "results"


def main(n_perm=2000):
    q, bags = L.load(); S = q.section; h = q.hand; lg = q.lang; Q = q.quire
    C = {
        "S1 Q15 h1A herbal vs pharma": (q.stratum == "Q15|h1|A"), "S2 Q10 h4 cosmo vs zodiac": (q.stratum == "Q10|h4|?"),
        "S3 Q9 h4 astro vs cosmo": (q.stratum == "Q9|h4|?"), "S4 Q14 h2B cosmo vs text-only": (q.stratum == "Q14|h2|B"),
        "S5 pooled S1-S4": q.stratum.isin(["Q15|h1|A", "Q10|h4|?", "Q9|h4|?", "Q14|h2|B"]),
    }
    rows = []
    for k, m in C.items():
        rows.append({"block": "S", **L.contrast(q, bags, m, "section", "stratum", n_perm, name=k)})
    H = {"H1 hand1A herbal vs pharma": (h == "1") & (lg == "A") & S.isin(["herbal", "pharmaceutical"]),
         "H2 hand2B herbal/bio/cosmo": (h == "2") & (lg == "B") & S.isin(["herbal", "biological", "cosmological"]),
         "H3 hand3B herbal vs stars": (h == "3") & (lg == "B") & S.isin(["herbal", "stars"]),
         "H4 hand4 astro/cosmo/zodiac": (h == "4") & S.isin(["astronomical", "cosmological", "zodiac"])}
    q["hl"] = q.hand + "|" + q.lang
    for k, m in H.items():
        rows.append({"block": "H", **L.contrast(q, bags, m, "section", "hl", n_perm, name=k)})
    q["hand_lang"] = q.hand + q.lang
    R = {"R1 herbal Q4-7 hand1A vs hand2B": (S == "herbal") & Q.isin(["4", "5", "6", "7"]) & q.hand_lang.isin(["1A", "2B"]),
         "R2 herbal Q6 hand1 vs hand5": (S == "herbal") & (Q == "6") & h.isin(["1", "5"]),
         "R3 herbal Q17 hand1A vs hand3B": (S == "herbal") & (Q == "17"),
         "R4 pharma Q15 vs Q19 (hand1A)": (S == "pharmaceutical"),
         "R5 herbal hand1A Q1-Q7": (S == "herbal") & (q.hand_lang == "1A") & Q.isin(list("1234567"))}
    q["sec_only"] = q.section; q["all"] = "all"; q["quire_s"] = "Q" + q.quire
    for k, m in R.items():
        lab = "quire_s" if k.startswith(("R4", "R5")) else "hand_lang"
        strata = "quire_s" if k.startswith(("R1", "R2", "R3")) else "sec_only"
        rows.append({"block": "R", **L.contrast(q, bags, m, lab, strata, n_perm, name=k)})
    df = pd.DataFrame(rows)
    for b in "SHR":
        for nn in ("perm", "drift"):
            for st in ("js", "ba"):
                m = (df.block == b) & ~df.contrast.str.startswith("S5")
                df.loc[m, f"holm_{st}_{nn}"] = L.H9.holm(df.loc[m, f"p_{st}_{nn}"].values)
    df["survives"] = (df.filter(like="holm_js_").max(axis=1) < .05) | (df.filter(like="holm_ba_").max(axis=1) < .05)
    df.to_csv(OUT / "contrasts.csv", index=False)
    V = L.decompose(q, bags, n_perm=499); V.to_csv(OUT / "variance_decomposition.csv", index=False)
    vinfo = dict(V.attrs)
    # I: h09 rechecks
    I = []
    water = "qol olkedy qokain qoteedy qokedy".split(); root = "ctheol ckhey qoor qokeody qockhey qokeol okeol".split()
    star = "cheeo lkaiin oteey al oteedy".split()
    tr = "chody ckhey oldy qockhey okeeey qokey sol aiin qokol okal".split()
    spec = [("I1 water words: bio vs herbal, hand2B", (h == "2") & (lg == "B") & S.isin(["herbal", "biological"]), "biological", water, "hl"),
            ("I1b water words: bio vs herbal, any hand (confounded ref)", S.isin(["herbal", "biological"]), "biological", water, "all"),
            ("I2 root/jar words: pharma vs herbal, Q15 h1A", q.stratum == "Q15|h1|A", "pharmaceutical", root, "stratum"),
            ("I2b root/jar words: pharma vs herbal, hand1A", (q.hand_lang == "1A") & S.isin(["herbal", "pharmaceutical"]), "pharmaceutical", root, "hl"),
            ("I3 star words: stars vs herbal, hand3B", (h == "3") & (lg == "B") & S.isin(["herbal", "stars"]), "stars", star, "hl")]
    for name, m, tgt, ws, stc in spec:
        I.append(dict(test=name, **L.wordset_contrast(q, bags, m, "section", tgt, ws, n_perm, strata_col=stc)))
    # I4 root transfer restricted to hand1A herbal; target = large-root tag
    tags = pd.read_csv(L.ROOT / "hypotheses" / "h09_image_context_cribs" / "data" / "visual_tags.csv").set_index("folio")
    q["large_root"] = np.where(q.page.map(tags.root_size).fillna(0) == 2, "yes", "no")
    for name, m in [("I4 root transfer, herbal hand1A", (S == "herbal") & (q.hand_lang == "1A")),
                    ("I4b root transfer, herbal hand2B", (S == "herbal") & (q.hand_lang == "2B")),
                    ("I4c root transfer, all herbal (h09 replication)", (S == "herbal"))]:
        I.append(dict(test=name, **L.wordset_contrast(q, bags, m, "large_root", "yes", tr, n_perm, strata_col="quire_s")))
    I = pd.DataFrame(I); I["holm_label_perm"] = L.H9.holm(I.p_label_perm); I["holm_random_words"] = L.H9.holm(I.p_random_words)
    I.to_csv(OUT / "h09_rechecks.csv", index=False)
    json.dump(dict(variance=vinfo), open(OUT / "summary.json", "w"), indent=1, default=float)
    return df, V, vinfo, I


if __name__ == "__main__":
    import sys
    df, V, vinfo, I = main(int(sys.argv[1]) if len(sys.argv) > 1 else 2000)
    pd.set_option("display.width", 250)
    print(df[["contrast", "classes", "ba", "ba_ci", "js", "js_excess_perm", "js_excess_drift", "p_js_perm", "p_js_drift", "p_ba_perm", "p_ba_drift", "n_drift", "holm_js_perm", "holm_js_drift", "survives"]].round(4).to_string())
    print(V.round(4).to_string(), vinfo); print(I.round(4).to_string())
