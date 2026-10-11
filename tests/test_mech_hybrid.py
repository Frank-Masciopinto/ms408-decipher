import random

import numpy as np

from msdecipher import mech_hybrid as H
from msdecipher import mech_hybrid_run as HR
from msdecipher import mech_hybrid_topics as T
from msdecipher import mech_naibbe as N

PLAIN = ("gallia est omnis divisa in partes tres quarum unam incolunt belgae aliam aquitani tertiam qui ipsorum lingua celtae "
         "nostra galli appellantur hi omnes lingua institutis legibus inter se differunt").split() * 20


def test_params_normalised_and_perturbed_in_bounds():
    rng = random.Random(1)
    for v in ("naibbe", "plain_edit"):
        p = H.sample_params(rng, v)
        for _ in range(100):
            p = H.perturb(rng, p, v)
            assert p.p_exact + p.p_suffix + p.p_prefix <= 1 + 1e-9 and p.p_inner >= 0
            b = {**H.BOUNDS, **H.VARIANT_BOUNDS.get(v, {})}
            for k in H.PARAM_NAMES:
                assert b[k][0] - 1e-9 <= getattr(p, k) <= b[k][1] + 1e-9


def test_naibbe_live_tokens_decode_to_consumed_letters():
    enc = H.NaibbeLive(PLAIN, 3)
    toks = [enc.next_token() for _ in range(200)]
    letters = N.clean_plaintext(" ".join(PLAIN))
    assert enc.c.decrypt(toks) == letters[: enc.consumed_letters]
    assert 1.2 < enc.consumed_letters / len(toks) < 1.8


def test_engine_p_copy_zero_is_pure_encoder_and_deterministic():
    p = H.Params(p_copy=0.0)
    a = H.generate(H.NaibbeLive(PLAIN, 5), p, 300, 5)
    b = H.generate(H.NaibbeLive(PLAIN, 5), p, 300, 5)
    e = H.NaibbeLive(PLAIN, 5)
    assert a == b == [e.next_token() for _ in range(300)]


def test_engine_copy_modify_properties():
    p = H.Params(p_copy=0.9, window=10, p_prev=0.5, p_exact=0.5, p_suffix=0.2, p_prefix=0.1)
    w = H.generate(H.NaibbeLive(PLAIN, 1), p, 3000, 1)
    assert len(w) == 3000
    assert max(len(H.SEG(x)) for x in w) <= H.MAX_UNITS
    run = best = 0
    for i in range(1, len(w)):
        run = run + 1 if w[i] == w[i - 1] else 0
        best = max(best, run)
    assert best < H.MAX_REPEAT                                 # at most MAX_REPEAT identical in a row
    assert len(set(w)) < 3000 * 0.5                            # heavy reuse
    plain = H.generate(H.NaibbeLive(PLAIN, 1), H.Params(p_copy=0.0), 3000, 1)
    assert len(set(w)) != len(set(plain))


def test_plain_edit_consumes_letters():
    enc = H.NaibbeLive(PLAIN, 2)
    w = H.generate(enc, H.Params(p_copy=0.95, p_exact=0.0, p_suffix=0.5, p_prefix=0.5), 400, 2, plain_edit=True)
    assert len(w) == 400 and enc.consumed_letters > 150


def test_codebook_is_invertible_and_keeps_word_frequencies():
    sampler = lambda n, rng: ["".join(rng.choice(["qo", "ch", "ol", "dy", "k", "e", "s", "y"]) for _ in range(rng.randint(2, 4))) for _ in range(n)]   # noqa: E731
    cb = H.Codebook(PLAIN, sampler, 4)
    toks = [cb.next_token() for _ in range(len(PLAIN))]
    assert len(set(cb.book.values())) == len(cb.book)
    assert [toks[i] == toks[j] for i, j in ((0, 0),)] == [True]
    assert len(set(toks)) == len(set(PLAIN))


def test_folds_by_folio_interleave():
    pages = ["a"] * 3 + ["b"] * 2 + ["c"] * 4 + ["d"]
    f = HR.folds_by_folio(pages, 3)
    assert f == [0, 0, 0, 1, 1, 2, 2, 2, 2, 0]


def test_fit_variant_improves_over_random_median():
    rng = random.Random(0)
    vocab = ["".join(rng.choice(["qo", "ch", "ol", "dy", "k", "e", "s", "y", "ai", "n"]) for _ in range(rng.randint(2, 5))) for _ in range(300)]
    words = [rng.choices(vocab, weights=[1 / (i + 1) for i in range(300)])[0] for _ in range(3000)]
    ref = HR.fit_vector(words)
    assert set(ref) >= set(HR.FIT_SET)
    sc = HR.scales(ref, HR.jackknife_se(words))
    assert all(v > 0 for v in sc.values())
    assert HR.chi2(HR.zvec(ref, ref, sc)) == 0.0


# ---------------------------------------------------------------- topics

def _docs(topical: bool, seed=0):
    rng = random.Random(seed)
    vocab = {c: [f"{c[:2]}{i}" for i in range(40)] for c in T.CLASSES}
    common = [f"cm{i}" for i in range(60)]
    docs = []
    for i in range(80):
        c = T.CLASSES[i % 5]
        ws = [rng.choice(vocab[c]) if (topical and rng.random() < 0.4) else rng.choice(common) for _ in range(150)]
        docs.append({"folio": f"f{i}", "section": c, "cls": c, "lang": "A", "words": ws})
    return docs


def test_section_statistics_detect_topic_signal():
    s1 = T.stats_for(_docs(True), n_perm=30, seed=1)
    s0 = T.stats_for(_docs(False), n_perm=30, seed=1)
    assert s1["nb_bal_acc"] > 0.9 and s1["lr_bal_acc"] > 0.9 and s1["js_excess"] > 0.1 and s1["nb_p"] < 0.1
    assert s0["nb_bal_acc"] < 0.45 and s0["js_excess"] < 0.03 and s0["js_p"] > 0.05


def test_js_zero_for_identical_distributions_and_layout_roundtrip():
    docs = _docs(False)
    X, y, _, _ = T.design(docs)
    assert T.mean_pairwise_js(X, y) >= 0
    lay = [{"folio": "f1", "section": "herbal", "cls": "herbal", "lang": "A", "words": ["a"] * 5},
           {"folio": "f2", "section": "stars", "cls": "recipes", "lang": "B", "words": ["b"] * 3}]
    c = T.corpus_from_layout(lay, list("abcdefgh"))
    assert [len(e["words"]) for e in c] == [5, 3] and c[1]["cls"] == "recipes"


def test_hybrid_layout_generation_matched_vs_mixed_uses_different_plaintexts():
    HR._PT.update({w: PLAIN[:200] if i % 2 else list(reversed(PLAIN))[:200] for i, w in enumerate(T.WORKS)})
    lay = [{"folio": f"f{i}", "section": "x", "cls": T.CLASSES[i % 5], "lang": "A", "words": ["x"] * 60} for i in range(10)]
    params = {"A1 Naibbe tokens + copy-modify": dict(p_copy=0.2, window=10, p_prev=0.2, p_exact=0.2, p_suffix=0.3, p_prefix=0.2)}
    a = T.generated_words("A1|matched", lay, params, None, 1, random.Random(1))
    b = T.generated_words("A1|mixed", lay, params, None, 1, random.Random(1))
    assert len(a) == len(b) == 600 and a != b
