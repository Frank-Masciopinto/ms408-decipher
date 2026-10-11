import random

import pytest

from msdecipher import mech_selfcitation as S

needs_java = pytest.mark.skipif(not S.available(), reason="reference Java generator not built (see mech_selfcitation.build)")


def test_bounds_are_documented_ranges_and_sampling_stays_inside():
    rng = random.Random(0)
    for _ in range(50):
        p = S.sample_params(rng)
        for k, (lo, hi) in S.BOUNDS.items():
            assert lo <= p[k] <= hi
        for k, ch in S.CHOICES.items():
            assert p[k] in ch
    assert "method.canFollow" not in S.SWEPT          # circular options (MS-408 dictionary / statistics) are not swept
    assert S.BOUNDS["method.morph.replace.probability"] == (20, 100)


def test_param_key_stable_and_sensitive():
    a = S.param_key({"method.morph.add_remove.probability": 10}, 1)
    assert a == S.param_key({"method.morph.add_remove.probability": 10}, 1)
    assert a != S.param_key({"method.morph.add_remove.probability": 11}, 1)
    assert a != S.param_key({"method.morph.add_remove.probability": 10}, 2)


@needs_java
def test_reference_generator_is_deterministic_and_parameter_sensitive():
    a = S.generate({}, 19, 3000)
    assert a == S.generate({}, 19, 3000) and len(a) == 3000
    assert a != S.generate({}, 20, 3000)
    assert a != S.generate({"method.morph.add_remove.probability": 0, "method.morph.replace.probability": 100}, 19, 3000)
    assert a[:4] == ["pchal", "shal", "shorchdy", "okeor"]          # the seed line of the paper (f103v.P.9)
    # self-citation: most words are copies or near-copies of earlier words, so types << tokens
    assert len(set(a)) < 0.4 * len(a)


def test_cached_text_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "available", lambda: False)
    monkeypatch.setattr(S, "cache_dir", lambda: tmp_path)
    (tmp_path / "toy_s1.txt").write_text("aa bb cc\ndd ee\n")
    assert S.generate({}, 1, 4, tag="toy") == ["aa", "bb", "cc", "dd"]
    with pytest.raises(RuntimeError):
        S.generate({}, 2, 4, tag="missing")
