"""h42: decay of one-edit near-repeats with token gap (PREREG.md).

Gap is the token-index difference j - i. Gap 1 is the next token.
"""
from __future__ import annotations

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import json
import platform
import sys
import time
from bisect import bisect_left, bisect_right
from collections import defaultdict
from pathlib import Path

import numpy as np
import rapidfuzz
from rapidfuzz.distance import Levenshtein

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (
    ROOT / "src",
    ROOT / "hypotheses" / "h20_generators_vs_italian",
    ROOT / "hypotheses" / "h12_per_hand_copy_modify",
    ROOT / "hypotheses" / "h30_line_structure",
    ROOT / "hypotheses" / "h13_top_word_context",
):
    sys.path.insert(0, str(_p))

import h13_lib  # noqa: E402
import h30_lib  # noqa: E402
import run_h12  # noqa: E402
from fetch_italian import load_italian  # noqa: E402

BINS = (
    ("1", 1, 1),
    ("2-5", 2, 5),
    ("6-20", 6, 20),
    ("21-100", 21, 100),
    ("101-500", 101, 500),
    ("501-1000", 501, 1000),
)
BIN_NAMES = tuple(name for name, _, _ in BINS)
DECAY_SHAPE = {
    "2-5": "local",
    "6-20": "local",
    "21-100": "page",
    "101-500": "page",
    "501-1000": "long",
}
MAX_PAIRS = 4000
N_NULL = 10
NULL_SEED = 42
N_STREAM = 10500
PAGE_TOKENS = 200
PAGES_PER_BLOCK = 8
BLOCK_TOKENS = PAGE_TOKENS * PAGES_PER_BLOCK
H39_DIR = ROOT / "hypotheses" / "h39_graph_respell_and_tuned_copier" / "results"
SELF_CITATION = ROOT / "data" / "mechanisms" / "selfcitation" / "fitted_s1.txt"

_EDIT: dict[tuple[tuple, tuple], bool] = {}


def edit1(a: tuple, b: tuple) -> bool:
    """True when Levenshtein distance on the unit tuples is exactly 1."""
    if abs(len(a) - len(b)) > 1 or a == b:
        return False
    if a > b:
        a, b = b, a
    key = (a, b)
    hit = _EDIT.get(key)
    if hit is None:
        hit = Levenshtein.distance(a, b) == 1
        _EDIT[key] = hit
    return hit


