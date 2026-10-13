"""Run h33 (PREREG.md): python run_h33.py [corpus ...] -> results/c_<name>.json"""
import json
import sys
from multiprocessing import Pool

import numpy as np

import h33_lib as L

R = L.HERE / "results"
NAT = {"augustine": "la prose", "macer": "la verse herbal", "sidrach": "it prose", "manzoni": "it prose", "cucina": "it recipes"}
GEN = {"GEN_naibbe_la_pliny": "naibbe la", "GEN_naibbe_it_ariosto": "naibbe it", "GEN_C0_2B": "C0 2B"}
HANDS = ["1A", "2B", "3B"]


def load(name):
    import h30_lib
    if name in HANDS: return [l["words"] for l in h30_lib.load_ms(name)]
    if name in NAT: return [l["words"] for l in h30_lib.load_control(h30_lib.CONTROLS[name][0], ntok=20000)]
    c = json.loads((L.ROOT / "hypotheses/h31_word_construction/results/corpora.json").read_text())[name]
    ws = [w for p in c["pages"] for w in p["words"]]; return [ws[i:i + 9] for i in range(0, len(ws), 9)]


def cap(lines, n):
    out, k = [], 0
    for l in lines:
        if k >= n: break
        out.append(l); k += len(l)
    return out


def run(name):
    ncap = json.loads((R / "cap.json").read_text())["cap"]
    base = cap(load(name), ncap); res = dict(corpus=name, group="MS" if name in HANDS else "NAT" if name in NAT else "GEN")
    for var in ("full", "interior"):
        lines = [l for l in base if len(l) >= 2] if var == "full" else [l[1:-1] for l in base if len(l) >= 4]
        rng = np.random.default_rng(33); res[var] = {t: L.all_metrics(L.transform(lines, t), rng) for t in L.TRANSFORMS}
        res[var]["space"] = L.space_predict(lines)
    (R / f"c_{name}.json").write_text(json.dumps(res, indent=1)); return name


if __name__ == "__main__":
    names = sys.argv[1:] or HANDS + list(NAT) + list(GEN)
    if not (R / "cap.json").exists():
        n = min(sum(len(l) for l in load(h)) for h in HANDS); (R / "cap.json").write_text(json.dumps(dict(cap=n)))
    with Pool(6) as p: print(list(p.imap_unordered(run, names)))
