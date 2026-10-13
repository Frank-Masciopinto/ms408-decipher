import h24_lib as L

P = L.clean("Nel mezzo del cammin di nostra vita mi ritrovai per una selva oscura".split() * 20)


def test_ciphers_are_word_preserving_and_neutral():
    assert len(set(L.GLYPHS)) == len(L.GLYPHS) >= 104 and not any("a" <= g <= "z" for g in L.GLYPHS)
    for c in L.CIPHERS:
        ct = L.encipher(P, c, seed=1); assert len(ct) == len(P) and all(ct) and not any("a" <= ch <= "z" for w in ct for ch in w), c


def test_verbose_and_nomenclator_deterministic_homophones_vary():
    v = L.encipher(P, "verb8", 2); assert v[0] == v[13]          # same word, same codeword
    n = L.encipher(P, "nomen", 2); assert n[0] == n[13] and len(set(n)) <= len(set(P))
    h = L.encipher(P * 5, "homo4", 2); assert len({h[i] for i in range(0, len(h), 13)}) > 1


def test_generic_swap_changes_last_unit_only():
    ct = L.encipher(P, "verb8", 3); out, lab, n = L.copy_variant(ct, list(range(len(ct))), .5, "swap", seed=1)
    assert n > 0
    for i, (o, l) in enumerate(zip(out, lab)):
        if l is None: assert any(o[:-1] == x[:-1] for x in out[max(0, i - 20):i])


def test_tci():
    m, lo, hi = L.tci([1, 2, 3, 4, 5]); assert m == 3 and lo < 3 < hi
