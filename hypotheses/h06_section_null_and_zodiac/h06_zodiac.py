"""h06 part 2: the zodiac pages (f70v2..f73v: ring text Cc + one label per nymph Lz) against generators fitted on NON-zodiac folios.

Data are read from h05's committed CSVs (``zodiac_loci.csv`` = ring text and labels per page, ``label_tokens.csv``); h05 itself is untouched.
Nothing here decodes MS 408; Roman-script month names in the centres are not in the transcription.
"""
from __future__ import annotations

import itertools
import math
import random
import re
from collections import Counter

import numpy as np
import pandas as pd

import h06_lib as L

HR, H, R, CI = L.HR, L.H, L.R, L.CI
SEG = L.SEG
H05 = L.ROOT / "hypotheses" / "h05_zodiac_cribs" / "results"
PAGES = ["f70v2", "f70v1", "f71r", "f71v", "f72r1", "f72r2", "f72r3", "f72v3", "f72v2", "f72v1", "f73r", "f73v"]
MONTH = {"f70v2": 3, "f70v1": 4, "f71r": 4, "f71v": 5, "f72r1": 5, "f72r2": 6, "f72r3": 7, "f72v3": 8, "f72v2": 9, "f72v1": 10, "f73r": 11, "f73v": 12}   # Mars ... Decembre (Jan, Feb = lost Aquarius/Capricorn)
SIGN = {"f70v2": "Pisces", "f70v1": "Aries", "f71r": "Aries", "f71v": "Taurus", "f72r1": "Taurus", "f72r2": "Gemini", "f72r3": "Cancer", "f72v3": "Leo",
        "f72v2": "Virgo", "f72v1": "Libra", "f73r": "Scorpio", "f73v": "Sagittarius"}
OK = re.compile(r"^[a-z]+$")


# ------------------------------------------------------------------ data

def zodiac_data() -> tuple[dict, dict]:
    """(ring tokens per page, label tokens per page) -- readable tokens only (a-z), in reading / locus order."""
    loci = pd.read_csv(H05 / "zodiac_loci.csv")
    lab = pd.read_csv(H05 / "label_tokens.csv")
    ring = {p: [] for p in PAGES}
    for _, r in loci[loci.ltype == "Cc"].iterrows():
        ring[r.folio] += [w for w in str(r.words).split() if OK.match(w)]
    labels = {p: [] for p in PAGES}
    for _, r in lab.iterrows():
        if bool(r.readable) and OK.match(str(r.word)):
            labels[r.folio].append(str(r.word))
    return ring, labels


def nonzodiac_label_words() -> list[str]:
    from msdecipher.analysis import groups, load_corpus
    from msdecipher.ivtff import readable
    g = groups(load_corpus(), "split")
    out = []
    for ln in g["labels"]:
        if ln.page in PAGES:
            continue
        out += [w for w in ln.words if readable(w) and OK.match(w)]
    return out


# ------------------------------------------------------------------ statistics

def _dist(tokens: list[str]) -> Counter:
    return Counter(tokens)


def js_bits(c1: Counter, c2: Counter) -> float:
    keys = set(c1) | set(c2)
    n1, n2 = sum(c1.values()), sum(c2.values())
    if not n1 or not n2:
        return float("nan")
    tot = 0.0
    for k in keys:
        p, q = c1.get(k, 0) / n1, c2.get(k, 0) / n2
        m = (p + q) / 2
        if p:
            tot += 0.5 * p * math.log2(p / m)
        if q:
            tot += 0.5 * q * math.log2(q / m)
    return tot


def unit_counter(tokens: list[str]) -> Counter:
    return Counter(u for w in tokens for u in SEG(w))


def bigram_vec(tokens: list[str]) -> Counter:
    c = Counter()
    for w in tokens:
        u = ("^",) + tuple(SEG(w)) + ("$",)
        c.update(zip(u, u[1:]))
    return c


