import random

import numpy as np
import pytest

from msdecipher import controls_ci as CI
from msdecipher import quires as Q
from msdecipher.paths import transcription_dir

HAVE = (transcription_dir() / "ZL3b-n.txt").exists()


@pytest.fixture(scope="module")
def df():
    return Q.load_quires()


def test_make_group_blocks_and_jackknife():
    pages = [["a"], ["b", "c"], ["d"], ["e"]]
    gb = CI.make_group_blocks(pages, [1, 1, 2, 3])
    assert gb == [["a", "b", "c"], ["d"], ["e"]]
    assert sorted(CI.leave_out(gb, 0)) == ["d", "e"]
    assert len(CI.resample_blocks(gb, random.Random(0))) >= 3
    with pytest.raises(ValueError):
        CI.make_group_blocks(pages, [1])


def test_existing_make_blocks_unchanged():
    assert CI.make_blocks([["a"], ["b"], ["c"]], 2) == [["a", "b"], ["c"]]


def test_quire_map_structure(df):
    assert df["quire"].nunique() == 18
    assert set(range(1, 21)) - set(df["quire"]) == {16, 18}
    assert len(df) >= 220


def test_conjugates(df):
    def conj(leaf):
        return df.loc[df.leaf == leaf, "conjugate_leaf"].iloc[0]
    assert conj("f1") == "f8" and conj("f8") == "f1"
    assert conj("f13") == "missing"          # f12 lost
    assert conj("f57") == "f66" and conj("f58") == "f65"
    assert conj("f73") == "missing"          # f74 lost
    assert conj("f103") == "f116" and conj("f108") == "f111"


def test_positions_and_foldouts(df):
    pos = df.drop_duplicates("leaf").set_index("leaf")["position_in_quire"]
    assert pos["f57"] == 1 and pos["f58"] == 2 and pos["f65"] == 9 and pos["f66"] == 10
    assert pos["f111"] == 9 and pos["f116"] == 14 and pos["f9"] == 1
    fo = set(df.loc[df.foldout, "leaf"])
    assert {"f67", "f68", "f85", "f86", "f89", "f101", "f102"} <= fo
    assert "f1" not in fo and "f75" not in fo


def test_lfd_numbering_and_hands(df):
    m = df.drop_duplicates("quire").set_index("quire")["lfd2020_quire"]
    assert m[17] == 16 and m[19] == 17 and m[20] == 18
    assert set(df.loc[df.leaf.isin(["f41", "f48"]), "lfd_hand"]) == {"5"}


def test_group_folds_leak_free(df):
    units = list(df["page"])
    for level in ("quire", "bifolium"):
        folds = Q.group_folds(units, df, 5, level, seed=1)
        assert Q.leakage(units, folds, df, level) == 0
        te = sorted(i for _, t in folds for i in t)
        assert te == list(range(len(units)))
    # naive page-level split leaks
    rng = np.random.default_rng(0)
    idx = rng.permutation(len(units))
    naive = [(sorted(set(range(len(units))) - set(idx[k::5])), sorted(idx[k::5])) for k in range(5)]
    assert Q.leakage(units, naive, df, "quire") > 0


def test_group_units_leaf_and_unknown(df):
    assert Q.group_units(["f12", "f1r", "xyz"], df) == ["?f12", "1", "?xyz"]


def test_ms_uncertainty_default_signature():
    import inspect
    from msdecipher import mech_hybrid_topics as MT
    sig = inspect.signature(MT.ms_uncertainty)
    assert sig.parameters["n_boot"].default == 300 and sig.parameters["group_of"].default is None
