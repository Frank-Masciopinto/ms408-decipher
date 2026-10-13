"""Run h22. python run_h22.py phase1 | phase2 ; then summarise.py"""
import json
import sys
from multiprocessing import Pool

import numpy as np

import h22_lib as L
from h22_lib import HERE, ROOT
sys.path.insert(0, str(ROOT / "hypotheses" / "h21_italian_order_breaking_and_cross_hand"))
import run_h21 as R21  # noqa: E402
R20 = R21.R20; R20.R = HERE / "results"; R19 = R20.R19; NTOK = R19.NTOK
SRC = R21.SRC
BASES = {"naibbe": ("naibbe", False, 0.0), "naibbeNull": ("naibbe", False, 0.5), "syllNull": ("syll", False, 0.5), "naibbeShuf": ("naibbe", True, 0.0)}
CS, WS = (0.05, 0.10, 0.20, 0.30), (5, 20)
_NB = {}


def name(src, b, c, W, nulls="clean"):
    return f"A_{src[3:]}_{b}_c{c}_W{W}_{nulls}"


def a_cell(src, b, c, W, nulls, cx):
    base, shuf, r = BASES[b]; seed = 22 + 1000 * SRC.index(src) + list(BASES).index(b)   # same base/null draws across (c, W)
    rng = np.random.default_rng(seed); full = R20.italian(src); plain = full[: 2 * NTOK]; nb = None
    if base == "naibbe":
        from msdecipher.mech_naibbe import NaibbeCipher
        nb = NaibbeCipher().encrypt(full, seed=0, n_words_out=2 * NTOK)
    lines, labs, info = L.build(plain, base, cx["codes"], nb, rng, shuf, r, nulls, cx["nulls"], c, W, seed=seed + int(100 * c) + W)
    flat = [w for l in lines for w in l][:NTOK]
    info["signal_share"] = sum(x is not None for x in labs[:NTOK]) / NTOK
    rec = L.plaintext_recovery(flat, labs[:NTOK]) if base == "syll" else {}
    cell = R20.lines_to_cell(lines, name(src, b, c, W, nulls)[2:], "ciph", "eva")
    cell["fit"] = dict(src=src, base=b, c=c, W=W, nulls=nulls, **info, **rec); return cell


def b_cells(seeds=(22, 23, 24)):
    sys.path.insert(0, str(ROOT / "hypotheses" / "h12_per_hand_copy_modify")); import run_h12 as H12
    q, pw = H12.page_words(); out = {}; hands = ["1A", "2B", "3B"]
    fits = {h: [h] for h in hands}; fits.update({"not" + h: [x for x in hands if x != h] for h in hands})
    for key, hs in fits.items():
        m = H12.fit(H12.words_of(list(q[q.HL.isin(hs)].page), pw), seed=0)
        for s in seeds:
            g = list(H12.generate(m, NTOK, seed=s))[:NTOK]
            c = R19.paginate(g, f"c0{key}s{s}", "synth", "eva"); c["fit"] = dict(train=hs, seed=s, fit_distance=m["fit_distance"])
            out[f"B_C0_{key}_s{s}"] = c
    return out


def phase1_names():
    out = []
    for b in BASES:
        out.append(("it_boccaccio", b, 0.0, 5, "clean"))
        for c in CS:
            for W in WS:
                out.append(("it_boccaccio", b, c, W, "clean"))
                if BASES[b][2] > 0: out.append(("it_boccaccio", b, c, W, "leaky"))
    return out


if __name__ == "__main__":
    cx = R21.ctx(); cells = {}
    if sys.argv[1] == "phase1":
        cells.update(b_cells())
        for a in phase1_names(): cells[name(*a)] = a_cell(*a, cx)
    else:
        for b, c, W in json.load(open(HERE / "results" / "search_best.json")):
            for src in SRC[1:]: cells[name(src, b, c, W)] = a_cell(src, b, c, W, "clean", cx)
    todo = [(n, c) for n, c in cells.items() if not (HERE / "results" / f"cell_{n}.json").exists()]
    print("todo", len(todo), flush=True); R19.plain_lms()
    with Pool(7) as pool:
        for n in pool.imap_unordered(R20.run_cell, todo): print("done", n, flush=True)
