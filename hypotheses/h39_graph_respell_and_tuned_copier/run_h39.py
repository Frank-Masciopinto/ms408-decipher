"""Run h39 (PREREG.md): python run_h39.py [measures|fingerprint]."""
import itertools, json, sys
from multiprocessing import Pool
import numpy as np
import h39_lib as S
import h34_lib as L
import h35_lib as S35
import h38_lib as S38
import run_h34 as R34
R = S.HERE / "results"; HANDS = R34.HANDS; GENS = R34.GENS; FEEDS = ("native", "naibbe_it", "naibbe_nonsense")
CELLS = [(h, g, m) for h in HANDS for g in GENS for m in ("graph", "graphshuf")] + [(h, f, "tuned") for h in HANDS for f in FEEDS]
GRID = list(itertools.product((.03, .06, .10, .15, .25), (5, 10, 25, 50), (.1, .25, .4, .55)))


def shuffled(words, rng):
    return ["".join(rng.permutation(list(w))) for w in words]


def tune(hand, m, fd, feed, tr, r, N):
    trw = [w for l in tr for w in l]; Vms = len(set(trw[:5000])); Cms = S.copy_proxy(trw); Sms = S.space_S(trw)
    best = None
    for pf, win, p0 in GRID:
        out = S.tuned_copier(6000, m, fd, np.random.default_rng(5), feed=feed, p_fresh=pf, window=win, p0=p0)
        lines = L.apply_rule(out, r, 1.0, np.random.default_rng(6), n_out=5000); toks = [w for l in lines for w in l]
        V = len(set(toks[:5000])); C = S.copy_proxy(toks[:3000]); Sx = S.space_S(toks)
        loss = abs(V - Vms) / Vms + abs(C - Cms) / Cms + 4 * abs(Sx - Sms)
        if best is None or loss < best[0]: best = (loss, dict(p_fresh=pf, window=win, p0=p0, V=V, C=C, S=Sx))
    return dict(loss=best[0], V_ms=Vms, C_ms=Cms, S_ms=Sms, **best[1])


def job(args):
    hand, gen, mode = args; import run_h20
    rng = np.random.default_rng(39); tr, te = R34.split(hand); r = L.fit_table(tr); N = run_h20.NTOK
    words = [w for l in tr for w in l]; extra = {}; E = None
    if mode in ("graph", "graphshuf"):
        base = R34.base_stream(gen, hand, tr)
        tw = shuffled(words, np.random.default_rng(2)) if mode == "graphshuf" else words
        tl = [tw[i:i + 9] for i in range(0, len(tw) - 8, 9)] if mode == "graphshuf" else tr
        maps, extra = S.anneal(base, S.Target(tw, tl), tw, np.random.default_rng(1))
        cache = {}; out = [cache.setdefault(t, S.apply(t, maps)) for t in base]
        E, nE = S38.S36.edit_preservation(base, out); extra["E_full"] = E; extra["merged_types"] = len(set(base)) - len(set(out))
    else:
        m = S35.fit_shape(words); fd = S38.final_dist(words)
        feed = None if gen == "native" else S35.respell(R34.base_stream(gen, hand, tr), m, np.random.default_rng(1))
        extra = tune(hand, m, fd, feed, tr, r, N)
        out = S.tuned_copier(2 * N, m, fd, np.random.default_rng(3), feed=feed, p_fresh=extra["p_fresh"], window=extra["window"], p0=extra["p0"])
    Jtr = L.junction(tr, rng); cells = {}
    for s in L.STRENGTHS:
        lines = L.apply_rule(out, r, s, np.random.default_rng(int(s * 10) + 1), n_out=N)
        cells[s] = (dict(s=s, **L.measures(lines, te, rng)), lines)
    ss = min(L.STRENGTHS, key=lambda s: abs(cells[s][0]["J"] - Jtr)); mm, lines = cells[ss]
    toks = [w for l in lines for w in l]; tet = [w for l in te for w in l]
    res = dict(hand=hand, gen=gen, mode=mode, J_train_ms=Jtr, s_star=ss, m=mm, E=E, F=S.js_final(toks, tet),
               V_ms=mm["types5k"] / len(set(tet[:5000])), copy_proxy=S.copy_proxy(toks[:3000]), copy_proxy_ms_test=S.copy_proxy(tet[:3000]), extra=extra)
    (R / f"m_{hand}_{gen}_{mode}.json").write_text(json.dumps(res, indent=1, default=float))
    if mode != "graphshuf": (R / f"lines_{hand}_{gen}_{mode}.json").write_text(json.dumps(lines))
    return hand, gen, mode, ss, round(mm["S"], 3), E and round(E, 3), round(res["F"], 3), round(res["V_ms"], 2)


def fp_job(args):
    name, lines = args; import run_h20
    run_h20.R = R; return run_h20.run_cell((name, run_h20.lines_to_cell(lines, name, "synth", "eva")))


if __name__ == "__main__":
    if (sys.argv[1:] or ["measures"])[0] == "measures":
        with Pool(7) as p:
            for x in p.imap_unordered(job, CELLS): print("done", x, flush=True)
    else:
        import run_h19; run_h19.plain_lms()
        todo = [(f"{h}_{g}_{m}", json.loads((R / f"lines_{h}_{g}_{m}.json").read_text())) for h, g, m in CELLS if m != "graphshuf"
                and not (R / f"cell_{h}_{g}_{m}.json").exists()]
        with Pool(7) as p:
            for n in p.imap_unordered(fp_job, todo): print("done", n, flush=True)
