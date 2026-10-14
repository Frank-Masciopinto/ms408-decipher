"""h35: per-hand word-shape model re-spelling generator words (PREREG.md). Statistics only, no meaning claims."""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses/h34_boundary_rule_generator"))
import h34_lib as L34  # noqa: E402

ORDER = 3; ADDK = 0.05


def fit_shape(words, shuffle_rng=None):
    """Glyph n-gram LM with ^/$ markers. If shuffle_rng given, glyphs are permuted within each word first."""
    cnt = defaultdict(Counter); alpha = set()
    for w in words:
        if shuffle_rng is not None: w = "".join(shuffle_rng.permutation(list(w)))
        s = "^" * (ORDER - 1) + w + "$"; alpha |= set(w)
        for i in range(ORDER - 1, len(s)): cnt[s[i - ORDER + 1:i]][s[i]] += 1
    syms = sorted(alpha) + ["$"]
    return dict(cnt=cnt, syms=syms)


def sample_word(m, rng, maxlen=15):
    h = "^" * (ORDER - 1); out = ""; syms = m["syms"]
    while len(out) < maxlen:
        c = m["cnt"].get(h, {}); p = np.array([c.get(x, 0) + ADDK for x in syms]); x = syms[rng.choice(len(syms), p=p / p.sum())]
        if x == "$": break
        out += x; h = (h + x)[-(ORDER - 1):]
    return out


def respell_map(types, m, rng, tries=200):
    """Type-level map: each type -> distinct sampled word, length within ±1 when possible (most frequent first)."""
    used = set(); mp = {}
    for t in types:
        best = None
        for _ in range(tries):
            w = sample_word(m, rng)
            if not w or w in used: continue
            best = w
            if abs(len(w) - len(t)) <= 1: break
        if best is None: best = t + "_" + str(len(mp))
        used.add(best); mp[t] = best
    return mp


def respell(tokens, m, rng):
    types = [t for t, _ in Counter(tokens).most_common()]; mp = respell_map(types, m, rng)
    return [mp[t] for t in tokens]


def ambiguity(lines):
    """Per glyph: share of its occurrences that are word-final, and its frequency."""
    fin = Counter(); tot = Counter()
    for l in lines:
        for w in l:
            for i, g in enumerate(w): tot[g] += 1; fin[g] += i == len(w) - 1
    n = sum(tot.values()); return {g: (fin[g] / tot[g], tot[g] / n) for g in tot}


def gap_drivers(gen_lines, ms_lines, top=6):
    """Glyphs ranked by frequency-weighted |P(final|glyph)| difference between generator and MS."""
    a = ambiguity(ms_lines); b = ambiguity(gen_lines); out = []
    for g, (fm, pm) in a.items():
        fg = b.get(g, (0.0, 0.0))[0]; out.append((g, round(pm * abs(fm - fg), 4), round(fm, 3), round(fg, 3)))
    return sorted(out, key=lambda x: -x[1])[:top]
