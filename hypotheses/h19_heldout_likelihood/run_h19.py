"""Run h19 (PREREG.md). Usage: python run_h19.py [cell ...]  -> results/cell_<name>.json + token tables."""
import json
import math
import sys
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

import h19_lib as L
from h19_lib import HERE, ROOT

R = HERE / "results"; R.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "hypotheses" / "h14_line_position_controls"))
CTRL = ["la_celsus", "la_vulgate", "it_sidrach", "it_dante"]
CIPH = {"naibbe_la_pliny": "la_pliny_herbal", "naibbe_it_ariosto": "it_ariosto"}
NTOK, PAGE = 10500, 150
MODELS = ["G", "SLOT", "KN1", "KN2", "KN3", "COPY1", "COPY3"]


# ---------------------------------------------------------------- data
def ms_cells():
    import h14_lib as L14
    d = L14.table(); q = pd.read_csv(ROOT / "data" / "quires.csv", dtype=str).set_index("page"); d["bif"] = d.folio.map(q.bifolium_id)
    cells = {}
    for hl in ["1A", "2B", "3B"]:
        s = d[d.HL == hl]; pages = []
        for f, g in s.groupby("folio", sort=False):
            pages.append(dict(id=f, words=g.w.tolist(), init=g.is_init.tolist(), bif=g.bif.iloc[0], quire=g.quire.iloc[0]))
        cells["MS_" + hl] = dict(kind="ms", seg="eva", pages=pages)
    return cells


def paginate(tokens, name, kind, seg):
    pages = []
    for i in range(0, len(tokens), PAGE):
        p = i // PAGE; qn, pin = p // 8, p % 8
        pages.append(dict(id=f"{name}_{p}", words=tokens[i:i + PAGE], init=[False] * len(tokens[i:i + PAGE]), bif=f"{qn}-{min(pin, 7 - pin)}", quire=str(qn)))
    return dict(kind=kind, seg=seg, pages=pages)


def synth_cell(ms, lam=.2, W=20, th=dict(pk=.7, ps=.15, pd=.15, pi=.05), seed=19):
    rng = np.random.default_rng(seed); ws = [w for p in ms["MS_2B"]["pages"] for w in p["words"]]
    c = Counter(ws); vocab = list(c); pw = np.array([c[w] for w in vocab], float); pw /= pw.sum()
    ch = Counter("".join(ws)); chars = list(ch); pc = np.array([ch[x] for x in chars], float); pc /= pc.sum()
    def edit(s):
        out = []
        for i in range(len(s) + 1):
            while rng.random() < th["pi"]: out.append(chars[rng.choice(len(chars), p=pc)])
            if i == len(s): break
            r = rng.random()
            if r < th["pk"]: out.append(s[i])
            elif r < th["pk"] + th["ps"]: out.append(chars[rng.choice(len(chars), p=pc)])
        return "".join(out) or s
    toks = []
    for i in range(NTOK):
        k = min(W, i % PAGE)
        if k and rng.random() < lam: toks.append(edit(toks[-rng.integers(1, k + 1)]))
        else: toks.append(vocab[rng.choice(len(vocab), p=pw)])
    return paginate(toks, "synth", "synth", "eva")


def all_cells():
    from msdecipher.controls_text import load_tokens
    from msdecipher.mech_naibbe import NaibbeCipher
    cells = ms_cells()
    for cid in CTRL: cells["CTRL_" + cid] = paginate(load_tokens(cid, NTOK), cid, "ctrl", "char")
    for name, cid in CIPH.items():
        cells["CIPH_" + name] = paginate(NaibbeCipher().encrypt(load_tokens(cid, None), seed=0, n_words_out=NTOK), name, "ciph", "eva")
    cells["SYNTH_copy0.2"] = synth_cell(cells)
    return cells


_PLAIN = {}


def plain_lms():
    if not _PLAIN:
        from msdecipher.controls_text import load_tokens
        from msdecipher.mech_naibbe import clean_plaintext
        for lang, ids in [("la", ["la_isidore", "la_augustine"]), ("it", ["it_manzoni", "it_sidrach"])]:
            _PLAIN[lang] = L.LetterLM(3).fit(clean_plaintext(" ".join(w for i in ids for w in load_tokens(i, None))))
    return _PLAIN


# ---------------------------------------------------------------- models on one split
def seg_fn(kind):
    if kind == "eva":
        sys.path.insert(0, str(ROOT / "hypotheses" / "h13_top_word_context")); import h13_lib
        return h13_lib.SEG
    return tuple


