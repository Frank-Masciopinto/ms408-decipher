"""Library for h05: zodiac pages of MS 408 as a crib source.

Facts the analysis starts from (all checked against the transcription header comments and the page images in data/images/native):
* 12 zodiac pages f70v2..f73v show 10 signs (Aries and Taurus are drawn twice, on two pages of 15 nymphs each; Aquarius and Capricorn are missing,
  f74 was cut out).
* In the centre of each diagram there is a ROMAN-script word (a French/Occitan/Catalan-looking month name, in a different hand: Mars, Abril, May ...)
  that is NOT Voynichese and is not in the Voynichese transcription (it is only mentioned in the header comments).
* The Voynichese text on these pages is (i) 2-4 rings of circular text (loci type Cc) and (ii) one short label per nymph/star (loci type Lz),
  ~15 or ~30 per page. Nothing in the transcription is a 'sign name'; the month words are the only names, and they are Roman.
"""
from __future__ import annotations

import itertools
import math
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h01_tone_sheet"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h02_full_tone_map"))
from msdecipher.segment import Segmenter, PRESETS  # noqa: E402

TR = ROOT / "data" / "transcriptions" / "ZL3b-n.txt"
SEG = Segmenter(PRESETS["collapsed"], name="collapsed")

# ---------------------------------------------------------------------------------------------- the 12 pages
# sign per page after Stolfi's zodiac note (ic.unicamp.br/~stolfi/voynich/Notes/040/data-sections/zod), voynich.nu quire 11/12 pages and my own check of the images
# (pdf page: f70v2 = 128 (left), f70v1 = 129, f71r = 130, f71v/f72r1/f72r2/f72r3 = 131, f72v3/f72v2 = 132, f72v1 = 133, f73r = 134, f73v = 135).
PAGES = [
    # folio, sign, roman word near the centre (reading by Stolfi/Zandbergen/Inamidst; ? = disputed), pdf page(s), what I saw in the image
    ("f70v2", "Pisces", "Mars", "128", "two fish; Roman word under them; two stars in centre; 29-30 nymphs in two rings plus ring text"),
    ("f70v1", "Aries", "Abril", "129", "ram eating a plant (dark); Roman word under it; 5 inner + 10 outer nymphs"),
    ("f71r", "Aries", "Abril", "130", "ram (light) with plant; Roman word under it; 5 inner + 10 outer nymphs, clothed, in barrels"),
    ("f71v", "Taurus", "May", "131 (1st panel)", "bull (light) at a manger; 15 nymphs"),
    ("f72r1", "Taurus", "May", "131 (2nd panel)", "red bull (dark); hole in the vellum on the inner band; 15 nymphs"),
    ("f72r2", "Gemini", "Yuny?", "131 (3rd panel)", "two people holding hands; 30 nymphs, 5 above the circle"),
    ("f72r3", "Cancer", "Jollet?", "131 (4th panel)", "red crab; 30 nymphs, 12 in the outer band"),
    ("f72v3", "Leo", "Augst", "132 (left)", "lion; 30 nymphs"),
    ("f72v2", "Virgo", "Septembre?", "132 (right)", "standing woman in blue with a plant/star; 30 nymphs"),
    ("f72v1", "Libra", "Octembre", "133", "balance scales; Roman word under them; hole in vellum; 30 nymphs"),
    ("f73r", "Scorpio", "Novembre", "134", "greenish four-legged animal with curved tail (looks like a lizard) and a star; 30 nymphs, 4 above the circle"),
    ("f73v", "Sagittarius", "Decembre?", "135", "man with a crossbow; 30 nymphs, 4 above the circle"),
]
SIGNS = ["Pisces", "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius"]
MISSING = ["Capricorn", "Aquarius"]
PAGE_SIGN = {p[0]: p[1] for p in PAGES}
FOLIOS = [p[0] for p in PAGES]

# ---------------------------------------------------------------------------------------------- extraction

