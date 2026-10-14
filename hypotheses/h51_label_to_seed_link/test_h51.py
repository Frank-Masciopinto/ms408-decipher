"""Unit and integration tests for h51_label_to_seed_link."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import h51_lib as H  # noqa: E402


def test_hit_functions_and_stem_stripping():
    # Collapsed EVA units: ch -> 1 unit, sh -> 1 unit, ii -> 2 units
    assert H.eva_units("chedy") == ("ch", "e", "d", "y")
    # stem3 strips leading o/q/d/s and takes first 3 core units
    assert H.stem3("otedy") == ("t", "e", "d")
    assert H.stem3("tedol") == ("t", "e", "d")
    assert H.stem3("qokedy") == ("o", "k", "e")
    assert H.stem3("daiin") == ("a", "i", "i")
    assert H.stem3("chedy") == ("ch", "e", "d")

    para = ["tedol", "qokeey", "chol"]
    assert H.exact_hit("tedol", para) is True
    assert H.exact_hit("otedy", para) is False
    assert H.edit1_hit("qokedy", para) is True  # d vs e in qokedy vs qokeey
    assert H.edit1_hit("otedy", para) is False  # 3 edits from tedol
    assert H.stem_hit("otedy", para) is True  # stem3("otedy") == ("t", "e", "d") == stem3("tedol")


def test_header_onset_stripping():
    # Strips leading d/s/p/t/k/f only when remainder has >= 2 EVA units
    assert H.strip_header_onset("daiin") == "aiin"
    assert H.strip_header_onset("shedy") == "shedy"  # first unit is 'sh', not 's'
    assert H.strip_header_onset("saldal") == "aldal"
    assert H.strip_header_onset("dy") == "dy"  # only 2 units total -> remainder has 1 unit, not stripped


def test_extract_seed_w25_window():
    # Tokens within unit edit distance <= 1 in the last 25 positions are stripped
    toks = ["chedy", "cheey", "shedy", "qokain"] + [f"x{k}aiin" for k in range(25)] + ["chedy"]
    seeds = H.extract_seed_w25(toks, window=25)
    # "cheey" and "shedy" are within edit distance 1 of "chedy" at lag 1 and 2 -> stripped
    assert "cheey" not in seeds
    assert "shedy" not in seeds
    # The second "chedy" is at lag 28 (> 25) from the first "chedy"/"cheey"/"shedy" -> retained
    assert seeds.count("chedy") == 2


def test_synthetic_test1_and_test3():
    # Build two synthetic folios in the same quire with distinct vocabularies and labels
    reps = {
        "f1": {
            "full_para": ["otedy", "oteda", "otedo", "otedl", "otedr", "qokaiin", "chckhy"],
            "seed_W25": ["otedy", "qokaiin", "chckhy"],
            "header_tokens_raw": ["otedy"],
            "header_tokens_stripped": ["otedy"],
            "header_tokens": ["otedy"],
        },
        "f2": {
            "full_para": ["opchedy", "opcheda", "opchedo", "opchedl", "opchedr", "lkaiin", "ykchdy"],
            "seed_W25": ["opchedy", "lkaiin", "ykchdy"],
            "header_tokens_raw": ["opchedy"],
            "header_tokens_stripped": ["opchedy"],
            "header_tokens": ["opchedy"],
        },
    }
    labels = [
        {
            "folio": "f1",
            "line": 1,
            "sub": "f",
            "obj": "plant_part",
            "quire": 1,
            "section": "pharmaceutical",
            "w": "otedy",
            "units": H.eva_units("otedy"),
            "unit_len": len(H.eva_units("otedy")),
            "stem3": H.stem3("otedy"),
        },
        {
            "folio": "f2",
            "line": 1,
            "sub": "f",
            "obj": "plant_part",
            "quire": 1,
            "section": "pharmaceutical",
            "w": "opchedy",
            "units": H.eva_units("opchedy"),
            "unit_len": len(H.eva_units("opchedy")),
            "stem3": H.stem3("opchedy"),
        },
    ]
    t1 = H.run_test1_own_folio(labels, reps, n_perm=50, seed=51)
    assert t1["representations"]["seed_W25"]["exact_hit"]["obs_rate"] == 1.0
    assert t1["representations"]["seed_W25"]["edit1_hit"]["obs_rate"] == 1.0

    t3 = H.run_test3_chain_size(labels, reps, n_perm=50, seed=51)
    main_mode = t3["link_modes"]["edit1_or_stem"]
    assert main_mode["n_linked"] == 2
    assert main_mode["n_unlinked"] == 4
    assert main_mode["mean_progeny_linked"] == 5.0
    assert main_mode["mean_progeny_unlinked"] == 1.0
    assert main_mode["obs_diff"] == 4.0


def test_saved_outputs_and_predictions():
    meas_path = HERE / "results" / "measurements.json"
    sum_path = HERE / "results" / "summary.json"
    stat_path = HERE / "results" / "STATUS.json"
    fig_path = HERE / "figures" / "label_to_seed_link.png"
    readme_path = HERE / "README.md"

    assert meas_path.is_file()
    assert sum_path.is_file()
    assert stat_path.is_file()
    assert fig_path.is_file()
    assert readme_path.is_file()

    data = json.loads(meas_path.read_text(encoding="utf-8"))
    recomputed = H.score_predictions(
        data["test1_own_folio"],
        data["test2_same_plant_seeds"],
        data["test3_chain_size"],
    )
    assert recomputed == data["predictions"]
    assert data["seed"] == 51
    assert data["n_perm"] == 2000
    assert data["paragraph_summary"]["n_folios_ge20_para"] == 206
    assert data["test1_own_folio"]["n_folios"] == 30
    assert data["test1_own_folio"]["n_labels"] == 428
    assert data["test2_same_plant_seeds"]["pairs_16"]["seed_W25"]["edit1_or_stem"]["all_herbal"]["n_pairs"] == 16
    assert data["predictions"]["L1"] is False
    assert data["predictions"]["L2"] is False
    assert data["predictions"]["L3"] is True
