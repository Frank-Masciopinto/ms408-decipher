"""h25: neutral hybrid cipher = Naibbe structure + random tables (PREREG.md). No meaning claims."""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h24_neutral_cipher_robustness")); sys.path.insert(0, str(ROOT / "src"))
import h24_lib as L24  # noqa: E402
from msdecipher import mech_naibbe as MN  # noqa: E402

GLYPHS = L24.GLYPHS
EVA_UNITS = ["o", "a", "i", "e", "y", "d", "l", "r", "s", "n", "m", "k", "t", "p", "f", "q", "g", "x",
             "ch", "sh", "cth", "ckh", "cph", "cfh", "in", "iin", "ain", "aiin", "ee", "eee"]
BASE = dict(A=20, lens="base", tables=6, weights="naibbe", p_uni=17 / 36)
LENS = {"base": dict(unigram=(1, 3), prefix=(1, 2), suffix=(1, 2)), "short": dict(unigram=(1, 2), prefix=(1, 2), suffix=(1, 2)),
        "long": dict(unigram=(2, 5), prefix=(1, 3), suffix=(1, 3))}
VARIANTS = {"base": {}, "A15": dict(A=15), "A25": dict(A=25), "short": dict(lens="short"), "long": dict(lens="long"),
            "T1": dict(tables=1), "T3": dict(tables=3), "uniform": dict(weights="uniform"), "p30": dict(p_uni=.3), "p70": dict(p_uni=.7)}


def params(variant): return {**BASE, **VARIANTS[variant]}


def write_tables(path, A, lens, seed):
    """Random tables in naibbe_tables.csv format (all 6 table names always written)."""
    rng = random.Random(seed); al = GLYPHS[:A]; rows = []
    for st in ("unigram", "prefix", "suffix"):
        lo, hi = LENS[lens][st]
        for t in MN.TABLES:
            for l in MN.ALPHABET:
                rows.append((f"{st}_{t}_{l}", "".join(rng.choice(al) for _ in range(rng.randint(lo, hi)))))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["code", "glyphs"]); w.writerows(rows)
    return path


class NH(MN.NaibbeCipher):
    def __init__(self, tables_file, tables=6, weights="naibbe", p_uni=17 / 36):
        super().__init__(tables_file=tables_file, deck=78, p_unigram=p_uni, max_retries=50)
        self.ntab, self.weights = tables, weights

    def _deck(self, rng):
        names = MN.TABLES[: self.ntab]
        w = MN.CARD_WEIGHTS[78] if self.weights == "naibbe" else {t: 13 for t in MN.TABLES}
        d = [t for t in names for _ in range(w[t])]; rng.shuffle(d); return d


def make_cipher(variant, seed, tdir):
    p = params(variant); f = write_tables(Path(tdir) / f"nh_{variant}_s{seed}.csv", p["A"], p["lens"], 1000 + seed)
    return NH(f, p["tables"], p["weights"], p["p_uni"])


def eva_render(seed, A):
    rng = random.Random(7000 + seed); u = EVA_UNITS[:]; rng.shuffle(u); return dict(zip(GLYPHS[:A], u[:A]))


def decodable_share(cipher, toks, labs):
    ok = [cipher.decrypt_word(t) is not None for t, l in zip(toks, labs) if l is not None]
    return sum(ok) / max(1, len(ok))