def cosine(c1: Counter, c2: Counter) -> float:
    num = sum(v * c2.get(k, 0) for k, v in c1.items())
    d = math.sqrt(sum(v * v for v in c1.values()) * sum(v * v for v in c2.values()))
    return num / d if d else float("nan")


def mean_pairwise(items: list, fn) -> float:
    vals = [fn(a, b) for a, b in itertools.combinations(items, 2)]
    vals = [v for v in vals if not math.isnan(v)]
    return float(np.mean(vals)) if vals else float("nan")


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else float("nan")


def edit1(a: str, b: str) -> bool:
    return CIedit(a, b)


def CIedit(a, b):
    from msdecipher.controls_metrics import edit_distance_le1
    return edit_distance_le1(a, b)


def zodiac_stats(ring: dict, lab: dict, rest: list[str], rest_types: set, rest_units: Counter, rest_words_c: Counter, pages: list[str] | None = None) -> dict:
    pages = [p for p in (pages or PAGES) if ring.get(p) or lab.get(p)]
    ring_all = [w for p in pages for w in ring.get(p, [])]
    lab_all = [w for p in pages for w in lab.get(p, [])]
    zod = ring_all + lab_all
    out = {}
    out["zod_js_vs_rest"] = js_bits(_dist(zod), rest_words_c)
    out["zod_oov_share"] = float(np.mean([w not in rest_types for w in zod])) if zod else float("nan")
    out["zod_unit_js_vs_rest"] = js_bits(unit_counter(zod), rest_units)
    out["ring_label_unit_js"] = js_bits(unit_counter(ring_all), unit_counter(lab_all))
    out["ring_label_word_js"] = js_bits(_dist(ring_all), _dist(lab_all))
    out["label_o_initial"] = float(np.mean([w[0] == "o" for w in lab_all])) if lab_all else float("nan")
    out["ring_o_initial"] = float(np.mean([w[0] == "o" for w in ring_all])) if ring_all else float("nan")
    out["label_q_share"] = float(np.mean(["q" in w for w in lab_all])) if lab_all else float("nan")
    out["ring_q_share"] = float(np.mean(["q" in w for w in ring_all])) if ring_all else float("nan")
    for nm, d in (("ring", ring), ("label", lab)):
        rep = []
        for p in pages:
            t = d.get(p, [])
            if t:
                c = Counter(t)
                rep.append(np.mean([c[w] > 1 for w in t]))
        out[f"rep_{nm}"] = float(np.mean(rep)) if rep else float("nan")
    lc = Counter(lab_all)
    out["label_hapax_types"] = float(np.mean([v == 1 for v in lc.values()])) if lc else float("nan")
    once = []
    for p in pages:
        t = lab.get(p, [])
        if t:
            c = Counter(t)
            once.append(np.mean([c[w] == 1 for w in t]))
    out["label_page_once"] = float(np.mean(once)) if once else float("nan")
    ll = np.array([len(SEG(w)) for w in lab_all], float)
    out["label_len_mean"], out["label_len_sd"] = (float(ll.mean()), float(ll.std())) if len(ll) else (float("nan"),) * 2
    out["ring_len_mean"] = float(np.mean([len(SEG(w)) for w in ring_all])) if ring_all else float("nan")
    out["jaccard_ring"] = mean_pairwise([set(ring.get(p, [])) for p in pages], jaccard)
    out["jaccard_label"] = mean_pairwise([set(lab.get(p, [])) for p in pages], jaccard)
    out["cos_ring"] = mean_pairwise([bigram_vec(ring.get(p, [])) for p in pages], cosine)
    out["cos_label"] = mean_pairwise([bigram_vec(lab.get(p, [])) for p in pages], cosine)
    out["ring_ttr"] = len(set(ring_all)) / len(ring_all) if ring_all else float("nan")
    adj = [edit1(a, b) for p in pages for a, b in zip(ring.get(p, []), ring.get(p, [])[1:])]
    out["ring_adj_edit1"] = float(np.mean(adj)) if adj else float("nan")
    return out


