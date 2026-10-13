"""h29: Spearman on stored fingerprints, and fixed-length toy Naibbe tables (PREREG.md). No meaning claims."""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h25_neutral_hybrid_cipher"))
sys.path.insert(0, str(ROOT / "src"))
import h25_lib as H25  # noqa: E402
from msdecipher import mech_naibbe as MN  # noqa: E402

ALPHABET_N = 20
H26_PROPS = ("mean_len", "rigidity", "H1", "decodable")
H26_CSV = ROOT / "hypotheses" / "h26_neutral_glyph_grammar_tables" / "results" / "fingerprints_bifolium.csv"
H25_CSV = ROOT / "hypotheses" / "h25_neutral_hybrid_cipher" / "results" / "fingerprints_bifolium.csv"
H24_CSV = ROOT / "hypotheses" / "h24_neutral_cipher_robustness" / "results" / "fingerprints_bifolium.csv"


def _glyphs():
    return H25.GLYPHS[:ALPHABET_N]


def _draw_string(rng, alphabet, length):
    return "".join(rng.choice(alphabet) for _ in range(length))


def _distinct_pool(rng, alphabet, length, n):
    """V distinct length-L strings, capped at the size of the glyph alphabet."""
    space = len(alphabet) ** length
    target = min(int(n), space)
    pool, used = [], set()
    while len(pool) < target:
        s = _draw_string(rng, alphabet, length)
        if s not in used:
            used.add(s)
            pool.append(s)
    return pool


def _draw_distinct(rng, alphabet, length, used):
    """One new string, resampling collisions. Reuse is unavoidable once the space is exhausted."""
    space = len(alphabet) ** length
    if len(used) >= space:
        return _draw_string(rng, alphabet, length)
    while True:
        s = _draw_string(rng, alphabet, length)
        if s not in used:
            used.add(s)
            return s


def toy_codes(L, V, seed):
    """Rows (code, glyphs) for 6 tables × 23 letters × 3 states, plus the shared suffix pool.

    Unigram and prefix codes have length L and are distinct inside each (state, table).
    The suffix pool is built first: V distinct length-L strings, or every string of that
    length when fewer than V exist. Each suffix slot then draws from that pool with replacement.
    """
    rng = random.Random(seed)
    alphabet = _glyphs()
    pool = _distinct_pool(rng, alphabet, L, V)
    chosen = {}
    for state in ("unigram", "prefix"):
        for table in MN.TABLES:
            used = set()
            for letter in MN.ALPHABET:
                chosen[(state, table, letter)] = _draw_distinct(rng, alphabet, L, used)
    for table in MN.TABLES:
        for letter in MN.ALPHABET:
            chosen[("suffix", table, letter)] = rng.choice(pool)
    rows = []
    for state in ("unigram", "prefix", "suffix"):
        for table in MN.TABLES:
            for letter in MN.ALPHABET:
                rows.append((f"{state}_{table}_{letter}", chosen[(state, table, letter)]))
    return rows, pool


def write_toy_tables(path, L, V, seed):
    """Write a naibbe_tables.csv (columns code, glyphs) and return the path."""
    rows, _pool = toy_codes(L, V, seed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["code", "glyphs"])
        writer.writerows(rows)
    return path


def _load_table(src):
    if isinstance(src, pd.DataFrame):
        return src.copy()
    return pd.read_csv(src)


def _rho(frame, x, y):
    return float(spearmanr(frame[x], frame[y]).correlation)


def spearman_report(h26_csv, h25_csv, h24_csv):
    """Part 1, on the subsets named in PREREG.md.

    h26: it_boccaccio, eva, grammar other than naibbe; rho of m_distance and of D4
    against mean_len, rigidity, H1, decodable.
    h25: it_boccaccio, split by render; rho of m_distance and of D4 against decodable.
    h24: mean distance and mean D4 by cipher (rows that have a cipher).
    """
    h26 = _load_table(h26_csv)
    sub = h26[(h26["src"] == "it_boccaccio") & (h26["render"] == "eva") & (h26["grammar"] != "naibbe")]
    h26_out = {"n": int(len(sub))}
    for target in ("m_distance", "D4"):
        h26_out[target] = {prop: _rho(sub, prop, target) for prop in H26_PROPS}

    h25 = _load_table(h25_csv)
    boc = h25[h25["src"] == "it_boccaccio"]
    h25_out = {}
    for render, group in boc.groupby("render", sort=True):
        h25_out[str(render)] = {
            "n": int(len(group)),
            "m_distance": {"decodable": _rho(group, "decodable", "m_distance")},
            "D4": {"decodable": _rho(group, "decodable", "D4")},
        }

    h24 = _load_table(h24_csv)
    known = h24[h24["cipher"].notna()]
    family = []
    for cipher, group in known.groupby("cipher", sort=True):
        family.append({
            "cipher": str(cipher),
            "n": int(len(group)),
            "mean_distance": float(group["m_distance"].mean()),
            "mean_D4": float(group["D4"].mean()),
        })
    return {"h26": h26_out, "h25": h25_out, "h24_by_cipher": family}
