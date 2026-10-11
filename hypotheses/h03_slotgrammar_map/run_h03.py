"""Run all h03 experiments. Usage: python hypotheses/h03_slotgrammar_map/run_h03.py [--quick]"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h03_lib as L  # noqa: E402
from msdecipher.controls_text import load_tokens  # noqa: E402
from msdecipher import controls_transforms as T  # noqa: E402
from msdecipher import mechanisms_run as MR  # noqa: E402

RES = L.HERE / "results"
N = 35000
_MS = {}


def ms():
    if "c" not in _MS:
        _MS["c"] = L.ms_corpus()
    return _MS["c"]


def build(name: str) -> L.Corpus:
    if name == "MS408":
        return ms()
    if name == "MS408_wordorder_shuffled":
        c = ms()
        rng = random.Random(1)
        w = list(c.words)
        rng.shuffle(w)
        c2 = L.Corpus(**{**c.__dict__})
        c2.words = w
        c2.name = name
        return c2
    if name == "MS408_letters_shuffled":
        c = ms()
        rng = random.Random(2)
        c2 = L.Corpus(**{**c.__dict__})
        c2.words = ["".join(rng.sample(list(w), len(w))) for w in c.words]
        c2.name = name
        return c2
    if name in ("la_vulgate", "la_pliny_herbal", "it_dante", "de_faust", "he_tanakh", "ar_quran"):
        return L.tokens_corpus(name, "natural", load_tokens(name, N))
    if name == "gen_slot_grammar":
        return L.tokens_corpus(name, "generator_eva", T.slot_grammar(N, 0))
    if name.startswith("naibbe_"):
        _, cid, s = name.split("|")
        return L.tokens_corpus(name.replace("|", "_"), "naibbe", MR.naibbe_words(cid, 78, int(s), N))
    if name.startswith("selfcite_"):
        _, tag, s = name.split("|")
        return L.selfcite_corpus(tag, int(s), N)
    raise KeyError(name)


JOBS = ([("MS408", ["learned", "zattera"]), ("MS408_wordorder_shuffled", ["learned", "zattera"]), ("MS408_letters_shuffled", ["learned", "zattera"])]
        + [(n, ["learned"]) for n in ("la_vulgate", "la_pliny_herbal", "it_dante", "de_faust", "he_tanakh", "ar_quran")]
        + [("gen_slot_grammar", ["learned", "zattera"])]
        + [(f"naibbe_|{c}|{s}", ["learned", "zattera"]) for c, s in (("la_vulgate", 1), ("la_vulgate", 2), ("la_vulgate", 3), ("it_dante", 1))]
        + [(f"selfcite_|{t}|{s}", ["learned", "zattera"]) for t in ("default", "fitted") for s in (1, 2, 3)])


def job(args):
    name, kinds, n_boot = args
    t0 = time.time()
    corp = build(name)
    out = {"overview": [], "pred": [], "syll": [], "prof": [], "fill": [], "patterns": [], "rf": []}
    for kind in kinds:
        o, fill, pats = L.heldout_overview(corp, kind)
        o["family"] = corp.family
        out["overview"].append(o)
        out["fill"].append({"corpus": corp.name, "grammar": kind, **{f"slot{k + 1}": float(v) for k, v in enumerate(fill)}})
        for p, c in pats.most_common(40):
            out["patterns"].append({"corpus": corp.name, "grammar": kind, "pattern_slots": "-".join(str(x + 1) for x in p), "count": c})
        for r, (p, c) in enumerate(pats.most_common(400)):
            out["rf"].append({"corpus": corp.name, "grammar": kind, "rank": r + 1, "count": c})
        out["pred"] += [{**r, "family": corp.family} for r in L.predictive_tasks(corp, kind, n_boot=n_boot)]
        srow, prof, *_ = L.syllable_overview(corp, kind)
        srow["family"] = corp.family
        out["syll"].append(srow)
        out["prof"].append(prof)
    if name == "MS408":     # letters shuffled copy of the overview only (coverage and vocabulary)
        pass
    return name, out, time.time() - t0


def perm_job(args):
    kind, n_perm = args
    return kind, L.label_perm_null(ms(), kind, n_perm=n_perm, seed=7)


def tables_and_sheet():
    """Full glyph -> slot -> Hz tables and the sheet's slot order, from the grammars fitted on all of MS 408 (descriptive)."""
    c = ms()
    res = {}
    for kind in ("learned", "zattera"):
        uw = L.segment_words(c.words, kind, True)
        fit = L.SlotFit(kind).fit(uw, seed=1)
        paths = fit.decode(uw)
        tab = L.slot_unit_table(fit, uw, paths)
        occ = L.sheet_occurrences(uw, paths)
        sp = L.sheet_slot_spearman(occ, n_boot=2000, seed=3)
        sp.insert(0, "grammar", kind)
        # fold stability: grammar fitted on one folio parity, decode all words
        stab = []
        for f in (0, 1):
            fit_f = L.SlotFit(kind).fit([u for u, t in zip(uw, c.fold == f) if t], seed=1)
            occ_f = L.sheet_occurrences(uw, fit_f.decode(uw))
            s = L.sheet_slot_spearman(occ_f, n_boot=200, seed=3)
            s.insert(0, "grammar", kind)
            s.insert(1, "fitted_on_folio_parity", f)
            stab.append(s)
        # sheet rows
        rows = []
        for u in L.SHEET_UNITS:
            o = np.array(occ[u], float)
            if len(o) == 0:
                rows.append({"unit": u, "unit_type": "sheet digraph", "count": 0, "sheet_hz": L.SHEET[u], "note": "no decodable occurrence (cannot be generated by this grammar's slot order)"})
                continue
            first = Counter(int(x) + 1 for x in o[:, 0])
            second = Counter(int(x) + 1 for x in o[:, 1])
            rows.append({"unit": u, "unit_type": "sheet digraph", "count": len(o), "modal_slot": f"{first.most_common(1)[0][0]}+{second.most_common(1)[0][0]}",
                         "mean_slot": float(o.mean() + 1), "first_letter_mean_slot": float(o[:, 0].mean() + 1), "second_letter_mean_slot": float(o[:, 1].mean() + 1),
                         "hz_slot": float(L.slot_hz_log(o.mean())), "sheet_hz": L.SHEET[u]})
        ms_row = sp[sp.variant == "mean_slot"].iloc[0]
        a, b = ms_row.intercept_hz, ms_row.slope_hz_per_slot
        tab["hz_slot_sheetfit"] = np.clip(a + b * tab["mean_slot"], 60, None)
        sheet_df = pd.DataFrame(rows)
        sheet_df["hz_slot_sheetfit"] = np.clip(a + b * sheet_df.get("mean_slot", np.nan), 60, None)
        full = pd.concat([tab.assign(unit_type="unit"), sheet_df], ignore_index=True)
        full.insert(0, "grammar", kind)
        full.to_csv(RES / f"slot_unit_hz_table_{kind}.csv", index=False)
        sp.to_csv(RES / f"sheet_slot_order_spearman_{kind}.csv", index=False)
        pd.concat(stab).to_csv(RES / f"sheet_slot_order_fold_stability_{kind}.csv", index=False)
        # slot x unit emission matrix for the heat map
        pd.DataFrame(fit.P_raw, columns=[str(u) for u in fit.units]).assign(slot=np.arange(1, 13), p_emit=fit.e).to_csv(RES / f"slot_emission_matrix_{kind}.csv", index=False)
        res[kind] = (fit, uw, paths)
    return res


