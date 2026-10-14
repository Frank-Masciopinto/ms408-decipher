"""Run h35 (PREREG.md): python run_h35.py [measures|fingerprint]."""
import json, sys
from multiprocessing import Pool
import numpy as np
import h35_lib as S
L = S.L34
sys.path.insert(0, str(S.ROOT / "hypotheses/h34_boundary_rule_generator"))
import run_h34 as R34  # noqa: E402
R = S.HERE / "results"; HANDS = R34.HANDS; GENS = R34.GENS


def job(args):
    hand, gen, mode = args; import run_h20
    rng = np.random.default_rng(35); tr, te = R34.split(hand); r = L.fit_table(tr); N = run_h20.NTOK
    base = R34.base_stream(gen, hand, tr); words = [w for l in tr for w in l]
    if mode == "on": base = S.respell(base, S.fit_shape(words), np.random.default_rng(1))
    elif mode == "shuf": base = S.respell(base, S.fit_shape(words, np.random.default_rng(2)), np.random.default_rng(1))
    Jtr = L.junction(tr, rng); cells = {}
    for s in L.STRENGTHS:
        lines = L.apply_rule(base, r, s, np.random.default_rng(int(s * 10) + 1), n_out=N)
        cells[s] = (dict(s=s, **L.measures(lines, te, rng)), lines)
    ss = min(L.STRENGTHS, key=lambda s: abs(cells[s][0]["J"] - Jtr)); m, lines = cells[ss]
    res = dict(hand=hand, gen=gen, mode=mode, J_train_ms=Jtr, s_star=ss, m=m, drivers=S.gap_drivers(lines, te))
    (R / f"m_{hand}_{gen}_{mode}.json").write_text(json.dumps(res, indent=1))
    if mode == "on": (R / f"lines_{hand}_{gen}_on.json").write_text(json.dumps(lines))
    return hand, gen, mode, ss, round(m["S"], 3)


def fp_job(args):
    name, lines = args; import run_h20
    run_h20.R = R; return run_h20.run_cell((name, run_h20.lines_to_cell(lines, name, "synth", "eva")))


if __name__ == "__main__":
    if (sys.argv[1:] or ["measures"])[0] == "measures":
        todo = [(h, g, m) for h in HANDS for g in GENS for m in ("off", "on", "shuf")]
        with Pool(7) as p:
            for x in p.imap_unordered(job, todo): print("done", x, flush=True)
    else:
        import run_h19; run_h19.plain_lms()
        todo = [(f"{h}_{g}_on", json.loads((R / f"lines_{h}_{g}_on.json").read_text())) for h in HANDS for g in GENS
                if not (R / f"cell_{h}_{g}_on.json").exists()]
        with Pool(7) as p:
            for n in p.imap_unordered(fp_job, todo): print("done", n, flush=True)
