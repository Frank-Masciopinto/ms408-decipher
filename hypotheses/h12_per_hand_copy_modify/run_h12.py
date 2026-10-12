"""h12: per-hand copy-modify generators (see PREREG.md)."""
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h11_hand_language_model")); sys.path.insert(0, str(ROOT / "src"))
import h11_lib as L  # noqa: E402
from msdecipher import mech_hybrid as H, mech_hybrid_run as MR  # noqa: E402
from msdecipher.quires import group_folds, load_quires  # noqa: E402

OUT = HERE / "results"
C0 = "C0 control: grammar innovations + copy-modify (no plaintext)"
CELLS = ["1A", "2B", "3B", "4"]
KEY = ["unit_h2", "mean_word_length_units", "zipf_mle_s_r10_1000", "heaps_beta_in_order"]
GEN_SEEDS = (101, 102, 103)
N_RANDOM, N_LOCAL = 60, 10


def page_words():
    q, _ = L.load(); lo = L.H10.H9.parse(); P = lo[lo.gtype.isin(["P", "C", "R"])]
    pw = {}
    for r in P.itertuples():
        pw.setdefault(r.folio, []).extend(r.words)
    q = q[q.page.isin(pw)].sort_values("order").reset_index(drop=True)
    return q, pw


def words_of(pages, pw):
    return [w for p in pages for w in pw[p]]


def fit(train_words, seed=0):
    t = time.time(); ctx = MR.Ctx(train_words)
    best, df, info = MR.fit_variant(C0, train_words, ctx, seed=seed, n_random=N_RANDOM, n_local=N_LOCAL, log=lambda *a: None)
    return dict(ctx=ctx, params=best, fit_distance=float(df.distance.iloc[0]), secs=time.time() - t)


def generate(model, n, seed):
    enc = MR.make_encoder("grammar", [], seed, model["ctx"])
    return H.generate(enc, model["params"], n, seed)


def top_js(gen, real, top=100):
    rc = Counter(real); tw = [w for w, _ in rc.most_common(top)]; gc = Counter(gen)
    a = np.array([rc[w] for w in tw] + [len(real) - sum(rc[w] for w in tw)], float); b = np.array([gc[w] for w in tw] + [len(gen) - sum(gc[w] for w in tw)], float)
    a /= a.sum(); b /= b.sum(); m = (a + b) / 2
    f = lambda u: np.sum(u[u > 0] * np.log2(u[u > 0] / m[u > 0]))
    return float(0.5 * f(a) + 0.5 * f(b))


def score(gens, test, ref, sc):
    ms = [MR.fit_vector(g, 1) for g in gens]; m = {k: float(np.mean([x[k] for x in ms])) for k in ms[0]}
    z = MR.zvec(m, ref, sc)
    out = {f"absz_{k}": abs(z[k]) for k in KEY}; out["rms_z"] = float(np.sqrt(np.mean([v * v for v in z.values()])))
    out["top_js"] = float(np.mean([top_js(g, test) for g in gens])); out.update({f"gen_{k}": m[k] for k in KEY})
    return out


def main():
    q, pw = page_words(); Q = load_quires(); rng = random.Random(0)
    rows, params = [], []
    for level in ("bifolium", "quire"):
        cells = [c for c in CELLS if level == "bifolium" or q[q.HL == c].quire.nunique() >= 3]
        folds = {}
        for c in cells:
            pg = list(q[q.HL == c].page); f = group_folds(pg, Q, k=3, level=level, seed=0)
            folds[c] = [([pg[i] for i in sorted(tr)], [pg[i] for i in sorted(te)]) for tr, te in f]
        for k in range(3):
            own = {}
            cells_all = cells
            cells = [c for c in cells_all if len(folds[c]) > k]
            for c in cells:
                own[c] = fit(words_of(folds[c][k][0], pw), seed=k)
                params.append(dict(level=level, fold=k, cell=c, model="OWN", fit_distance=own[c]["fit_distance"], secs=own[c]["secs"], **own[c]["params"].as_dict()))
            pooled_pages = sorted(set().union(*[folds[c][k][0] for c in cells]), key=lambda p: int(q.set_index("page").order[p]))
            pooled = fit(words_of(pooled_pages, pw), seed=k)
            params.append(dict(level=level, fold=k, cell="all", model="POOLED", fit_distance=pooled["fit_distance"], secs=pooled["secs"], **pooled["params"].as_dict()))
            all_train = [p for p in pooled_pages]
            for c in cells:
                train, test_pages = folds[c][k]; test = words_of(test_pages, pw); n = len(test)
                if n < 200: continue
                ref = MR.fit_vector(test); sc = MR.scales(ref, MR.jackknife_se(test, g=min(8, max(3, len(test_pages)))))
                # SHUF: random pages from all cells' training pools with the same token count
                ntr = len(words_of(train, pw)); sh = rng.sample(all_train, len(all_train)); pick, t = [], 0
                for p in sh:
                    if t >= ntr: break
                    pick.append(p); t += len(pw[p])
                pick.sort(key=lambda p: int(q.set_index("page").order[p])); shuf = fit(words_of(pick, pw), seed=k)
                models = {"OWN": own[c], "POOLED": pooled, "SHUF": shuf, **{f"CROSS from {d}": own[d] for d in cells if d != c}}
                for name, mdl in models.items():
                    gens = [generate(mdl, n, s) for s in GEN_SEEDS]
                    rows.append(dict(level=level, fold=k, cell=c, model=name, test_tokens=n, **score(gens, test, ref, sc)))
                    if name.startswith("CROSS") and {c, name[-2:]} == {"1A", "2B"}:
                        d = name[-2:]
                        rules = L.greedy_rules(Counter(words_of(folds[d][k][0], pw)), Counter(words_of(train, pw)), 10)
                        mg = [[_rw(w, rules) for w in g] for g in gens]
                        rows.append(dict(level=level, fold=k, cell=c, model=f"MAPPED from {d}", test_tokens=n, n_rules=len(rules),
                                         rules=" ; ".join(f"{a}:{s}->{t or '∅'}" for a, s, t in rules), **score(mg, test, ref, sc)))
                print(level, k, c, "done", flush=True)
                pd.DataFrame(rows).to_csv(OUT / "scores.csv", index=False); pd.DataFrame(params).to_csv(OUT / "fitted_params.csv", index=False)
            cells = cells_all
    return pd.DataFrame(rows), pd.DataFrame(params)


def _rw(w, rules):
    for r in rules: w = L.apply_rule(w, r)
    return w


if __name__ == "__main__":
    t = time.time(); s, p = main(); print("total", time.time() - t)