def systematic_ranks(n_eligible: int, k: int) -> list[int]:
    """Evenly spaced ranks 0 .. n_eligible-1. Exactly min(k, n_eligible) of them."""
    if k <= 0 or n_eligible <= 0:
        return []
    if k >= n_eligible:
        return list(range(n_eligible))
    return [(i * n_eligible) // k for i in range(k)]


def index_lengths(lengths: list[int]) -> dict[int, list[int]]:
    by: dict[int, list[int]] = defaultdict(list)
    for i, length in enumerate(lengths):
        by[length].append(i)
    return by


def _spans(by: dict[int, list[int]], length: int, j0: int, j1: int):
    spans = []
    for delta in (-1, 0, 1):
        positions = by.get(length + delta)
        if not positions:
            continue
        a = bisect_left(positions, j0)
        b = bisect_right(positions, j1)
        if a < b:
            spans.append((positions, a, b))
    return spans


def _span_count(spans) -> int:
    return sum(b - a for _, a, b in spans)


def _kth(spans, k: int) -> int:
    if len(spans) == 1:
        positions, a, _b = spans[0]
        return positions[a + k]
    joined: list[int] = []
    for positions, a, b in spans:
        joined.extend(positions[a:b])
    joined.sort()
    return joined[k]


def count_eligible(lengths: list[int], by: dict[int, list[int]], lo: int, hi: int) -> int:
    n = len(lengths)
    total = 0
    for i, length in enumerate(lengths):
        j0 = i + lo
        if j0 >= n:
            break
        j1 = i + hi
        if j1 >= n:
            j1 = n - 1
        total += _span_count(_spans(by, length, j0, j1))
    return total


def take_ranks(lengths: list[int], by: dict[int, list[int]], lo: int, hi: int, ranks: list[int]) -> list[tuple[int, int]]:
    """Eligible pairs at the given ranks, in stream order (increasing i, then j)."""
    if not ranks:
        return []
    n = len(lengths)
    pairs: list[tuple[int, int]] = []
    seen = 0
    ptr = 0
    target = ranks[0]
    for i, length in enumerate(lengths):
        j0 = i + lo
        if j0 >= n:
            break
        j1 = i + hi
        if j1 >= n:
            j1 = n - 1
        spans = _spans(by, length, j0, j1)
        c = _span_count(spans)
        if c:
            while ptr < len(ranks) and target < seen + c:
                local = target - seen
                if local < 0:
                    raise RuntimeError("pair rank went backwards")
                pairs.append((i, _kth(spans, local)))
                ptr += 1
                if ptr == len(ranks):
                    return pairs
                target = ranks[ptr]
        seen += c
    raise RuntimeError(f"found {ptr} of {len(ranks)} eligible pairs")


def pair_rate(units: list[tuple], pairs: list[tuple[int, int]]) -> float | None:
    if not pairs:
        return None
    hits = 0
    for i, j in pairs:
        if edit1(units[i], units[j]):
            hits += 1
    return hits / len(pairs)


def gap_rate(units: list[tuple], lo: int, hi: int) -> float | None:
    lengths = [len(unit) for unit in units]
    by = index_lengths(lengths)
    n_eligible = count_eligible(lengths, by, lo, hi)
    ranks = systematic_ranks(n_eligible, min(MAX_PAIRS, n_eligible))
    pairs = take_ranks(lengths, by, lo, hi, ranks)
    return pair_rate(units, pairs)


def summarise_bin(rate: float | None, null_rates: list[float | None]):
    vals = [float(x) for x in null_rates if x is not None]
    if rate is None or not vals:
        return None, 0.0, None, False
    arr = np.asarray(vals, dtype=float)
    mean = float(arr.mean())
    sd = float(arr.std(ddof=1)) if len(vals) >= 2 else 0.0
    excess = float(rate - mean)
    elevated = bool(excess > 2.0 * sd and sd > 0.0)
    return mean, sd, excess, elevated


def profile_shape(elevated: list[bool]) -> tuple[str, str | None]:
    flags = [bool(x) for x in elevated]
    if len(flags) != len(BIN_NAMES):
        raise ValueError(f"expected {len(BIN_NAMES)} bins, got {len(flags)}")
    if not any(flags):
        return "none", None
    seen = False
    for name, flag in zip(BIN_NAMES, flags):
        if flag:
            seen = True
            continue
        if seen:
            return DECAY_SHAPE[name], name
    return "flat", None


def later_decay(left: str | None, right: str | None) -> bool:
    """True when decay point `left` is strictly later than `right`."""
    if left is None or right is None:
        return False
    return BIN_NAMES.index(left) > BIN_NAMES.index(right)


def predictions(streams: dict) -> dict[str, bool]:
    ms = streams["MS_2B"]
    native = streams["h39_native_tuned"]
    boc = streams["boccaccio"]
    n1 = ms["shape"] in ("local", "page")
    n2 = later_decay(native["decay_point"], ms["decay_point"]) or (
        native["shape"] == "flat" and ms["shape"] != "flat"
    )
    n3 = boc["bins"]["1"]["excess"] < ms["bins"]["1"]["excess"]
    return {"N1": bool(n1), "N2": bool(n2), "N3": bool(n3)}


def block_ids(n: int) -> list[int]:
    """Blocks of 8 fake pages of 200 tokens. A short tail is its own block."""
    return [i // BLOCK_TOKENS for i in range(n)]


def shuffle_units(units: list[tuple], blocks: list, rng: np.random.Generator) -> list[tuple]:
    """Permute tokens inside each block. The multiset of each block stays put."""
    if len(blocks) != len(units):
        raise ValueError("blocks and units have different lengths")
    out = list(units)
    groups: dict[object, list[int]] = defaultdict(list)
    for i, block in enumerate(blocks):
        groups[block].append(i)
    for key in sorted(groups):
        slots = groups[key]
        vals = [out[i] for i in slots]
        order = np.arange(len(slots))
        rng.shuffle(order)
        for slot, src in zip(slots, order):
            out[slot] = vals[int(src)]
    return out


def eva_units(words: list[str]) -> list[tuple]:
    return [tuple(h13_lib.SEG(word)) for word in words]


def character_units(words: list[str]) -> list[tuple]:
    return [tuple(word) for word in words]


def score_units(units: list[tuple], blocks: list, n_null: int = N_NULL, seed: int = NULL_SEED) -> dict:
    lengths = [len(unit) for unit in units]
    by = index_lengths(lengths)
    rng = np.random.default_rng(seed)
    null_units = []
    null_lengths = []
    null_index = []
    for _ in range(n_null):
        shuffled = shuffle_units(units, blocks, rng)
        sl = [len(unit) for unit in shuffled]
        null_units.append(shuffled)
        null_lengths.append(sl)
        null_index.append(index_lengths(sl))
    bins: dict[str, dict] = {}
    for name, lo, hi in BINS:
        n_eligible = count_eligible(lengths, by, lo, hi)
        null_elig = [count_eligible(sl, sb, lo, hi) for sl, sb in zip(null_lengths, null_index)]
        # One count for the observed stream and every shuffle: an even grid of at most 4000
        # eligible pairs. Each grid is spaced across that stream's own eligible pairs.
        shared = min([MAX_PAIRS, n_eligible, *null_elig]) if null_elig else min(MAX_PAIRS, n_eligible)
        pairs = take_ranks(lengths, by, lo, hi, systematic_ranks(n_eligible, shared))
        if len(pairs) != shared:
            raise RuntimeError(f"bin {name}: sampled {len(pairs)} pairs, shared count is {shared}")
        rate = pair_rate(units, pairs)
        null_rates: list[float | None] = []
        null_n = []
        for sh, sl, sb, n_sh in zip(null_units, null_lengths, null_index, null_elig):
            npairs = take_ranks(sl, sb, lo, hi, systematic_ranks(n_sh, shared))
            if len(npairs) != shared:
                raise RuntimeError(f"bin {name}: null sample {len(npairs)} != shared {shared}")
            null_n.append(len(npairs))
            null_rates.append(pair_rate(sh, npairs))
        mean, sd, excess, elevated = summarise_bin(rate, null_rates)
        bins[name] = {
            "n_eligible": int(n_eligible),
            "null_n_eligible": [int(n) for n in null_elig],
            "n_sampled": int(len(pairs)),
            "n_edit1": int(sum(edit1(units[i], units[j]) for i, j in pairs)),
            "rate": rate,
            "null_rates": null_rates,
            "null_n_sampled": null_n,
            "null_mean": mean,
            "null_sd": sd,
            "excess": excess,
            "elevated": elevated,
        }
    flags = [bins[name]["elevated"] for name in BIN_NAMES]
    shape, decay = profile_shape(flags)
    return {
        "n_tokens": len(units),
        "n_blocks": len(set(blocks)),
        "shape": shape,
        "decay_point": decay,
        "bins": bins,
    }


def load_ms(hand: str):
    lines = h30_lib.load_ms(hand)
    words: list[str] = []
    blocks: list[str] = []
    for line in lines:
        quire = str(line["quire"])
        for word in line["words"]:
            words.append(word)
            blocks.append(quire)
    return words, eva_units(words), blocks


def load_boccaccio(n: int = N_STREAM):
    words = list(load_italian("it_boccaccio"))[:n]
    return words, character_units(words), block_ids(len(words))


def load_self_citation(n: int = N_STREAM):
    words = SELF_CITATION.read_text(encoding="utf-8").split()[:n]
    return words, eva_units(words), block_ids(len(words))


def load_h39(filename: str):
    lines = json.loads((H39_DIR / filename).read_text(encoding="utf-8"))
    words = [word for line in lines for word in line]
    return words, eva_units(words), block_ids(len(words))


def _c0_plaintext(_cid: str) -> list[str]:
    """C0's grammar encoder ignores plaintext. The fitter still calls plaintext()."""
    return []


def fit_c0(train_words: list[str]) -> tuple[list[str], dict]:
    """C0 fit on hand 2B (seed 0) and a 10500-token draw (seed 1), via run_h12.fit.

    The Latin control files used by the shared fitter are not in data/controls. For the
    grammar encoder those strings are never read, so plaintext() is replaced with an empty
    list for the duration of the fit. The search size, seed, and generator are run_h12.fit.
    """
    t0 = time.time()
    print(f"C0 fit run_h12.fit n_train={len(train_words)} n_random={run_h12.N_RANDOM} n_local={run_h12.N_LOCAL}", flush=True)
    saved = run_h12.MR.plaintext
    run_h12.MR.plaintext = _c0_plaintext
    try:
        model = run_h12.fit(train_words, seed=0)
    finally:
        run_h12.MR.plaintext = saved
    words = run_h12.generate(model, N_STREAM, 1)
    info = {
        "method": "run_h12.fit",
        "n_random": int(run_h12.N_RANDOM),
        "n_local": int(run_h12.N_LOCAL),
        "fit_seed": 0,
        "gen_seed": 1,
        "plaintext": "empty_stub_grammar_encoder_ignores_it",
        "fit_distance": float(model["fit_distance"]),
        "secs": time.time() - t0,
        "n_train": len(train_words),
        "n_gen": len(words),
    }
    print(f"C0 fit done distance={info['fit_distance']:.4f} secs={info['secs']:.1f}", flush=True)
    return words, info


def _score_named(name: str, units, blocks, unit_kind: str, extra: dict | None = None) -> dict:
    t0 = time.time()
    print(f"score {name} n={len(units)} blocks={len(set(blocks))}", flush=True)
    rec = score_units(units, blocks)
    rec["name"] = name
    rec["unit"] = unit_kind
    rec["seconds"] = time.time() - t0
    if extra:
        rec.update(extra)
    b1 = rec["bins"]["1"]
    print(
        f"done {name} shape={rec['shape']} decay={rec['decay_point']} "
        f"bin1_excess={b1['excess']} seconds={rec['seconds']:.1f}",
        flush=True,
    )
    return rec


def run_all() -> dict:
    streams: dict[str, dict] = {}
    ms_words: dict[str, list[str]] = {}
    for hand in ("1A", "2B", "3B"):
        print(f"load MS {hand}", flush=True)
        words, units, blocks = load_ms(hand)
        ms_words[hand] = words
        streams[f"MS_{hand}"] = _score_named(f"MS_{hand}", units, blocks, "collapsed_eva")
    words, units, blocks = load_boccaccio()
    streams["boccaccio"] = _score_named("boccaccio", units, blocks, "characters")
    c0_words, fit_info = fit_c0(ms_words["2B"])
    streams["C0"] = _score_named("C0", eva_units(c0_words), block_ids(len(c0_words)), "collapsed_eva", {"fit": fit_info})
    words, units, blocks = load_self_citation()
    streams["self_citation"] = _score_named("self_citation", units, blocks, "collapsed_eva")
    for name, filename in (
        ("h39_native_tuned", "lines_2B_native_tuned.json"),
        ("h39_C0_graph", "lines_2B_C0_graph.json"),
    ):
        words, units, blocks = load_h39(filename)
        streams[name] = _score_named(name, units, blocks, "collapsed_eva", {"source": filename})
    payload = {
        "bins": list(BIN_NAMES),
        "max_pairs": MAX_PAIRS,
        "n_null": N_NULL,
        "null_seed": NULL_SEED,
        "block_tokens": BLOCK_TOKENS,
        "page_tokens": PAGE_TOKENS,
        "n_stream": N_STREAM,
        "numpy": np.__version__,
        "rapidfuzz": rapidfuzz.__version__,
        "python": platform.python_version(),
        "streams": streams,
    }
    out = HERE / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "streams.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("wrote", out / "streams.json", flush=True)
    return payload


if __name__ == "__main__":
    run_all()
