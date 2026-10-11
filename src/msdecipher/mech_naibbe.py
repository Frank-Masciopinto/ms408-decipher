"""The Naibbe cipher (Greshko 2025): a verbose homophonic substitution cipher applied to Latin/Italian.

Faithful re-implementation of the published scheme, written from the paper's description and the
author's released code (https://github.com/greshko/naibbe-cipher, MIT with a citation clause):

    Greshko, Michael A. (2025). The Naibbe cipher: a substitution cipher that encrypts Latin and
    Italian as Voynich Manuscript-like ciphertext. Cryptologia. https://doi.org/10.1080/01611194.2025.2566408

The scheme
* The plaintext is reduced to the 23-letter alphabet of the tables (``j->i``, ``k->c``, ``w->uu``),
  spaces are removed, and the letter stream is *re-spaced at random* into **unigrams** (one letter)
  and **bigrams** (two letters). A unigram is chosen with probability ``p_uni`` = 17/36 at each
  step (the paper's "standard respacing", a slight excess of bigrams; 18/36 gives 50:50), and the
  last letter of a text is always a unigram.
* Six substitution tables: one primary (alpha), three secondary (beta1-3), two tertiary (gamma1-2).
  Each table maps every plaintext letter, in each of three states (unigram; first letter of a
  bigram = *prefix*; second letter of a bigram = *suffix*) to a string of Voynichese (EVA) glyphs.
  A unigram becomes a whole word; a bigram becomes one word = prefix string + suffix string.
  The tables are the author's (``data/mechanisms/naibbe_tables.csv``); I did not re-derive them.
* **Card-draw scheme:** for every plaintext *letter* a card is drawn from a shuffled deck, and the
  card selects the table. 78-card (tarocchi) deck: 28 alpha, 14 beta1, 11 beta2, 11 beta3, 7 gamma1,
  7 gamma2; 52-card deck: 20/8/8/8/4/4 (both ~5:2:2:2:1:1). The deck is reshuffled when exhausted
  (the author's code also starts a fresh deck for every plaintext line).
* **Unambiguous bigrams:** a drawn (prefix, suffix) pair is rejected, and two new cards drawn, if the
  concatenated word equals any unigram word or can also be produced by a *different* (prefix, suffix)
  pair, so the ciphertext stays uniquely decodable (``decrypt``).

Not part of the cipher and therefore absent here: nulls, line/paragraph/page structure, any
correlation between plaintext and word position (the paper lists this as a known limitation).
This is an attempt to reproduce the *word-level* statistics of Voynich B, not a claim that the
manuscript is Naibbe-enciphered."""
from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path
from typing import Sequence

from .paths import repo_root

TABLES = ("alpha", "beta1", "beta2", "beta3", "gamma1", "gamma2")
CARD_WEIGHTS = {
    52: {"alpha": 20, "beta1": 8, "beta2": 8, "beta3": 8, "gamma1": 4, "gamma2": 4},
    78: {"alpha": 28, "beta1": 14, "beta2": 11, "beta3": 11, "gamma1": 7, "gamma2": 7},
}
P_UNIGRAM_STANDARD = 17 / 36          # "standard respacing" of the paper (slight bigram excess)
P_UNIGRAM_BALANCED = 18 / 36          # "simplified respacing" (50:50)
ALPHABET = "abcdefghilmnopqrstuvxyz"   # the 23 letters the tables cover
_REPL = {"æ": "ae", "œ": "oe", "ð": "d", "þ": "th", "ł": "l", "ß": "ss", "ø": "o"}


def clean_plaintext(text: str) -> str:
    """Letters only, lower case, diacritics folded, ``j->i``, ``k->c``, ``w->uu`` (as in the author's code)."""
    import unicodedata
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = "".join(_REPL.get(c, c) for c in t)
    t = "".join(c for c in t if "a" <= c <= "z")
    return t.replace("w", "uu").replace("j", "i").replace("k", "c")


