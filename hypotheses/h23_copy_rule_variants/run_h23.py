"""Run h23. python run_h23.py phase1 | phase2 ; then summarise.py"""
import json
import sys
from multiprocessing import Pool

import numpy as np

import h23_lib as L
from h23_lib import HERE, ROOT
sys.path.insert(0, str(ROOT / "hypotheses" / "h21_italian_order_breaking_and_cross_hand"))
import run_h21 as R21  # noqa: E402
R20 = R21.R20; R20.R = HERE / "results"; R19 = R20.R19; NTOK = R19.NTOK; SRC = R21.SRC
CS = (0.03, 0.05, 0.10); BSZ = 4500


def name(src, base, v, c): return f"A_{src[3:]}_{base}_{v}_c{c}"


def a_cell(src, base, v, c, cx):
    seed = 23 + 1000 * SRC.index(src) + (base == "syll"); rng = np.random.default_rng(seed)
    full = R20.italian(src); plain = full[: 2 * NTOK]; nb = None
    if base == "naibbe":
        from msdecipher.mech_naibbe import NaibbeCipher
        nb = NaibbeCipher().encrypt(full, seed=0, n_words_out=2 * NTOK)
    lines, labs, info = L.build(plain, base, cx["codes"], nb, rng, v, c, seed + 7 * L.VARIANTS.index(v) + int(100 * c), r=.5 if base == "syll" else 0)
    flat = [w for l in lines for w in l][:NTOK]; info["signal_share"] = sum(x is not None for x in labs[:NTOK]) / NTOK
    rec = L.plaintext_recovery(flat, labs[:NTOK]) if base == "syll" else {}
    cell = R20.lines_to_cell(lines, name(src, base, v, c)[2:], "ciph", "eva")
    cell["fit"] = dict(src=src, base=base, variant=v, c=c, **info, **rec); return cell


def ms_sub(pages, n=BSZ):
    out, k = [], 0
    for p in pages:
        if k >= n: break
        out.append(p); k += len(p["words"])
    return out


def b_cells():
    import h14_lib as L14
    d = L14.table(); sec = d.groupby("folio").section.first(); ms = R19.ms_cells(); out = {}
    p2 = ms["MS_2B"]["pages"]
    out["B_2B_bio"] = ms_sub([p for p in p2 if sec[p["id"]] == "biological"])
    out["B_2B_nonbio"] = [p for p in p2 if sec[p["id"]] != "biological"]
    for h in ["1A", "3B", "2B"]: out[f"B_{h}_sub"] = ms_sub(ms[f"MS_{h}"]["pages"])
    for h in ["2B", "3B"]:
        out[f"B_{h}_noedy"] = [dict(p, words=[w for w in p["words"] if not w.endswith("edy")], init=[i for w, i in zip(p["words"], p["init"]) if not w.endswith("edy")]) for p in ms[f"MS_{h}"]["pages"]]
    for k, v in out.items():                      # fewer than 5 quires: quire folds would leave an empty train set
        if len({p["quire"] for p in v}) < 5: out[k] = [dict(p, quire="b" + str(p["bif"])) for p in v]
    return {k: dict(kind="ms", seg="eva", pages=[p for p in v if p["words"]], fit=dict(n_tokens=sum(len(p["words"]) for p in v))) for k, v in out.items()}


if __name__ == "__main__":
    cx = R21.ctx(); cells = {}
    if sys.argv[1] == "phase1":
        cells.update(b_cells())
        cells[name("it_boccaccio", "naibbe", "ref", 0.0)] = a_cell("it_boccaccio", "naibbe", "ref", 0.0, cx)
        for v in L.VARIANTS:
            for c in CS: cells[name("it_boccaccio", "naibbe", v, c)] = a_cell("it_boccaccio", "naibbe", v, c, cx)
            cells[name("it_boccaccio", "syll", v, 0.05)] = a_cell("it_boccaccio", "syll", v, 0.05, cx)
    else:
        for v, c in json.load(open(HERE / "results" / "search_best.json")):
            for src in SRC[1:]: cells[name(src, "naibbe", v, c)] = a_cell(src, "naibbe", v, c, cx)
    todo = [(n, c) for n, c in cells.items() if not (HERE / "results" / f"cell_{n}.json").exists()]
    print("todo", len(todo), flush=True); R19.plain_lms()
    with Pool(7) as pool:
        for n in pool.imap_unordered(R20.run_cell, todo): print("done", n, flush=True)
