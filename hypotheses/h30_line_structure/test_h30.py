import numpy as np

import h30_lib as L


def test_pos_bin_and_mi():
    assert [L.pos_bin(i, 6) for i in range(6)] == [0, 1, 2, 2, 3, 4]
    assert L.mi([(0, "a"), (1, "b")] * 5) == 1.0 and L.mi([(0, "a"), (1, "a")]) == 0.0


def test_permute_within_keeps_lengths_and_multiset():
    lines = [dict(stratum="s", page="p") for _ in range(3)]; cl = [["a", "b"], ["c"], ["d", "e", "f"]]
    out = L.permute_within(lines, cl, np.random.default_rng(0))
    assert [len(x) for x in out] == [2, 1, 3] and sorted(sum(out, [])) == list("abcdef")


def test_models_positional_beats_bag_on_slotted_lines():
    lines = [["H", "x", "y", "x", "E"], ["H", "y", "x", "y", "E"]] * 40
    b = L.model_bits(lines[:60], lines[60:], 4); assert b["positional"] < b["bag"] and b["hmm"] < b["bag"]
