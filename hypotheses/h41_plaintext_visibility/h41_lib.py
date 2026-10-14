"""h41 long-range statistics (PREREG.md). Pure functions of a token list."""
from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence

BLOCK = 200
TOP = 50


def new_type(tokens: Sequence[str]) -> float:
    """Fraction of second-half types that do not occur in the first half."""
    mid = len(tokens) // 2
    first = set(tokens[:mid])
    second = set(tokens[mid:])
    if not second:
        return 0.0
    return len(second - first) / len(second)


def _complete_blocks(tokens: Sequence[str], block: int) -> list[Sequence[str]]:
    if block <= 0:
        raise ValueError("block must be positive")
    n_blocks = len(tokens) // block
    return [tokens[i * block:(i + 1) * block] for i in range(n_blocks)]


def burst(tokens: Sequence[str], block: int = BLOCK, top: int = TOP) -> float:
    """Mean, over the `top` most frequent types, of busiest-block count / (count / n_blocks).

    Only complete blocks are used. A short tail is left out. Ties break by token text.
    """
    blocks = _complete_blocks(tokens, block)
    if not blocks or top <= 0:
        return 0.0
    counts = [Counter(b) for b in blocks]
    total: Counter[str] = Counter()
    for c in counts:
        total.update(c)
    n_blocks = len(blocks)
    ranked = sorted(total, key=lambda w: (-total[w], w))[:top]
    ratios = []
    for w in ranked:
        count = total[w]
        busiest = max(c[w] for c in counts)
        ratios.append(busiest / (count / n_blocks))
    return sum(ratios) / len(ratios)


def _word_mi(tokens: Sequence[str], lag: int) -> float:
    """Word-identity mutual information, in bits, at `lag`. No pairs -> 0."""
    n = len(tokens) - lag
    if lag <= 0 or n <= 0:
        return 0.0
    joint: Counter[tuple[str, str]] = Counter()
    left: Counter[str] = Counter()
    right: Counter[str] = Counter()
    for i in range(n):
        a = tokens[i]
        b = tokens[i + lag]
        joint[(a, b)] += 1
        left[a] += 1
        right[b] += 1
    mi = 0.0
    for (a, b), c in joint.items():
        pxy = c / n
        mi += pxy * math.log2(pxy / ((left[a] / n) * (right[b] / n)))
    return mi


def mi100(tokens: Sequence[str]) -> float:
    """MI at lag 100 divided by MI at lag 1. The ratio is 0 when lag-1 MI is 0."""
    mi1 = _word_mi(tokens, 1)
    if mi1 <= 0.0:
        return 0.0
    return _word_mi(tokens, 100) / mi1


def _js_bits(p: Counter[str], q: Counter[str]) -> float:
    np_ = sum(p.values())
    nq = sum(q.values())
    if np_ == 0 or nq == 0:
        return 0.0
    js = 0.0
    for k in set(p) | set(q):
        pk = p[k] / np_
        qk = q[k] / nq
        mk = 0.5 * (pk + qk)
        if pk > 0.0:
            js += 0.5 * pk * math.log2(pk / mk)
        if qk > 0.0:
            js += 0.5 * qk * math.log2(qk / mk)
    return js


def block_js(tokens: Sequence[str], block: int = BLOCK) -> float:
    """Mean Jensen-Shannon divergence, in bits, between unigram distributions of adjacent blocks."""
    blocks = _complete_blocks(tokens, block)
    if len(blocks) < 2:
        return 0.0
    counts = [Counter(b) for b in blocks]
    vals = [_js_bits(counts[i], counts[i + 1]) for i in range(len(counts) - 1)]
    return sum(vals) / len(vals)


def score(tokens: Sequence[str]) -> dict[str, float]:
    return {
        "new_type": new_type(tokens),
        "burst": burst(tokens),
        "mi100": mi100(tokens),
        "block_js": block_js(tokens),
    }