LOC = re.compile(r"^<(f\d+[rv]\d?)\.(\d+),([@+&*=\-])(\w+)>\s*(?:<!([^>]*)>)?\s*(.*)$")
BAND_KEYS = [("central", "centre"), ("top", "top"), ("outer", "outer"), ("second", "outer"), ("middle", "middle"), ("inner", "inner")]


def _words(raw: str) -> list[str]:
    raw = re.sub(r"<[^>]*>", "", raw)
    raw = re.sub(r"\{([^}]*)\}", r"X", raw)            # {ckhh} style ligatures -> one glyph placeholder
    raw = re.sub(r"@\d+;", "X", raw)                   # rare glyph codes
    raw = re.sub(r"\[([^:\]]*):[^\]]*\]", r"\1", raw)  # [a:b] alternatives: keep first reading
    return [w for w in re.split(r"[.,\-]+", raw) if w]


def readable(w: str) -> bool:
    return bool(w) and not any(c in w for c in "?X*!")


def extract_loci(path: Path = TR) -> pd.DataFrame:
    """One row per locus (ring text Cc and nymph/star label Lz) of the 12 zodiac pages, with band (outer/middle/inner/top/centre) taken from the
    transcriber's comment lines, clock position of the nymph, and the label words."""
    rows, folio, band, ring = [], None, "unspecified", 0
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        m = re.match(r"^<(f\d+[rv]\d?)>", line)
        if m:
            folio, band, ring = m.group(1), "unspecified", 0
            continue
        if folio not in PAGE_SIGN:
            continue
        if line.startswith("#"):
            low = line.lower()
            if any(k in low for k in ("label", "nymph", "ring", "band", "circle", "row", "star")):
                for key, name in BAND_KEYS:
                    if re.search(rf"\b{key}\b", low) and "text" not in low.split(key)[0][-6:]:
                        band = name
                        break
            continue
        m = LOC.match(line)
        if not m or m.group(1) != folio:
            continue
        _, num, loc, ltype, clock, rest = m.groups()
        if ltype not in ("Cc", "Lz"):
            continue
        if ltype == "Cc":
            ring += 1
        rows.append({"folio": folio, "sign": PAGE_SIGN[folio], "locus": f"{folio}.{num}", "num": int(num), "ltype": ltype,
                     "ring_index_outer_to_inner": ring if ltype == "Cc" else None, "band": band if ltype == "Lz" else f"C{ring}",
                     "clock": clock or "", "raw": rest.strip(), "words": _words(rest)})
    df = pd.DataFrame(rows)
    df["n_words"] = df.words.map(len)
    return df


def labels(df: pd.DataFrame) -> pd.DataFrame:
    return df[df.ltype == "Lz"].reset_index(drop=True)


def ring_text(df: pd.DataFrame) -> pd.DataFrame:
    return df[df.ltype == "Cc"].reset_index(drop=True)


def units(w: str) -> tuple:
    return tuple(SEG(w))


# ---------------------------------------------------------------------------------------------- candidate name lists (letters only)

def strip_marks(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z\u0590-\u05ff\u0600-\u06ff]", "", s.replace("ß", "ss"))


def _order(d: dict) -> list[str]:
    """Names listed per page in page order (Aries and Taurus appear twice)."""
    per_sign = [d[s] for s in SIGNS]
    return [per_sign[SIGNS.index(PAGE_SIGN[f])] for f in FOLIOS]