STAT_LABELS = {
    "zod_js_vs_rest": "zodiac vs rest-of-MS word JS (bits)", "zod_oov_share": "zodiac tokens absent from non-zodiac text", "zod_unit_js_vs_rest": "zodiac vs rest unit JS (bits)",
    "ring_label_unit_js": "ring vs label unit JS (bits)", "ring_label_word_js": "ring vs label word JS (bits)", "label_o_initial": "label o-initial share",
    "ring_o_initial": "ring o-initial share", "label_q_share": "labels containing q", "ring_q_share": "ring tokens containing q",
    "rep_ring": "ring: within-page repeated-token share", "rep_label": "labels: within-page repeated share", "label_hapax_types": "label hapax share of types",
    "label_page_once": "label words occurring once on their page", "label_len_mean": "label length mean (units)", "label_len_sd": "label length SD (units)",
    "ring_len_mean": "ring word length mean (units)", "jaccard_ring": "page-to-page type Jaccard (ring)", "jaccard_label": "page-to-page type Jaccard (labels)",
    "cos_ring": "page-to-page unit-bigram cosine (ring)", "cos_label": "page-to-page unit-bigram cosine (labels)", "ring_ttr": "ring type/token ratio", "ring_adj_edit1": "ring adjacent edit-1 rate"}


class Rest:
    """Non-zodiac reference text (the running text P)."""

    def __init__(self, words: list[str]):
        self.words = words
        self.types = set(words)
        self.units = unit_counter(words)
        self.counter = Counter(words)


def jackknife_pages(ring: dict, lab: dict, rest: Rest) -> dict:
    full = zodiac_stats(ring, lab, rest.words, rest.types, rest.units, rest.counter)
    jk = [zodiac_stats(ring, lab, rest.words, rest.types, rest.units, rest.counter, [q for q in PAGES if q != p]) for p in PAGES]
    se = {k: CI.jackknife_se([j[k] for j in jk]) for k in full}
    return {"stats": full, "se": se}


def null_windows(rest: Rest, sizes: list[int], n: int = 100, seed: int = 0) -> dict:
    """Same statistics for page-sized contiguous windows of the non-zodiac text (a 'no zodiac specialness' null for the distinctiveness stats)."""
    rng = random.Random(seed)
    js, oov, ujs = [], [], []
    w = rest.words
    for _ in range(n):
        toks = []
        for s in sizes:
            i = rng.randrange(len(w) - s)
            toks += w[i:i + s]
        c = Counter(toks)
        # rest = everything except those windows is approximated by the full text (bias is the same sign for real data)
        js.append(js_bits(c, rest.counter))
        oov.append(float(np.mean([t not in rest.types for t in toks])))
        ujs.append(js_bits(unit_counter(toks), rest.units))
    return {"zod_js_vs_rest": (float(np.mean(js)), float(np.std(js))), "zod_oov_share": (float(np.mean(oov)), float(np.std(oov))),
            "zod_unit_js_vs_rest": (float(np.mean(ujs)), float(np.std(ujs)))}


# ================================================================== generators laid out on the zodiac pages

