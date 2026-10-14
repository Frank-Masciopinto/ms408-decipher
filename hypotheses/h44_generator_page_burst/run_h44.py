"""Score h44 streams. One process. Writes results/streams.json inside this folder only."""
from __future__ import annotations

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"

import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _path in (
    HERE,
    ROOT / "src",
    ROOT / "hypotheses" / "h06_section_null_and_zodiac",
    ROOT / "hypotheses" / "h12_per_hand_copy_modify",
    ROOT / "hypotheses" / "h14_line_position_controls",
):
    sys.path.insert(0, str(_path))

import h06_lib  # noqa: E402
import h14_lib  # noqa: E402
import h44_lib as H  # noqa: E402
import run_h12  # noqa: E402
from msdecipher import controls_ci as CI  # noqa: E402

RES = HERE / "results"
STREAMS = RES / "streams.json"
SELF_DIR = ROOT / "data" / "mechanisms" / "selfcitation"
H39_DIR = ROOT / "hypotheses" / "h39_graph_respell_and_tuned_copier" / "results"
HANDS = ("1A", "2B", "3B")


def _serial_pmap(fn, jobs, workers=None):
    """One process. Sibling jobs are running, so the fitter must not fork."""
    jobs = list(jobs)
    print(f"pmap {len(jobs)} jobs, one worker", flush=True)
    t0 = time.perf_counter()
    out = []
    for i, job in enumerate(jobs, 1):
        out.append(fn(job))
        if i == 1 or i % 5 == 0 or i == len(jobs):
            print(f"  {i}/{len(jobs)} {time.perf_counter() - t0:.1f}s", flush=True)
    return out


def _load() -> dict:
    if STREAMS.exists():
        return json.loads(STREAMS.read_text(encoding="utf-8"))
    return {"streams": {}}


def _save(state: dict) -> None:
    RES.mkdir(parents=True, exist_ok=True)
    STREAMS.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def hand_frame(table, hand: str):
    d = table[table.HL == hand]
    folio_order = {folio: i for i, folio in enumerate(dict.fromkeys(table.folio))}
    d = d.assign(_fo=d.folio.map(folio_order))
    return d.sort_values(["_fo", "line", "pos"], kind="mergesort")


