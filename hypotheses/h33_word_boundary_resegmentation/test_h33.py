import numpy as np
import h33_lib as L


def test_shift_and_join_preserve_glyphs():
    line = ["qokeedy", "chol", "daiin"]
    for t in ("join2", "shift+1", "shift+2", "shift-1", "shift-2"):
        assert "".join(L.transform([line], t)[0]) == "".join(line)
    assert L.shift(line, 1) == ["qokeed", "ycho", "ldaiin"]
    assert L.shift(line, -1) == ["qokeedyc", "hold", "aiin"]


def test_space_predict_fixed_rule_is_easy():
    rng = np.random.default_rng(0); words = ["ab", "cab", "dab"]
    lines = [[words[rng.integers(3)] for _ in range(8)] for _ in range(300)]
    assert L.space_predict(lines)["entropy_removed"] > 0.9
