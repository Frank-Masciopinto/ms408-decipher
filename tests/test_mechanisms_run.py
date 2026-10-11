import math

import pandas as pd

from msdecipher import mechanisms_report as MR
from msdecipher import mechanisms_run as R


def _ms():
    return {k: 1.0 for k in R.SUITE}, {k: 0.05 for k in R.SUITE}


def test_fit_distance_zero_at_match_and_grows():
    ms, se = _ms()
    ms = {**ms, **{k: 0.5 for k in R.FIT_METRICS}}
    d0, _ = R.fit_distance(dict(ms), ms, se)
    d1, z = R.fit_distance({k: v + 0.2 for k, v in ms.items()}, ms, se)
    assert d0 == 0.0 and d1 > 3
    assert set(z) == set(R.FIT_METRICS)


def test_suite_covers_requested_groups():
    groups = {g for _, g in R.SUITE.values()}
    for g in ("letter entropy", "within-word shuffle", "positional skew", "slot grammar", "suffix", "Zipf / Heaps",
              "adjacent repeats", "cluster stability"):
        assert g in groups
    assert set(R.FIT_METRICS) & {"unit_h2", "slot_null_gap_type", "affix_suffix_type_share"} == set()   # fit never touches structure metrics


def test_mechanism_table_verdicts_and_scorecard():
    ms, se = _ms()
    rows = []
    for i in range(5):
        rows.append({"mechanism": "A", "variant": "x", "base": "", "seed": i, **{k: 1.0 + 0.01 * i for k in R.SUITE}})
        rows.append({"mechanism": "B", "variant": "x", "base": "", "seed": i, **{k: 3.0 + 0.01 * i for k in R.SUITE}})
    rows.append({"mechanism": "C", "variant": "x", "base": "", "seed": 0, **{k: 1.0 for k in R.SUITE}})      # one run: no honest SD
    runs = pd.DataFrame(rows)
    tab = R.mechanism_table(runs, ms, se)
    assert set(tab.mechanism) == {"A", "B"}
    assert (tab[tab.mechanism == "A"].verdict == "≈").all()
    assert (tab[tab.mechanism == "B"].verdict == "↓").all()           # MS 408 below the mechanism
    sc = R.scorecard(tab)
    assert sc[sc.mechanism == "A"].reproduced.sum() == len(R.SUITE)
    assert sc[sc.mechanism == "B"].reproduced.sum() == 0
    assert "A" in MR.matrix(sc)["mechanism"].tolist()


def test_perturb_stays_in_bounds():
    import random
    from msdecipher import mech_selfcitation as S
    rng = random.Random(1)
    p = S.sample_params(rng)
    for _ in range(200):
        p = R._perturb(rng, p)
        for k, (lo, hi) in S.BOUNDS.items():
            assert lo <= p[k] <= hi


def test_grammar_coverage_counts_tokens():
    c = R.grammar_coverage(["daiin", "daiin", "chedy", "xyz"])
    assert math.isclose(c["cov_zattera_tok"], 0.75) and math.isclose(c["cov_stolfi_tok"], 0.75)


def test_naibbe_info_roundtrips():
    info = R.naibbe_info()
    assert info["roundtrip"].endswith("True")
    assert 1.2 < 1 / info["tokens_per_letter"] < 1.8