def folio_median(frame) -> dict:
    counts = frame.groupby("folio", sort=False).size().to_numpy(dtype=float)
    ordered = np.sort(counts)
    n = int(ordered.size)
    if n < 2:
        raise RuntimeError(f"need at least two folios, found {n}")
    median = float(np.median(ordered))
    return {
        "L": median,
        "page_tokens": H.page_len_from_median(median),
        "n_folios": n,
        "central_folio_counts": [int(ordered[n // 2 - 1]), int(ordered[n // 2])],
        "min_folio_tokens": int(ordered[0]),
        "max_folio_tokens": int(ordered[-1]),
    }


def _score(tokens, pages, quires, **meta) -> dict:
    t0 = time.perf_counter()
    rec = H.score_stream(tokens, pages, quires)
    rec.update(meta)
    rec["seconds"] = time.perf_counter() - t0
    print(
        f"scored {meta.get('name')} n={rec['n']} orig={rec['orig']:.6f} "
        f"in_page={rec['in_page']:.6f} in_quire={rec['in_quire']:.6f} "
        f"full={rec['full']:.6f} excess={rec['excess']:.6f} {rec['seconds']:.1f}s",
        flush=True,
    )
    return rec


def _generated(tokens: list[str], page_len: int, **meta) -> dict:
    if len(tokens) != H.N_STREAM:
        raise RuntimeError(f"{meta.get('name')} has {len(tokens)} tokens, expected {H.N_STREAM}")
    pages, quires = H.layout(len(tokens), page_len)
    return _score(tokens, pages, quires, page_kind="L", quire_kind="eight_pages", page_tokens=page_len, **meta)


def _words(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").split()[: H.N_STREAM]


def _h39(filename: str) -> list[str]:
    lines = json.loads((H39_DIR / filename).read_text(encoding="utf-8"))
    words = [word for line in lines for word in line]
    return words[: H.N_STREAM]


def _unused_plaintext(_cid: str) -> list[str]:
    """C0's grammar encoder never reads this list. Three of the four fit ids are not on disk."""
    return []


def _fit_c0(train: list[str]) -> tuple[list[str], dict]:
    if run_h12.N_LOCAL != 10:
        raise RuntimeError(f"run_h12.N_LOCAL is {run_h12.N_LOCAL}, prereg requires 10")
    CI.default_workers = lambda: 1
    CI.pmap = _serial_pmap
    saved_plain = run_h12.MR.plaintext
    run_h12.MR.plaintext = _unused_plaintext
    print(f"fit C0 n_train={len(train)} seed=0 n_random=20 n_local=10 one worker", flush=True)
    t0 = time.perf_counter()
    try:
        ctx = run_h12.MR.Ctx(train)
        best, df, _info = run_h12.MR.fit_variant(
            run_h12.C0,
            train,
            ctx,
            seed=0,
            n_random=20,
            n_local=10,
            workers=1,
            log=lambda *_args: None,
        )
    finally:
        run_h12.MR.plaintext = saved_plain
    secs = time.perf_counter() - t0
    model = {"ctx": ctx, "params": best, "fit_distance": float(df.distance.iloc[0]), "secs": secs}
    words = list(run_h12.generate(model, H.N_STREAM, 1))
    info = {
        "method": "run_h12.MR.fit_variant",
        "variant": run_h12.C0,
        "n_random": 20,
        "n_local": 10,
        "fit_seed": 0,
        "gen_seed": 1,
        "workers": 1,
        "n_train": len(train),
        "fit_distance": model["fit_distance"],
        "secs": secs,
        "params": {key: (int(value) if key == "window" else float(value)) for key, value in best.as_dict().items()},
        "fit_plaintext": "empty_stub; grammar encoder ignores plaintext",
        "parameters_searched": True,
    }
    print(f"C0 fit distance={info['fit_distance']:.6f} secs={secs:.1f} generated={len(words)}", flush=True)
    return words, info


def _h06_streams(train: list[str], page_len: int, state: dict) -> None:
    need = [name for name in ("h06_pool", "h06_p0") if name not in state["streams"]]
    if not need:
        return
    print(f"h06 Shared from hand 2B n_train={len(train)} seed=0; parameters not fitted", flush=True)
    t0 = time.perf_counter()
    shared = h06_lib.Shared(train, seed=0)
    print(f"h06 Shared ready {time.perf_counter() - t0:.1f}s", flush=True)
    base = dict(h06_lib.DEFAULT_BASE)
    specs = {
        "h06_pool": {"p_pool": 0.5, "S": 10},
        "h06_p0": {"p_pool": 0.0, "S": 0},
    }
    for name in need:
        spec = specs[name]
        params = dict(base)
        params["p_pool"] = spec["p_pool"]
        model = h06_lib.make_group_model(shared, train, params, spec["S"], tilt=False)
        print(f"h06 generate {name} p_pool={params['p_pool']} S={spec['S']} seed=1", flush=True)
        t1 = time.perf_counter()
        words = h06_lib.sv_generate(
            [{"group": "2B", "n": H.N_STREAM, "page": 0}],
            {"2B": model, "__all__": model},
            shared,
            seed=1,
        )[0]
        print(f"h06 generated {name} n={len(words)} {time.perf_counter() - t1:.1f}s", flush=True)
        state["streams"][name] = _generated(
            words,
            page_len,
            name=name,
            kind="h06",
            parameters_fitted=False,
            shared_source="hand 2B paragraph words",
            shared_seed=0,
            gen_seed=1,
            n_train=len(train),
            base_params={key: (int(value) if key == "window" else float(value)) for key, value in base.items()},
            params={key: (int(value) if key == "window" else float(value)) for key, value in params.items()},
            S=spec["S"],
            p_pool=float(params["p_pool"]),
            tilt=False,
            pool=list(model.pool),
            scope="window",
        )
        _save(state)


def main() -> None:
    t0 = time.perf_counter()
    state = _load()
    state.setdefault("streams", {})
    print("load h14 table", flush=True)
    table = h14_lib.table()
    frames = {hand: hand_frame(table, hand) for hand in HANDS}
    med = folio_median(frames["2B"])
    if "L" in state and float(state["L"]) != med["L"]:
        raise RuntimeError(f"stored L {state['L']} != recomputed {med['L']}")
    state.update(med)
    state["pages_per_quire"] = H.PAGES_PER_QUIRE
    state["n_stream"] = H.N_STREAM
    state["n_shuffles"] = H.N_SHUFFLES
    state["shuffle_seed"] = H.SHUFFLE_SEED
    state["block"] = H.BLOCK
    state["top"] = H.TOP
    state["positive_seed"] = H.POSITIVE_SEED
    state["positive_types"] = H.POSITIVE_TYPES
    state["numpy"] = np.__version__
    state["python"] = platform.python_version()
    page_len = int(state["page_tokens"])
    print(f"L={state['L']} page_tokens={page_len} central={state['central_folio_counts']}", flush=True)

    for hand in HANDS:
        name = f"MS_{hand}"
        if name in state["streams"]:
            continue
        frame = frames[hand]
        take = frame.head(H.N_STREAM)
        tokens = [str(word) for word in take.w.tolist()]
        pages = [str(folio) for folio in take.folio.tolist()]
        quires = [str(quire) for quire in take.quire.tolist()]
        state["streams"][name] = _score(
            tokens,
            pages,
            quires,
            name=name,
            kind="ms",
            hand=hand,
            n_available=int(len(frame)),
            page_kind="folio",
            quire_kind="quire",
        )
        _save(state)

    train_2b = [str(word) for word in frames["2B"].w.tolist()]
    text_sources = {
        "fitted_s1": SELF_DIR / "fitted_s1.txt",
        "fitted_s2": SELF_DIR / "fitted_s2.txt",
    }
    for name, path in text_sources.items():
        if name in state["streams"]:
            continue
        state["streams"][name] = _generated(_words(path), page_len, name=name, kind="self_citation", source=str(path.relative_to(ROOT)))
        _save(state)

    h39_sources = {
        "h39_native_tuned": "lines_2B_native_tuned.json",
        "h39_C0_graph": "lines_2B_C0_graph.json",
    }
    for name, filename in h39_sources.items():
        if name in state["streams"]:
            continue
        state["streams"][name] = _generated(_h39(filename), page_len, name=name, kind="h39", source=filename)
        _save(state)

    if H.CONTROL_NAME not in state["streams"]:
        tokens, pages, quires = H.positive_control(H.N_STREAM, page_len)
        state["streams"][H.CONTROL_NAME] = _score(
            tokens,
            pages,
            quires,
            name=H.CONTROL_NAME,
            kind="positive_control",
            page_kind="L",
            quire_kind="eight_pages",
            page_tokens=page_len,
            n_types=H.POSITIVE_TYPES,
            seed=H.POSITIVE_SEED,
            zipf="1/rank",
        )
        _save(state)

    _h06_streams(train_2b, page_len, state)

    if "C0" not in state["streams"]:
        words, info = _fit_c0(train_2b)
        state["streams"]["C0"] = _generated(words, page_len, name="C0", kind="C0", fit=info)
        _save(state)

    missing = [name for name in H.ORDER if name not in state["streams"]]
    if missing:
        raise RuntimeError("missing streams: " + ", ".join(missing))
    state["runtime_sec"] = time.perf_counter() - t0
    _save(state)
    print(f"streams written {state['runtime_sec']:.1f}s", flush=True)


if __name__ == "__main__":
    main()
