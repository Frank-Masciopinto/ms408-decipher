"""h07: leave-one-section-out falsification test.

For each of the 5 section classes S, every generator is fitted on the folios of the OTHER sections only (S's text is never seen), then generates the whole
manuscript layout (same folios, token counts, Currier language labels); the statistics below are computed on the generated held-out section *relative to the
generated other sections of the same run*, i.e. each generator predicts how the unseen section relates to the rest. Predictions are written to disk (with a SHA256
manifest) before the real held-out section is scored (``run_h07.py predict`` then ``run_h07.py score``).

Nothing here decodes MS 408.
"""
from __future__ import annotations

import hashlib
import math
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "hypotheses" / "h06_section_null_and_zodiac"))
import h06_lib as L6  # noqa: E402

HR, H, T, CI = L6.HR, L6.H, L6.T, L6.CI
SEG = L6.SEG
CLASSES = T.CLASSES
RESULTS = HERE / "results"
FIG = HERE / "figures"
TOPN = 30

# ------------------------------------------------------------------ pre-registered rules (fixed before any held-out text is looked at)
PREREG = {
    "held_out_settings_rules": {
        "nearest": "the training section whose share of Currier-A folios is closest to the held-out section's share (folio metadata only, no text); ties -> the training section with more folios",
        "pooled": "one model fitted on all training text pooled (engine, pool and unit tilt from the union of the other sections)",
        "random-section (null)": "a training section drawn uniformly at random per seed",
    },
    "topic_rule": "held-out section's plaintext = the work of mech_hybrid_topics.TOPIC_WORK (fixed in the hybrid stage before this test); null: a random other work per seed",
    "primary_comparison": "SV P50 nearest (best no-plaintext accuracy variant of h06) vs A2 codebook topic-matched (the only topic hybrid that reached the section signal in step 2); secondary: all other rows",
    "score": "per (section, statistic): z = (generator mean - MS 408) / sqrt(SD_gen^2 (1 + 1/n) + SE_MS^2), SE_MS = delete-one-block jackknife over blocks of 3 consecutive held-out folios; family score = mean |z| (clipped at 10) over 5 sections x statistics, and number inside the 95 % prediction interval; paired Wilcoxon over (section, statistic) cells",
    "seeds": 8,
}

STATS = ["overlap_tokens", "new_type_rate", "hapax_share", "ttr", "js_mean_to_others", "unit_js_to_others", "len_mean", "unit_H1", "unit_h2", "top30_rank_rho"]
STAT_LABELS = {"overlap_tokens": "held-out tokens whose type occurs in the other sections", "new_type_rate": "held-out types absent from the other sections",
               "hapax_share": "hapax share of held-out types", "ttr": "held-out type/token ratio", "js_mean_to_others": "mean word JS to each other section (bits)",
               "unit_js_to_others": "unit-distribution JS held-out vs rest (bits)", "len_mean": "mean word length (units)", "unit_H1": "unit entropy H1 (bits)",
               "unit_h2": "within-word conditional unit entropy h2 (bits)", "top30_rank_rho": "Spearman rank stability of the rest's top-30 words in the held-out section"}


def js_bits(c1: Counter, c2: Counter) -> float:
    n1, n2 = sum(c1.values()), sum(c2.values())
    if not n1 or not n2:
        return float("nan")
    t = 0.0
    for k in set(c1) | set(c2):
        p, q = c1.get(k, 0) / n1, c2.get(k, 0) / n2
        m = (p + q) / 2
        if p:
            t += 0.5 * p * math.log2(p / m)
        if q:
            t += 0.5 * q * math.log2(q / m)
    return t


def unit_entropies(words: list[str]) -> tuple[float, float]:
    c = Counter()
    pair = Counter()
    prev_c = Counter()
    for w in words:
        u = SEG(w)
        c.update(u)
        for a, b in zip(u, u[1:]):
            pair[(a, b)] += 1
            prev_c[a] += 1
    n = sum(c.values())
    h1 = -sum(v / n * math.log2(v / n) for v in c.values())
    m = sum(pair.values())
    h2 = -sum(v / m * math.log2(v / prev_c[a]) for (a, _), v in pair.items()) if m else float("nan")
    return h1, h2


def section_stats(docs: list[dict], held: str) -> dict:
    """Statistics of the held-out section ``held`` relative to the four other section classes of the same corpus (docs = folio dicts with cls / words)."""
    hw = [w for d in docs if d["cls"] == held for w in d["words"]]
    others = {c: [w for d in docs if d["cls"] == c for w in d["words"]] for c in CLASSES if c != held}
    rest = [w for ws in others.values() for w in ws]
    rest_types = set(rest)
    hc, rc = Counter(hw), Counter(rest)
    out = {"n_tokens": len(hw)}
    out["overlap_tokens"] = float(np.mean([w in rest_types for w in hw]))
    out["new_type_rate"] = float(np.mean([t not in rest_types for t in hc]))
    out["hapax_share"] = float(np.mean([v == 1 for v in hc.values()]))
    out["ttr"] = len(hc) / len(hw)
    for c, ws in others.items():
        out[f"js_to_{c}"] = js_bits(hc, Counter(ws))
    out["js_mean_to_others"] = float(np.mean([out[f"js_to_{c}"] for c in others]))
    out["unit_js_to_others"] = js_bits(Counter(u for w in hw for u in SEG(w)), Counter(u for w in rest for u in SEG(w)))
    out["len_mean"] = float(np.mean([len(SEG(w)) for w in hw]))
    out["unit_H1"], out["unit_h2"] = unit_entropies(hw)
    top = [w for w, _ in rc.most_common(TOPN)]
    from scipy.stats import spearmanr
    out["top30_rank_rho"] = float(spearmanr([rc[w] for w in top], [hc.get(w, 0) for w in top]).statistic)
    return out


def jackknife_blocks(docs: list[dict], held: str, block: int = 3) -> dict:
    """Delete-one-block jackknife SE of the real held-out statistics (blocks of ``block`` consecutive held-out folios)."""
    idx = [i for i, d in enumerate(docs) if d["cls"] == held]
    blocks = [idx[i:i + block] for i in range(0, len(idx), block)]
    reps = []
    for b in blocks:
        drop = set(b)
        reps.append(section_stats([d for i, d in enumerate(docs) if i not in drop], held))
    keys = [k for k in reps[0] if k != "n_tokens"]
    return {k: CI.jackknife_se([r[k] for r in reps]) for k in keys}


def nearest_section(entries: list[dict], held: str) -> str:
    """Pre-registered nearest rule: Currier-A folio share (metadata only)."""
    share = {}
    nfol = Counter()
    for e in entries:
        if e["cls"] in CLASSES:
            share.setdefault(e["cls"], []).append(e["lang"] == "A")
            nfol[e["cls"]] += 1
    s = {c: float(np.mean(v)) for c, v in share.items()}
    cands = [c for c in CLASSES if c != held]
    return min(cands, key=lambda c: (abs(s[c] - s[held]), -nfol[c]))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
