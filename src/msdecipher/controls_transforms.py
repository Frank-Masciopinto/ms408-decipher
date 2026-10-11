"""Transformations of plaintext token lists and synthetic null generators.

All functions take / return ``list[str]`` (one string per word; every character of a word is
one symbol of the output alphabet, so the raw per-character segmenter applies). Everything is
seeded and deterministic.

Honesty notes
-------------
* These are *simplified, illustrative* versions of the families named in the literature. They
  are **not** reproductions of any published cipher (in particular ``naibbe_like`` is NOT
  Greshko's Naibbe cipher: it only shares the idea of unigram/bigram tiles with several
  homophones each) nor of the Timm-Schinner generator (``selfcitation`` copies earlier words
  with small mutations, parameters not tuned to MS 408).
* Parameters (key lengths, number of homophones, mutation rate ...) are arbitrary choices;
  none of these controls is a model of MS 408. They only show what *kind of* statistic each
  family tends to produce.
* A relabelling of symbols (``monoalphabetic``, ``caesar``) cannot change any of the
  label-free statistics used here; those controls exist to prove that in the tests.
"""
from __future__ import annotations

import random
import re
from collections import Counter
from typing import Callable, Sequence

LATIN_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
GREEK = "αβγδεζηθικλμνξοπρστυφχψω"   # 24 distinct symbols for code alphabets
VOWELS = "aeiou"


# --------------------------------------------------------------- plaintext-preserving / simple

def abjad(tokens: Sequence[str]) -> list[str]:
    """Abjad-style: delete all vowels (a e i o u); words that become empty are dropped."""
    out = [re.sub("[aeiou]", "", t) for t in tokens]
    return [t for t in out if t]


def monoalphabetic(tokens: Sequence[str], seed: int = 0) -> list[str]:
    """Random one-to-one substitution onto a different (Greek) alphabet."""
    rng = random.Random(seed)
    letters = sorted({c for t in tokens for c in t})
    syms = list(GREEK)
    if len(letters) > len(syms):
        raise ValueError("alphabet too large for the symbol pool")
    rng.shuffle(syms)
    key = dict(zip(letters, syms))
    return ["".join(key[c] for c in t) for t in tokens]


def vigenere_generic(tokens: Sequence[str], key_len: int = 6, seed: int = 0) -> list[str]:
    """Vigenere over the text's own alphabet (sorted code points, cyclic shifts); used for
    Hebrew/Arabic where the a-z version does not apply. Same rule as :func:`vigenere`
    (key advances over letters only)."""
    rng = random.Random(seed)
    alpha = sorted({c for t in tokens for c in t})
    idx = {c: i for i, c in enumerate(alpha)}
    n = len(alpha)
    key = [rng.randrange(1, n) for _ in range(key_len)]
    out, i = [], 0
    for t in tokens:
        w = []
        for c in t:
            w.append(alpha[(idx[c] + key[i % key_len]) % n])
            i += 1
        out.append("".join(w))
    return out


def caesar(tokens: Sequence[str], shift: int = 3) -> list[str]:
    return ["".join(chr((ord(c) - 97 + shift) % 26 + 97) for c in t) for t in tokens]


def vigenere(tokens: Sequence[str], key_len: int = 6, seed: int = 0) -> list[str]:
    """Vigenere over a-z with a random key of length ``key_len``. The key advances over
    letters only (word boundaries are kept and do not consume key). Flattens H1, raises h2/h3."""
    rng = random.Random(seed)
    key = [rng.randrange(1, 26) for _ in range(key_len)]
    out, i = [], 0
    for t in tokens:
        w = []
        for c in t:
            w.append(chr((ord(c) - 97 + key[i % key_len]) % 26 + 97))
            i += 1
        out.append("".join(w))
    return out


_SYL = re.compile(r"[^aeiou]*[aeiou]+")


