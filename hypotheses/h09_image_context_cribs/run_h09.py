"""Run all h09 tests; writes results/*.csv and results/summary.json."""
import json
import numpy as np
import pandas as pd
import h09_lib as H

OUT = H.HERE / "results"; OUT.mkdir(exist_ok=True)
NP = 2000


def main():
    lo = H.parse(); q = H.load_quires().set_index("page")
    tags = pd.read_csv(H.HERE / "data" / "visual_tags.csv"); S = H.tag_scores(tags)
    summ = {}
    # 1 label-object
    L = H.label_table(lo); L.drop(columns="words").to_csv(OUT / "labels.csv", index=False)
    prof = H.per_type_profile(L); prof.to_csv(OUT / "label_type_profile.csv", index=False)
    t1 = H.test_label_objects(L, NP); t1.to_csv(OUT / "t1_label_object_sharing.csv", index=False)
    # same within pharma only (jar vs plant part) and bio only (nymph vs tube)
    sub = []
    for name, objs in [("pharma_jar_vs_part", ["jar", "plant_part"]), ("bio_nymph_vs_tube", ["nymph", "tube_tub"])]:
        d = H.test_label_objects(L[L.obj.isin(objs)].reset_index(drop=True), NP); d["subset"] = name; sub.append(d)
    pd.concat(sub).to_csv(OUT / "t1b_within_section.csv", index=False)
    summ["t1"] = t1.to_dict("records"); summ["t1b"] = pd.concat(sub).to_dict("records")
    # 2 same plant
    t2 = H.test_same_plant(lo, H.same_plant_pairs()); t2.to_csv(OUT / "t2_same_plant_pairs.csv", index=False)
    summ["t2"] = dict(n_pairs=len(t2), mean_rank_pct=t2.attrs.get("mean_rank_pct"), p=t2.attrs.get("p"))
    # 3 label in own-page text
    r3, by3 = H.test_label_in_text(L, lo, NP); by3.to_csv(OUT / "t3_label_in_text_by_type.csv"); summ["t3"] = r3
    # 4 enrichment
    folios, vocab, M, n = H.rate_matrix(lo, [f for f in tags.folio if f in q.index])
    grp = np.array([q.quire[f] for f in folios]); sec = np.array([q.section[f] for f in folios])
    enr = {}
    for tag in ["water", "star", "root", "jar", "nymph"]:
        for null, g in [("within_quire", grp), ("global", np.zeros(len(folios)))]:
            d = H.enrichment(folios, vocab, M, n, S[tag], g, NP); d.to_csv(OUT / f"t4_enrich_{tag}_{null}.csv", index=False)
            enr[(tag, null)] = d
    summ["t4"] = {f"{t}|{nl}": dict(n_words=len(d), n_p05=int((d.p < .05).sum()), n_holm05=int((d.p_holm < .05).sum()),
                                     expected_p05=round(.05 * len(d), 1), top=d.head(8)[["word", "r", "p", "p_holm", "rate_ratio", "count"]].round(4).to_dict("records"))
                  for (t, nl), d in enr.items()}
    # random tag sets: how many Holm-significant words would a random tag vector (shuffled across all pages) give?
    rng = np.random.default_rng(1); rnd = []
    for k in range(20):
        fake = pd.Series(rng.permutation(S["water"].reindex(folios).fillna(0).values), index=folios)
        d = H.enrichment(folios, vocab, M, n, fake, np.zeros(len(folios)), 500, seed=k)
        rnd.append(int((d.p_holm < .05).sum()))
    summ["t4_random_tag_global_holm05"] = rnd
    # quire-block null: tag values assigned per quire (quire means permuted across quires) -> section-like random tags
    qb = {}
    for tag in ["water", "star", "root", "jar", "nymph"]:
        v = S[tag].reindex(folios).fillna(0); qm = v.groupby(grp).mean(); cnt = []
        for k in range(30):
            perm = dict(zip(qm.index, rng.permutation(qm.values)))
            fake = pd.Series([perm[g] for g in grp], index=folios)
            if fake.std() == 0: continue
            d = H.enrichment(folios, vocab, M, n, fake, np.zeros(len(folios)), 500, seed=k); cnt.append(int((d.p_holm < .05).sum()))
        qb[tag] = dict(observed_global_holm05=int((enr[(tag, "global")].p_holm < .05).sum()), quire_block_null=cnt,
                       frac_null_ge_obs=float(np.mean([c >= (enr[(tag, "global")].p_holm < .05).sum() for c in cnt])))
    summ["t4_quire_block_null"] = qb
    # 5 transfer: candidates selected inside one section, tested on herbal tags
    res5 = {}
    def sel(section, tag, k=10):
        m = sec == section
        d = H.enrichment([f for f, x in zip(folios, m) if x], vocab, M[m], n[m], S[tag], grp[m], 500)
        d = d[d["count"] >= 5]; return list(d.sort_values("r", ascending=False).head(k).word), d
    herb = sec == "herbal"; hf = [f for f, x in zip(folios, herb) if x]
    for cname, (section, tag) in {"water_from_bio": ("biological", "water"), "root_from_pharma": ("pharmaceutical", "root"),
                                  "jar_from_pharma": ("pharmaceutical", "jar"), "star_from_stars": ("stars", "star")}.items():
        cand, dsel = sel(section, tag); dsel.to_csv(OUT / f"t5_select_{cname}.csv", index=False)
        for target in ["large_root", "blue_flower"]:
            mask = S[target].reindex(hf).fillna(0).values > 0
            r = H.transfer(hf, vocab, M[herb], n[herb], cand, mask, grp[herb]); r["candidates"] = " ".join(cand)
            res5[f"{cname}->herbal_{target}"] = r
    # robustness of the one positive transfer: k and Currier-language stratification
    rob = {}
    lang = np.array([q.currier_language[f] for f in hf])
    for k in (5, 10, 20, 30):
        cand, _ = sel("pharmaceutical", "root", k)
        mask = S["large_root"].reindex(hf).fillna(0).values > 0
        rob[f"k={k}"] = H.transfer(hf, vocab, M[herb], n[herb], cand, mask, grp[herb])
        for L_ in ("A", "B"):
            mm = lang == L_
            if mask[mm].sum() >= 3:
                rob[f"k={k}|lang={L_}"] = H.transfer([f for f, x in zip(hf, mm) if x], vocab, M[herb][mm], n[herb][mm], cand, mask[mm], grp[herb][mm])
    summ["t5_root_robustness"] = rob
    summ["t5"] = res5
    # 6 speculative star-word structure check
    star_labels = L[L.obj == "star"].w
    top_star = enr[("star", "within_quire")].head(5).word.tolist()
    cands = list(dict.fromkeys(top_star + star_labels.value_counts().head(5).index.tolist()))
    rows = []
    for c in cands:
        sc = {lang: H.struct_score(v, c) for lang, v in H.STAR.items()}
        nulls = [H.struct_score(v, c) for lst in H.NULL_CONCEPTS.values() for v in lst]
        rows.append(dict(word=c, star_mean=np.mean(list(sc.values())), null_mean=np.mean(nulls),
                         p=(1 + sum(x >= np.mean(list(sc.values())) for x in [np.mean(rng.choice(nulls, len(sc))) for _ in range(2000)])) / 2001, **sc))
    # how many Voynich word types match each 'star' pattern at all (baseline hit rate)
    types = sorted({w for ws in lo.words for w in ws})
    base = {lang: float(np.mean([H.struct_score(v, w) == 1.0 for w in types])) for lang, v in H.STAR.items()}
    summ["t6_pattern_base_rate"] = base
    t6 = pd.DataFrame(rows); t6.to_csv(OUT / "t6_speculative_star_words.csv", index=False); summ["t6"] = t6.round(3).to_dict("records")
    json.dump(summ, open(OUT / "summary.json", "w"), indent=1, default=str)
    return summ


if __name__ == "__main__":
    s = main()
    print(pd.DataFrame(s["t1"]).round(4).to_string()); print(pd.DataFrame(s["t1b"])[["subset","null","feature","obs","z","p","p_holm"]].round(4).to_string())
    for k in ("t2", "t3", "t5_root_robustness", "t4_quire_block_null", "t6_pattern_base_rate"): print(k, json.dumps(s[k], default=str, indent=0))
    print(pd.DataFrame(s["t6"]).to_string())
    for k, v in s["t4"].items():
        print(k, v["n_p05"], v["expected_p05"], v["n_holm05"], [(t["word"], round(t["r"], 2), round(t["rate_ratio"],1), "%.2g" % t["p_holm"]) for t in v["top"][:5]])
