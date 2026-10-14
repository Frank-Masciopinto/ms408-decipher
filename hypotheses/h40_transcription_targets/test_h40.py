"""Unit tests for the h40 tokenizer wrapper. No full scoring."""
import h40_lib as H
import h13_lib

LOCUS = "<f1r.2,+P0>       or,y"


def test_join_makes_ory_one_token_and_split_makes_two():
    assert H.locus_tokens(LOCUS, join=True) == ["ory"]
    assert H.locus_tokens(LOCUS, join=False) == ["or", "y"]


def test_join_patch_matches_wrapper_and_restores_loader():
    assert H.loader_restored()
    with H.applied_transcription("zl_join"):
        toks, _para = h13_lib.tokens_raw(LOCUS)
        assert [w for w, _ok in toks] == ["ory"]
        assert h13_lib.H9.TR.name == "ZL3b-n.txt"
    assert H.loader_restored()
    assert H.locus_tokens(LOCUS, join=False) == ["or", "y"]
