import h23_lib as L

T = [f"qo{'k' * (i % 3)}edy" for i in range(900)]


def test_variants_rate_and_labels():
    for v in L.VARIANTS:
        out, lab, n = L.copy_variant(T, list(range(900)), .2, v, seed=3)
        assert len(out) == 900 and sum(l is None for l in lab) == n and 0 < n < 300, v
    assert L.copy_variant(T, list(range(900)), 0, "ref", 1)[0] == T


def test_inline_never_copies_line_start_and_prevline_needs_a_line():
    out, lab, _ = L.copy_variant(T, list(range(900)), 1.0, "inline", seed=1)
    assert all(lab[i] is not None for i in range(0, 900, 9))
    out, lab, _ = L.copy_variant(T, list(range(900)), 1.0, "prevline", seed=1)
    assert all(l is not None for l in lab[:9])


def test_swap_changes_final_unit():
    out, lab, n = L.copy_variant(["qokedy", "qokol", "dal"] * 100, list(range(300)), .5, "swap", seed=2)
    assert n > 0 and all(o in {"qokedy", "qokol", "dal"} or lab[i] is None for i, o in enumerate(out))