class Fitted:
    def __init__(self, pages, seg, slot_hyper=None):
        from msdecipher.mech_grammars import LearnedUnit
        ws = [w for p in pages for w in p["words"]]
        self.G = L.CharLM(4).fit(ws); self.kn = {n: L.KN(n, self.G).fit([p["words"] for p in pages]) for n in (1, 2, 3)}
        self.slot = LearnedUnit(seg, "slot"); self.slot.fit(Counter(ws)); self.lu = L.char_unigram_log(ws)
        if slot_hyper is not None: self.slot.hyper = slot_hyper

    def base(self, pages):
        """per-token log2 for G, SLOT, KN1-3 on pages (history within page)."""
        out = {m: [] for m in ["G", "SLOT", "KN1", "KN2", "KN3"]}
        for p in pages:
            ws = p["words"]
            out["G"] += [self.G.logp(w) for w in ws]
            s = self.slot.logprob2(ws); g = np.array([self.G.logp(w) for w in ws])
            s = np.where(np.isfinite(s), s, -np.inf)
            out["SLOT"] += list(np.log2(.99 * 2.0 ** s + .01 * 2.0 ** g))
            for n in (1, 2, 3): out[f"KN{n}"] += [self.kn[n].logp(w, ws[:i]) for i, w in enumerate(ws)]
        return {k: np.array(v) for k, v in out.items()}

    def stripped(self, pages, copy_par):
        """for line-initial tokens with an onset: log2 of the stripped base b under each model at the same position."""
        rows = []
        for p in pages:
            ws = p["words"]
            for i, (w, ini) in enumerate(zip(ws, p["init"])):
                o, b = L.onset_parts(w) if ini else (None, None)
                rows.append((o, b, ws[:i]))
        res = {m: np.zeros(len(rows)) for m in ["SLOT", "KN1", "KN3", "COPY1", "COPY3"]}; oid = np.full(len(rows), -1)
        for j, (o, b, h) in enumerate(rows):
            if o is None: continue
            oid[j] = L.ONSETS.index(o); g = self.G.logp(b)
            s = self.slot.logprob2([b])[0]; s = s if np.isfinite(s) else -np.inf
            res["SLOT"][j] = math.log2(.99 * 2.0 ** s + .01 * 2.0 ** g)
            for n in (1, 3): res[f"KN{n}"][j] = self.kn[n].logp(b, h)
            for n, key in ((1, "COPY1"), (3, "COPY3")):
                W, th = copy_par[key]; k = min(W, len(h)); P = (1 - th["lam"] if k else 1) * 2.0 ** self.kn[n].logp(b, h)
                for lag in range(1, k + 1):
                    st = L.edit_stats(h[-lag], b)
                    if st is None: continue
                    nk, ns, nd, ni, gp, em = st
                    le = nk * math.log(th["pk"]) + ns * math.log(th["ps"]) + nd * math.log(th["pd"]) + ni * math.log(th["pi"]) + gp * math.log(1 - th["pi"]) + sum(self.lu.get(c, min(self.lu.values())) for c in em)
                    P += th["lam"] / k * math.exp(le)
                res[key][j] = math.log2(P)
        return res, oid


def inner_split(pages, rng):
    g = sorted({p["bif"] for p in pages})
    if len(g) >= 5:
        val = set(rng.choice(g, max(1, round(.2 * len(g))), replace=False))
        return [p for p in pages if p["bif"] not in val], [p for p in pages if p["bif"] in val]
    idx = rng.permutation(len(pages)); nv = max(1, round(.2 * len(pages))); vs = set(idx[:nv])
    return [p for i, p in enumerate(pages) if i not in vs], [p for i, p in enumerate(pages) if i in vs]


def run_split(train, test, cell, rng):
    seg = seg_fn(cell["seg"]); itr, iva = inner_split(train, rng)
    fi = Fitted(itr, seg); vw = [w for p in iva for w in p["words"]]; fi.slot.tune(vw); hyp = fi.slot.hyper
    bv = fi.base(iva); cdv = L.CopyData([p["words"] for p in iva])
    copy_par, copy_W = {}, {}
    for n, key in ((1, "COPY1"), (3, "COPY3")):
        best = None; allW = {}
        for W in (5, 20, 100):
            th, ll = L.copy_em(bv[f"KN{n}"], cdv, fi.lu, W); allW[W] = dict(th, ll=ll)
            if best is None or ll > best[2]: best = (W, th, ll)
        copy_par[key] = best[:2]; copy_W[key] = allW
    ff = Fitted(train, seg, hyp); bt = ff.base(test); cdt = L.CopyData([p["words"] for p in test])
    for n, key in ((1, "COPY1"), (3, "COPY3")):
        W, th = copy_par[key]; bt[key] = L.copy_score(bt[f"KN{n}"], cdt, ff.lu, W, th)
    extra = dict(copy_par={k: dict(W=v[0], **v[1]) for k, v in copy_par.items()}, copy_W=copy_W, slot_hyper=hyp)
    if cell["kind"] in ("ms", "ciph", "synth"):
        for lang, plm in plain_lms().items():
            nl = L.NaibbeLM(plm)
            pv = np.concatenate([nl.page_probs(p["words"]) for p in iva]); gv = np.array([fi.G.logp(w) for p in iva for w in p["words"]])
            with np.errstate(divide="ignore"): eps = L.mix_em(np.log2(pv), gv)
            pt = np.concatenate([nl.page_probs(p["words"]) for p in test]); gt = bt["G"]
            bt[f"NAIBBE_{lang}"] = np.log2((1 - eps) * pt + eps * 2.0 ** gt)
            extra[f"naibbe_{lang}_eps"] = eps; extra[f"naibbe_{lang}_decodable_test"] = float((pt > 0).mean())
    if cell["kind"] == "ms":
        sv, oidv = fi.stripped(iva, copy_par); initv = np.array([x for p in iva for x in p["init"]])
        st, oidt = ff.stripped(test, copy_par); initt = np.array([x for p in test for x in p["init"]])
        for m in ["SLOT", "KN1", "KN3", "COPY1", "COPY3"]:
            lv = bv[m] if m in bv else L.copy_score(bv[f"KN{m[-1]}"], cdv, fi.lu, *copy_par[m])
            th, pi = L.onset_em(lv[initv], sv[m][initv], oidv[initv])
            sc = bt[m].copy(); sc[initt] = L.onset_score(bt[m][initt], st[m][initt], oidt[initt], th, pi)
            bt[m + "+ONSET"] = sc; extra[f"onset_{m}"] = dict(theta=th, pi=dict(zip(L.ONSETS, map(float, pi))))
    return bt, extra