def syllabify(word: str) -> list[str]:
    """Crude open-syllable split: each syllable = consonants + vowel run; leftover consonants
    attach to the last syllable. Words with no vowel stay whole."""
    syl = _SYL.findall(word)
    if not syl:
        return [word]
    tail = word[len("".join(syl)):]
    if tail:
        syl[-1] += tail
    return syl


def nomenclator(tokens: Sequence[str], seed: int = 0, n_words: int = 60, n_short: int = 300) -> list[str]:
    """Nomenclator-like code. The ``n_words`` most frequent words each get one 2-symbol code;
    every other word is split into syllables and each syllable gets a 2-symbol code (the
    ``n_short`` most frequent syllables) or a 3-symbol code (rarer syllables). Code alphabet:
    20 symbols; codes assigned at random (not frequency ordered). Output word = concatenation."""
    rng = random.Random(seed)
    alpha = GREEK[:20]
    wc = Counter(tokens)
    top_words = {w for w, _ in wc.most_common(n_words)}
    sc = Counter(s for w in tokens if w not in top_words for s in syllabify(w))
    items = [("W", w) for w in sorted(top_words)] + [("S", s) for s, _ in sc.most_common()]
    n2 = n_words + n_short
    pairs = [a + b for a in alpha for b in alpha]
    rng.shuffle(pairs)
    triples = set()
    code: dict = {}
    pi = 0
    for rank, it in enumerate(items):
        if rank < n2 and pi < len(pairs):
            code[it] = pairs[pi]
            pi += 1
        else:
            while True:
                c = "".join(rng.choice(alpha) for _ in range(3))
                if c not in triples:
                    triples.add(c)
                    break
            code[it] = c
    out = []
    for w in tokens:
        if w in top_words:
            out.append(code[("W", w)])
        else:
            out.append("".join(code[("S", s)] for s in syllabify(w)))
    return out


def verbose_2sym(tokens: Sequence[str], seed: int = 0, homophones: int = 2, alphabet_size: int = 16) -> list[str]:
    """Verbose cipher: every plaintext letter -> one of ``homophones`` distinct 2-symbol groups
    (chosen uniformly at random each time). Word boundaries are kept."""
    rng = random.Random(seed)
    alpha = GREEK[:alphabet_size]
    letters = sorted({c for t in tokens for c in t})
    pairs = [a + b for a in alpha for b in alpha]
    if len(letters) * homophones > len(pairs):
        raise ValueError("not enough 2-symbol groups")
    rng.shuffle(pairs)
    table = {c: pairs[i * homophones:(i + 1) * homophones] for i, c in enumerate(letters)}
    return ["".join(rng.choice(table[c]) for c in t) for t in tokens]


def naibbe_like(tokens: Sequence[str], seed: int = 0, p_bigram: float = 0.45, n_bigrams: int = 60,
                alphabet_size: int = 14, max_homophones: int = 4) -> list[str]:
    """Verbose homophonic cipher in the *spirit* of the Naibbe cipher (NOT Greshko's tables).

    Each word is cut into tiles left to right: with probability ``p_bigram`` a frequent bigram
    (one of the ``n_bigrams`` most frequent in the plaintext) is taken as one tile if it fits,
    otherwise a single letter. Every tile has several ciphertext groups (frequent letters get up
    to ``max_homophones``; bigram tiles get 2), each group a random string of 2-3 symbols; a group
    is drawn at random on every use."""
    rng = random.Random(seed)
    alpha = GREEK[:alphabet_size]
    lc = Counter(c for t in tokens for c in t)
    bc = Counter(t[i:i + 2] for t in tokens for i in range(len(t) - 1))
    bigrams = {b for b, _ in bc.most_common(n_bigrams)}
    total = sum(lc.values())
    used: set[str] = set()

    def new_group(length):
        while True:
            g = "".join(rng.choice(alpha) for _ in range(length))
            if g not in used:
                used.add(g)
                return g

    table: dict[str, list[str]] = {}
    for c, v in sorted(lc.items()):
        n = max(1, min(max_homophones, round(v / total * 40)))
        table[c] = [new_group(rng.choice((2, 3))) for _ in range(n)]
    for b in sorted(bigrams):
        table[b] = [new_group(rng.choice((2, 3, 3))) for _ in range(2)]
    out = []
    for t in tokens:
        i, w = 0, []
        while i < len(t):
            if i + 1 < len(t) and t[i:i + 2] in bigrams and rng.random() < p_bigram:
                w.append(rng.choice(table[t[i:i + 2]]))
                i += 2
            else:
                w.append(rng.choice(table[t[i]]))
                i += 1
        out.append("".join(w))
    return out