class ZodiacModels:
    """Everything fitted on NON-zodiac folios: global grammar, global engine, per-section EUP50 models, a label-mode group fitted on non-zodiac labels."""

    def __init__(self, seed: int = 0, S: int = 50):
        d = HR.ms_data()
        self.d = d
        self.entries = L.T.folio_layout(d)
        self.rest = Rest(d["words"])
        self.sh = L.Shared(d["words"], seed=seed)
        self.gm_all, _ = L.fit_group(self.sh, d["words"], 0, False, L.PARAMS[:6], L.DEFAULT_BASE, seed=seed)
        base = {**self.gm_all.params, "p_pool": 0.2}
        groups: dict[str, list[str]] = {}
        for e in self.entries:
            groups.setdefault(e["cls"] or "other", []).extend(e["words"])
        self.sec_models = {"__all__": self.gm_all}
        for g, ws in groups.items():
            self.sec_models[g], _ = L.fit_group(self.sh, ws, S, True, L.PARAMS, base, seed=seed)
        self.label_words = nonzodiac_label_words()
        gl, _ = L.fit_group(self.sh, self.label_words, S, True, L.PARAMS, base, seed=seed)
        self.lab_models = {**self.sec_models, "labels": gl}
        import json
        self.hyb = json.loads((L.ROOT / "reports" / "mechanisms" / "hybrid" / "hybrid_params_all_ms408.json").read_text())
        bj = L.ROOT / "reports" / "mechanisms" / "selfcitation_best_params.json"
        self.sc_best = json.loads(bj.read_text()) if bj.exists() else {}
        self.cosmo_words = groups.get("cosmo-astro", [])


GENERATORS = ["A1 cipher + copy-modify (Isidore plaintext)", "A2 codebook + copy-modify (Isidore plaintext)", "Naibbe cipher (Isidore plaintext, no copying)",
              "C0g no plaintext, global (copy-modify)", "SV no plaintext, per-section EUP50 (group cosmo-astro)", "SV + label mode (labels group fitted on non-zodiac labels)",
              "Self-citation (Java, fitted)", "i.i.d. words of non-zodiac cosmo-astro folios (memorised vocabulary)"]


def _split(flat: list[str], ring: dict, lab: dict) -> tuple[dict, dict]:
    i = 0
    r, l = {}, {}
    for p in PAGES:
        r[p] = flat[i:i + len(ring[p])]
        i += len(ring[p])
        l[p] = flat[i:i + len(lab[p])]
        i += len(lab[p])
    return r, l


def gen_zodiac(name: str, seed: int, ring: dict, lab: dict, zm: ZodiacModels, scope: str = "window") -> tuple[dict, dict]:
    N = sum(len(ring[p]) + len(lab[p]) for p in PAGES)
    steps = [(k, n) for p in PAGES for k, n in (("ring", len(ring[p])), ("lab", len(lab[p])))]
    if name.startswith(("A1", "A2", "Naibbe")):
        v = "A2 whole-word codebook + copy-modify" if name.startswith("A2") else "A1 Naibbe tokens + copy-modify"
        p = H.Params(p_copy=0.0) if name.startswith("Naibbe") else H.Params(**zm.hyb[v])
        enc = HR.make_encoder("codebook" if name.startswith("A2") else "naibbe", HR.plaintext("la_isidore"), seed, zm.sh.ctx)
        flat = H.generate(None, p, 0, seed, plain_edit=False, section_encoders={"ring": enc, "lab": enc}, layout=steps)
        return _split(flat, ring, lab)
    if name.startswith("C0g"):
        specs = [{"group": "__all__", "n": n, "page": 0} for _, n in steps]
        return _split([w for part in L.sv_generate(specs, zm.sec_models, zm.sh, seed, scope=scope) for w in part], ring, lab)
    if name.startswith("SV"):
        label_mode = "label mode" in name
        specs = [{"group": ("labels" if (label_mode and k == "lab") else "cosmo-astro"), "n": n, "page": 0} for k, n in steps]
        return _split([w for part in L.sv_generate(specs, zm.lab_models, zm.sh, seed, scope=scope) for w in part], ring, lab)
    if name.startswith("Self-citation"):
        from msdecipher import mech_selfcitation as S
        return _split(S.generate(zm.sc_best, seed, N), ring, lab)
    if name.startswith("i.i.d."):
        rng = random.Random(seed)
        return _split([rng.choice(zm.cosmo_words) for _ in range(N)], ring, lab)
    raise ValueError(name)


# ================================================================== copy locality (real data) and scope fits

