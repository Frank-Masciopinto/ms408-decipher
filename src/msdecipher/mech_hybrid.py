"""Hybrid generators: plaintext dependence (cipher-like) + copy-and-modify word reuse (self-citation-like).

**These are test generators, not a model of how MS 408 was made, and none of them decodes it.** They ask whether combining the two
ingredients that the mechanisms stage found complementary (reports/mechanisms/) repairs the metrics each parent misses.

The engine (:func:`generate`) is a *simplified, documented* Python copy-and-modify process in the spirit of Timm & Schinner (2020)
-- it is **not** the authors' rule set (that is driven through their Java code in ``mech_selfcitation``; its glyph-class tables and
follow rules are not re-implemented here).  At every output position:

1. with probability ``p_copy`` a **source** word is copied from the recent output: the immediately preceding word with probability
   ``p_prev``, otherwise a uniformly chosen one of the last ``window`` words;
2. the copy is **modified** by one operation drawn from {exact repeat (``p_exact``), final-unit edit (``p_suffix``), initial-unit edit
   (``p_prefix``), inner-unit replacement (the rest)}.  Edits are replace / add / remove with equal probability (remove only if the word
   has > 1 unit).  A word may repeat identically at most ``max_repeat`` = 3 times in a row (the authors' default) and never exceeds
   ``max_units`` = 10 units;
3. otherwise (probability ``1 - p_copy``) the **innovation** comes from the *encoder*, i.e. from the plaintext.

Encoders (the plaintext-dependent part):

* ``naibbe``   -- Naibbe-cipher tokens (``mech_naibbe`` tables, card-draw table choice, 17/36 unigram respacing, unambiguity check),
  produced *on the fly*: each innovation consumes the next 1-2 plaintext letters.  Edit units are drawn from the empirical
  initial / final / any-unit distributions of the *innovated* words so far (no information from MS 408).
* ``codebook`` -- one **whole-word** encoding: every plaintext word *type* is assigned a fixed Voynichese codeword (first use: a fresh
  draw from a slot-conditioned-bigram word grammar, rejected if already taken, so the code is invertible).  This keeps the plaintext's
  word-frequency structure and topic vocabulary intact.  The grammar is fitted on MS 408 *types*: its ~1.6k parameters are a fitting
  cost that must be counted (and it makes letter-level agreement partly circular).
* ``plain_edit`` (the **reverse** hybrid, "self-citation base, plaintext-driven"): copy-and-modify with ``p_copy`` forced high; every
  edit consumes the next plaintext letter and inserts / substitutes the Naibbe glyph string (table drawn from the card deck) of
  that letter in the matching state (prefix / suffix / unigram); innovations are Naibbe tokens.
* ``none`` / ``grammar`` -- control: the same engine with innovations drawn i.i.d. from a grammar (no plaintext at all).

Free parameters of the engine: ``p_copy, window, p_prev, p_exact, p_suffix, p_prefix`` (6; ``p_inner = 1 - ...``).  Everything else is fixed
and documented above.  :data:`BOUNDS` are the search ranges (plaintext-driven reverse hybrid: ``p_copy >= 0.6``).
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import asdict, dataclass, field, replace

from . import mech_naibbe as N
from .segment import Segmenter

SEG = Segmenter.preset("collapsed")
MAX_UNITS = 10
MAX_REPEAT = 3

PARAM_NAMES = ("p_copy", "window", "p_prev", "p_exact", "p_suffix", "p_prefix")
BOUNDS = {"p_copy": (0.0, 0.95), "window": (3, 200), "p_prev": (0.0, 1.0), "p_exact": (0.0, 1.0),
          "p_suffix": (0.0, 1.0), "p_prefix": (0.0, 1.0)}
VARIANT_BOUNDS = {"plain_edit": {"p_copy": (0.6, 0.99)}}
N_FREE_PARAMS = len(PARAM_NAMES)


@dataclass(frozen=True)
class Params:
    p_copy: float = 0.5
    window: int = 30
    p_prev: float = 0.3
    p_exact: float = 0.2
    p_suffix: float = 0.4
    p_prefix: float = 0.2
    # p_inner = 1 - p_exact - p_suffix - p_prefix (> 0 enforced by `normalised`)

    @property
    def p_inner(self) -> float:
        return max(0.0, 1.0 - self.p_exact - self.p_suffix - self.p_prefix)

    def normalised(self) -> "Params":
        s = self.p_exact + self.p_suffix + self.p_prefix
        if s <= 1.0:
            return self
        return replace(self, p_exact=self.p_exact / s, p_suffix=self.p_suffix / s, p_prefix=self.p_prefix / s)

    def as_dict(self) -> dict:
        return asdict(self)


def sample_params(rng: random.Random, variant: str = "naibbe") -> Params:
    b = {**BOUNDS, **VARIANT_BOUNDS.get(variant, {})}
    # operation mix: Dirichlet-like draw of 4 weights
    w = [rng.expovariate(1.0) for _ in range(4)]
    t = sum(w)
    lo, hi = b["p_copy"]
    return Params(p_copy=rng.uniform(lo, hi), window=int(round(10 ** rng.uniform(0.5, 2.3))), p_prev=rng.random(),
                  p_exact=w[0] / t, p_suffix=w[1] / t, p_prefix=w[2] / t).normalised()


def perturb(rng: random.Random, p: Params, variant: str = "naibbe", scale: float = 0.15) -> Params:
    b = {**BOUNDS, **VARIANT_BOUNDS.get(variant, {})}
    d = p.as_dict()
    for k in rng.sample(PARAM_NAMES, rng.randint(1, 3)):
        lo, hi = b[k]
        if k == "window":
            d[k] = int(min(hi, max(lo, round(d[k] * 10 ** rng.gauss(0, 0.2)))))
        else:
            d[k] = min(hi, max(lo, d[k] + rng.gauss(0, scale * (hi - lo))))
    return Params(**d).normalised()


# ------------------------------------------------------------------ encoders

class NaibbeLive:
    """Streaming Naibbe cipher: consumes plaintext letters one or two at a time (same tables, deck, respacing, unambiguity rule as
    :class:`mech_naibbe.NaibbeCipher`, which stays the reference implementation; round-trip tested)."""

    def __init__(self, plain_words, seed: int, deck: int = 78, p_unigram: float = N.P_UNIGRAM_STANDARD, cipher=None):
        self.c = cipher or N.NaibbeCipher(deck=deck, p_unigram=p_unigram)
        self.rng = random.Random(seed)
        self.letters = N.clean_plaintext(" ".join(plain_words))
        self.i = 0
        self._deck: list[str] = []
        self._k = 0
        self.consumed_letters = 0

    def exhausted(self) -> bool:
        return self.i >= len(self.letters)

    def _draw(self) -> str:
        if self._k >= len(self._deck):
            self._deck = self.c._deck(self.rng)
            self._k = 0
        self._k += 1
        return self._deck[self._k - 1]

    def _take(self, n: int) -> str:
        if self.exhausted():                       # wrap around: the plaintext is a finite sample
            self.i = 0
        s = self.letters[self.i:self.i + n]
        self.i += len(s)
        self.consumed_letters += len(s)
        return s

    def next_token(self) -> str:
        c = self.c
        if self.i >= len(self.letters) - 1 or self.rng.random() < c.p_unigram:
            L = self._take(1)
            return c.glyph[("unigram", self._draw(), L)]
        two = self._take(2)
        a, b = two[0], two[1]
        for _ in range(c.max_retries):
            t1, t2 = self._draw(), self._draw()
            w = c.glyph[("prefix", t1, a)] + c.glyph[("suffix", t2, b)]
            if w in c.unigram_words or len(c.bi_decode[w]) > 1:
                continue
            break
        return w

    def edit_unit(self, state: str) -> str:
        """Glyph string for the next plaintext letter in ``state`` (prefix / suffix / unigram), table by card draw."""
        L = self._take(1)
        return self.c.glyph[(state, self._draw(), L)]


class Codebook:
    """Whole-word encoding: plaintext word type -> fixed codeword drawn from ``sampler(n, rng) -> list[str]`` (invertible)."""

    def __init__(self, plain_words, sampler, seed: int):
        self.words = list(plain_words)
        self.i = 0
        self.rng = random.Random(seed)
        self.sampler = sampler
        self.book: dict[str, str] = {}
        self.used: set[str] = set()
        self._buf: list[str] = []

    def _new_code(self) -> str:
        for _ in range(200):
            if not self._buf:
                self._buf = self.sampler(256, self.rng)
            c = self._buf.pop()
            if c and c not in self.used:
                return c
        return self._buf.pop() if self._buf else "daiin"

    def next_token(self) -> str:
        w = self.words[self.i % len(self.words)]
        self.i += 1
        c = self.book.get(w)
        if c is None:
            c = self.book[w] = self._new_code()
            self.used.add(c)
        return c


class GrammarInnovator:
    """No plaintext: i.i.d. word draws from a grammar sampler (control)."""

    def __init__(self, sampler, seed: int):
        self.rng = random.Random(seed)
        self.sampler = sampler
        self._buf: list[str] = []

    def next_token(self) -> str:
        if not self._buf:
            self._buf = self.sampler(512, self.rng)
        return self._buf.pop()


# ------------------------------------------------------------------ the engine

class _Pools:
    """Unit pools of innovated words (initial / final / any unit) used by self-referential edits."""

    def __init__(self):
        self.init: Counter = Counter()
        self.final: Counter = Counter()
        self.any: Counter = Counter()

    def add(self, w: str):
        u = SEG(w)
        if not u:
            return
        self.init[u[0]] += 1
        self.final[u[-1]] += 1
        for x in u:
            self.any[x] += 1

    def draw(self, kind: str, rng: random.Random) -> str | None:
        c = getattr(self, kind)
        if not c:
            return None
        return rng.choices(list(c), weights=list(c.values()))[0]


def _edit(units: list[str], op: str, draw_unit, rng: random.Random) -> list[str] | None:
    """Apply one prefix/suffix/inner edit. ``draw_unit(state)`` returns a unit string (may be several units) or None."""
    u = list(units)
    kind = rng.choice(("replace", "add", "remove"))
    if op == "suffix":
        if kind == "remove" and len(u) > 1:
            return u[:-1]
        x = draw_unit("suffix")
        if x is None:
            return None
        return u[:-1] + list(SEG(x)) if kind == "replace" else u + list(SEG(x))
    if op == "prefix":
        if kind == "remove" and len(u) > 1:
            return u[1:]
        x = draw_unit("prefix")
        if x is None:
            return None
        return list(SEG(x)) + u[1:] if kind == "replace" else list(SEG(x)) + u
    # inner: replace one unit (not the only one's edge preference: any position)
    x = draw_unit("unigram")
    if x is None:
        return None
    j = rng.randrange(len(u))
    return u[:j] + list(SEG(x)) + u[j + 1:]


def generate(encoder, params: Params, n_tokens: int, seed: int, plain_edit: bool = False, section_encoders=None,
             layout: list[tuple[str, int]] | None = None) -> list[str]:
    """``n_tokens`` words (or the whole ``layout`` = [(section, n_tokens) per folio] if given; the encoder is then
    ``section_encoders[section]`` for that folio). ``plain_edit``: edits insert plaintext-letter glyph strings (reverse hybrid)."""
    p = params.normalised()
    rng = random.Random(seed * 7919 + 13)
    out: list[str] = []
    pools = _Pools()
    steps = layout if layout is not None else [("", n_tokens)]
    run = 0
    for sec, n in steps:
        enc = section_encoders[sec] if layout is not None else encoder
        for _ in range(n):
            w = None
            if out and rng.random() < p.p_copy:
                src = out[-1] if rng.random() < p.p_prev else out[-1 - rng.randrange(min(p.window, len(out)))]
                r = rng.random()
                op = "exact" if r < p.p_exact else "suffix" if r < p.p_exact + p.p_suffix else \
                     "prefix" if r < p.p_exact + p.p_suffix + p.p_prefix else "inner"
                if op == "exact":
                    w = src
                else:
                    if plain_edit:
                        draw = enc.edit_unit
                    else:
                        draw = lambda st: pools.draw({"suffix": "final", "prefix": "init", "unigram": "any"}[st], rng)  # noqa: E731
                    for _try in range(4):
                        e = _edit(list(SEG(src)), op, draw, rng)
                        if e and 0 < len(e) <= MAX_UNITS:
                            w = "".join(e)
                            break
                    if w is None:
                        w = src
                if w == out[-1] and run + 1 >= MAX_REPEAT:
                    w = None                                   # too many identical in a row: innovate instead
            if w is None:
                w = enc.next_token()
                pools.add(w)
            run = run + 1 if (out and w == out[-1]) else 0
            out.append(w)
    return out
