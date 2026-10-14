"""Measure h41 streams. One worker. Writes results/scores.json only inside this folder."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h27_plaintext_ablation"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h20_generators_vs_italian"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h12_per_hand_copy_modify"))
sys.path.insert(0, str(ROOT / "hypotheses" / "h14_line_position_controls"))

import msdecipher.controls_ci as ci  # noqa: E402
import h14_lib as H14  # noqa: E402
import h27_lib as H27  # noqa: E402
import h41_lib as H  # noqa: E402
import run_h12  # noqa: E402
from fetch_italian import load_italian  # noqa: E402

RES = HERE / "results"
SCORES = RES / "scores.json"
N_STREAM = 10500
N_CIPHER_OUT = 2 * N_STREAM
REAL_STARTS = (0, 10500, 21000, 31500, 42000)
SEEDS = (1, 2, 3, 4, 5)
HANDS = ("1A", "2B", "3B")
N_RANDOM = run_h12.N_RANDOM


def _one_worker_pmap(fn, jobs, workers=None):
    jobs = list(jobs)
    print(f"pmap {len(jobs)} jobs, one worker", flush=True)
    t0 = time.perf_counter()
    out = []
    for i, job in enumerate(jobs, 1):
        out.append(fn(job))
        if i == 1 or i % 10 == 0 or i == len(jobs):
            print(f"  {i}/{len(jobs)} {time.perf_counter() - t0:.1f}s", flush=True)
    return out


def _load_state() -> dict:
    if SCORES.exists():
        return json.loads(SCORES.read_text())
    return {
        "n_stream": N_STREAM,
        "n_cipher_out": N_CIPHER_OUT,
        "block": H.BLOCK,
        "top": H.TOP,
        "real_starts": list(REAL_STARTS),
        "seeds": list(SEEDS),
        "builder_seed": "same integer as encrypt_swap, seeds 1..5",
        "n_random": None,
        "source_n": None,
        "fit": None,
        "real": [],
        "shuffle": [],
        "zipf": [],
        "real_naibbe": [],
        "C0": [],
        "MS": [],
    }


def _save(state: dict) -> None:
    RES.mkdir(parents=True, exist_ok=True)
    SCORES.write_text(json.dumps(state, indent=1) + "\n")


def paragraph_words(table, hand: str) -> list[str]:
    d = table[table.HL == hand]
    folio_order = {f: i for i, f in enumerate(dict.fromkeys(table.folio))}
    d = d.assign(_fo=d.folio.map(folio_order))
    d = d.sort_values(["_fo", "line", "pos"], kind="mergesort")
    return [str(w) for w in d.w.tolist()]


def _plain(kind: str, source: list[str], seed: int) -> list[str]:
    if kind == "real":
        return H27.real_plaintext(source)
    if kind == "shuffle":
        return H27.shuffle_plaintext(source, seed)
    if kind == "zipf":
        return H27.zipf_plaintext(source, seed)
    raise AssertionError(repr(kind))


def cipher_stream(kind: str, source: list[str], seed: int) -> tuple[list[str], int]:
    plain = _plain(kind, source, seed)
    out, n_copy = H27.encrypt_swap(plain, seed, N_CIPHER_OUT)
    if len(out) < N_STREAM:
        raise RuntimeError(f"{kind} seed {seed} produced {len(out)} ciphertext tokens")
    return out[:N_STREAM], int(n_copy)


def _row(tokens: list[str], **meta) -> dict:
    return {"n": len(tokens), **meta, **H.score(tokens)}


def _fill_real(state: dict, source: list[str]) -> None:
    have = {r["start"] for r in state["real"]}
    for start in REAL_STARTS:
        if start in have:
            continue
        window = source[start:start + N_STREAM]
        if len(window) != N_STREAM:
            raise RuntimeError(f"real window at {start} has {len(window)} tokens")
        state["real"].append(_row(window, start=start))
        _save(state)
        print("real", start, "done", flush=True)


def _fill_cipher(state: dict, source: list[str], kind: str, key: str) -> None:
    have = {r["seed"] for r in state[key]}
    for seed in SEEDS:
        if seed in have:
            continue
        print("start", key, seed, flush=True)
        t0 = time.perf_counter()
        tokens, n_copy = cipher_stream(kind, source, seed)
        state[key].append(_row(tokens, seed=seed, n_copy=n_copy))
        _save(state)
        print("done", key, seed, round(time.perf_counter() - t0, 1), flush=True)


def _fill_ms(state: dict) -> None:
    have = {r["hand"] for r in state["MS"]}
    if set(HANDS) <= have:
        return
    print("load ZL3b paragraph words", flush=True)
    table = H14.table()
    for hand in HANDS:
        if hand in have:
            continue
        words = paragraph_words(table, hand)
        if not words:
            raise RuntimeError(f"no paragraph words for {hand}")
        stream = words[:N_STREAM]
        state["MS"].append(_row(stream, hand=hand, n_available=len(words)))
        _save(state)
        print("MS", hand, "n", len(stream), "available", len(words), flush=True)


def _unused_fit_plaintext(_cid: str) -> list[str]:
    """C0's grammar encoder never reads this list.

    fit_variant still calls plaintext() for every candidate. The FIT_PLAIN files are not in
    this checkout, and fetching them would write outside this folder. The returned tokens
    are discarded by GrammarInnovator.
    """
    return ["x"]


def _fit_c0(train: list[str], n_random: int) -> dict:
    ci.default_workers = lambda: 1
    ci.pmap = _one_worker_pmap
    run_h12.MR.plaintext = _unused_fit_plaintext
    print(f"fit C0 on {len(train)} tokens, n_random={n_random}, one worker", flush=True)
    t0 = time.perf_counter()
    ctx = run_h12.MR.Ctx(train)
    best, df, _info = run_h12.MR.fit_variant(
        run_h12.C0,
        train,
        ctx,
        seed=0,
        n_random=n_random,
        n_local=run_h12.N_LOCAL,
        workers=1,
        log=lambda *a: None,
    )
    secs = time.perf_counter() - t0
    model = {"ctx": ctx, "params": best, "fit_distance": float(df.distance.iloc[0]), "secs": secs}
    print("fit done", round(secs, 1), "distance", model["fit_distance"], flush=True)
    return model


def _fill_c0(state: dict, train: list[str], n_random: int) -> None:
    state["n_random"] = n_random
    have = {r["seed"] for r in state["C0"]}
    fit = state.get("fit") or {}
    if fit.get("n_random") == n_random and set(SEEDS) <= have:
        return
    model = _fit_c0(train, n_random)
    state["fit"] = {
        "seed": 0,
        "n_train": len(train),
        "n_random": n_random,
        "n_local": run_h12.N_LOCAL,
        "fit_distance": model["fit_distance"],
        "secs": model["secs"],
        "params": model["params"].as_dict(),
        "fit_plaintext": "unused; C0 grammar encoder ignores FIT_PLAIN",
    }
    _save(state)
    for seed in SEEDS:
        if seed in have:
            continue
        tokens = list(run_h12.generate(model, N_STREAM, seed))
        if len(tokens) < N_STREAM:
            raise RuntimeError(f"C0 seed {seed} produced {len(tokens)} tokens")
        state["C0"].append(_row(tokens[:N_STREAM], seed=seed))
        _save(state)
        print("C0", seed, "done", flush=True)


def main(n_random: int = N_RANDOM) -> None:
    t0 = time.perf_counter()
    state = _load_state()
    if state.get("n_stream") not in (None, N_STREAM):
        raise RuntimeError("existing scores.json was built at another stream length")
    print("load it_boccaccio", flush=True)
    source = load_italian("it_boccaccio")
    state["source_n"] = len(source)
    need = REAL_STARTS[-1] + N_STREAM
    if len(source) < need:
        raise RuntimeError(f"it_boccaccio has {len(source)} tokens, need {need}")
    print("source", len(source), flush=True)
    _fill_real(state, source)
    _fill_cipher(state, source, "shuffle", "shuffle")
    _fill_cipher(state, source, "zipf", "zipf")
    _fill_cipher(state, source, "real", "real_naibbe")
    _fill_ms(state)
    train = next(r for r in state["MS"] if r["hand"] == "2B")
    # Fit uses every paragraph word of hand 2B, not the 10500-token score slice.
    table = H14.table()
    words_2b = paragraph_words(table, "2B")
    if train["n_available"] != len(words_2b):
        raise RuntimeError("2B length changed between the MS score and the C0 fit")
    _fill_c0(state, words_2b, n_random)
    state["runtime_sec"] = time.perf_counter() - t0
    _save(state)
    print("scores written", round(state["runtime_sec"], 1), flush=True)


if __name__ == "__main__":
    chosen = int(sys.argv[1]) if len(sys.argv) > 1 else N_RANDOM
    main(chosen)