SIGN_NAMES = {
    "latin": dict(zip(SIGNS, "pisces aries taurus gemini cancer leo virgo libra scorpio sagittarius".split())),
    "italian": dict(zip(SIGNS, "pesci ariete toro gemelli cancro leone vergine bilancia scorpione sagittario".split())),
    "french": dict(zip(SIGNS, "poissons belier taureau gemeaux cancer lion vierge balance scorpion sagittaire".split())),
    "spanish": dict(zip(SIGNS, "piscis aries tauro geminis cancer leo virgo libra escorpio sagitario".split())),
    "catalan": dict(zip(SIGNS, "peixos aries taure bessons cranc lleo verge balanca escorpi sagitari".split())),
    "occitan": dict(zip(SIGNS, "peisses belier taure bessons cranc leon vierge balanca escorpion sagitari".split())),
    "german": dict(zip(SIGNS, "fische widder stier zwillinge krebs lowe jungfrau waage skorpion schutze".split())),
    "hebrew": dict(zip(SIGNS, "דגים טלה שור תאומים סרטן אריה בתולה מאזניים עקרב קשת".split())),
    "arabic": dict(zip(SIGNS, "حوت حمل ثور جوزاء سرطان اسد سنبلة ميزان عقرب قوس".split())),
}
MONTH_NAMES = {   # page order: March April April May May June July August September October November December
    "latin": "martius aprilis aprilis maius maius iunius iulius augustus september october november december".split(),
    "italian": "marzo aprile aprile maggio maggio giugno luglio agosto settembre ottobre novembre dicembre".split(),
    "french": "mars avril avril mai mai juin juillet aout septembre octobre novembre decembre".split(),
    "catalan": "marc abril abril maig maig juny juliol agost setembre octubre novembre desembre".split(),
    "occitan": "marc abrial abrial mai mai junh julh agost setembre octobre novembre decembre".split(),
    "german": "marz april april mai mai juni juli august september oktober november dezember".split(),
    "roman_words_on_the_pages": "mars abril abril may may yony jollet augst septembre octembre novembre decembre".split(),
    "roman_words_schwerdtfeger_via_bax": "mars aberil aberil may may yony jolliz augst septembr octembre novembre decebre".split(),
    "arabic_west_kunitsch": "مارس ابريل ابريل مايه مايه يونيه يوليه اغست شتنبر اكتوبر نونبر دجنبر".split(),
}


def name_lists() -> dict[str, list[str]]:
    out = {}
    for lang, d in SIGN_NAMES.items():
        out[f"sign:{lang}"] = [strip_marks(x) for x in _order(d)]
    for lang, l in MONTH_NAMES.items():
        out[f"month:{lang}"] = [strip_marks(x) for x in l]
    return out


def lang_of(listname: str) -> str:
    l = listname.split(":")[1]
    if l.startswith("roman_words"):
        return "latin"
    return {"arabic_west_kunitsch": "arabic"}.get(l, l)


# ---------------------------------------------------------------------------------------------- statistics helpers

def pattern(seq) -> tuple:
    seen: dict = {}
    return tuple(seen.setdefault(x, len(seen)) for x in seq)


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def spearman(x, y) -> float:
    rx, ry = pd.Series(x).rank().values, pd.Series(y).rank().values
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def perm_corr_p(x, y, n_perm=20000, seed=0):
    """Spearman between x (per sign) and y (names); null = permuting which name goes with which sign. Two-sided p with +1 correction (exact when 10! is sampled enough)."""
    rng = np.random.default_rng(seed)
    obs = spearman(x, y)
    if np.isnan(obs):
        return obs, float("nan")
    ry = pd.Series(y).rank().values
    rx = pd.Series(x).rank().values
    rxc = rx - rx.mean()
    cnt = 0
    for _ in range(n_perm):
        p = rng.permutation(len(ry))
        v = ry[p] - ry.mean()
        r = (v * rxc).sum() / math.sqrt((v ** 2).sum() * (rxc ** 2).sum())
        cnt += abs(r) >= abs(obs) - 1e-12
    return obs, (cnt + 1) / (n_perm + 1)


# ---------------------------------------------------------------------------------------------- page texts

@dataclass
class ZText:
    """Word tokens (strings) of the zodiac pages, by page and kind."""
    labels: dict      # folio -> list[str] (every readable label word)
    rings: dict       # folio -> list[str] (every readable ring-text word)
    label_phrases: dict   # folio -> list[list[str]]

    def sign_words(self, sign: str, kinds=("labels", "rings")) -> list[str]:
        out = []
        for f in FOLIOS:
            if PAGE_SIGN[f] == sign:
                for k in kinds:
                    out += getattr(self, k)[f]
        return out

    def all_words(self, kinds=("labels", "rings")) -> list[str]:
        return [w for s in SIGNS for w in self.sign_words(s, kinds)]


