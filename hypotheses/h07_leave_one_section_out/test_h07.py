import json
from collections import Counter

import pytest

import h07_lib as L


def _docs():
    return [{"cls": c, "words": ws} for c, ws in [("herbal", ["daiin", "chol", "chor", "daiin"]), ("recipes", ["qokedy", "daiin", "chedy"]),
                                                  ("biological", ["qokedy", "shedy"]), ("pharmaceutical", ["chol", "okal"]), ("cosmo-astro", ["otar", "daiin"])]]


def test_js_bounds():
    assert L.js_bits(Counter("aab"), Counter("aab")) == pytest.approx(0)
    assert L.js_bits(Counter("a"), Counter("b")) == pytest.approx(1)


def test_section_stats_simple():
    st = L.section_stats(_docs(), "herbal")
    assert st["n_tokens"] == 4
    assert st["overlap_tokens"] == pytest.approx(3 / 4)       # daiin x2 + chol occur elsewhere
    assert st["new_type_rate"] == pytest.approx(1 / 3)        # chor
    assert st["hapax_share"] == pytest.approx(2 / 3)
    assert set(L.STATS) <= set(st)


def test_heldout_text_not_used_by_rest():
    a = L.section_stats(_docs(), "herbal")
    d = _docs()
    d[0]["words"] = ["zzz"] * 4
    b = L.section_stats(d, "herbal")
    assert a["js_to_recipes"] != b["js_to_recipes"] and b["overlap_tokens"] == 0


def test_nearest_rule_metadata_only():
    e = [{"cls": "herbal", "lang": "A"}, {"cls": "pharmaceutical", "lang": "A"}, {"cls": "recipes", "lang": "B"}, {"cls": "biological", "lang": "B"},
         {"cls": "cosmo-astro", "lang": "B"}, {"cls": "cosmo-astro", "lang": "A"}]
    assert L.nearest_section(e, "herbal") == "pharmaceutical"
    assert L.nearest_section(e, "recipes") in ("biological",)


def test_jackknife_finite():
    d = _docs() + [{"cls": "herbal", "words": ["chol", "sho"]}] * 5
    se = L.jackknife_blocks(d, "herbal", block=2)
    assert se["overlap_tokens"] >= 0


def test_manifest_matches_if_present():
    man = L.RESULTS / "predictions_manifest.json"
    if not man.exists():
        pytest.skip("no predictions yet")
    m = json.loads(man.read_text())
    for f in ("prereg.json", "predictions_runs.csv"):
        assert L.sha256(L.RESULTS / f) == m[f]
