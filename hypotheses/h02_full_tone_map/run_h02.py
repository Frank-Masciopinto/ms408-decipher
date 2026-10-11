"""Run all h02 experiments. Usage: python hypotheses/h02_full_tone_map/run_h02.py [--quick]
Writes results/*.csv. Deterministic given the seeds (python's hash() is only used for per-map RNG seeds: PYTHONHASHSEED is fixed below)."""
from __future__ import annotations

import os
import sys

if os.environ.get("PYTHONHASHSEED") != "0":            # make hash((name, ...)) seeds reproducible
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable] + sys.argv)

import argparse
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h02_lib as L  # noqa: E402
from msdecipher.controls_text import load_tokens  # noqa: E402
from msdecipher import controls_transforms as T  # noqa: E402

RES = L.HERE / "results"

CONTROLS = [  # (name, family, builder)
    ("la_vulgate", "natural", lambda: load_tokens("la_vulgate", 35000)),
    ("la_pliny_herbal", "natural", lambda: load_tokens("la_pliny_herbal", 35000)),
    ("it_dante", "natural", lambda: load_tokens("it_dante", 35000)),
    ("de_faust", "natural", lambda: load_tokens("de_faust", 35000)),
    ("he_tanakh", "natural", lambda: load_tokens("he_tanakh", 35000)),
    ("ar_quran", "natural", lambda: load_tokens("ar_quran", 35000)),
    ("cipher_monoalphabetic_la", "cipher", lambda: T.monoalphabetic(load_tokens("la_vulgate", 35000), 0)),
    ("cipher_vigenere_la", "cipher", lambda: T.vigenere(load_tokens("la_vulgate", 35000), 6, 0)),
    ("cipher_verbose2_la", "cipher", lambda: T.verbose_2sym(load_tokens("la_vulgate", 35000), 0)),
    ("cipher_naibbe_like_la", "cipher", lambda: T.naibbe_like(load_tokens("la_vulgate", 35000), 0)),
    ("gen_iid_letters", "generator", lambda: T.iid_letters(load_tokens("la_vulgate", 35000), 35000, 0)),
    ("gen_markov2", "generator", lambda: T.markov_char(load_tokens("la_vulgate", 35000), 35000, 2, 0)),
    ("gen_slot_grammar", "generator", lambda: T.slot_grammar(35000, 0)),
]


def build_text(spec):
    kind, name, tok = spec
    if kind == "ms":
        return L.build_ms(tok)
    for n, fam, b in CONTROLS:
        if n == name:
            return L.build_tokens_text(n, fam, b())
    raise KeyError(name)


def job(args):
    spec, maps, n_shuf, n_rand, n_sec, is_ms = args
    t0 = time.time()
    t = build_text(spec)
    ev = L.Evaluator(t, n_shuf, n_rand, seed=1)
    rows, sec_rows, table_rows = [], [], []
    rng = np.random.default_rng(5)
    for m in maps:
        res = ev.evaluate(m, want_words=is_ms)
        for r in L.summarise_eval(res):
            rows.append({"text": t.name, "family": t.family, "tok": t.tok, "map": m, "n_pitches": res["n_unique_pitches"], **r})
        pv_all = ev.map_all(m)
        if is_ms:
            for u, h in zip(t.inv, pv_all):
                table_rows.append({"tok": t.tok, "map": m, "unit": u, "hz": float(h), "count_in_text": int((t.U == t.inv.index(u)).sum())})
            sec_rows += section_tests(t, ev, m, res, n_sec, rng)
    return rows, sec_rows, table_rows, (t.name, t.tok, time.time() - t0, len(maps))


def section_tests(t, ev, m, res, n_perm, rng):
    out = []
    sections = np.array(t.folio_section)
    lang = np.array(t.folio_language)
    keep_sec = np.isin(sections, ["herbal", "biological", "pharmaceutical", "stars", "cosmological", "astronomical", "text-only"])
    for key in ("meanP", "mai", "mono"):
        x = L.folio_means(t, {f: {k: v for k, v in {"meanP": res["words"][f]["_word_meanP"], "mai": res["words"][f]["_word_mai"], "mono": res["words"][f]["_word_mono"]}.items()} for f in (0, 1)}, key)
        eta, p = L.perm_eta_p(np.where(keep_sec, x, np.nan), sections, n_perm, rng)
        d, pd_ = L.ab_effect(x, lang, n_perm, rng)
        # random-map reference
        etas, ds = [], []
        for _ in range(40):
            words = {}
            for f in (0, 1):
                pv = rng.permutation(L.build_map(m, ev.st[f], t.inv))
                Ut, Lt = ev.test[f]
                words[f] = L.light_word_stats(pv, Ut, Lt)
            xr = L.folio_means(t, words, key)
            etas.append(L.eta_squared(np.where(keep_sec, xr, np.nan), sections))
            ok = np.isin(lang, ["A", "B"]) & ~np.isnan(xr)
            a, b = xr[ok & (lang == "A")], xr[ok & (lang == "B")]
            sp = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
            ds.append(abs((a.mean() - b.mean()) / sp) if sp > 0 else 0.0)
        out.append({"tok": t.tok, "map": m, "folio_stat": key, "eta2_section": eta, "p_section_perm": p, "eta2_rand_median": float(np.median(etas)),
                    "eta2_rand_p95": float(np.percentile(etas, 95)), "frac_rand_eta2_ge": float(np.mean(np.array(etas) >= eta)),
                    "ab_d": d, "p_ab_perm": pd_, "abs_d_rand_median": float(np.median(ds)), "abs_d_rand_p95": float(np.percentile(ds, 95)),
                    "frac_rand_abs_d_ge": float(np.mean(np.array(ds) >= abs(d)))})
    return out


