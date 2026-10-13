"""Run h31 (PREREG.md): python run_h31.py [cell ...] -> results/cell_<name>.json"""
import json
import sys
from collections import Counter
from multiprocessing import Pool

import numpy as np

import h31_lib as L
from corpora import build

R = L.HERE / "results"


def folds(pages, k=5):
    if pages[0]["id"].startswith("f"):
        g = sorted({p["bif"] for p in pages}); rng = np.random.default_rng(31); rng.shuffle(g)
        lab = {b: i % k for i, b in enumerate(g)}; return [lab[p["bif"]] for p in pages]
    n = len(pages); return [min(k - 1, i * k // n) for i in range(n)]


def heldout(pages):
    import h19_lib as H19
    fl = folds(pages); res = {m: [] for m in ("CharLM", "M1", "M2", "M3")}
    for f in sorted(set(fl)):
        tr = [w for p, x in zip(pages, fl) if x != f for w in p["words"]]; te = [w for p, x in zip(pages, fl) if x == f for w in p["words"]]
        G = H19.CharLM(4).fit(tr); res["CharLM"] += [G.logp(w) for w in te]
        ty = Counter(tr)
        _, mm = L.seg_morfessor(ty); f1 = lambda w: mm.viterbi_segment(w)[0]
        _, bb = L.seg_bayes(ty, sweeps=100); f2 = lambda w: [x for x in bb.segment(w) if x]
        for key, fn in (("M1", f1), ("M2", f2)):
            lm = L.MorphLM(tr, fn); res[key] += [lm.logp(w) for w in te]
        _, am = L.seg_affix(ty); res["M3"] += list(am.logprob2([tuple(w) for w in te]))
    return {k: float(-np.mean(np.maximum(v, -60))) for k, v in res.items()} | {"n_test": len(res["CharLM"])}


def run(name):
    out = R / f"cell_{name}.json"
    if out.exists(): return name
    C = build()[name]; pages = [p["words"] for p in C["pages"]]; toks = [w for p in pages for w in p]
    ty = Counter(toks); rng = np.random.default_rng(0); res = dict(cell=name, n_tokens=len(toks))
    segs = {"M1": L.seg_morfessor(ty)[0], "M2": L.seg_bayes(ty)[0], "M3": L.seg_affix(ty)[0]}
    for k, s in segs.items():
        res[k] = L.metrics(toks, pages, s, rng)
        top = Counter(s[w][1] for w in toks).most_common(15); res[k]["top_suffixes"] = top
        res[k]["examples"] = {w: s[w][2] for w, _ in ty.most_common(12)}
    res["heldout_bits_per_word"] = heldout(C["pages"])
    out.write_text(json.dumps(res, indent=1, default=float, ensure_ascii=False)); return name


if __name__ == "__main__":
    names = sys.argv[1:] or list(build())
    with Pool(min(8, len(names))) as p:
        for n in p.imap_unordered(run, names): print("done", n, flush=True)