def build_ztext(df: pd.DataFrame | None = None) -> ZText:
    df = extract_loci() if df is None else df
    lab = {f: [] for f in FOLIOS}
    ring = {f: [] for f in FOLIOS}
    ph = {f: [] for f in FOLIOS}
    for r in df.itertuples():
        ws = [w for w in r.words if readable(w)]
        if r.ltype == "Lz":
            lab[r.folio] += ws
            if r.words:
                ph[r.folio].append(list(r.words))
        else:
            ring[r.folio] += ws
    return ZText(lab, ring, ph)


def ms_words(exclude_zodiac: bool = True) -> list[tuple[str, str]]:
    """(folio, word) for every readable running-text word (P loci) of the transcription."""
    import h01_lib as H1
    out = []
    for f in H1.load_folios(TR, "P"):
        if exclude_zodiac and f.folio in PAGE_SIGN:
            continue
        for w in f.tokens:
            if readable(w):
                out.append((f.folio, w))
    return out


# ---------------------------------------------------------------------------------------------- similarity between pages

def bigram_vec(words: list[str], vocab: dict) -> np.ndarray:
    v = np.zeros(len(vocab))
    for w in words:
        u = ("^",) + units(w) + ("$",)
        for a, b in zip(u, u[1:]):
            if (a, b) in vocab:
                v[vocab[(a, b)]] += 1
    return v


def bigram_vocab(words_by_page: dict) -> dict:
    s = set()
    for ws in words_by_page.values():
        for w in ws:
            u = ("^",) + units(w) + ("$",)
            s.update(zip(u, u[1:]))
    return {k: i for i, k in enumerate(sorted(s, key=str))}


def page_similarity(words_by_page: dict, kind: str = "bigram") -> pd.DataFrame:
    keys = list(words_by_page)
    if kind == "bigram":
        voc = bigram_vocab(words_by_page)
        V = np.array([bigram_vec(words_by_page[k], voc) for k in keys])
    else:  # word types
        voc = {w: i for i, w in enumerate(sorted({w for ws in words_by_page.values() for w in ws}))}
        V = np.zeros((len(keys), len(voc)))
        for i, k in enumerate(keys):
            for w in words_by_page[k]:
                V[i, voc[w]] += 1
    V = np.sqrt(V)                                     # Hellinger-like damping of very frequent items
    V = V / np.linalg.norm(V, axis=1, keepdims=True).clip(1e-9)
    return pd.DataFrame(V @ V.T, index=keys, columns=keys)


def same_sign_pair_test(S: pd.DataFrame, n_perm: int = 20000, seed: int = 0) -> dict:
    """Do the two pages of Aries and the two of Taurus resemble each other more than other page pairs do?
    Statistic: mean similarity of the 2 same-sign pairs. Nulls: (a) all 66 page pairs drawn in pairs-of-pairs at random; (b) only ADJACENT page pairs that are not
    the same sign (f70v2-f70v1, f71r-f71v, f72r1-f72r2 ...): controls for 'neighbouring pages resemble each other' (same quire, scribe state, drawing run)."""
    idx = list(S.index)
    same = [("f70v1", "f71r"), ("f71v", "f72r1")]
    obs = np.mean([S.loc[a, b] for a, b in same])
    allp = [(a, b) for i, a in enumerate(idx) for b in idx[i + 1:]]
    vals = np.array([S.loc[a, b] for a, b in allp])
    rng = np.random.default_rng(seed)
    # random pair-of-pairs without replacement of pages
    cnt = 0
    for _ in range(n_perm):
        p = rng.permutation(len(idx))[:4]
        cnt += np.mean([S.iloc[p[0], p[1]], S.iloc[p[2], p[3]]]) >= obs - 1e-12
    adj = [(idx[i], idx[i + 1]) for i in range(len(idx) - 1) if (idx[i], idx[i + 1]) not in same and PAGE_SIGN[idx[i]] != PAGE_SIGN[idx[i + 1]]]
    adjv = np.array([S.loc[a, b] for a, b in adj])
    return {"obs_mean_same_sign_pairs": obs, "p_random_pair_of_pairs": (cnt + 1) / (n_perm + 1), "mean_all_pairs": float(vals.mean()),
            "mean_adjacent_different_sign": float(adjv.mean()), "n_adjacent_diff": len(adj), "max_adjacent_diff": float(adjv.max()),
            "same_sign_pairs": [float(S.loc[a, b]) for a, b in same], "rank_of_each_same_pair_among_66": [int((vals >= S.loc[a, b]).sum()) for a, b in same]}


