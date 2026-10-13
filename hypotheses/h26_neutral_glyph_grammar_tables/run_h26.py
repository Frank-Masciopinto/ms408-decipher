"""Run h26. python run_h26.py phase1 | phase2 ; then summarise.py. Tables and cells are built serially; only scoring is parallel."""
import json
import random
import sys
from multiprocessing import Pool

import h26_lib as L
from h26_lib import HERE, ROOT
sys.path.insert(0, str(ROOT / "hypotheses" / "h25_neutral_hybrid_cipher")); sys.path.insert(0, str(ROOT / "hypotheses" / "h24_neutral_cipher_robustness"))
import h24_lib as L24  # noqa: E402
import h25_lib as L25  # noqa: E402
sys.path.insert(0, str(ROOT / "hypotheses" / "h21_italian_order_breaking_and_cross_hand"))
import run_h21 as R21  # noqa: E402
R20 = R21.R20; R20.R = HERE / "results"; R19 = R20.R19; NTOK = R19.NTOK; SRC = R21.SRC
COPY = {"none": 0.0, "swap": .05}; TD = HERE / "tables"
NSEED_MAIN, NSEED_VAR = 5, 3


def name(src, g, cp, render, s): return f"G_{src[3:]}_{g}_{cp}_{render}_s{s}"


def cell(src, g, cp, s, render):
    gram = L.make_grammar(g, s); f = L.write_tables(TD / f"{g}_s{s}.csv", gram)
    ci = L25.NH(f, 6, "naibbe", 17 / 36); full = R20.italian(src)
    toks = [str(t) for t in ci.encrypt(full, seed=s, n_words_out=2 * NTOK)]; labs = ["#"] * len(toks)
    eva_native = g == "ms"; segf = R19.seg_fn("eva") if eva_native else tuple
    toks, labs, n = L24.copy_variant(toks, labs, COPY[cp], cp, seed=100 * s + 17, seg=segf) if COPY[cp] > 0 else (toks, labs, 0)
    dec = L25.decodable_share(ci, toks[:NTOK], labs[:NTOK]); seg = "eva" if eva_native else "char"
    if render == "eva" and not eva_native:
        used = sorted({ch for t in toks for ch in t}); u = L.EVA_UNITS[:]; random.Random(7100 + s).shuffle(u); assert len(used) <= len(u), len(used)
        m = dict(zip(used, u)); toks = ["".join(m[ch] for ch in t) for t in toks]; seg = "eva"
    props = L.grammar_props(toks[:NTOK], R19.seg_fn(seg))
    c = R20.lines_to_cell([toks[i:i + 9] for i in range(0, len(toks), 9)], name(src, g, cp, render, s), "ciph", seg)
    c["fit"] = dict(src=src, grammar=g, copy=cp, seed=s, render=render, decodable=dec, signal_share=sum(x is not None for x in labs[:NTOK]) / NTOK, **props)
    return name(src, g, cp, render, s), c


def plan(phase):
    out = []
    if phase == "phase1":
        for g in ("rs", "lat", "ms"):
            for s in range(1, NSEED_MAIN + 1):
                for cp in COPY: out.append(("it_boccaccio", g, cp, s, "eva"))
        for s in range(1, NSEED_MAIN + 1): out.append(("it_boccaccio", "rs", "none", s, "char"))
        for g in L.RS_VAR:
            if g == "rs": continue
            for s in range(1, NSEED_VAR + 1):
                for cp in COPY: out.append(("it_boccaccio", g, cp, s, "eva"))
    else:
        for g, cp in json.load(open(HERE / "results" / "transfer_settings.json")):
            for src in SRC[1:]:
                for s in range(1, 4): out.append((src, g, cp, s, "eva"))
    return out


if __name__ == "__main__":
    TD.mkdir(exist_ok=True)
    todo = [a for a in plan(sys.argv[1]) if not (HERE / "results" / f"cell_{name(a[0], a[1], a[2], a[4], a[3])}.json").exists()]
    print("todo", len(todo), flush=True); cells = [cell(*a) for a in todo]; R19.plain_lms()
    with Pool(7) as pool:
        for n in pool.imap_unordered(R20.run_cell, cells): print("done", n, flush=True)