def reverse_words(tokens: Sequence[str]) -> list[str]:
    return [t[::-1] for t in tokens]


def alphagram(tokens: Sequence[str]) -> list[str]:
    """Anagram normal form: letters of each word sorted alphabetically (consistent per type)."""
    return ["".join(sorted(t)) for t in tokens]


def shuffle_letters(tokens: Sequence[str], seed: int = 0) -> list[str]:
    """Random permutation of the letters inside every token occurrence (fresh each time)."""
    rng = random.Random(seed)
    out = []
    for t in tokens:
        l = list(t)
        rng.shuffle(l)
        out.append("".join(l))
    return out


def shuffle_tokens(tokens: Sequence[str], seed: int = 0) -> list[str]:
    """Random permutation of the tokens (destroys all order; keeps token and letter counts)."""
    rng = random.Random(seed)
    l = list(tokens)
    rng.shuffle(l)
    return l


# --------------------------------------------------------------- generators (no plaintext meaning)

def markov_char(train: Sequence[str], n_tokens: int, order: int = 2, seed: int = 0) -> list[str]:
    """Character-level Markov gibberish: words are generated from an order-``order`` model
    (with word-start/end markers) trained on ``train``. Word *repetition* patterns, word order
    and any lexicon are NOT modelled; only the letter-transition structure inside words."""
    rng = random.Random(seed)
    trans: dict[tuple, Counter] = {}
    for w in train:
        s = ("^",) * order + tuple(w) + ("$",)
        for i in range(order, len(s)):
            trans.setdefault(s[i - order:i], Counter())[s[i]] += 1
    cache = {k: (list(c), list(c.values())) for k, c in trans.items()}
    out = []
    while len(out) < n_tokens:
        ctx = ("^",) * order
        w = []
        while True:
            syms, wts = cache[ctx]
            x = rng.choices(syms, wts)[0]
            if x == "$":
                break
            w.append(x)
            ctx = ctx[1:] + (x,)
            if len(w) > 30:
                break
        if w:
            out.append("".join(w))
    return out


def iid_letters(train: Sequence[str], n_tokens: int, seed: int = 0) -> list[str]:
    """Letters drawn independently from the training letter distribution; word lengths drawn
    from the training word-length distribution."""
    rng = random.Random(seed)
    lc = Counter(c for t in train for c in t)
    ll = Counter(len(t) for t in train)
    letters, lw = list(lc), list(lc.values())
    lens, lnw = list(ll), list(ll.values())
    return ["".join(rng.choices(letters, lw, k=rng.choices(lens, lnw)[0])) for _ in range(n_tokens)]


def selfcitation(n_tokens: int, seed: int = 0, p_mutate: float = 0.3, window: int = 40,
                 alphabet: str = "abcdefghijklmnopqrstu") -> list[str]:
    """Self-citation generator in the spirit of Timm & Schinner (2020): each new word is a copy
    of a word from the recent past (geometric-ish distance, mean ~``window``/2) which with
    probability ``p_mutate`` is changed by one random edit (replace 70 %, insert up to 15 % when
    the word has < 9 letters, otherwise delete when it has > 2). Letters are drawn from a Zipf-like distribution. No lexicon, no grammar, no meaning.
    Parameters are NOT fitted to MS 408."""
    rng = random.Random(seed)
    k = len(alphabet)
    w8 = [1.0 / (i + 1) for i in range(k)]
    def rl():
        return rng.choices(alphabet, w8)[0]
    text = ["".join(rl() for _ in range(rng.randint(3, 6))) for _ in range(8)]
    while len(text) < n_tokens:
        back = min(len(text), 1 + int(rng.expovariate(2.0 / window)))
        w = text[-back]
        if rng.random() < p_mutate and w:
            r = rng.random()
            pos = rng.randrange(len(w))
            # length-regulated edits (insertion only for short words, deletion only for longer
            # ones) keep word length from drifting; without this the mean length random-walks.
            if r < 0.70:
                w = w[:pos] + rl() + w[pos + 1:]
            elif r < 0.85 and len(w) < 9:
                w = w[:pos] + rl() + w[pos:]
            elif len(w) > 2:
                w = w[:pos] + w[pos + 1:]
        text.append(w)
    return text[:n_tokens]


