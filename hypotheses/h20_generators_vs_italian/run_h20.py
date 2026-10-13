"""Run h20: build all conditions, score with the h19 pipeline (+PCLM), write results/."""
import json
import random
import sys
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

import h20_lib as L
from h20_lib import HERE, ROOT, L19
sys.path.insert(0, str(ROOT / "hypotheses" / "h19_heldout_likelihood"))
import run_h19 as R19  # noqa: E402
import fetch_italian as FI  # noqa: E402

R = HERE / "results"; NTOK = R19.NTOK
IT_PLAIN = ["it_dante", "it_sidrach", "it_ariosto"]          # from data/controls (msdecipher.controls_text)
IT_NEW = [s["id"] for s in FI.SOURCES]
ENC_SRC = ["it_boccaccio", "it_cucina", "it_sidrach"]


def italian(cid, n=None):
    if cid in IT_NEW: return FI.load_italian(cid, n)
    from msdecipher.controls_text import load_tokens
    return load_tokens(cid, n)


def lines_to_cell(lines, name, kind, seg):
    toks, init = [], []
    for l in lines:
        for i, w in enumerate(l): toks.append(w); init.append(i == 0)
        if len(toks) >= NTOK: break
    toks, init = toks[:NTOK], init[:NTOK]; c = R19.paginate(toks, name, kind, seg)
    k = 0
    for p in c["pages"]:
        p["init"] = init[k:k + len(p["words"])]; k += len(p["words"])
    return c


def c0_cells():
    sys.path.insert(0, str(ROOT / "hypotheses" / "h12_per_hand_copy_modify")); import run_h12 as H12
    q, pw = H12.page_words(); out = {}
    for hl in ["1A", "2B", "3B"]:
        tw = H12.words_of(list(q[q.HL == hl].page), pw); m = H12.fit(tw, seed=0); g = H12.generate(m, NTOK, seed=20)
        out["GEN_C0_" + hl] = R19.paginate(list(g)[:NTOK], "c0" + hl, "synth", "eva")
        out["GEN_C0_" + hl]["fit"] = dict(fit_distance=m["fit_distance"], secs=m["secs"])
    return out


def sc_cells():
    d = ROOT / "data" / "mechanisms" / "selfcitation"; out = {}
    for tag in ["default_s1", "default_s2", "fitted_s1", "fitted_s2"]:
        lines = [l.split() for l in (d / f"{tag}.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
        out["GEN_SC_" + tag] = lines_to_cell(lines, "sc" + tag, "synth", "eva")
    return out


def build_cells():
    from msdecipher.mech_naibbe import NaibbeCipher
    cells = R19.ms_cells()
    for cid in IT_PLAIN + IT_NEW: cells["IT_" + cid] = R19.paginate(italian(cid, NTOK), cid, "ctrl", "char")
    cells.update(c0_cells()); cells.update(sc_cells())
    seg = R19.seg_fn("eva"); ms2b = [w for p in cells["MS_2B"]["pages"] for w in p["words"]]; codes = L.ms_codes(ms2b, seg)
    books = {}
    for cid in ENC_SRC:
        full = italian(cid); plain = full[:NTOK]
        cells["ENC_naibbe_" + cid] = R19.paginate(NaibbeCipher().encrypt(full, seed=0, n_words_out=NTOK), "nb" + cid, "ciph", "eva")
        ct, book = L.syllabic_cipher(plain, codes); books[cid] = len(book)
        cells["ENC_syll_" + cid] = R19.paginate(ct, "sy" + cid, "ciph", "eva")
        cells["ENC_novowel_" + cid] = R19.paginate([L.remove_vowels(w) for w in plain], "nv" + cid, "ctrl", "char")
        cells["ENC_suspend_" + cid] = R19.paginate([L.suspend(w) for w in plain], "su" + cid, "ctrl", "char")
    json.dump(dict(syllable_types=books, n_codes=len(codes)), open(R / "encoding_info.json", "w"), indent=1)
    return cells


def run_cell(args):
    name, cell = args; rng = np.random.default_rng(19); pages = cell["pages"]
    res = {"cell": name, "kind": cell["kind"], "n_tokens": sum(len(p["words"]) for p in pages), "fit": cell.get("fit"), "schemes": {}}
    for scheme, key in (("bifolium", "bif"), ("quire", "quire")):
        folds = R19.group_folds(pages, key, 5); tok = []; extras = []
        for fi_, (tr, te) in enumerate(folds):
            trp, tep = [pages[i] for i in tr], [pages[i] for i in te]
            bt, ex = R19.run_split(trp, tep, cell, rng); extras.append(ex)
            pc = L.PosCharLM().fit([w for p in trp for w in p["words"]]); bt["PCLM"] = np.array([pc.logp(w) for p in tep for w in p["words"]])
            df = pd.DataFrame(bt); df["page"] = [p["id"] for p in tep for _ in p["words"]]; df["fold"] = fi_
            df["init"] = [x for p in tep for x in p["init"]]; df["glyphs"] = [len(w) + 1 for p in tep for w in p["words"]]; tok.append(df)
        tok = pd.concat(tok, ignore_index=True); tok.to_csv(R / f"tokens_{name}_{scheme}.csv.gz", index=False)
        res["schemes"][scheme] = dict(bits={c: float(-tok[c].mean()) for c in tok.columns if c not in ("page", "fold", "init", "glyphs")},
                                      glyphs_per_word=float(tok.glyphs.mean()), extras=extras)
        if scheme == "bifolium":
            res["crossfit_W5"] = R19.crossfit_lambda(cell, folds, 5, rng); res["crossfit_W100"] = R19.crossfit_lambda(cell, folds, 100, rng)
    json.dump(res, open(R / f"cell_{name}.json", "w"), indent=1, default=float)
    return name


if __name__ == "__main__":
    cells = build_cells(); want = sys.argv[1:] or list(cells)
    json.dump({k: dict(kind=v["kind"], n_tokens=sum(len(p["words"]) for p in v["pages"]), n_pages=len(v["pages"])) for k, v in cells.items()}, open(R / "cells.json", "w"), indent=1)
    R19.plain_lms()
    with Pool(7) as pool:
        for n in pool.imap_unordered(run_cell, [(n, cells[n]) for n in want]): print("done", n, flush=True)
