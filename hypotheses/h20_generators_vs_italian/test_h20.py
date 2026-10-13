import itertools

import h20_lib as L


def test_syllables_and_encodings():
    assert L.syllables("chiamato") == ["chia", "ma", "to"] and L.syllables("per") == ["per"]
    assert L.remove_vowels("ordinamento") == "ordnmnt" and L.remove_vowels("a") == "a"
    assert L.suspend("ordinamento") == "ordo" and L.suspend("casa") == "casa"


def test_syllabic_cipher_is_word_preserving():
    ct, book = L.syllabic_cipher(["casa", "cosa", "casa"], ["qo", "ke", "dy", "ol"])
    assert ct[0] == ct[2] and len(book) == 3 and len(ct) == 3


def test_pclm_normalised():
    pc = L.PosCharLM().fit(["abc", "ab", "b", "abcd", "abcdef"] * 3)
    tot = sum(2 ** pc.logp("".join(s)) for n in range(0, 8) for s in itertools.product("abcdef", repeat=n))
    assert 0.9 < tot <= 1.0 + 1e-9


def test_match_logic():
    ms = [dict(D1=-.15, D2=.25, D3=.04, D4=.05, D5=1.8), dict(D1=-.13, D2=.27, D3=.03, D4=.08, D5=1.9)]
    assert L.match(ms[0], ms)["reproduces"]
    m = L.match(dict(D1=.8, D2=.25, D3=.005, D4=-1.5, D5=2.3), ms); assert not m["reproduces"] and m["n_match"] == 1
