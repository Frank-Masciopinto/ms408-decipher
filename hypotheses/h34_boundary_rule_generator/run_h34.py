"""Run h34 (PREREG.md): python run_h34.py [measures|fingerprint]."""
import json
import sys
from multiprocessing import Pool

import numpy as np

import h34_lib as L

R = L.HERE / "results"; HANDS = ["1A", "2B", "3B"]; GENS = ["C0", "naibbe_it", "naibbe_nonsense"]


def split(hand):
    import h30_lib
    ls = h30_lib.load_ms(hand)
    import pandas as pd
    q = pd.read_csv(L.ROOT / "data" / "quires.csv", dtype=str).set_index("page").bifolium_id
    bifs = sorted({str(q.get(l["page"])) for l in ls}); te_b = set(bifs[1::2])
    tr = [l["words"] for l in ls if str(q.get(l["page"])) not in te_b]; te = [l["words"] for l in ls if str(q.get(l["page"])) in te_b]
    return tr, te


def base_stream(gen, hand, tr):
    import run_h20
    N = run_h20.NTOK
    if gen == "C0":
        f = R / f"base_C0_{hand}.json"
        if f.exists(): return json.loads(f.read_text())
        import run_h12 as H12
        m = H12.fit([w for l in tr for w in l], seed=0); out = [w for w in H12.generate(m, 2 * N, seed=34) if w]; f.write_text(json.dumps(out)); return out
    import h27_lib as H; from fetch_italian import load_italian
    src = load_italian("it_boccaccio")
    pt = H.real_plaintext(src) if gen == "naibbe_it" else H.zipf_sample(src, 3001)[1]
    return H.encrypt_swap(pt, 1, 2 * N)[0]


def job(args):
    hand, gen = args; rng = np.random.default_rng(34); import run_h20
    tr, te = split(hand); r = L.fit_table(tr); base = base_stream(gen, hand, tr); N = run_h20.NTOK
    Jtr = L.junction(tr, rng); res = dict(hand=hand, gen=gen, J_train_ms=Jtr, cells={})
    for s in L.STRENGTHS:
        lines = L.apply_rule(base, r, s, np.random.default_rng(int(s * 10) + 1), n_out=N)
        res["cells"][f"s{s}"] = dict(s=s, **L.measures(lines, te, rng))
    s_star = min(L.STRENGTHS, key=lambda s: abs(res["cells"][f"s{s}"]["J"] - Jtr)); res["s_star"] = s_star
    rs = L.shuffle_table(r, np.random.default_rng(7))
    res["cells"]["shuffled"] = dict(s=s_star, **L.measures(L.apply_rule(base, rs, s_star, np.random.default_rng(99), n_out=N), te, rng))
    res["cells"]["allgaps"] = dict(s=s_star, **L.measures(L.apply_rule(base, r, s_star, np.random.default_rng(98), all_gaps=True, n_out=N), te, rng))
    (R / f"lines_{hand}_{gen}.json").write_text(json.dumps({k: L.apply_rule(base, r, v, np.random.default_rng(int(v * 10) + 1), n_out=N)
                                                          for k, v in (("s0", 0.0), ("sstar", s_star))}))
    (R / f"m_{hand}_{gen}.json").write_text(json.dumps(res, indent=1)); return hand, gen, s_star


def ms_job(hand):
    rng = np.random.default_rng(34); tr, te = split(hand)
    return hand, dict(train=L.measures(tr, None, rng), test=L.measures(te, te, rng), n_train=sum(map(len, tr)), n_test=sum(map(len, te)))


def fp_job(args):
    name, lines = args; import run_h20
    run_h20.R = R; cell = run_h20.lines_to_cell(lines, name, "synth", "eva"); return run_h20.run_cell((name, cell))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "measures"
    if what == "measures":
        with Pool(4) as p: ms = dict(p.map(ms_job, HANDS))
        for h in HANDS: base_stream("C0", h, split(h)[0])
        (R / "ms_targets.json").write_text(json.dumps(ms, indent=1)); print(json.dumps(ms, indent=1), flush=True)
        with Pool(7) as p:
            for x in p.imap_unordered(job, [(h, g) for h in HANDS for g in GENS]): print("done", x, flush=True)
    else:
        import run_h19; run_h19.plain_lms(); todo = []
        for h in HANDS:
            for g in GENS:
                d = json.loads((R / f"lines_{h}_{g}.json").read_text())
                for k, v in d.items():
                    if not (R / f"cell_{h}_{g}_{k}.json").exists(): todo.append((f"{h}_{g}_{k}", v))
        with Pool(7) as p:
            for n in p.imap_unordered(fp_job, todo): print("done", n, flush=True)
