"""h27: real Naibbe tables with the plaintext removed (PREREG.md). No translation claims."""
from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h19_heldout_likelihood"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h24_neutral_cipher_robustness"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h25_neutral_hybrid_cipher"))

from msdecipher.mech_naibbe import clean_plaintext  # noqa: E402
import h24_lib  # noqa: E402
import h25_lib  # noqa: E402
import run_h19  # noqa: E402

N_TYPES = 4000
TABLES = ROOT / "data" / "mechanisms" / "naibbe_tables.csv"
_TYPE_DRAW_CAP = N_TYPES * 80


def cleaned_tokens(tokens) -> list[str]:
    """clean_plaintext per token, dropping anything that cleans to empty."""
    out = []
    for tok in tokens:
        cleaned = clean_plaintext(str(tok))
        if cleaned:
            out.append(cleaned)
    return out


def cleaned_lengths(tokens) -> list[int]:
    return [len(tok) for tok in cleaned_tokens(tokens)]


def real_plaintext(tokens) -> list[str]:
    return [str(tok) for tok in tokens]


def shuffle_plaintext(tokens, seed: int) -> list[str]:
    """Same tokens, seeded order. Word-internal spelling is untouched."""
    out = [str(tok) for tok in tokens]
    random.Random(seed).shuffle(out)
    return out


def _length_and_letters(tokens):
    cleaned = cleaned_tokens(tokens)
    if not cleaned:
        raise ValueError("no cleaned tokens to build a zipf plaintext")
    lengths = [len(tok) for tok in cleaned]
    counts = Counter(ch for tok in cleaned for ch in tok)
    alphabet = sorted(counts)
    weights = [counts[ch] for ch in alphabet]
    return lengths, alphabet, weights


def _draw_types(lengths, alphabet, weights, rng: random.Random) -> tuple[list[str], int]:
    types: list[str] = []
    seen: set[str] = set()
    redraws = 0
    draws = 0
    while len(types) < N_TYPES:
        draws += 1
        if draws > _TYPE_DRAW_CAP:
            raise RuntimeError(f"could not draw {N_TYPES} distinct zipf types")
        length = rng.choice(lengths)
        word = "".join(rng.choices(alphabet, weights=weights, k=length))
        if word in seen:
            redraws += 1
            continue
        seen.add(word)
        types.append(word)
    return types, redraws


def zipf_sample(tokens, seed: int) -> tuple[list[str], list[str], int]:
    """4000 types, a draw of len(tokens) tokens, and the duplicate-type redraw count.

    Type length ~ empirical cleaned length. Letters ~ empirical unigram of the
    cleaned letter stream. Ranks follow generation order, P(rank) ∝ 1/rank.
    """
    lengths, alphabet, letter_weights = _length_and_letters(tokens)
    rng = random.Random(seed)
    types, redraws = _draw_types(lengths, alphabet, letter_weights, rng)
    rank_weights = [1.0 / rank for rank in range(1, N_TYPES + 1)]
    drawn = rng.choices(types, weights=rank_weights, k=len(tokens))
    return types, drawn, redraws


def zipf_types(tokens, seed: int) -> list[str]:
    return zipf_sample(tokens, seed)[0]


def zipf_plaintext(tokens, seed: int) -> list[str]:
    return zipf_sample(tokens, seed)[1]


def encrypt_swap(tokens, seed: int, n_words_out: int) -> tuple[list[str], int]:
    """NH on the author's tables, then swap-copy at c=0.05. Same path as the h26 anchor."""
    cipher = h25_lib.NH(TABLES, 6, "naibbe", 17 / 36)
    toks = [str(tok) for tok in cipher.encrypt(tokens, seed=seed, n_words_out=n_words_out)]
    labs = ["#"] * len(toks)
    out, _labs, n_copy = h24_lib.copy_variant(
        toks, labs, 0.05, "swap", seed=100 * seed + 17, seg=run_h19.seg_fn("eva")
    )
    return out, n_copy