class NaibbeCipher:
    """Naibbe cipher with the author's tables. ``encrypt`` is stochastic (respacing and card draws)."""

    def __init__(self, tables_file: Path | None = None, deck: int = 78, p_unigram: float = P_UNIGRAM_STANDARD,
                 unambiguous: bool = True, max_retries: int = 10000, line_letters: int | None = None):
        if deck not in CARD_WEIGHTS:
            raise ValueError("deck must be 52 or 78")
        path = Path(tables_file) if tables_file else repo_root() / "data" / "mechanisms" / "naibbe_tables.csv"
        self.glyph: dict[tuple[str, str, str], str] = {}        # (state, table, letter) -> EVA string
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                state, table, letter = row["code"].split("_")
                self.glyph[(state, table, letter)] = row["glyphs"]
        self.deck_size, self.p_unigram, self.unambiguous, self.max_retries = deck, p_unigram, unambiguous, max_retries
        self.line_letters = line_letters
        self.unigram_words = {self.glyph[("unigram", t, L)] for t in TABLES for L in ALPHABET}
        # decoding tables
        self.uni_decode: dict[str, set[str]] = defaultdict(set)
        for t in TABLES:
            for L in ALPHABET:
                self.uni_decode[self.glyph[("unigram", t, L)]].add(L)
        self.bi_decode: dict[str, set[tuple[str, str]]] = defaultdict(set)
        for t1 in TABLES:
            for L1 in ALPHABET:
                p = self.glyph[("prefix", t1, L1)]
                for t2 in TABLES:
                    for L2 in ALPHABET:
                        self.bi_decode[p + self.glyph[("suffix", t2, L2)]].add((L1, L2))
        self.retries = 0
        self.bigrams = 0

    # ---- encryption
    def _deck(self, rng: random.Random) -> list[str]:
        d = [t for t, n in CARD_WEIGHTS[self.deck_size].items() for _ in range(n)]
        rng.shuffle(d)
        return d

    def respace(self, letters: str, rng: random.Random) -> list[str]:
        out, i = [], 0
        while i < len(letters):
            if i == len(letters) - 1 or rng.random() < self.p_unigram:
                out.append(letters[i])
                i += 1
            else:
                out.append(letters[i:i + 2])
                i += 2
        return out

    def encrypt_letters(self, letters: str, rng: random.Random) -> list[str]:
        """One line of cleaned plaintext -> list of ciphertext words (a fresh shuffled deck per call)."""
        deck, k = self._deck(rng), 0

        def draw():
            nonlocal deck, k
            if k >= len(deck):
                deck, k = self._deck(rng), 0
            k += 1
            return deck[k - 1]
        words = []
        for g in self.respace(letters, rng):
            if len(g) == 1:
                words.append(self.glyph[("unigram", draw(), g)])
                continue
            self.bigrams += 1
            for _ in range(self.max_retries):
                t1, t2 = draw(), draw()
                p, s = self.glyph[("prefix", t1, g[0])], self.glyph[("suffix", t2, g[1])]
                w = p + s
                if self.unambiguous and (w in self.unigram_words or len(self.bi_decode[w]) > 1):
                    self.retries += 1
                    continue
                break
            words.append(w)
        return words

    def encrypt(self, plain_words: Sequence[str], seed: int = 0, n_words_out: int | None = None) -> list[str]:
        """Encrypt a word list (cleaned, spaces removed, processed in pseudo-lines of ``line_letters`` letters,
        default one plaintext word-group of ~60 letters). Stops after ``n_words_out`` ciphertext words if given."""
        rng = random.Random(seed)
        L = self.line_letters or 60
        text = clean_plaintext(" ".join(plain_words))
        out: list[str] = []
        for i in range(0, len(text), L):
            out += self.encrypt_letters(text[i:i + L], rng)
            if n_words_out and len(out) >= n_words_out:
                return out[:n_words_out]
        return out

    # ---- decryption (the cipher is uniquely decodable when ``unambiguous``)
    def decrypt_word(self, w: str) -> str | None:
        if w in self.uni_decode and len(self.uni_decode[w]) == 1:
            return next(iter(self.uni_decode[w]))
        if w not in self.uni_decode and w in self.bi_decode and len(self.bi_decode[w]) == 1:
            return "".join(next(iter(self.bi_decode[w])))
        return None

    def decrypt(self, words: Sequence[str]) -> str:
        out = []
        for w in words:
            d = self.decrypt_word(w)
            if d is None:
                raise ValueError(f"ambiguous or unknown ciphertext word {w!r}")
            out.append(d)
        return "".join(out)

    def stats(self) -> dict:
        uni = {w for w in self.unigram_words}
        n_amb_uni = sum(len(v) > 1 for v in self.uni_decode.values())
        return {"unigram_word_types": len(uni), "bigram_word_types": len(self.bi_decode),
                "unigram_words_ambiguous": n_amb_uni,
                "bigram_words_ambiguous": sum(len(v) > 1 for v in self.bi_decode.values()),
                "bigram_words_equal_unigram": sum(w in uni for w in self.bi_decode)}