def main(quick: bool):
    RES.mkdir(exist_ok=True)
    n_shuf_ms, n_rand_ms, n_shuf_c, n_rand_c, n_sec = (20, 20, 8, 8, 200) if quick else (120, 120, 40, 40, 1000)
    all_maps = L.map_names(True)
    t_ms = {tok: L.build_ms(tok) for tok in ("T1", "T2")}
    jobs = []
    chunks = [all_maps[i::4] for i in range(4)]
    for tok in ("T1", "T2"):
        for ch in chunks:
            jobs.append((("ms", "MS408", tok), ch, n_shuf_ms, n_rand_ms, n_sec, True))
    ctl = CONTROLS[:3] if quick else CONTROLS
    for n, fam, b in ctl:
        jobs.append((("ctl", n, "C"), all_maps, n_shuf_c, n_rand_c, 0, False))
    # biggest first
    t0 = time.time()
    rows, sec_rows, table_rows = [], [], []
    with mp.get_context("fork").Pool(8) as pool:
        for r, s, tb, info in pool.imap_unordered(job, jobs):
            rows += r
            sec_rows += s
            table_rows += tb
            print(f"[{time.time() - t0:6.0f}s] done {info}", flush=True)
    pd.DataFrame(rows).to_csv(RES / "map_stats.csv", index=False)
    pd.DataFrame(sec_rows).to_csv(RES / "section_tests.csv", index=False)
    pd.DataFrame(table_rows).to_csv(RES / "map_table_long.csv", index=False)

    # ---- ordering support for the sheet's 8 values (T2 inventory, all data)
    for tok in ("T2", "T1"):
        pass
    t2 = t_ms["T2"]
    st = L.unit_stats(t2, np.ones(len(t2.L), bool), slot_grammar=True, seed=1)
    rk = L.ordering_ranks(st, t2.inv)
    osup = L.ordering_support(st, t2.inv, rk)
    osup.to_csv(RES / "ordering_support_of_the_8_values.csv", index=False)
    # unit statistics table
    ust = pd.DataFrame({"unit": t2.inv, "count": st["count"], "mean_rel_pos": st["meanpos"], "share_initial": st["init"], "share_final": st["final"],
                        "H_next_bits": st["H_next"], "surprisal_bits": st["surprisal"], "fiedler": st["fiedler"], "sukhotin_vowel_like": st["is_vowel"],
                        "slot_expected": st["slot_exp"], "cluster_k5": st["cluster"], **{f"rank_{k}": v for k, v in rk.items()}})
    ust.to_csv(RES / "unit_statistics_T2.csv", index=False)
    pd.DataFrame([{"map": m, "group": L.GROUP[m[0]], "description": L.describe_map(m)} for m in all_maps]).to_csv(RES / "maps_description.csv", index=False)
    # rare units: fallback position map
    from collections import Counter
    from msdecipher.segment import Segmenter, PRESETS
    folios = L.H1.load_folios(L.TR / "ZL3b-n.txt", "P")
    seg = Segmenter(PRESETS["collapsed"])
    cnt, pos_sum, pos_n = Counter(), Counter(), Counter()
    for f in folios:
        for w in f.tokens:
            us = seg(w)
            for i, u in enumerate(us):
                cnt[u] += 1
                if len(us) >= 2:
                    pos_sum[u] += i / (len(us) - 1)
                    pos_n[u] += 1
    rare = []
    main_units = set(t_ms["T1"].inv)
    mp_main = {u: pos_sum[u] / pos_n[u] for u in main_units if pos_n[u]}
    lo, hi = min(mp_main.values()), max(mp_main.values())
    for u, c in sorted(cnt.items(), key=lambda kv: -kv[1]):
        if u in main_units:
            continue
        mpos = pos_sum[u] / pos_n[u] if pos_n[u] else float("nan")
        h = L.F0 * 2 ** (min(max((mpos - lo) / (hi - lo), 0), 1) * L.RANGE_CENTS / 1200) if mpos == mpos else float("nan")
        rare.append({"unit": L.H1.__name__ and __import__("msdecipher.ivtff", fromlist=["render"]).render(u), "count": c, "mean_rel_pos": mpos, "fallback_hz_c_pos": h,
                     "note": "count < 20: statistics too thin; Hz is only the position fallback"})
    pd.DataFrame(rare).to_csv(RES / "rare_units_fallback.csv", index=False)
    print("all done", time.time() - t0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    main(ap.parse_args().quick)
