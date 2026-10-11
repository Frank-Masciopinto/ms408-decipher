"""Glyph catalogue from a transcription (EVA symbols + digraph candidates).

This catalogues the symbols *a transcriber used*. It says nothing yet about whether the
physical glyphs on the page really split into these classes: that needs the image stage
(see :mod:`msdecipher.glyph_stage`).
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict

import pandas as pd

from .corpus_view import Line
from .ivtff import is_rare, render, readable

# Composite candidates flagged (not merged) here; merging is decided in msdecipher.segment.
CANDIDATES = ["ch", "sh", "cth", "ckh", "cph", "cfh", "ee", "ii", "iii", "in", "iin", "iiin",
              "ain", "aiin", "aiiin", "ct", "ck", "cp", "cf", "qo"]


def _is_text(ch: str) -> bool:
    return ch != "?"


def glyph_table(lines_by_group: dict[str, list[Line]], main: str = "all") -> pd.DataFrame:
    """One row per single EVA symbol / rare code. ``lines_by_group`` maps a group name
    (``'all'``, ``'A'``, ``'B'`` ...) to lines; ``main`` is the group used for the positional
    columns and ranking."""
    pos = defaultdict(Counter)   # glyph -> Counter of positions
    counts: dict[str, Counter] = {g: Counter() for g in lines_by_group}
    for g, lines in lines_by_group.items():
        for ln in lines:
            for wi, w in enumerate(ln.words):
                if not readable(w):
                    # count the readable glyphs but skip positional stats for damaged words
                    counts[g].update(c for c in w if _is_text(c))
                    continue
                counts[g].update(w)
                if g != main:
                    continue
                n = len(w)
                for i, c in enumerate(w):
                    if n == 1:
                        pos[c]["sole"] += 1
                    elif i == 0:
                        pos[c]["initial"] += 1
                    elif i == n - 1:
                        pos[c]["final"] += 1
                    else:
                        pos[c]["medial"] += 1
                if wi == 0 and ln.locus.starts_own_line:
                    pos[w[0]]["line_initial"] += 1
                    if ln.locus.paragraph_start:
                        pos[w[0]]["para_initial"] += 1
                if wi == len(ln.words) - 1 and ln.locus.starts_own_line:
                    pos[w[-1]]["line_final"] += 1
    all_glyphs = sorted(set().union(*[set(c) for c in counts.values()]))
    rows = []
    total = sum(counts[main].values())
    for gl in all_glyphs:
        n = counts[main][gl]
        p = pos[gl]
        in_word = p["initial"] + p["medial"] + p["final"] + p["sole"]
        row = {
            "glyph": render(gl),
            "kind": "rare-code" if is_rare(gl) else ("unreadable" if gl == "?" else "eva"),
            "count": n,
            "share": n / total if total else 0.0,
            "n_positioned": in_word,
            "initial": p["initial"] / in_word if in_word else 0.0,
            "medial": p["medial"] / in_word if in_word else 0.0,
            "final": p["final"] / in_word if in_word else 0.0,
            "sole": p["sole"] / in_word if in_word else 0.0,
            "line_initial_n": p["line_initial"],
            "line_final_n": p["line_final"],
            "para_initial_n": p["para_initial"],
        }
        for g in lines_by_group:
            if g != main:
                row[f"count_{g}"] = counts[g][gl]
        rows.append(row)
    df = pd.DataFrame(rows).sort_values(["count", "glyph"], ascending=[False, True]).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    df.insert(0, "group", main)
    return df


def digraph_table(lines: list[Line], candidates=CANDIDATES) -> pd.DataFrame:
    """For each candidate composite: occurrences, and a *cohesion* measure for 2-glyph
    candidates: P(second | first) and P(first | second) (how rarely the parts occur apart),
    plus pointwise mutual information of the adjacent pair within words.
    Cohesion is evidence for treating a pair as one unit, not proof."""
    uni, big = Counter(), Counter()
    words = [w for ln in lines for w in ln.words if readable(w)]
    for w in words:
        uni.update(w)
        big.update(zip(w, w[1:]))
    n_pairs = sum(big.values())
    n_uni = sum(uni.values())
    first_of = Counter()
    second_of = Counter()
    for (a, b), v in big.items():
        first_of[a] += v
        second_of[b] += v
    # Occurrence counts of each candidate as a substring in words
    sub = Counter()
    for w in words:
        for cand in candidates:
            if cand in w:
                sub[cand] += sum(1 for i in range(len(w) - len(cand) + 1) if w.startswith(cand, i))
    rows = []
    for cand in candidates:
        r = {"candidate": cand, "length": len(cand), "occurrences": sub[cand]}
        if len(cand) == 2:
            a, b = cand
            ab = big[(a, b)]
            r["p_next_given_first"] = ab / uni[a] if uni[a] else float("nan")
            r["p_prev_given_second"] = ab / uni[b] if uni[b] else float("nan")
            exp = (first_of[a] * second_of[b] / n_pairs) if n_pairs else 0
            r["pmi_bits"] = math.log2(ab * n_pairs / (first_of[a] * second_of[b])) \
                if ab and first_of[a] and second_of[b] else float("nan")
            r["observed_over_expected"] = ab / exp if exp else float("nan")
        rows.append(r)
    df = pd.DataFrame(rows)
    return df


def top_bigrams(lines: list[Line], k: int = 30) -> pd.DataFrame:
    """Highest-PMI adjacent EVA pairs inside words (min 30 occurrences): data-driven
    composite candidates."""
    uni, big = Counter(), Counter()
    for ln in lines:
        for w in ln.words:
            if readable(w):
                uni.update(w)
                big.update(zip(w, w[1:]))
    n = sum(big.values())
    fa, sb = Counter(), Counter()
    for (a, b), v in big.items():
        fa[a] += v
        sb[b] += v
    rows = [{"pair": render(a + b), "count": v,
             "pmi_bits": math.log2(v * n / (fa[a] * sb[b])),
             "p_second_given_first": v / uni[a]}
            for (a, b), v in big.items() if v >= 30]
    return pd.DataFrame(rows).sort_values("pmi_bits", ascending=False).head(k).reset_index(drop=True)
