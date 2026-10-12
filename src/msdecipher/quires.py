"""Quire map of MS 408 and quire-aware resampling / fold utilities (h08).

Sources (see hypotheses/h08_quires/README.md for full citations and disagreements):

* ZL3b IVTFF page variables ($Q quire A-T, $P page in quire, $F folio in quire a-f / u-z with conjugates
  a<->z, b<->y, ..., $B bifolio counted from the outside, $L Currier language, $H Fagin Davis hand, $C Currier hand,
  $I illustration type) -- Zandbergen, IVTFF format description, voynich.nu/software/ivtt/IVTFF_format.pdf.
* voynich.nu per-quire pages (Zandbergen), e.g. voynich.nu/q08 ("probably used to contain 5 normal-sized bifolia").
* L. Fagin Davis, "How Many Glyphs and How Many Scribes? Digital Paleography and the Voynich Manuscript",
  Manuscript Studies 5(1) (2020) 164-180: collation formula (18 quires) and the five hands.
* L. Fagin Davis, Manuscript Road Trip blog: the same collation in the conventional 20-quire numbering.
"""
from __future__ import annotations

import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from .paths import repo_root, transcription_dir


def data_dir() -> Path:
    return repo_root() / "data"

QUIRE_LETTERS = "ABCDEFGHIJKLMNOPQRST"          # $Q: A=1 ... T=20 (P=16 and R=18 are lost quires)
HALF1, HALF2 = "abcdef", "zyxwvu"               # $F conjugates: a<->z, b<->y, ...

# Original number of bifolia per quire (20-quire numbering) and the leaves now missing.
# Collation: Fagin Davis 2020 (MS 5(1)) and voynich.nu quire pages; numbering converted to 20 quires.
ORIG_BIFOLIA = {1: 4, 2: 4, 3: 4, 4: 4, 5: 4, 6: 4, 7: 4, 8: 5, 9: 1, 10: 1, 11: 1, 12: 1, 13: 5, 14: 1, 15: 2,
                16: 1, 17: 2, 18: 1, 19: 2, 20: 7}
MISSING_LEAVES = {2: ["f12"], 8: ["f59", "f60", "f61", "f62", "f63", "f64"], 12: ["f74"], 16: ["f91", "f92"],
                  18: ["f97", "f98"], 20: ["f109", "f110"]}
# Fagin Davis 2020 article numbering (18 quires): 16 = 20-quire 16+17+18 ("16^(8-4) lacking 91-92, 97-98"),
# 17 = 19, 18 = 20.
LFD2020_QUIRE = {**{q: q for q in range(1, 16)}, 16: 16, 17: 16, 18: 16, 19: 17, 20: 18}
LFD2020_FORMULA = {1: "1^8", 2: "2^(8-1)", 3: "3^8", 4: "4^8", 5: "5^8", 6: "6^8", 7: "7^8", 8: "8^(10-6)", 9: "9^2",
                   10: "10^2", 11: "11^2", 12: "12^(2-1)", 13: "13^10", 14: "14^1", 15: "15^4", 16: "16^(8-4)",
                   17: "17^4", 18: "18^(14-2)"}

_HDR = re.compile(r"^<(f\d+[rv]\d*)>\s*<!\s*(.*?)>")


def _leaf(page: str) -> str:
    return re.match(r"f\d+", page).group(0)


def _default_transcription() -> Path:
    return transcription_dir() / "ZL3b-n.txt"


def parse_page_variables(path: Path | None = None) -> list[dict]:
    """Page headers of an IVTFF file: one dict per page with the raw $-variables."""
    rows = []
    for ln in Path(path or _default_transcription()).read_text(encoding="utf-8", errors="replace").splitlines():
        m = _HDR.match(ln)
        if m:
            v = dict(re.findall(r"\$(\w)=(\S+)", m.group(2)))
            rows.append({"page": m.group(1), **v})
    return rows


def _section(illus: str | None, quire: int) -> str:
    return {"H": "herbal", "A": "astronomical", "Z": "zodiac", "C": "cosmological", "B": "biological",
            "P": "pharmaceutical", "S": "stars", "T": "text-only"}.get(illus or "", "unknown")


def build_quire_table(path: Path | None = None) -> pd.DataFrame:
    """One row per transcription page with quire, bifolium, conjugate, position, foldout, language and hand."""
    raw = parse_page_variables(path)
    # leaves present per (quire, bifolio, half)
    present = defaultdict(set)
    for r in raw:
        present[(r["Q"], r["B"], r["F"])].add(_leaf(r["page"]))
    p_per_leaf = defaultdict(set)
    for r in raw:
        p_per_leaf[_leaf(r["page"])].add(r["P"])
    out = []
    for r in raw:
        q = QUIRE_LETTERS.index(r["Q"]) + 1
        f, b = r["F"], int(r["B"])
        conj_f = HALF2[HALF1.index(f)] if f in HALF1 else HALF1[HALF2.index(f)]
        conj = sorted(present.get((r["Q"], r["B"], conj_f), set()))
        n = ORIG_BIFOLIA[q]
        pos = b if f in HALF1 else 2 * n + 1 - b
        leaf = _leaf(r["page"])
        panels = bool(re.search(r"[rv]\d+$", r["page"]))
        ps = [ord(x) for x in p_per_leaf[leaf] if len(x) == 1]
        multi_p = bool(ps) and (max(ps) - min(ps) + 1 > 2)  # $P letters reserve more than 2 page slots
        if not conj:
            conj_s = "missing" if any(_leaf_in_missing(q, b, n)) else "none(singleton)"
        else:
            conj_s = ";".join(conj)
        out.append({
            "page": r["page"], "leaf": leaf, "quire_letter": r["Q"], "quire": q, "lfd2020_quire": LFD2020_QUIRE[q],
            "page_in_quire": r.get("P"), "folio_in_quire": f, "bifolio": b, "bifolium_id": f"Q{q:02d}-B{b}",
            "conjugate_leaf": conj_s, "position_in_quire": pos, "leaves_in_original_quire": 2 * n,
            "foldout": panels or multi_p, "currier_language": r.get("L", ""), "lfd_hand": r.get("H", ""),
            "currier_hand": r.get("C", ""), "illustration": r.get("I", ""), "section": _section(r.get("I"), q),
            "quire_missing_leaves": ";".join(MISSING_LEAVES.get(q, [])),
        })
    return pd.DataFrame(out)