SLOT_INVENTORIES = (
    # (symbols, weights) for each slot; Zipf-like weights; abstract letters, NOT EVA values
    (["", "q", "s"], [0.55, 0.30, 0.15]),
    (["d", "k", "t", "l", "r", "p"], [1 / (i + 1) for i in range(6)]),
    (["o", "a", "e", "i", "oe", "ai"], [1 / (i + 1) for i in range(6)]),
    (["", "y", "n", "in", "l", "r", "m"], [0.35, 0.25, 0.15, 0.1, 0.07, 0.05, 0.03]),
)


def slot_grammar(n_tokens: int, seed: int = 0, p_second_core: float = 0.35) -> list[str]:
    """Slot-grammar word generator: word = onset + head + vowel [+ head + vowel] + tail, each slot
    drawn independently from a small Zipf-weighted inventory. Words have strong positional
    constraints by construction but no meaning.

    CAUTION: the inventories were written with the published *descriptions* of Voynichese word
    structure in mind (q- onsets, -y/-n/-in endings, a few frequent 'gallows-like' heads); the
    letters are abstract but the design is not independent of MS 408. Resembling MS 408's
    positional statistics is therefore expected and is NOT evidence for a slot-grammar origin."""
    rng = random.Random(seed)
    def pick(i):
        s, w = SLOT_INVENTORIES[i]
        return rng.choices(s, w)[0]
    out = []
    for _ in range(n_tokens):
        w = pick(0) + pick(1) + pick(2)
        if rng.random() < p_second_core:
            w += pick(1) + pick(2)
        w += pick(3)
        out.append(w or "o")
    return out


TRANSFORMS: dict[str, Callable] = {
    "abjad": lambda t, seed=0: abjad(t),
    "monoalphabetic": monoalphabetic,
    "caesar3": lambda t, seed=0: caesar(t, 3),
    "vigenere_k3": lambda t, seed=0: vigenere(t, 3, seed),
    "vigenere_k6": lambda t, seed=0: vigenere(t, 6, seed),
    "nomenclator": nomenclator,
    "verbose_2sym": verbose_2sym,
    "naibbe_like": naibbe_like,
    "reverse_words": lambda t, seed=0: reverse_words(t),
    "alphagram": lambda t, seed=0: alphagram(t),
    "shuffle_letters": shuffle_letters,
    "shuffle_tokens": shuffle_tokens,
}


# Alphabet-independent subset: these work on any script (Hebrew, Arabic ...). Not included on
# purpose: monoalphabetic/caesar (provably invisible, already demonstrated), abjad (a natural
# abjad text already has no vowel letters) and nomenclator (its syllabifier needs Latin vowels).
GENERIC_TRANSFORMS: dict[str, Callable] = {
    "vigenere_k3": lambda t, seed=0: vigenere_generic(t, 3, seed),
    "vigenere_k6": lambda t, seed=0: vigenere_generic(t, 6, seed),
    "verbose_2sym": verbose_2sym,
    "naibbe_like": naibbe_like,
    "reverse_words": lambda t, seed=0: reverse_words(t),
    "alphagram": lambda t, seed=0: alphagram(t),
    "shuffle_letters": shuffle_letters,
    "shuffle_tokens": shuffle_tokens,
}
