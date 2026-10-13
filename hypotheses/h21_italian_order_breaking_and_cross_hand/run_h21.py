"""Run h21. python run_h21.py phase1 | phase2 ; then summarise.py"""
import json
import sys
from collections import Counter
from multiprocessing import Pool

import numpy as np

import h21_lib as L
from h21_lib import HERE, ROOT, L20
sys.path.insert(0, str(ROOT / "hypotheses" / "h20_generators_vs_italian"))
import run_h20 as R20  # noqa: E402
R20.R = HERE / "results"; R19 = R20.R19
NTOK = R19.NTOK
SRC = ["it_boccaccio", "it_cucina", "it_sidrach", "it_cennini"]
BASE = [("plain", 1, True, 0.0), ("syll", 1, True, 0.0), ("syll", 1, False, 0.5), ("syll", 4, False, 0.0), ("naibbe", 1, True, 0.0), ("naibbe", 1, False, 0.5)]
GRID = [("syll", K, s, r) for K in (2, 4, 8) for s in (False, True) for r in (0.0, 0.3, 0.7)]


def name(src, base, K, s, r):
    return f"A_{src[3:]}_{base}_K{K}_{'shuf' if s else 'noshuf'}_r{r}"


def a_cell(src, base, K, s, r, ctx):
    rng = np.random.default_rng(abs(hash((src, base, K, s, r))) % 2 ** 31 if False else 21 + 1000 * SRC.index(src) + 10 * K + 3 * s + int(10 * r))
    full = R20.italian(src); plain = full[: 2 * NTOK]
    nb = None
    if base == "naibbe":
        from msdecipher.mech_naibbe import NaibbeCipher
        nb = NaibbeCipher().encrypt(full, seed=0, n_words_out=2 * NTOK)
    lines, info = L.encode(plain, base, ctx["codes"], rng, K, s, r, ctx["nulls"], nb)
    cell = R20.lines_to_cell(lines, name(src, base, K, s, r)[2:], "ciph" if base != "plain" else "ctrl", "eva" if base != "plain" else "char")
    cell["fit"] = dict(src=src, base=base, K=K, shuf=s, r=r, **info); return cell


def ctx():
    seg = R19.seg_fn("eva"); ms = R19.ms_cells(); w2b = [w for p in ms["MS_2B"]["pages"] for w in p["words"]]
    c = Counter(w2b); nw = list(c); p = np.array([c[w] for w in nw], float); p /= p.sum()
    return dict(codes=L20.ms_codes(w2b, seg), nulls=(nw, p))


def b_cells():
    sys.path.insert(0, str(ROOT / "hypotheses" / "h12_per_hand_copy_modify")); import run_h12 as H12
    q, pw = H12.page_words(); out = {}
    hands = ["1A", "2B", "3B"]
    fits = {h: [h] for h in hands}; fits.update({"not" + h: [x for x in hands if x != h] for h in hands})
    for key, hs in fits.items():
        tw = H12.words_of(list(q[q.HL.isin(hs)].page), pw); m = H12.fit(tw, seed=0)
        for seed in ((21,) if len(hs) == 1 else (20, 21)):
            g = list(H12.generate(m, NTOK, seed=seed))[:NTOK]
            c = R19.paginate(g, f"c0{key}s{seed}", "synth", "eva"); c["fit"] = dict(train=hs, seed=seed, fit_distance=m["fit_distance"])
            out[f"B_C0_{key}_s{seed}"] = c
    return out


if __name__ == "__main__":
    phase = sys.argv[1]; cx = ctx(); cells = {}
    if phase == "phase1":
        cells.update(b_cells())
        for src in SRC:
            for b in BASE: cells[name(src, *b)] = a_cell(src, *b, cx)
        for g in GRID: cells.setdefault(name("it_boccaccio", *g), a_cell("it_boccaccio", *g, cx))
    else:
        best = json.load(open(HERE / "results" / "search_best.json"))
        for src in SRC[1:]:
            for g in best: cells[name(src, *g)] = a_cell(src, *g, cx)
    todo = [(n, c) for n, c in cells.items() if not (HERE / "results" / f"cell_{n}.json").exists()]
    R19.plain_lms()
    with Pool(7) as pool:
        for n in pool.imap_unordered(R20.run_cell, todo): print("done", n, flush=True)
