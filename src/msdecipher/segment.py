"""Unit segmentation: which glyph sequences are analysed as one 'letter'.

EVA is a *transcription* alphabet. Several EVA sequences (ch, sh, and the gallows with a
bench: cth, ckh, cph, cfh) are drawn as one connected shape, so counting their parts as
independent letters distorts statistics (e.g. ``h`` looks like a vowel in raw EVA only
because it is half of ``ch``/``sh``). Which merges are right is itself a hypothesis, so the
inventory is configurable and presets are provided. Segmentation is greedy
longest-match, left to right. Rare glyph codes (private-use code points) and ``?`` are always
single units.
"""
from __future__ import annotations

from functools import lru_cache

PRESETS: dict[str, tuple[str, ...]] = {
    # every EVA character is its own unit
    "raw": (),
    # only the two benches that are almost never seen apart
    "basic": ("ch", "sh"),
    # DEFAULT: benches plus bench-gallows ligatures
    "collapsed": ("ch", "sh", "cth", "ckh", "cph", "cfh"),
    # more aggressive: also doubled e / i and the common 'in' endings (hypothesis only)
    "extended": ("ch", "sh", "cth", "ckh", "cph", "cfh", "ee", "ii", "iin", "in"),
}
DEFAULT_PRESET = "collapsed"


class Segmenter:
    """Greedy longest-match segmenter over a set of multi-glyph units."""

    def __init__(self, composites=(), name: str | None = None):
        comps = sorted({c for c in composites if len(c) > 1}, key=lambda s: (-len(s), s))
        self.composites = tuple(comps)
        self.name = name or ("custom:" + ",".join(comps) if comps else "raw")
        self._max = len(comps[0]) if comps else 1
        self._set = frozenset(comps)
        self._cache: dict[str, tuple[str, ...]] = {}

    @classmethod
    def preset(cls, name: str) -> "Segmenter":
        if name not in PRESETS:
            raise ValueError(f"unknown preset {name!r}; choose from {sorted(PRESETS)}")
        return cls(PRESETS[name], name=name)

    @classmethod
    def from_spec(cls, spec: str) -> "Segmenter":
        """``'collapsed'`` (preset name) or ``'ch,sh,cth'`` (explicit list)."""
        spec = spec.strip()
        if spec in PRESETS:
            return cls.preset(spec)
        return cls([s for s in spec.split(",") if s])

    def segment(self, word: str) -> tuple[str, ...]:
        hit = self._cache.get(word)
        if hit is not None:
            return hit
        out: list[str] = []
        i, n = 0, len(word)
        while i < n:
            for L in range(min(self._max, n - i), 1, -1):
                if word[i:i + L] in self._set:
                    out.append(word[i:i + L])
                    i += L
                    break
            else:
                out.append(word[i])
                i += 1
        res = tuple(out)
        self._cache[word] = res
        return res

    def __call__(self, word: str) -> tuple[str, ...]:
        return self.segment(word)

    def __repr__(self) -> str:
        return f"Segmenter({self.name}: {list(self.composites)})"
