"""Run h24. python run_h24.py phase1 | phase2 ; then summarise.py"""
import json
import sys
from multiprocessing import Pool

import numpy as np

import h24_lib as L
from h24_lib import HERE, ROOT, L23
sys.path.insert(0, str(ROOT / "hypotheses" / "h21_italian_order_breaking_and_cross_hand"))
import run_h21 as R21  # noqa: E402
R20 = R21.R20; R20.R = HERE / "results"; R19 = R20.R19; NTOK = R19.NTOK; SRC = R21.SRC
SEEDS1 = (1, 2, 3, 4, 5); SEEDS2 = (1, 2, 3)
P1 = [("swap", 0.05), ("inline", 0.03), ("unit", 0.05)]
P2 = [("none", 0.0), ("swap", 0.05), ("inline", 0.03)]


def lines_of(toks): return [toks[i:i + 9] for i in range(0, len(toks), 9)]


def naibbe_cell(src, v, c, s):
    from msdecipher.mech_naibbe import NaibbeCipher
    full = R20.italian(src); nb = [str(t) for t in NaibbeCipher().encrypt(full, seed=s, n_words_out=2 * NTOK)]
    toks, labs, n = L23.copy_variant(nb, ["#"] * len(nb), c, v, seed=100 * s + 7)
    nm = f"N_{src[3:]}_{v}_c{c}_s{s}"; cell = R20.lines_to_cell(lines_of(toks), nm, "ciph", "eva")
    cell["fit"] = dict(part=1, src=src, cipher="naibbe", variant=v, c=c, seed=s, signal_share=sum(x is not None for x in labs[:NTOK]) / NTOK); return nm, cell


def neutral_cell(src, ci, v, c, s):
    plain = L.clean(R20.italian(src))[: 2 * NTOK]; toks = L.encipher(plain, ci, seed=s); labs = list(plain)
    if ci.endswith("null"): toks, labs = L.add_nulls(toks, labs, .3, np.random.default_rng(s))
    toks, labs, n = L.copy_variant(toks, labs, c, v, seed=100 * s + 11) if c > 0 else (toks, labs, 0)
    nm = f"X_{src[3:]}_{ci}_{v}_c{c}_s{s}"; cell = R20.lines_to_cell(lines_of(toks), nm, "ciph", "char")
    cell["fit"] = dict(part=2, src=src, cipher=ci, variant=v, c=c, seed=s, signal_share=sum(x is not None for x in labs[:NTOK]) / NTOK); return nm, cell


def chunks(pages, n, k):
    out, cur, tot = [], [], 0
    for p in pages:
        cur.append(p); tot += len(p["words"])
        if tot >= n: out.append(cur); cur, tot = [], 0
        if len(out) == k: break
    return out


def h_cells():
    import h14_lib as L14
    d = L14.table(); sec = d.groupby("folio").section.first(); ms = R19.ms_cells(); out = {}
    pg = lambda h, f: [p for p in ms[f"MS_{h}"]["pages"] if f(sec[p["id"]])]  # noqa: E731
    out["H_2B_bio"] = chunks(pg("2B", lambda s: s == "biological"), 4400, 1)[0]
    out["H_2B_nonbio"] = chunks(pg("2B", lambda s: s != "biological"), 4400, 1)[0]
    for i, ch in enumerate(chunks(pg("3B", lambda s: s == "stars"), 4400, 2)): out[f"H_3B_stars{i}"] = ch
    herb1a = pg("1A", lambda s: s == "herbal")
    for i, ch in enumerate(chunks(herb1a, 4400, 2)): out[f"H_1A_herb{i}"] = ch
    out["H_2B_herb"] = chunks(pg("2B", lambda s: s == "herbal"), 2250, 1)[0]
    rest = [p for p in herb1a if p not in out["H_1A_herb0"]]
    out["H_1A_herbS0"] = chunks(rest, 2250, 1)[0]; out["H_1A_herbS1"] = chunks(out["H_1A_herb0"], 2250, 1)[0]   # S0, S1 disjoint
    res = {}
    for k, v in out.items():
        if len({p["quire"] for p in v}) < 5 or len({p["bif"] for p in v}) < 5:
            v = [dict(p, quire=f"g{i % 5}", bif=f"g{i % 5}") if len({q["bif"] for q in v}) < 5 else dict(p, quire="b" + str(p["bif"])) for i, p in enumerate(v)]
        res[k] = dict(kind="ms", seg="eva", pages=v, fit=dict(part=3, n_tokens=sum(len(p["words"]) for p in v), n_pages=len(v)))
    return res


if __name__ == "__main__":
    cells = {}
    if sys.argv[1] == "phase1":
        cells.update(h_cells())
        for ci in L.CIPHERS:
            for v, c in P2:
                for s in SEEDS2: n, x = neutral_cell("it_boccaccio", ci, v, c, s); cells[n] = x
        for src in SRC:
            for v, c in P1:
                for s in SEEDS1: n, x = naibbe_cell(src, v, c, s); cells[n] = x
    else:
        ci, v, c = json.load(open(HERE / "results" / "neutral_best.json"))
        for src in SRC[1:]:
            for s in SEEDS2: n, x = neutral_cell(src, ci, v, c, s); cells[n] = x
    todo = [(n, c) for n, c in cells.items() if not (HERE / "results" / f"cell_{n}.json").exists()]
    print("todo", len(todo), flush=True); R19.plain_lms()
    with Pool(7) as pool:
        for n in pool.imap_unordered(R20.run_cell, todo): print("done", n, flush=True)
