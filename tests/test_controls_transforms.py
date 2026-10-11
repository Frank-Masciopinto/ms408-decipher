from collections import Counter

from msdecipher import controls_transforms as T
from msdecipher import stats as S

TEXT = ("in principio creavit deus caelum et terram terra autem erat inanis et vacua et tenebrae "
        "erant super faciem abyssi et spiritus dei ferebatur super aquas dixitque deus fiat lux "
        "et facta est lux et vidit deus lucem quod esset bona et divisit lucem a tenebris").split() * 40


def test_abjad_removes_vowels_and_drops_empty():
    out = T.abjad(["deus", "et", "a", "io", "terra"])
    assert out == ["ds", "t", "terra".replace("e", "").replace("a", "")]
    assert all(not set(w) & set("aeiou") for w in out)


def test_monoalphabetic_and_caesar_preserve_statistics():
    base = S.entropy_profile([tuple(w) for w in TEXT], n_shuffles=2)
    for out in (T.monoalphabetic(TEXT, 3), T.caesar(TEXT, 5)):
        assert len(out) == len(TEXT)
        assert len(set(out)) == len(set(TEXT))                       # one-to-one on words
        p = S.entropy_profile([tuple(w) for w in out], n_shuffles=2)
        for k in ("H1", "h2", "h3"):
            assert abs(p[k] - base[k]) < 1e-9                       # relabelling is invisible


def test_vigenere_flattens_h1_and_is_seeded():
    a = T.vigenere(TEXT, 6, seed=1)
    assert a == T.vigenere(TEXT, 6, seed=1)
    assert a != T.vigenere(TEXT, 6, seed=2)
    h1 = lambda ws: S.block_entropy([tuple(w) for w in ws], 1)
    assert h1(a) > h1(TEXT)
    assert [len(x) for x in a] == [len(x) for x in TEXT]            # word lengths preserved


def test_syllabify_roundtrip():
    for w in ["terra", "principio", "abyssi", "ex", "spiritus", "str"]:
        assert "".join(T.syllabify(w)) == w
    assert T.syllabify("terra") == ["te", "rra"]


def test_nomenclator_is_consistent_and_changes_alphabet():
    out = T.nomenclator(TEXT, seed=1, n_words=5, n_short=20)
    assert len(out) == len(TEXT)
    m = {}
    for a, b in zip(TEXT, out):
        assert m.setdefault(a, b) == b                               # same word -> same code
    assert not set("".join(out)) & set("abcdefghijklmnopqrstuvwxyz")
    assert T.nomenclator(TEXT, seed=1, n_words=5, n_short=20) == out


def test_verbose_two_symbols_per_letter():
    out = T.verbose_2sym(TEXT, seed=1)
    assert all(len(o) == 2 * len(t) for o, t in zip(out, TEXT))
    # at most `homophones` distinct 2-groups per plaintext letter
    groups = {}
    for t, o in zip(TEXT, out):
        for i, c in enumerate(t):
            groups.setdefault(c, set()).add(o[2 * i:2 * i + 2])
    assert max(len(v) for v in groups.values()) <= 2


def test_naibbe_like_is_longer_and_seeded():
    out = T.naibbe_like(TEXT, seed=1)
    assert out == T.naibbe_like(TEXT, seed=1)
    assert sum(map(len, out)) > sum(map(len, TEXT))
    assert len(out) == len(TEXT)


def test_reversal_anagram_shuffles():
    assert T.reverse_words(["abc", "de"]) == ["cba", "ed"]
    assert T.reverse_words(T.reverse_words(TEXT)) == TEXT
    assert T.alphagram(["terra", "erat"]) == ["aerrt", "aert"]
    sh = T.shuffle_letters(TEXT, 1)
    assert [sorted(a) for a in sh] == [sorted(a) for a in TEXT]
    st = T.shuffle_tokens(TEXT, 1)
    assert Counter(st) == Counter(TEXT) and st != TEXT


def test_generators_shape_and_determinism():
    for gen in (lambda s: T.markov_char(TEXT, 500, 2, s), lambda s: T.iid_letters(TEXT, 500, s),
                lambda s: T.selfcitation(500, s), lambda s: T.slot_grammar(500, s)):
        a, b = gen(1), gen(1)
        assert a == b and len(a) == 500 and all(a)
        assert gen(2) != a


def test_selfcitation_has_many_near_repeats():
    t = T.selfcitation(3000, 1)
    ident = sum(1 for a, b in zip(t, t[1:]) if a == b)
    assert ident > 0 and len(set(t)) < len(t) * 0.6


def test_slot_grammar_has_positional_structure():
    t = T.slot_grammar(4000, 1)
    first = Counter(w[0] for w in t)
    last = Counter(w[-1] for w in t)
    assert first != last