def _leaf_in_missing(q: int, b: int, n: int):
    yield bool(MISSING_LEAVES.get(q))


def quire_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for q in range(1, 21):
        s = df[df["quire"] == q]
        rows.append({"quire": q, "quire_letter": QUIRE_LETTERS[q - 1], "lfd2020_quire": LFD2020_QUIRE[q],
                     "lfd2020_formula": LFD2020_FORMULA[LFD2020_QUIRE[q]], "original_bifolia": ORIG_BIFOLIA[q],
                     "leaves_present": ";".join(dict.fromkeys(s["leaf"])), "n_pages": len(s),
                     "missing_leaves": ";".join(MISSING_LEAVES.get(q, [])) or "",
                     "lost_entirely": len(s) == 0,
                     "foldout_leaves": ";".join(dict.fromkeys(s.loc[s["foldout"], "leaf"])),
                     "languages": ";".join(f"{k}:{v}" for k, v in Counter(s["currier_language"]).most_common()),
                     "lfd_hands": ";".join(f"{k}:{v}" for k, v in Counter(s["lfd_hand"]).most_common()),
                     "sections": ";".join(f"{k}:{v}" for k, v in Counter(s["section"]).most_common())})
    return pd.DataFrame(rows)


def quires_csv() -> Path:
    return data_dir() / "quires.csv"


def load_quires(path: Path | None = None) -> pd.DataFrame:
    p = Path(path) if path else quires_csv()
    return pd.read_csv(p, dtype={"page_in_quire": str, "lfd_hand": str, "currier_hand": str}, keep_default_na=False) \
        if p.exists() else build_quire_table()


def page_groups(df: pd.DataFrame, level: str = "quire") -> dict[str, str]:
    """page -> group key. level: 'quire', 'bifolium' (conjugate leaves together), 'leaf'."""
    col = {"quire": "quire", "bifolium": "bifolium_id", "leaf": "leaf", "lfd2020_quire": "lfd2020_quire"}[level]
    return {p: str(g) for p, g in zip(df["page"], df[col])}


def group_units(units: Sequence[str], df: pd.DataFrame, level: str = "quire") -> list[str]:
    """Group key for each unit (a page name such as 'f68r1' or a leaf 'f12'); unknown -> its own group."""
    g = page_groups(df, level)
    leaf_g = {}
    for p, k in g.items():
        leaf_g.setdefault(_leaf(p), k)
    return [g.get(u, leaf_g.get(_leaf(u), f"?{u}")) if re.match(r"f\d+", u) else f"?{u}" for u in units]


def group_folds(units: Sequence[str], df: pd.DataFrame, k: int = 5, level: str = "quire", seed: int = 0,
                labels: Sequence | None = None) -> list[tuple[list[int], list[int]]]:
    """k (train_idx, test_idx) folds in which every group (quire by default; 'bifolium' keeps conjugate leaves
    together) lies wholly in one fold, so no quire / conjugate-leaf leakage. Groups are assigned greedily
    (largest first) to the currently smallest fold; with ``labels`` the balance is on per-label counts."""
    keys = group_units(units, df, level)
    members = defaultdict(list)
    for i, key in enumerate(keys):
        members[key].append(i)
    rng = random.Random(seed)
    order = list(members)
    rng.shuffle(order)
    order.sort(key=lambda g: -len(members[g]))
    k = max(2, min(k, len(order)))
    folds: list[list[int]] = [[] for _ in range(k)]
    lab_cnt = [Counter() for _ in range(k)]
    for g in order:
        if labels is not None:
            c = Counter(labels[i] for i in members[g])
            j = min(range(k), key=lambda f: (sum(lab_cnt[f][l] for l in c), len(folds[f])))
            lab_cnt[j].update(c)
        else:
            j = min(range(k), key=lambda f: len(folds[f]))
        folds[j].extend(members[g])
    n = len(units)
    return [(sorted(set(range(n)) - set(te)), sorted(te)) for te in folds if te]


def leakage(units: Sequence[str], folds, df: pd.DataFrame, level: str = "quire") -> int:
    """Number of (fold, group) pairs where a group occurs in both train and test (0 = leak-free)."""
    keys = group_units(units, df, level)
    bad = 0
    for tr, te in folds:
        bad += len({keys[i] for i in tr} & {keys[i] for i in te})
    return bad


def write_quire_map(path: Path | None = None, out_dir: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = build_quire_table(path)
    df.to_csv(quires_csv(), index=False)
    summ = quire_summary(df)
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        summ.to_csv(Path(out_dir) / "quire_summary.csv", index=False)
    return df, summ