def near_sets(types: list[str], pool_types: set[str]) -> dict:
    """for each type: the pool types within unit... character edit distance <= 1 (identical included)."""
    by_len: dict[int, list[str]] = {}
    for t in pool_types:
        by_len.setdefault(len(t), []).append(t)
    out = {}
    for t in set(types):
        s = {t}
        for L_ in (len(t) - 1, len(t), len(t) + 1):
            for u in by_len.get(L_, ()):
                if u != t and CIedit(t, u):
                    s.add(u)
        out[t] = s
    return out


def locality(seqs: dict, near_zod: dict, rest_pool: list[str], near_rest: dict, W: int = 30, n_draw: int = 10, seed: int = 0, perm: int = 0) -> dict:
    """Hit rate: share of tokens with an identical / edit-1 token in (a) the preceding <= W tokens of the SAME page, (b) a same-size random sample of tokens of OTHER pages, (c) a same-size
    random sample of non-zodiac text (dispersed)."""
    rng = random.Random(seed)
    pages = [p for p in seqs if len(seqs[p]) > 3]
    allt = {p: seqs[p] for p in pages}
    hits_a = hits_b = hits_c = 0.0
    n = 0
    per_page = {}
    for p in pages:
        others = [w for q in pages if q != p for w in allt[q]]
        ha = hb = hc = nn = 0.0
        t = allt[p]
        for i in range(1, len(t)):
            w = t[i]
            k = min(W, i)
            near = near_zod[w]
            ha += bool(near & set(t[i - k:i]))
            rb = hc_ = 0.0
            for _ in range(n_draw):
                rb += bool(near & set(rng.sample(others, k)))
                hc_ += bool(near_rest[w] & set(rng.sample(rest_pool, k)))
            hb += rb / n_draw
            hc += hc_ / n_draw
            nn += 1
        per_page[p] = (ha / nn, hb / nn, hc / nn, nn)
        hits_a += ha
        hits_b += hb
        hits_c += hc
        n += nn
    out = {"local": hits_a / n, "other_pages": hits_b / n, "nonzodiac": hits_c / n, "n_tokens": int(n)}
    pp = np.array([[v[0], v[1], v[2]] for v in per_page.values()])
    g = len(pp)
    jk_diff = [np.mean(np.delete(pp[:, 0] - pp[:, 1], i)) for i in range(g)]
    out["diff_local_minus_other"] = float(np.mean(pp[:, 0] - pp[:, 1]))
    out["diff_se_jackknife"] = CI.jackknife_se(jk_diff)
    if perm:
        allw = [w for p in pages for w in allt[p]]
        sizes = [len(allt[p]) for p in pages]
        null = []
        for _ in range(perm):
            rng.shuffle(allw)
            i = 0
            hh = nn = 0
            for s in sizes:
                t = allw[i:i + s]
                i += s
                for j in range(1, len(t)):
                    k = min(W, j)
                    hh += bool(near_zod[t[j]] & set(t[j - k:j]))
                    nn += 1
            null.append(hh / nn)
        out["perm_local_null_mean"] = float(np.mean(null))
        out["perm_p_local"] = float((1 + sum(x >= out["local"] for x in null)) / (1 + perm))
    return out


RING_STATS = ["ring_ttr", "ring_hapax", "rep_ring", "jaccard_ring", "cos_ring", "ring_adj_edit1", "ring_adj_ident", "ring_top10"]