def group_cohesion_test(S: pd.DataFrame, group: list[str]) -> dict:
    """Mean within-group similarity of ``group`` (e.g. the four '-bre' months) vs ALL 4-subsets of the 12 pages (exact) and vs contiguous windows."""
    idx = list(S.index)
    k = len(group)

    def coh(g):
        return float(np.mean([S.loc[a, b] for a, b in itertools.combinations(g, 2)]))
    obs = coh(group)
    allv = np.array([coh(g) for g in itertools.combinations(idx, k)])
    win = np.array([coh(idx[i:i + k]) for i in range(len(idx) - k + 1)])
    return {"obs": obs, "p_all_subsets": float((allv >= obs - 1e-12).mean()), "n_subsets": len(allv),
            "p_contiguous_windows": float((win >= obs - 1e-12).mean()), "n_windows": len(win), "mean_all": float(allv.mean())}


def label_classification(words_by_page: dict, n_perm: int = 300, seed: int = 0) -> dict:
    """Leave-one-LABEL-out naive-Bayes (unit bigrams, add-0.5) prediction of the page from a label word; null = shuffling page labels over labels."""
    items = [(p, w) for p, ws in words_by_page.items() for w in ws]
    voc = bigram_vocab(words_by_page)
    X = np.array([bigram_vec([w], voc) for _, w in items])
    pages = sorted(words_by_page)
    y = np.array([pages.index(p) for p, _ in items])

    def acc(y):
        K = len(pages)
        C = np.zeros((K, X.shape[1]))
        for k in range(K):
            C[k] = X[y == k].sum(0)
        tot = C.sum(1, keepdims=True)
        n_k = np.bincount(y, minlength=K).astype(float)
        correct = 0
        for i in range(len(y)):
            Ci, ti, ni = C.copy(), tot.copy(), n_k.copy()
            Ci[y[i]] -= X[i]
            ti[y[i]] -= X[i].sum()
            ni[y[i]] -= 1
            lp = ((X[i] * np.log((Ci + 0.5) / (ti + 0.5 * X.shape[1]))).sum(1) + np.log(ni / ni.sum()))
            correct += int(np.argmax(lp) == y[i])
        return correct / len(y)
    obs = acc(y)
    rng = np.random.default_rng(seed)
    null = np.array([acc(rng.permutation(y)) for _ in range(n_perm)])
    return {"acc": obs, "null_mean": float(null.mean()), "null_max": float(null.max()), "p": (int((null >= obs).sum()) + 1) / (n_perm + 1), "n_labels": len(y),
            "n_classes": len(pages), "chance_majority": float(np.bincount(y).max() / len(y))}


