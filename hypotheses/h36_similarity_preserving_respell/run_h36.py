"""Run h36 (PREREG.md): python run_h36.py [measures|fingerprint]."""
import json, sys
from multiprocessing import Pool
import numpy as np
import h36_lib as S
import h34_lib as L
import h35_lib as S35
import run_h34 as R34
R = S.HERE / "results"; HANDS = R34.HANDS; GENS = R34.GENS; MODES = ("off", "pos", "ctx", "shuf", "h35")


def job(args):
    hand, gen, mode = args; import run_h20
    rng = np.random.default_rng(36); tr, te = R34.split(hand); r = L.fit_table(tr); N = run_h20.NTOK
    base = R34.base_stream(gen, hand, tr); words = [w for l in tr for w in l]; out = base
    if mode in ("pos", "ctx", "shuf"):
        out = S.respell(base, S.fit_map(base, words, ctx=mode == "ctx", rng=np.random.default_rng(3) if mode == "shuf" else None))
    elif mode == "h35": out = S35.respell(base, S35.fit_shape(words), np.random.default_rng(1))
    E, nE = S.edit_preservation(base, out)
    Jtr = L.junction(tr, rng); cells = {}
    for s in L.STRENGTHS:
        lines = L.apply_rule(out, r, s, np.random.default_rng(int(s * 10) + 1), n_out=N)
        cells[s] = (dict(s=s, **L.measures(lines, te, rng)), lines)
    ss = min(L.STRENGTHS, key=lambda s: abs(cells[s][0]["J"] - Jtr)); m, lines = cells[ss]
    res = dict(hand=hand, gen=gen, mode=mode, J_train_ms=Jtr, s_star=ss, m=m, E=E, nE=nE, drivers=S35.gap_drivers(lines, te))
    (R / f"m_{hand}_{gen}_{mode}.json").write_text(json.dumps(res, indent=1))
    if mode in ("pos", "ctx"): (R / f"lines_{hand}_{gen}_{mode}.json").write_text(json.dumps(lines))
    return hand, gen, mode, ss, round(m["S"], 3), round(E, 3)


def fp_job(args):
    name, lines = args; import run_h20
    run_h20.R = R; return run_h20.run_cell((name, run_h20.lines_to_cell(lines, name, "synth", "eva")))


if __name__ == "__main__":
    if (sys.argv[1:] or ["measures"])[0] == "measures":
        todo = [(h, g, m) for h in HANDS for g in GENS for m in MODES]
        with Pool(7) as p:
            for x in p.imap_unordered(job, todo): print("done", x, flush=True)
    else:
        import run_h19; run_h19.plain_lms()
        todo = [(f"{h}_{g}_{m}", json.loads((R / f"lines_{h}_{g}_{m}.json").read_text())) for h in HANDS for g in GENS for m in ("pos", "ctx")
                if not (R / f"cell_{h}_{g}_{m}.json").exists()]
        with Pool(7) as p:
            for n in p.imap_unordered(fp_job, todo): print("done", n, flush=True)