def main(quick: bool):
    RES.mkdir(exist_ok=True)
    t0 = time.time()
    n_boot, n_perm = (200, 4) if quick else (2000, 40)
    jobs = JOBS[:2] + JOBS[3:5] if quick else JOBS
    args = [(n, k, n_boot) for n, k in jobs]
    ov, pr, sy, pf, fl, pt, rf = [], [], [], [], [], [], []
    with mp.get_context("fork").Pool(8) as pool:
        perm_res = pool.map_async(perm_job, [("learned", n_perm), ("zattera", n_perm)])
        for name, out, dt in pool.imap_unordered(job, args):
            ov += out["overview"]; pr += out["pred"]; sy += out["syll"]; pf += out["prof"]; fl += out["fill"]; pt += out["patterns"]; rf += out["rf"]
            print(f"[{time.time() - t0:5.0f}s] {name} {dt:.0f}s", flush=True)
        perms = perm_res.get()
    # shuffled-letter MS overview rows (fit and test on words whose letters were shuffled inside each word)
    c = ms()
    for kind in ("learned", "zattera"):
        o, *_ = L.heldout_overview(c, kind, shuffle_letters=True)
        o["family"] = "ms408_letters_shuffled_inside_words"
        ov.append(o)
    pd.DataFrame(ov).to_csv(RES / "heldout_overview.csv", index=False)
    pd.DataFrame(pr).to_csv(RES / "predictive_gains.csv", index=False)
    pd.DataFrame(sy).to_csv(RES / "syllable_overview.csv", index=False)
    pd.concat(pf).to_csv(RES / "slot_cv_profiles.csv", index=False)
    pd.DataFrame(fl).to_csv(RES / "slot_fill_probability.csv", index=False)
    pd.DataFrame(pt).to_csv(RES / "top_slot_patterns.csv", index=False)
    pd.DataFrame(rf).to_csv(RES / "pattern_rank_frequency.csv", index=False)
    pd.concat([d.assign(grammar=k) for k, d in perms]).to_csv(RES / "label_permutation_null.csv", index=False)
    tables_and_sheet()
    print("all done", time.time() - t0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    main(ap.parse_args().quick)