def ring_stats(ring: dict, pages: list[str]) -> dict:
    ps = [p for p in pages if ring.get(p)]
    allr = [w for p in ps for w in ring[p]]
    c = Counter(allr)
    out = {"ring_ttr": len(c) / len(allr), "ring_hapax": float(np.mean([v == 1 for v in c.values()])), "ring_top10": sum(v for _, v in c.most_common(10)) / len(allr)}
    rep = [np.mean([Counter(ring[p])[w] > 1 for w in ring[p]]) for p in ps]
    out["rep_ring"] = float(np.mean(rep))
    out["jaccard_ring"] = mean_pairwise([set(ring[p]) for p in ps], jaccard)
    out["cos_ring"] = mean_pairwise([bigram_vec(ring[p]) for p in ps], cosine)
    adj = [(a == b, edit1(a, b)) for p in ps for a, b in zip(ring[p], ring[p][1:])]
    out["ring_adj_ident"] = float(np.mean([a for a, _ in adj]))
    out["ring_adj_edit1"] = float(np.mean([b for _, b in adj]))
    return out


_Z: dict = {}


def _scope_job(job):
    L.WSR._one_thread()
    params, label = job
    zm, ring, scope, pages, tgt, sc, extra, seeds = (_Z[k] for k in ("zm", "ring", "scope", "pages", "tgt", "sc", "extra", "seeds"))
    gm = L.GroupModel(params=params)
    specs = [{"group": "g", "n": len(ring[p]), "page": p} for p in pages]
    accs = []
    for s in seeds:
        res = L.sv_generate(specs, {"g": gm, "__all__": gm}, zm.sh, s, scope=scope, extra_pool=extra)
        accs.append(ring_stats({p: w for p, w in zip(pages, res)}, pages))
    m = {k: float(np.mean([a[k] for a in accs])) for k in accs[0]}
    z = {k: (m[k] - tgt[k]) / sc[k] for k in RING_STATS}
    return {"label": label, "dist": math.sqrt(float(np.mean([v * v for v in z.values()]))), **{f"p:{k}": v for k, v in params.items()}, **{f"m:{k}": v for k, v in m.items()}}


def scope_fit(zm: ZodiacModels, ring: dict, scope: str, fit_pages: list[str], eval_pages: list[str], n_random: int = 60, n_local: int = 15, seed: int = 0,
              workers=None) -> dict:
    """Fit the 6 engine parameters for a copy scope on ``fit_pages`` (ring text), report in-sample and held-out distance (RMS z over RING_STATS)."""
    extra = random.Random(seed).sample(zm.rest.words, 3000) if scope == "global+P" else None
    sc_scope = "global" if scope == "global+P" else scope

    def target(pages):
        tg = ring_stats(ring, pages)
        jk = [ring_stats(ring, [q for q in pages if q != p]) for p in pages]
        se = {k: CI.jackknife_se([j[k] for j in jk]) for k in tg}
        return tg, {k: math.sqrt(se[k] ** 2 + (0.05 * abs(tg[k])) ** 2 + 0.005 ** 2) for k in tg}
    tgt, sc = target(fit_pages)
    _Z.update(zm=zm, ring=ring, scope=sc_scope, pages=fit_pages, tgt=tgt, sc=sc, extra=extra, seeds=(seed + 1, seed + 2, seed + 3))
    rng = random.Random(seed)
    free = L.PARAMS[:6]
    cands = [dict(L.DEFAULT_BASE)] + [L.sample_params(rng, free, L.DEFAULT_BASE) for _ in range(n_random)]
    rows = CI.pmap(_scope_job, [(p, f"r{i}") for i, p in enumerate(cands)], workers)
    top = sorted(range(len(rows)), key=lambda i: rows[i]["dist"])[:3]
    jobs = [(L.perturb_params(rng, cands[i], free), f"l{i}~{j}") for i in top for j in range(n_local)]
    rows2 = CI.pmap(_scope_job, jobs, workers)
    allp, allr = cands + [j[0] for j in jobs], rows + rows2
    ib = min(range(len(allr)), key=lambda i: allr[i]["dist"])
    best = allp[ib]
    # held-out evaluation, fresh seeds
    if eval_pages:
        tgt2, sc2 = target(eval_pages)
        _Z.update(pages=eval_pages, tgt=tgt2, sc=sc2, seeds=(seed + 11, seed + 12, seed + 13, seed + 14, seed + 15))
        ho = _scope_job((best, "eval"))
        held = ho["dist"]
        held_m = {k: ho[f"m:{k}"] for k in RING_STATS}
    else:
        held, held_m = float("nan"), {}
    return {"scope": scope, "fit_dist": float(allr[ib]["dist"]), "heldout_dist": held, "params": best, "heldout_stats": held_m}


