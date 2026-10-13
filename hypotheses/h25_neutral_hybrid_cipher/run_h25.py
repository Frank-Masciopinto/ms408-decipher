"""Run h25. python run_h25.py phase1 | phase2 ; then summarise.py"""
import json
import sys
from multiprocessing import Pool

import h25_lib as L
from h25_lib import HERE, ROOT, L24
sys.path.insert(0, str(ROOT / "hypotheses" / "h21_italian_order_breaking_and_cross_hand"))
import run_h21 as R21  # noqa: E402
R20 = R21.R20; R20.R = HERE / "results"; R19 = R20.R19; NTOK = R19.NTOK; SRC = R21.SRC
COPY = {"none": 0.0, "swap": .05, "inline": .03, "unit": .05}
TD = HERE / "tables"
NSEED = 6          # reduced from the pre-registered 10 for runtime (see README)


def cell(src, variant, copy, seed, render):
    ci = L.make_cipher(variant, seed, TD); full = R20.italian(src)
    toks = [str(t) for t in ci.encrypt(full, seed=seed, n_words_out=2 * NTOK)]; labs = ["#"] * len(toks)
    toks, labs, n = L24.copy_variant(toks, labs, COPY[copy], copy, seed=100 * seed + 13) if COPY[copy] > 0 else (toks, labs, 0)
    dec = L.decodable_share(ci, toks[:NTOK], labs[:NTOK])
    seg = "char"
    if render == "eva":
        m = L.eva_render(seed, L.params(variant)["A"]); toks = ["".join(m[g] for g in t) for t in toks]; seg = "eva"
    nm = f"NH_{src[3:]}_{variant}_{copy}_{render}_s{seed}"
    c = R20.lines_to_cell([toks[i:i + 9] for i in range(0, len(toks), 9)], nm, "ciph", seg)
    c["fit"] = dict(src=src, variant=variant, copy=copy, seed=seed, render=render, signal_share=sum(x is not None for x in labs[:NTOK]) / NTOK, decodable=dec, **{k: (v if not isinstance(v, float) else round(v, 4)) for k, v in L.params(variant).items()})
    return nm, c


def plan(phase):
    out = []
    if phase == "phase1":
        for s in range(1, NSEED + 1):
            for cp in COPY: out.append(("it_boccaccio", "base", cp, s, "char"))
            for src in SRC[1:]:
                for cp in ("none", "swap"): out.append((src, "base", cp, s, "char"))
            for cp in ("none", "swap"): out.append(("it_boccaccio", "base", cp, s, "eva"))
        for v in L.VARIANTS:
            if v == "base": continue
            for s in range(1, 4):
                for cp in ("none", "swap"): out.append(("it_boccaccio", v, cp, s, "char"))
    else:
        v = json.load(open(HERE / "results" / "best_variant.json"))
        for src in SRC:
            for s in range(1, 4): out.append((src, v, "swap", s, "eva"))
    return out


def build(a): return cell(*a)


if __name__ == "__main__":
    TD.mkdir(exist_ok=True); todo_args = [a for a in plan(sys.argv[1]) if not (HERE / "results" / f"cell_NH_{a[0][3:]}_{a[1]}_{a[2]}_{a[4]}_s{a[3]}.json").exists()]
    print("todo", len(todo_args), flush=True); R19.plain_lms()
    with Pool(7) as pool:
        cells = [build(a) for a in todo_args]          # serial: cells of one (variant, seed) share a table file
        for n in pool.imap_unordered(R20.run_cell, cells): print("done", n, flush=True)