def crossfit_lambda(cell, folds, Wsel, rng, n_boot=500):
    """cross-fitted ML copy rate (COPY1 base): base KN1 fitted on other folds, EM pooled over held-out tokens; page bootstrap."""
    pages = cell["pages"]; order = []; base = []
    for tr, te in folds:
        G = L.CharLM(4).fit([w for i in tr for w in pages[i]["words"]]); kn = L.KN(1, G).fit([pages[i]["words"] for i in tr])
        for i in te: order.append(i); base += [kn.logp(w, []) for w in pages[i]["words"]]
    cd = L.CopyData([pages[i]["words"] for i in order]); lu = L.char_unigram_log([w for p in pages for w in p["words"]]); base = np.array(base)
    th, _ = L.copy_em(base, cd, lu, Wsel); tp = np.array(cd.tok_page); boots = []
    for _ in range(n_boot):
        m = np.bincount(rng.integers(0, len(order), len(order)), minlength=len(order)).astype(float)
        tb, _ = L.copy_em(base, cd, lu, Wsel, iters=60, init=th, tok_weight=m[tp]); boots.append(tb["lam"])
    return dict(W=Wsel, **th, lam_lo=float(np.quantile(boots, .025)), lam_hi=float(np.quantile(boots, .975)), n_boot=n_boot)


def group_folds(pages, key, k):
    g = sorted({p[key] for p in pages}); k = min(k, len(g))
    sizes = Counter(); [sizes.update({p[key]: len(p["words"])}) for p in pages]
    bins = [[] for _ in range(k)]; load = np.zeros(k)
    for gg in sorted(g, key=lambda x: -sizes[x]): j = int(np.argmin(load)); bins[j].append(gg); load[j] += sizes[gg]
    out = []
    for b in bins:
        te = [i for i, p in enumerate(pages) if p[key] in b]; tr = [i for i, p in enumerate(pages) if p[key] not in b]
        out.append((tr, te))
    return out


def run_cell(args):
    name, cell = args; rng = np.random.default_rng(abs(hash(name)) % 2 ** 32 if False else 19)
    res = {"cell": name, "kind": cell["kind"], "n_tokens": sum(len(p["words"]) for p in cell["pages"]), "n_pages": len(cell["pages"]), "schemes": {}}
    pages = cell["pages"]
    for scheme, key in (("bifolium", "bif"), ("quire", "quire")):
        folds = group_folds(pages, key, 5); tok = []; extras = []
        for fi_, (tr, te) in enumerate(folds):
            bt, ex = run_split([pages[i] for i in tr], [pages[i] for i in te], cell, rng); extras.append(ex)
            df = pd.DataFrame(bt); df["page"] = [pages[i]["id"] for i in te for _ in pages[i]["words"]]; df["fold"] = fi_
            df["init"] = [x for i in te for x in pages[i]["init"]]; df["glyphs"] = [len(w) + 1 for i in te for w in pages[i]["words"]]
            df["word"] = [w for i in te for w in pages[i]["words"]]; tok.append(df)
        tok = pd.concat(tok, ignore_index=True); tok.to_csv(R / f"tokens_{name}_{scheme}.csv.gz", index=False)
        res["schemes"][scheme] = dict(n_folds=len(folds), extras=extras)
        if scheme == "bifolium":
            Ws = Counter(e["copy_par"]["COPY1"]["W"] for e in extras).most_common(1)[0][0]
            res["crossfit_copy"] = crossfit_lambda(cell, folds, Ws, rng)
    json.dump(res, open(R / f"cell_{name}.json", "w"), indent=1, default=float)
    return name


if __name__ == "__main__":
    cells = all_cells(); want = sys.argv[1:] or list(cells)
    plain_lms()
    with Pool(min(7, len(want))) as pool:
        for n in pool.imap_unordered(run_cell, [(n, cells[n]) for n in want]): print("done", n, flush=True)