# ================================================================== calendar structure

def page_similarity(tokens_by_page: dict, kind: str) -> np.ndarray:
    n = len(PAGES)
    M = np.full((n, n), np.nan)
    vec = {p: (set(tokens_by_page.get(p, [])) if kind == "jaccard" else bigram_vec(tokens_by_page.get(p, []))) for p in PAGES}
    f = jaccard if kind == "jaccard" else cosine
    for i, j in itertools.combinations(range(n), 2):
        M[i, j] = M[j, i] = f(vec[PAGES[i]], vec[PAGES[j]])
    return M


def circ_dist(a: int, b: int) -> int:
    d = abs(a - b)
    return min(d, 12 - d)


def calendar_tests(M: np.ndarray, n_perm: int = 20000, seed: int = 0) -> dict:
    """Do pages of adjacent months share more vocabulary than distant ones?  Statistic: Spearman(similarity, -circular month distance) over the 66 page pairs.
    Null: the 10 month values (Mar..Dec) are permuted among the 10 *pages-of-one-sign groups* (Aries and Taurus pages stay together), i.e. the month order is randomised
    while the pages' texts and the grouping are kept.  Also: linear folio-order drift, and the partial correlation with circular month distance given folio-order distance."""
    from scipy.stats import spearmanr
    n = len(PAGES)
    pairs = list(itertools.combinations(range(n), 2))
    sim = np.array([M[i, j] for i, j in pairs])
    ok = ~np.isnan(sim)
    sim = sim[ok]
    pairs = [p for p, o in zip(pairs, ok) if o]
    months = np.array([MONTH[p] for p in PAGES])
    groups = [[i for i in range(n) if SIGN[PAGES[i]] == s] for s in dict.fromkeys(SIGN[p] for p in PAGES)]
    uniq = sorted(set(months))
    dl = np.array([abs(i - j) for i, j in pairs], float)
    rng = np.random.default_rng(seed)

    def dc_for(mv):
        return np.array([circ_dist(mv[i], mv[j]) for i, j in pairs], float)

    def stat(mv):
        dc = dc_for(mv)
        r = spearmanr(sim, -dc).statistic
        # partial (rank) correlation with dc controlling for dl
        rs, rd, rl = (np.argsort(np.argsort(x)).astype(float) for x in (sim, -dc, -dl))
        def res(y, x):
            b = np.cov(y, x)[0, 1] / np.var(x, ddof=1)
            return y - b * x
        pr = np.corrcoef(res(rs, rl), res(rd, rl))[0, 1]
        adj = np.nanmean(sim[(dc <= 1) & (dc > 0)]) - np.nanmean(sim[dc >= 4])
        return r, pr, adj
    obs = stat(months)
    null = []
    for _ in range(n_perm):
        perm = rng.permutation(uniq)
        mv = months.copy()
        for g, m in zip(groups, perm):
            for i in g:
                mv[i] = m
        null.append(stat(mv))
    null = np.array(null)
    lin = spearmanr(sim, -dl).statistic
    # drift null: random page orders
    lnull = []
    for _ in range(5000):
        o = rng.permutation(n)
        dlp = np.array([abs(o[i] - o[j]) for i, j in pairs], float)
        lnull.append(spearmanr(sim, -dlp).statistic)
    return {"spearman_circular": obs[0], "p_circular": float((1 + (null[:, 0] >= obs[0]).sum()) / (1 + n_perm)), "null_mean_circular": float(null[:, 0].mean()),
            "partial_circular_given_folio_order": obs[1], "p_partial": float((1 + (null[:, 1] >= obs[1]).sum()) / (1 + n_perm)),
            "adjacent_minus_distant": obs[2], "p_adjacent_minus_distant": float((1 + (null[:, 2] >= obs[2]).sum()) / (1 + n_perm)),
            "spearman_folio_order_drift": float(lin), "p_folio_order": float((1 + (np.array(lnull) >= lin).sum()) / (1 + len(lnull))), "n_pairs": len(pairs)}


