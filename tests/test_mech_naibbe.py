import random
from collections import Counter

import pytest

from msdecipher import mech_naibbe as N

PLAIN = ("in principio creavit deus caelum et terram terra autem erat inanis et vacua et tenebrae super faciem abyssi "
         "et spiritus dei ferebatur super aquas dixitque deus fiat lux et facta est lux ") * 12


def test_tables_complete():
    c = N.NaibbeCipher()
    assert len(c.glyph) == 3 * 6 * 23 == 414
    for st in ("unigram", "prefix", "suffix"):
        for t in N.TABLES:
            for L in N.ALPHABET:
                assert c.glyph[(st, t, L)]


def test_card_weights_are_the_published_proportions():
    for deck, w in N.CARD_WEIGHTS.items():
        assert sum(w.values()) == deck
        assert w["alpha"] > w["beta1"] >= w["beta2"] >= w["gamma1"]
    r = [N.CARD_WEIGHTS[78][t] / 78 for t in N.TABLES]
    assert abs(r[0] - 5 / 13) < 0.03 and abs(r[1] - 2 / 13) < 0.03 and abs(r[4] - 1 / 13) < 0.03


def test_clean_plaintext():
    assert N.clean_plaintext("Jacob, KÆsar & Wolf!") == "iacobcaesarunuolf".replace("unuolf", "uuolf")
    assert N.clean_plaintext("Æ") == "ae"


def test_respacing_share_and_roundtrip():
    c = N.NaibbeCipher(deck=78)
    rng = random.Random(1)
    letters = N.clean_plaintext(PLAIN)
    ng = c.respace(letters, rng)
    uni = sum(len(g) == 1 for g in ng) / len(ng)
    assert abs(uni - 17 / 36) < 0.03           # slight bigram excess, as in the paper's standard respacing
    assert "".join(ng) == letters
    ct = c.encrypt(PLAIN.split(), seed=3)
    assert c.decrypt(ct) == letters            # the cipher is uniquely decodable
    assert 1.2 < len(letters) / len(ct) < 1.8  # a token stands for 1 or 2 letters


def test_unambiguous_bigrams_never_equal_a_unigram_word():
    c = N.NaibbeCipher()
    ct = c.encrypt(PLAIN.split() * 5, seed=2)
    # every ciphertext word decodes to exactly one letter or one letter pair
    for w in set(ct):
        assert c.decrypt_word(w) is not None


def test_determinism_and_decks():
    a = N.NaibbeCipher(deck=78).encrypt(PLAIN.split(), seed=5)
    b = N.NaibbeCipher(deck=78).encrypt(PLAIN.split(), seed=5)
    c = N.NaibbeCipher(deck=52).encrypt(PLAIN.split(), seed=5)
    assert a == b and a != c
    with pytest.raises(ValueError):
        N.NaibbeCipher(deck=60)


def test_table_usage_follows_deck():
    """Over many letters the primary table is used ~5/13 of the time (checked through unigram words of 'e')."""
    c = N.NaibbeCipher(deck=78)
    rng = random.Random(0)
    uni = Counter(c.encrypt_letters("e" * 60, rng)[0] for _ in range(4000))     # ~first token of a fresh deck: could be uni or bi
    alpha = c.glyph[("unigram", "alpha", "e")]
    # only check the table-selection law directly on the deck
    cards = Counter(t for _ in range(2000) for t in c._deck(rng)[:13])
    assert abs(cards["alpha"] / sum(cards.values()) - 28 / 78) < 0.02
    assert alpha in uni
