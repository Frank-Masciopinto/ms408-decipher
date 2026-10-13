"""Run h30: python run_h30.py -> results/measures.json"""
import json
import sys
from collections import Counter
from multiprocessing import Pool

import numpy as np

import h30_lib as L
from h30_lib import HERE
NPERM = 200


def z(obs, null): null = np.asarray(null); return float((obs - null.mean()) / (null.std() + 1e-12))


def analyse(name):
    lines = L.load_ms(name) if name in ("1A", "2B", "3B", "3A") else L.load_control(L.CONTROLS[name][0])
    rng = np.random.default_rng(30); CL = L.classes(lines); r = dict(text=name, n_lines=len(lines), n_tokens=sum(len(l["words"]) for l in lines))
    nw = np.array([len(l["words"]) for l in lines]); ng = np.array([sum(len(w) for w in l["words"]) for l in lines])
    mode = Counter(nw).most_common(1)[0]
    r["M1"] = dict(words_mean=float(nw.mean()), words_cv=float(nw.std() / nw.mean()), glyphs_mean=float(ng.mean()), glyphs_cv=float(ng.std() / ng.mean()), modal_len=int(mode[0]), modal_share=float(mode[1] / len(nw)),
                   hist={int(k): int(v) for k, v in sorted(Counter(nw).items())})
    r["M2"] = {}
    for c, cl in CL.items():
        obs = L.mi(L.pos_pairs(cl)); null = [L.mi(L.pos_pairs(L.permute_within(lines, cl, rng))) for _ in range(NPERM)]
        con = L.pos_contrib(cl); nc = [L.pos_contrib(L.permute_within(lines, cl, rng)) for _ in range(50)]
        exc = {b: con[b] - np.mean([x[b] for x in nc]) for b in con}; tot = sum(max(v, 0) for v in exc.values())
        r["M2"][c] = dict(obs=obs, null_mean=float(np.mean(null)), excess=float(obs - np.mean(null)), z=z(obs, null),
                          excess_by_bin={int(b): float(v) for b, v in exc.items()}, first_last_share=float((max(exc[0], 0) + max(exc[4], 0)) / tot) if tot > 0 else None)
    r["M3"] = {}
    for key, (a, b) in {"END>ONSET": ("END", "ONSET"), "TYPE>TYPE": ("TYPE", "TYPE")}.items():
        wi = L.mi([(x[i], y[i + 1]) for x, y in zip(CL[a], CL[b]) for i in range(len(x) - 1)])
        perm = []
        for _ in range(NPERM // 4):
            idx = [np.random.default_rng(int(rng.integers(1e9))).permutation(len(l)) for l in CL[a]]
            perm.append(L.mi([(x[j[i]], y[j[i + 1]]) for x, y, j in zip(CL[a], CL[b], idx) for i in range(len(x) - 1)]))
        ac = L.mi(L.across_pairs(lines, None, a_cl=CL[a], b_cl=CL[b]))
        an = [L.mi(L.across_pairs(lines, None, order=L.shuffle_order(lines, rng), a_cl=CL[a], b_cl=CL[b])) for _ in range(NPERM)]
        r["M3"][key] = dict(within=wi, within_null_inline_shuffle=float(np.mean(perm)), within_excess=float(wi - np.mean(perm)),
                            across=ac, across_null=float(np.mean(an)), across_excess=float(ac - np.mean(an)), across_z=z(ac, an))
    E = CL["END"]
    def rates(order):
        o = order; s1 = [E[x][-1] == E[y][-1] for x, y in zip(o, o[1:]) if lines[x]["page"] == lines[y]["page"]]
        s2 = [E[x][-1] == E[y][-1] for x, y in zip(o, o[2:]) if lines[x]["page"] == lines[y]["page"]]
        return float(np.mean(s1)) if s1 else np.nan, float(np.mean(s2)) if s2 else np.nan
    r1, r2 = rates(list(range(len(lines)))); nul = [rates(L.shuffle_order(lines, rng)) for _ in range(NPERM)]
    within = float(np.mean([l[i] == l[i + 1] for l in E for i in range(len(l) - 1)]))
    r["M4"] = dict(next_line=r1, line_plus2=r2, null_next=float(np.nanmean([x[0] for x in nul])), null_plus2=float(np.nanmean([x[1] for x in nul])),
                   z_next=z(r1, [x[0] for x in nul]), z_plus2=z(r2, [x[1] for x in nul]), within_adjacent=within)
    pf = np.array([l["para_first"] for l in lines]); on = [c[0] for c in CL["ONSET"]]
    def jsd(lab): return L.js(Counter(o for o, f in zip(on, lab) if f), Counter(o for o, f in zip(on, lab) if not f))
    obs = jsd(pf); null = []
    for _ in range(NPERM):
        lab = pf.copy(); by = {}
        for i, l in enumerate(lines): by.setdefault(l["stratum"], []).append(i)
        for ii in by.values(): lab[ii] = rng.permutation(lab[ii])
        null.append(jsd(lab))
    r["M5"] = dict(n_para_first=int(pf.sum()), len_first=float(nw[pf].mean()) if pf.any() else None, len_other=float(nw[~pf].mean()), onset_js=obs, onset_js_null=float(np.mean(null)), z=z(obs, null),
                   onset_first_top=dict(Counter(o for o, f in zip(on, pf) if f).most_common(5)), onset_other_top=dict(Counter(o for o, f in zip(on, pf) if not f).most_common(5)))
    # M6 held-out
    T = CL["TYPE"]; V = 31
    if name in ("1A", "2B", "3B", "3A") and len({l["quire"] for l in lines}) >= 5:
        qs = sorted({l["quire"] for l in lines}, key=lambda q: (len(q), q)); fold_of = {q: i % 5 for i, q in enumerate(qs)}; f = [fold_of[l["quire"]] for l in lines]
    else:
        f = [min(4, i * 5 // len(lines)) for i in range(len(lines))]
    res = []
    for k in range(5):
        tr = [t for t, ff in zip(T, f) if ff != k]; te = [t for t, ff in zip(T, f) if ff == k]
        if te and tr: res.append((L.model_bits(tr, te, V), sum(map(len, te))))
    w = np.array([n for _, n in res], float)
    r["M6"] = {m: float(np.average([b[m] for b, _ in res], weights=w)) for m in res[0][0]}
    r["M6"].update({f"gain_{m}": r["M6"]["bag"] - r["M6"][m] for m in ("positional", "bigram", "hmm")})
    json.dump(r, open(HERE / "results" / f"m_{name}.json", "w"), indent=1, default=float)
    return name


if __name__ == "__main__":
    names = sys.argv[1:] or ["1A", "2B", "3B", "3A"] + list(L.CONTROLS)
    with Pool(6) as p:
        for n in p.imap_unordered(analyse, names): print("done", n, flush=True)