def chi2_perm(words_by_page: dict, featfn, n_perm: int = 3000, seed: int = 0, min_count: int = 8) -> dict:
    """Chi-square between page and a categorical feature of the label word (e.g. first unit), p by shuffling the page labels over labels."""
    items = [(p, featfn(w)) for p, ws in words_by_page.items() for w in ws]
    cats = Counter(f for _, f in items)
    keep = {c for c, n in cats.items() if n >= min_count}
    items = [(p, f if f in keep else "other") for p, f in items]
    pages = sorted(words_by_page)
    cl = sorted({f for _, f in items}, key=str)
    P = np.array([pages.index(p) for p, _ in items])
    F = np.array([cl.index(f) for _, f in items])

    def chi2(P):
        T = np.zeros((len(pages), len(cl)))
        np.add.at(T, (P, F), 1)
        E = T.sum(1, keepdims=True) * T.sum(0, keepdims=True) / T.sum()
        return float(((T - E) ** 2 / E.clip(1e-9)).sum())
    obs = chi2(P)
    rng = np.random.default_rng(seed)
    null = np.array([chi2(rng.permutation(P)) for _ in range(n_perm)])
    return {"chi2": obs, "null_mean": float(null.mean()), "p": (int((null >= obs).sum()) + 1) / (n_perm + 1), "n_categories": len(cl), "n": len(P)}


# ---------------------------------------------------------------------------------------------- isomorph (name-in-page) test

def window_patterns(u: tuple, n: int):
    for i in range(len(u) - n + 1):
        yield pattern(u[i:i + n])


class IsoIndex:
    """Counts of words by (length, repeat pattern) at unit level, for the whole MS and per sign; exact (whole token) and window (contiguous inside a token)."""

    def __init__(self, ms_tokens: list[str], ztext: ZText, kinds=("labels", "rings")):
        self.ms_n = len(ms_tokens)
        self.ms_exact = Counter(pattern(units(w)) for w in ms_tokens)
        self.sign_exact = {s: Counter(pattern(units(w)) for w in ztext.sign_words(s, kinds)) for s in SIGNS}
        self.sign_n = {s: len(ztext.sign_words(s, kinds)) for s in SIGNS}
        self.ms_window: dict[int, Counter] = {}
        self.sign_window: dict = {}
        self._ms_units = [units(w) for w in ms_tokens]
        self._sign_units = {s: [units(w) for w in ztext.sign_words(s, kinds)] for s in SIGNS}

    def _win(self, n):
        if n not in self.ms_window:
            c = Counter()
            for u in self._ms_units:
                for p in window_patterns(u, n):
                    c[p] += 1
            self.ms_window[n] = c
            self.sign_window[n] = {s: Counter(p for u in us for p in window_patterns(u, n)) for s, us in self._sign_units.items()}
        return self.ms_window[n], self.sign_window[n]

    def z(self, sign: str, name: str, mode: str) -> float:
        """Binomial-style z of the number of tokens (or windows) in the sign's text isomorphic to ``name`` against the MS-wide rate."""
        pat = pattern(name)
        n = len(pat)
        if mode == "exact":
            r = (self.ms_exact[pat] + 0.5) / (self.ms_n + 1)
            c = self.sign_exact[sign][pat]
            N = self.sign_n[sign]
        else:
            ms_w, sg_w = self._win(n)
            tot = sum(ms_w.values())
            r = (ms_w[pat] + 0.5) / (tot + 1)
            c = sg_w[sign][pat]
            N = sum(sg_w[sign].values())
        return (c - N * r) / math.sqrt(max(N * r * (1 - r), 1e-9)), c, N * r


def iso_matrix(idx: IsoIndex, names_by_sign: list[str], mode: str) -> np.ndarray:
    return np.array([[idx.z(s, n, mode)[0] for n in names_by_sign] for s in SIGNS])


def perm_diag_sum(Z: np.ndarray, n_perm: int = 20000, seed: int = 0) -> dict:
    """Sum over signs of Z[sign, name assigned]; the true assignment is the diagonal; null = random permutations of the names over signs."""
    rng = np.random.default_rng(seed)
    n = Z.shape[0]
    obs = float(np.trace(Z))
    nulls = np.array([Z[np.arange(n), rng.permutation(n)].sum() for _ in range(n_perm)])
    return {"obs": obs, "null_mean": float(nulls.mean()), "null_sd": float(nulls.std()), "z": float((obs - nulls.mean()) / max(nulls.std(), 1e-9)),
            "p": (int((nulls >= obs).sum()) + 1) / (n_perm + 1)}