# ================================================================== zodiac as one more 'section': fit on half of the zodiac pages, test on the other half

def zodiac_cv(zm: ZodiacModels, ring: dict, lab: dict, n_seeds: int = 10, S: int = 50) -> pd.DataFrame:
    odd, even = PAGES[0::2], PAGES[1::2]
    rows = []
    for fold, (train, test) in enumerate(((odd, even), (even, odd))):
        rt = [w for p in train for w in ring[p]]
        lt = [w for p in train for w in lab[p]]
        base = {**zm.gm_all.params, "p_pool": 0.2}
        g_one, _ = L.fit_group(zm.sh, rt + lt, S, True, L.PARAMS, base, seed=fold)
        g_r, _ = L.fit_group(zm.sh, rt, S, True, L.PARAMS, base, seed=fold)
        g_l, _ = L.fit_group(zm.sh, lt, S, True, L.PARAMS, base, seed=fold)
        gens = {
            "C0g (fit on non-zodiac)": ({"__all__": zm.gm_all}, lambda k: "__all__", 0),
            "SV per-section, group cosmo-astro (fit on non-zodiac)": (zm.sec_models, lambda k: "cosmo-astro", 0),
            f"SV zodiac group (ring+labels pooled), fit on {len(train)} zodiac pages": ({"z": g_one, "__all__": zm.gm_all}, lambda k: "z", 3 * S + 7 + zm.sh.n_units),
            f"SV zodiac ring group + zodiac label group, fit on {len(train)} zodiac pages": ({"zr": g_r, "zl": g_l, "__all__": zm.gm_all}, lambda k: "zr" if k == "ring" else "zl", 2 * (2 * S + 7 + zm.sh.n_units)),
        }
        rr = {p: ring[p] for p in test}
        ll = {p: lab[p] for p in test}
        real = zodiac_stats(rr, ll, zm.rest.words, zm.rest.types, zm.rest.units, zm.rest.counter, test)
        jk = [zodiac_stats(rr, ll, zm.rest.words, zm.rest.types, zm.rest.units, zm.rest.counter, [q for q in test if q != p]) for p in test]
        se = {k: CI.jackknife_se([j[k] for j in jk]) for k in real}
        steps = [(k, p, n) for p in test for k, n in (("ring", len(ring[p])), ("lab", len(lab[p])))]
        for name, (models, grp, kparams) in gens.items():
            runs = []
            for s in range(1, n_seeds + 1):
                specs = [{"group": grp("ring" if k == "ring" else "lab"), "n": n, "page": p} for k, p, n in steps]
                flat = [w for part in L.sv_generate(specs, models, zm.sh, 100 * fold + s) for w in part]
                i = 0
                gr, gl = {}, {}
                for p in test:
                    gr[p] = flat[i:i + len(ring[p])]
                    i += len(ring[p])
                    gl[p] = flat[i:i + len(lab[p])]
                    i += len(lab[p])
                runs.append(zodiac_stats(gr, gl, zm.rest.words, zm.rest.types, zm.rest.units, zm.rest.counter, test))
            for k in real:
                v = CI.interval_verdict(real[k], se[k], [r[k] for r in runs])
                rows.append({"fold": fold, "test_pages": " ".join(test), "generator": name, "k_zodiac_params": kparams, "stat": k, "zodiac": real[k], "se": se[k], **v})
    return pd.DataFrame(rows)
