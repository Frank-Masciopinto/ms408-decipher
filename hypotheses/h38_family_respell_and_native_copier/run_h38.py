"""Run h38 (PREREG.md): python run_h38.py [measures|fingerprint]."""
import json, sys
from multiprocessing import Pool
import numpy as np
import h38_lib as S
import h36_lib as S36
import h34_lib as L
import h35_lib as S35
import run_h34 as R34
R = S.HERE / "results"; HANDS = R34.HANDS; GENS = R34.GENS
CELLS = [(h, g, m) for h in HANDS for g in GENS for m in ("fam", "famshuf")] + [(h, f, "nat") for h in HANDS for f in ("native", "naibbe_it", "naibbe_nonsense")]


def job(args):
    hand, gen, mode = args; import run_h20
    rng = np.random.default_rng(38); tr, te = R34.split(hand); r = L.fit_table(tr); N = run_h20.NTOK
    words = [w for l in tr for w in l]; fd = S.final_dist(words); m = S35.fit_shape(words); st = {}; E = nE = None
    if mode == "fam":
        base = R34.base_stream(gen, hand, tr); out, st = S.fam_respell(base, m, fd, np.random.default_rng(1)); E, nE = S36.edit_preservation(base, out)
    elif mode == "famshuf":
        base = R34.base_stream(gen, hand, tr); out, st = S.fam_respell(base, S35.fit_shape(words, np.random.default_rng(2)), fd, np.random.default_rng(1)); E, nE = S36.edit_preservation(base, out)
    else:
        feed = None if gen == "native" else S35.respell(R34.base_stream(gen, hand, tr), m, np.random.default_rng(1))
        out = S.native_copier(2 * N, m, fd, np.random.default_rng(3), feed=feed)
    Jtr = L.junction(tr, rng); cells = {}
    for s in L.STRENGTHS:
        lines = L.apply_rule(out, r, s, np.random.default_rng(int(s * 10) + 1), n_out=N)
        cells[s] = (dict(s=s, **L.measures(lines, te, rng)), lines)
    ss = min(L.STRENGTHS, key=lambda s: abs(cells[s][0]["J"] - Jtr)); mm, lines = cells[ss]
    toks = [w for l in lines for w in l]; tet = [w for l in te for w in l]
    res = dict(hand=hand, gen=gen, mode=mode, J_train_ms=Jtr, s_star=ss, m=mm, E=E, nE=nE, F=S.js_final(toks, tet),
               V_ms=mm["types5k"] / len(set(tet[:5000])), respell_stats=dict(st), drivers=S35.gap_drivers(lines, te))
    (R / f"m_{hand}_{gen}_{mode}.json").write_text(json.dumps(res, indent=1))
    if mode != "famshuf": (R / f"lines_{hand}_{gen}_{mode}.json").write_text(json.dumps(lines))
    return hand, gen, mode, ss, round(mm["S"], 3), E and round(E, 3), round(res["F"], 3)


def fp_job(args):
    name, lines = args; import run_h20
    run_h20.R = R; return run_h20.run_cell((name, run_h20.lines_to_cell(lines, name, "synth", "eva")))


if __name__ == "__main__":
    if (sys.argv[1:] or ["measures"])[0] == "measures":
        with Pool(7) as p:
            for x in p.imap_unordered(job, CELLS): print("done", x, flush=True)
    else:
        import run_h19; run_h19.plain_lms()
        todo = [(f"{h}_{g}_{m}", json.loads((R / f"lines_{h}_{g}_{m}.json").read_text())) for h, g, m in CELLS if m != "famshuf"
                and not (R / f"cell_{h}_{g}_{m}.json").exists()]
        with Pool(7) as p:
            for n in p.imap_unordered(fp_job, todo): print("done", n, flush=True)