def names_by_sign(lst: list[str]) -> list[str]:
    """Collapse the per-page list (12) to one name per sign (10)."""
    d = {}
    for f, nm in zip(FOLIOS, lst):
        d.setdefault(PAGE_SIGN[f], nm)
    return [d[s] for s in SIGNS]


# ---------------------------------------------------------------------------------------------- crib-drag

def lexicons(n_tokens: int = 300000, min_count: int = 2) -> dict[str, set]:
    """Word-type lexicons per language from the repo's control texts (types seen >= min_count times in the first n_tokens tokens)."""
    from msdecipher import controls_text as CT
    src = {"latin": ["la_vulgate", "la_celsus"], "italian": ["it_dante", "it_manzoni"], "german": ["de_faust"], "hebrew": ["he_tanakh"], "arabic": ["ar_quran"]}
    out = {}
    for lang, ids in src.items():
        c = Counter()
        for i in ids:
            try:
                c.update(CT.load_tokens(i, n_tokens))
            except FileNotFoundError:
                pass
        out[lang] = {w for w, n in c.items() if n >= min_count and len(w) >= 2}
    return out


def to_lex_alphabet(name: str, lang: str) -> str:
    return name.replace("v", "u").replace("j", "i") if lang == "latin" else name


def pick_candidates(sign_units: dict, names: list[str], global_count: Counter) -> dict:
    """For each sign the most frequent token (in the sign's own text) that is isomorphic (same length and repeat pattern, unit level) to its name."""
    out = {}
    for s, nm in zip(SIGNS, names):
        pat = pattern(nm)
        cnt = Counter(u for u in sign_units[s] if len(u) == len(nm) and pattern(u) == pat)
        if cnt:
            best = max(cnt, key=lambda u: (cnt[u], -global_count[u]))
            out[s] = (best, cnt[best])
    return out


def derive_mapping(cands: dict, names_by_s: dict) -> tuple[dict, int, int]:
    votes: dict = defaultdict(Counter)
    for s, (u, _) in cands.items():
        for a, b in zip(u, names_by_s[s]):
            votes[a][b] += 1
    mp = {a: c.most_common(1)[0][0] for a, c in votes.items()}
    conflicts = sum(1 for c in votes.values() if len(c) > 1)
    letters_shared = len(mp) - len(set(mp.values()))   # many-to-one violations
    return mp, conflicts, letters_shared


def transfer_hits(type_counts: Counter, mapping: dict, lex: set, skip: set = frozenset()) -> tuple[int, int, int]:
    """Tokens (and types) whose units are ALL in the mapping, length >= 3, and whose mapped string is a lexicon word; also the number of fully mapped tokens."""
    hit_tok = hit_typ = full = 0
    for u, n in type_counts.items():
        if len(u) < 3 or u in skip:
            continue
        if all(a in mapping for a in u):
            full += n
            if "".join(mapping[a] for a in u) in lex:
                hit_tok += n
                hit_typ += 1
    return hit_tok, hit_typ, full


def crib_run(names_by_s: dict, sign_units: dict, glob: Counter, zod_types: Counter, rest_types: Counter, lex: set) -> dict:
    cands = pick_candidates(sign_units, [names_by_s[s] for s in SIGNS], glob)
    mp, conf, many = derive_mapping(cands, names_by_s)
    skip = {u for u, _ in cands.values()}
    z = transfer_hits(zod_types, mp, lex, skip)
    r = transfer_hits(rest_types, mp, lex, skip)
    return {"n_signs_with_candidate": len(cands), "n_units_mapped": len(mp), "conflicts": conf, "many_to_one": many,
            "zod_hits": z[0], "zod_hit_types": z[1], "zod_fullmapped": z[2], "rest_hits": r[0], "rest_hit_types": r[1], "rest_fullmapped": r[2],
            "candidates": {s: ("".join(u), c) for s, (u, c) in cands.items()}, "mapping": mp}


def random_names_like(names: list[str], lex_by_len: dict, rng) -> list[str]:
    return [rng.choice(lex_by_len[len(n)]) if lex_by_len.get(len(n)) else n for n in names]
