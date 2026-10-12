"""Run h17 tests (PREREG.md) and write results/."""
import json
import numpy as np
import pandas as pd
import h17_lib as L

N = 10000


def main():
    C = L.load(); R = L.HERE / "results"; R.mkdir(exist_ok=True)
    ids = L.id_summary(C); ids.to_csv(R / "plant_id_consensus.csv", index=False)
    tabA, obsA, resA = L.test_A(C, N); tabA.to_csv(R / "A_pairs.csv", index=False)
    B = []
    for lvl in ("genus", "family"):
        for mc in (1, 2):
            B.append(dict(L.test_B(C, lvl, mc, N), null="HL"))
        B.append(dict(L.test_B(C, lvl, 1, N, by_quire=True), null="quireHL"))
        B.append(dict(L.test_B(C, lvl, 2, N, merge_elv=True), null="HL_ELVmerged"))
    tabC, combC = L.test_C(C, N); tabC.to_csv(R / "C_bax_cribs.csv", index=False)
    tabC2, combC2 = L.test_C(C, N, exclude=("Sherwood_Bax",)); tabC2.to_csv(R / "C_bax_cribs_noBaxIDs.csv", index=False)
    # crib-agnostic control: every k-initial paragraph-initial word of a family-ID'd folio used as a pseudo-crib
    ctrl = L.control_C(C, 2000); dropm = L.test_C_drop_mutual(C, N)
    prim = [("A_" + m, resA["quireHL"]["p"][i]) for i, m in enumerate(("S1", "S2", "S3"))]
    for b in B:
        if b["null"] == "HL" and b["min_cons"] == 1:
            prim += [(f"B_{b['level']}_" + m, b["p"][i]) for i, m in enumerate(("F1", "F2", "F3"))]
    prim += [("C_" + k, v["p"]) for k, v in combC.items()]
    adj = L.holm([p for _, p in prim])
    out = dict(
        A=dict(n_pairs=len(tabA), obs=obsA.tolist(), **{k: dict(null_mean=v["null_mean"].tolist(), p=v["p"].tolist()) for k, v in resA.items()}),
        B=[{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in b.items()} for b in B],
        C=combC, C_without_Bax_IDs=combC2, C_control_all_k_initial=ctrl, C_drop_crib_folios=dropm, primary=[dict(test=t, p=p, holm=float(a)) for (t, p), a in zip(prim, adj)],
        n_id_folios=int(len(ids)), n_consensus2=int((ids.consensus >= 2).sum()), n_consensus3=int((ids.consensus >= 3).sum()))
    (R / "summary.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float)); print(tabA.drop(columns=["shared"]).to_string()); print(tabC.to_string()); print(tabC2.to_string()); print(ctrl)


if __name__ == "__main__":
    main()
