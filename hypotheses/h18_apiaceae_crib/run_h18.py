import json
import numpy as np
import h18_lib as L

N = 10000


def main():
    C, pool, toks, prim, novat = L.load(); R = L.HERE / "results"; R.mkdir(exist_ok=True)
    M = L.outcomes(C, pool, toks, L.in_shape); G = L.strata(C, pool); G2 = L.strata(C, pool, False)
    res, prims = {}, []
    for nm, S in (("primary", prim), ("noVatne", novat)):
        flag = np.array([f in S for f in pool])
        o, nm_, p = L.perm_test(M, flag, G, N); o2, nm2, p2 = L.perm_test(M, flag, G2, N)
        inf = sum(1 for f in S if G.count(G[pool.index(f)]) > 1 and sum(1 for g, ff in zip(G, pool) if g == G[pool.index(f)] and ff not in S) > 0)
        res[nm] = dict(folios=S, informative_in_quireHL=inf, obs=o.tolist(), null_quireHL=nm_.tolist(), p_quireHL=p.tolist(), null_HL=nm2.tolist(), p_HL=p2.tolist(),
                       words={f: dict(first=C["first"][f], para=C["para"].get(f, []), hits=[w for w in toks.get(f, []) if L.in_shape(w)]) for f in S})
        prims += [(f"{nm}_O{i+1}", p[i]) for i in range(3)]
    adj = L.H17.holm([p for _, p in prims])
    base, cands = L.calib_shapes(C, pool, toks)
    flagN = np.array([f in novat for f in pool]); flagP = np.array([f in prim for f in pool])
    cal = {"noVatne": [], "primary": []}
    for x, y, r in cands:
        Mx = L.outcomes(C, pool, toks, L.regex_shape(x, y))
        cal["noVatne"].append(L.perm_test(Mx, flagN, G, 2000)[2].tolist()); cal["primary"].append(L.perm_test(Mx, flagP, G, 2000)[2].tolist())
    pct = {k: [float(np.mean(np.array(v)[:, i] <= res[k]["p_quireHL"][i])) for i in range(3)] for k, v in cal.items()}
    pool_rate = M.mean(0).tolist()
    out = dict(pool_n=len(pool), shape_token_rate=base, pool_mean=pool_rate, res=res, n_calib=len(cands), calib_percentile_of_shape_p=pct,
               calib_frac_p05={k: np.mean(np.array(v) < 0.05, 0).tolist() for k, v in cal.items()},
               primary=[dict(test=t, p=float(p), holm=float(a)) for (t, p), a in zip(prims, adj)])
    (R / "summary.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
