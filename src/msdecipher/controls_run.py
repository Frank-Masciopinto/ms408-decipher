"""Run the statistics suite on MS 408 and on every control; write comparison tables, CIs, verdicts and plots.

Outputs (``reports/controls/``): ``comparison.csv`` (one row per control / MS variant: mean over seeds),
``comparison_sd.csv``, ``comparison_runs.csv`` (every run), ``comparison_ci.csv`` (jackknife SE and
95% CI per control row), ``ms408_ci.csv`` (page / page-block jackknife and bootstrap SE and CI for MS 408),
``family_ranges.csv`` + ``verdicts.csv`` + ``verdict_summary.csv`` (prediction-interval verdicts of MS 408
against each hypothesis family, metric by metric), ``control_z.csv`` / ``control_z_summary.csv``
(MS 408 vs each single control, bootstrap SEs), ``alphabet_adjusted.csv``, ``size_sensitivity.csv``,
``comparison.md`` and ``figures/*.png``.

Reading the output: for each family the members (base text x window, seeds averaged) give a mean and an SD;
MS 408 counts as "inside" when it lies within the 95% *prediction interval* (which also includes MS 408's own
bootstrap uncertainty). With 3-30 members built from a few books that is a coarse screen, not a hypothesis test.
MS 408 is undeciphered; falling inside or outside a family says nothing decisive about what the text is.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
import pandas as pd

from . import controls_ci as CI
from . import controls_transforms as T
from .analysis import md_table
from .controls_metrics import METRIC_INFO, metrics
from .controls_text import TARGET_TOKENS, load_windows
from .paths import reports_dir

PLAIN_LATIN = ["la_vulgate", "la_augustine", "la_pliny_herbal", "la_pliny_general", "la_celsus", "la_isidore", "la_macer"]
PLAIN_ITALIAN = ["it_dante", "it_manzoni", "it_sidrach", "it_ariosto"]
PLAIN_GERMAN = ["de_walther_mhg", "de_faust"]
PLAIN = PLAIN_LATIN + PLAIN_ITALIAN + PLAIN_GERMAN
HERBAL_MEDICAL = ["la_pliny_herbal", "la_celsus", "la_macer"]
BASES = ["la_vulgate", "la_pliny_herbal", "la_celsus", "it_manzoni", "it_sidrach"]   # texts the Latin-alphabet transformations are applied to
# Natural abjad texts (consonantal Hebrew / Arabic, one native code point per unit)
ABJAD = ["he_tanakh", "he_mishneh_torah", "ar_quran", "ar_muqaddimah"]
ABJAD_BASES = list(ABJAD)                # the generic (alphabet-independent) transformations are applied to all four
SEED_DEFAULT = 3
UNDERSIZED = 0.8                         # a sample shorter than this share of the target is "undersized"

# transformation name -> hypothesis family
TRANSFORM_FAMILY = {
    "abjad": "abjad (vowels removed)",
    "monoalphabetic": "monoalphabetic substitution",
    "caesar3": "monoalphabetic substitution",
    "vigenere_k3": "polyalphabetic (Vigenere)",
    "vigenere_k6": "polyalphabetic (Vigenere)",
    "nomenclator": "nomenclator-like syllable code",
    "verbose_2sym": "verbose cipher (letter -> 2 symbols)",
    "naibbe_like": "Naibbe-inspired homophonic tiles",
    "reverse_words": "word reversal",
    "alphagram": "anagram (alphagram)",
    "shuffle_letters": "letters shuffled inside words",
    "shuffle_tokens": "shuffled tokens",
}
STOCHASTIC_TRANSFORMS = {"monoalphabetic", "vigenere_k3", "vigenere_k6", "nomenclator", "verbose_2sym",
                         "naibbe_like", "shuffle_letters", "shuffle_tokens"}
FAMILY_PLAIN = "natural-language plaintext (Latin/Italian/German)"
FAMILY_PLAIN_LATIN = "natural plaintext: Latin only"
FAMILY_PLAIN_HERBAL = "natural plaintext: herbal/medical Latin"
FAMILY_PLAIN_SMALL = "natural plaintext, UNDERSIZED (<80% of target; sensitivity only)"
FAMILY_MS_MARKOV = "Markov o2 TRAINED ON MS 408 (matches by construction)"
FAMILY_ABJAD = "natural abjad text (Hebrew/Arabic)"
FAMILY_ABJAD_VARIANT = "natural abjad, folded-alphabet variant (sensitivity only)"
NOT_HYPOTHESES = ("MS 408", FAMILY_MS_MARKOV, FAMILY_ABJAD_VARIANT, FAMILY_PLAIN_SMALL)   # excluded from the family verdicts
MS_MAIN = "MS408 P (collapsed units)"
MS_RAW = "MS408 P (raw EVA chars)"


def _wname(base: str, w: int) -> str:
    return base if w == 0 else f"{base}@w{w}"


def _word_sets(n_tokens: int, log=lambda *a: None) -> dict[str, list[str]]:
    """Token lists keyed ``id`` (window 0), ``id@w1`` ... (later non-overlapping windows) and ``id#folded`` (abjad)."""
    d: dict[str, list[str]] = {}
    for cid in PLAIN:
        try:
            for w, toks in enumerate(load_windows(cid, n_tokens)):
                d[_wname(cid, w)] = toks
        except FileNotFoundError:
            log("control", cid, "not fetched (python -m msdecipher controls-fetch --only", cid + "): skipped")
    for cid in ABJAD:
        try:
            for w, toks in enumerate(load_windows(cid, n_tokens)):
                d[_wname(cid, w)] = toks
            d[cid + "#folded"] = load_windows(cid, n_tokens, max_windows=1, variant="folded")[0]
        except FileNotFoundError:
            log("abjad control", cid, "not fetched (python -m msdecipher controls-fetch --only", cid + "): skipped")
    return d


def _windows_of(plain: dict[str, list[str]], cid: str) -> list[tuple[int, str]]:
    out, w = [], 0
    while _wname(cid, w) in plain:
        out.append((w, _wname(cid, w)))
        w += 1
    return out


def control_specs(n_tokens: int, seeds: int, plain: dict[str, list[str]], ms_train: list[str] | None):
    """Return list of dicts (name, family, base, window, stochastic, build(seed)->words, memberships).
    Plain texts get one row per window; transformations / generators use window 0 of each base."""
    specs = []

    def add(name, fam, base, window, stoch, build, members=None):
        specs.append(dict(name=name, family=fam, base=base, window=window, stochastic=stoch, build=build,
                          memberships=members or [fam]))

    for cid in PLAIN:
        for w, key in _windows_of(plain, cid):
            small = len(plain[key]) < UNDERSIZED * n_tokens
            if small:
                fams = [FAMILY_PLAIN_SMALL]
            else:
                fams = [FAMILY_PLAIN]
                if cid in PLAIN_LATIN:
                    fams.append(FAMILY_PLAIN_LATIN)
                if cid in HERBAL_MEDICAL:
                    fams.append(FAMILY_PLAIN_HERBAL)
            add(f"plain:{_wname(cid, w)}", fams[0], cid, w, False, lambda s, k=key: plain[k], fams)
    bases = [b for b in BASES if b in plain]
    for tr, fam in TRANSFORM_FAMILY.items():
        for b in bases:
            add(f"{tr}:{b}", fam, b, 0, tr in STOCHASTIC_TRANSFORMS, lambda s, tr=tr, b=b: T.TRANSFORMS[tr](plain[b], s))
    ab = [b for b in ABJAD_BASES if b in plain]
    for cid in ab:
        for w, key in _windows_of(plain, cid):
            add(f"plain:{_wname(cid, w)}", FAMILY_ABJAD, cid, w, False, lambda s, k=key: plain[k])
        add(f"plain_folded:{cid}", FAMILY_ABJAD_VARIANT, cid, 0, False, lambda s, c=cid: plain[c + "#folded"])
    for tr in T.GENERIC_TRANSFORMS:
        for b in ab:
            add(f"{tr}:{b}", TRANSFORM_FAMILY[tr], b, 0, tr in STOCHASTIC_TRANSFORMS,
                lambda s, tr=tr, b=b: T.GENERIC_TRANSFORMS[tr](plain[b], s))
    for b in bases + ab:
        add(f"markov_o2:{b}", "Markov character gibberish", b, 0, True, lambda s, b=b: T.markov_char(plain[b], n_tokens, 2, s))
        add(f"markov_o1:{b}", "Markov character gibberish", b, 0, True, lambda s, b=b: T.markov_char(plain[b], n_tokens, 1, s))
        add(f"iid_letters:{b}", "iid letters (no structure)", b, 0, True, lambda s, b=b: T.iid_letters(plain[b], n_tokens, s))
    for p in (0.15, 0.3, 0.5):
        add(f"selfcitation_p{p}", "self-citation generator", "-", 0, True, lambda s, p=p: T.selfcitation(n_tokens, s, p_mutate=p))
    for p in (0.2, 0.35, 0.5):
        add(f"slot_grammar_p{p}", "slot-grammar generator", "-", 0, True, lambda s, p=p: T.slot_grammar(n_tokens, s, p_second_core=p))
    if ms_train:
        add("markov_o2:ms408", FAMILY_MS_MARKOV, "ms408", 0, True, lambda s: T.markov_char(ms_train, n_tokens, 2, s))
    return specs


def ms_variants(main_file=None, uncertain: str = "split"):
    """Word lists + segmenters for MS 408 (target) rows. Returns (rows, train_words) or ({}, None)."""
    from .analysis import groups, load_corpus
    from .corpus_view import readable_words
    from .segment import Segmenter
    try:
        corpus = load_corpus(main_file)
    except FileNotFoundError:
        return {}, None
    grp = groups(corpus, uncertain)
    coll = Segmenter.preset("collapsed")
    raw = Segmenter.preset("raw")
    P = readable_words(grp["P"])
    rows = {
        MS_MAIN: (P, coll),
        MS_RAW: (P, raw),
        "MS408 Currier A (collapsed)": (readable_words(grp["A"]), coll),
        "MS408 Currier B (collapsed)": (readable_words(grp["B"]), coll),
        "MS408 P tokens shuffled (collapsed)": (T.shuffle_tokens(P, 1), coll),
        "MS408 P letters shuffled in tokens (collapsed)": (_shuffle_units_in_tokens(P, coll, 1), coll),
    }
    # single-char encoding of the collapsed units, for the Markov-trained-on-MS control
    comps = {}
    train = []
    for w in P:
        u = coll(w)
        train.append("".join(comps.setdefault(x, x if len(x) == 1 else chr(0x100 + len(comps))) for x in u))
    return rows, train


def ms_pages(main_file=None, uncertain: str = "split") -> list[list[str]]:
    """Readable words of the MS 408 running text, one list per folio (page), in manuscript order."""
    from .analysis import groups, load_corpus
    from .ivtff import readable
    try:
        corpus = load_corpus(main_file)
    except FileNotFoundError:
        return []
    pages: dict[str, list[str]] = {}
    for ln in groups(corpus, uncertain)["P"]:
        pages.setdefault(ln.page, []).extend(w for w in ln.words if readable(w))
    return [w for w in pages.values() if w]


def ms_pages_named(main_file=None, uncertain: str = "split") -> list[tuple[str, list[str]]]:
    """Like ``ms_pages`` but keeps the page name: ``[(page, words), ...]`` in manuscript order (h08)."""
    from .analysis import groups, load_corpus
    from .ivtff import readable
    try:
        corpus = load_corpus(main_file)
    except FileNotFoundError:
        return []
    pages: dict[str, list[str]] = {}
    for ln in groups(corpus, uncertain)["P"]:
        pages.setdefault(ln.page, []).extend(w for w in ln.words if readable(w))
    return [(p, w) for p, w in pages.items() if w]


def resample_ms_groups(pages, keys, segs: dict, B: int = 100, workers: int | None = None, log=lambda *a: None,
                       name: str = "quire") -> dict[str, pd.DataFrame]:
    """Group-level (e.g. quire) bootstrap (``B`` resamples) and delete-one-group jackknife of every metric,
    same columns as ``_resample_ms``; returns ``{name: ..., f"jack_{name}": ...}`` (h08)."""
    gb = CI.make_group_blocks(pages, keys)
    jobs = [(name, b) for b in range(B)] + [(f"jack_{name}", i) for i in range(len(gb))]

    def one(job):
        kind, b = job
        w = CI.resample_blocks(gb, random.Random(31337 + b)) if kind == name else CI.leave_out(gb, b)
        row = {}
        for tag, seg in segs.items():
            m = metrics(w, seg, seed=b + 1, n_shuffles=3)
            for k in METRIC_INFO:
                row[f"{k}__{tag}"] = m[k]
        return kind, row
    log(f"MS 408 {name} resampling: {B} bootstraps, jackknife over {len(gb)} groups")
    res = CI.pmap(one, jobs, workers)
    return {kind: pd.DataFrame([r for k, r in res if k == kind]) for kind in (name, f"jack_{name}")}


def group_ci_table(point: dict[str, pd.Series], reps: dict[str, pd.DataFrame], name: str = "quire") -> pd.DataFrame:
    """Per metric / unit variant: group bootstrap SE + percentile CI, group jackknife SE, and the CI
    estimate ± 1.96 · jackknife SE (same convention as ``ms_ci_table``)."""
    rows = []
    for tag, pt in point.items():
        for m in METRIC_INFO:
            r = {"metric": m, "units": tag, "estimate": float(pt[m])}
            s = CI.summarize(reps[name][f"{m}__{tag}"].values)
            r[f"boot_se_{name}"], r[f"boot_lo_{name}"], r[f"boot_hi_{name}"] = s["se"], s["lo"], s["hi"]
            r[f"se_jack_{name}"] = se = CI.jackknife_se(reps[f"jack_{name}"][f"{m}__{tag}"].values)
            r[f"ci_lo_{name}"], r[f"ci_hi_{name}"] = r["estimate"] - 1.96 * se, r["estimate"] + 1.96 * se
            rows.append(r)
    return pd.DataFrame(rows)


def _shuffle_units_in_tokens(words, seg, seed):
    rng = random.Random(seed)
    out = []
    for w in words:
        u = list(seg(w))
        rng.shuffle(u)
        out.append("".join(u))
    return out


BOOT_BLOCK_PAGES = 8        # "block" bootstrap for MS 408: 8 consecutive folios ~ one quire-sized unit


def _resample_ms(pages, segs: dict, B: int, workers: int | None, log) -> dict[str, pd.DataFrame]:
    """Replicates of every metric (columns ``metric__collapsed`` / ``metric__raw``) for four schemes:
    ``page`` and ``block8`` bootstraps (``B`` resamples each) and the delete-one-page / delete-one-8-page-block
    jackknives (one replicate per page / block)."""
    pb = CI.make_blocks(pages, 1)
    bb = CI.make_blocks(pages, BOOT_BLOCK_PAGES)
    kb = f"block{BOOT_BLOCK_PAGES}"
    jobs = ([("page", b) for b in range(B)] + [(kb, b) for b in range(B)] +
            [("jack_page", i) for i in range(len(pb))] + [(f"jack_{kb}", i) for i in range(len(bb))])

    def one(job):
        kind, b = job
        if kind == "page":
            w = CI.resample_blocks(pb, random.Random(7919 + b))
        elif kind == kb:
            w = CI.resample_blocks(bb, random.Random(15838 + b))
        elif kind == "jack_page":
            w = CI.leave_out(pb, b)
        else:
            w = CI.leave_out(bb, b)
        row = {}
        for tag, seg in segs.items():
            m = metrics(w, seg, seed=b + 1, n_shuffles=3)
            for k in METRIC_INFO:
                row[f"{k}__{tag}"] = m[k]
        return kind, row
    log(f"MS 408 resampling: {B} page + {B} {BOOT_BLOCK_PAGES}-page-block bootstraps, jackknives over {len(pb)} pages / {len(bb)} blocks")
    res = CI.pmap(one, jobs, workers)
    kinds = ("page", kb, "jack_page", f"jack_{kb}")
    return {kind: pd.DataFrame([r for k, r in res if k == kind]) for kind in kinds}


def ms_ci_table(point: dict[str, pd.Series], reps: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Per metric and unit variant: point estimate, bootstrap SE / percentile CI (page, 8-page block), jackknife SE
    (page, 8-page block) and ``se_used`` = the larger jackknife SE. ``ci_lo``/``ci_hi`` = estimate ± 1.96 ``se_used``."""
    kb = f"block{BOOT_BLOCK_PAGES}"
    rows = []
    for tag, pt in point.items():
        for m in METRIC_INFO:
            r = {"metric": m, "units": tag, "estimate": float(pt[m])}
            for kind in ("page", kb):
                s = CI.summarize(reps[kind][f"{m}__{tag}"].values)
                r[f"boot_se_{kind}"], r[f"boot_lo_{kind}"], r[f"boot_hi_{kind}"] = s["se"], s["lo"], s["hi"]
            for kind in ("jack_page", f"jack_{kb}"):
                r[f"se_{kind}"] = CI.jackknife_se(reps[kind][f"{m}__{tag}"].values)
            ses = [x for x in (r["se_jack_page"], r[f"se_jack_{kb}"]) if not math.isnan(x)]
            r["se_used"] = max(ses) if ses else float("nan")
            r["ci_lo"], r["ci_hi"] = r["estimate"] - 1.96 * r["se_used"], r["estimate"] + 1.96 * r["se_used"]
            rows.append(r)
    return pd.DataFrame(rows)


def run_controls(n_tokens: int = TARGET_TOKENS, seeds: int = SEED_DEFAULT, out_dir: Path | None = None,
                 main_file=None, make_plots: bool = True, quiet: bool = False, boot: int = 100,
                 control_jack: int = 20, workers: int | None = None) -> dict:
    out = Path(out_dir) if out_dir else reports_dir() / "controls"
    out.mkdir(parents=True, exist_ok=True)
    log = (lambda *a: None) if quiet else (lambda *a: print(*a, flush=True))
    plain = _word_sets(n_tokens, log)
    ms_rows, ms_train = ms_variants(main_file)
    if not ms_rows:
        log("MS 408 transcription not found (python -m msdecipher fetch): controls only, no verdicts")
    specs = control_specs(n_tokens, seeds, plain, ms_train)
    log(f"{len(specs)} control rows, {len(plain)} size-matched text windows")

    # ---- point estimates
    runs, samples = [], {}
    for name, (w, seg) in ms_rows.items():
        runs.append({"name": name, "family": "MS 408", "base": "-", "window": 0, "seed": 0, **metrics(w, seg, seed=1)})
        samples[name] = w
    jobs = [(i, s) for i, sp in enumerate(specs) for s in (range(1, seeds + 1) if sp["stochastic"] else [0])]

    def run_one(job):
        i, s = job
        sp = specs[i]
        w = sp["build"](s)
        return i, s, metrics(w, None, seed=max(s, 1)), (w if s <= 1 else None)
    log(f"metrics: {len(jobs)} runs")
    for i, s, m, w in CI.pmap(run_one, jobs, workers):
        sp = specs[i]
        runs.append({"name": sp["name"], "family": sp["family"], "base": sp["base"], "window": sp["window"], "seed": s, **m})
        if w is not None:
            samples[sp["name"]] = w
    runs_df = pd.DataFrame(runs)
    runs_df.to_csv(out / "comparison_runs.csv", index=False)
    mcols = [c for c in runs_df.columns if c not in ("name", "family", "base", "window", "seed")]
    order = list(dict.fromkeys(runs_df["name"]))
    grp = runs_df.groupby("name", sort=False)
    mean_df = grp[mcols].mean().loc[order]
    sd_df = grp[mcols].std(ddof=0).loc[order]
    meta = {r["name"]: r for r in runs}
    info = pd.DataFrame({"name": order, "family": [meta[n]["family"] for n in order],
                         "base": [meta[n]["base"] for n in order], "window": [meta[n]["window"] for n in order],
                         "n_runs": [int((runs_df["name"] == n).sum()) for n in order]}).set_index("name")
    comp = info.join(mean_df)
    comp.reset_index().to_csv(out / "comparison.csv", index=False)
    info.join(sd_df).reset_index().to_csv(out / "comparison_sd.csv", index=False)
    memberships = {sp["name"]: sp["memberships"] for sp in specs}

    res = {"comparison": comp, "sd": sd_df, "n_tokens": n_tokens, "seeds": seeds, "memberships": memberships,
           "boot": boot, "control_jack": control_jack}

    # ---- controls: delete-one-group jackknife of each window-0 row (seed 1)
    if control_jack > 0:
        cjobs = [i for i, sp in enumerate(specs) if sp["window"] == 0 and sp["family"] != FAMILY_ABJAD_VARIANT]

        def jack_one(i):
            sp = specs[i]
            w = sp["build"](1 if sp["stochastic"] else 0)
            groups = CI.group_split(w, control_jack)
            rows = [metrics(CI.leave_out(groups, g), None, seed=g + 1, n_shuffles=2) for g in range(len(groups))]
            return i, {k: (CI.jackknife_se([r[k] for r in rows])) for k in METRIC_INFO}
        log(f"controls jackknife: {len(cjobs)} rows x {control_jack} groups")
        crow = []
        for i, d in CI.pmap(jack_one, cjobs, workers):
            for k, se in d.items():
                est = float(comp.loc[specs[i]["name"], k])
                crow.append({"name": specs[i]["name"], "metric": k, "estimate": est, "se": se,
                             "ci_lo": est - 1.96 * se, "ci_hi": est + 1.96 * se})
        cci = pd.DataFrame(crow)
        cci.to_csv(out / "comparison_ci.csv", index=False)
        res["control_ci"] = cci

    # ---- MS 408: page / block bootstrap, verdicts
    if ms_rows:
        pages = ms_pages(main_file)
        segs = {"collapsed": ms_rows[MS_MAIN][1], "raw": ms_rows[MS_RAW][1]}
        if boot > 0 and pages:
            reps = _resample_ms(pages, segs, boot, workers, log)
            point = {"collapsed": comp.loc[MS_MAIN], "raw": comp.loc[MS_RAW]}
            msci = ms_ci_table(point, reps)
            msci.to_csv(out / "ms408_ci.csv", index=False)
            res["ms_ci"] = msci
            res["ms_se"] = {tag: dict(zip(g["metric"], g["se_used"])) for tag, g in msci.groupby("units")}
        else:
            res["ms_se"] = None
        ranges, verd, summ = family_verdicts(comp, res.get("ms_se"), memberships)
        ranges.to_csv(out / "family_ranges.csv", index=False)
        verd.to_csv(out / "verdicts.csv", index=False)
        summ.to_csv(out / "verdict_summary.csv", index=False)
        res.update(ranges=ranges, verdicts=verd, summary=summ)
        shift = verdict_shift(comp, res.get("ms_se"), memberships)
        if shift is not None:
            shift.to_csv(out / "verdict_shift_abjad.csv", index=False)
            res["shift"] = shift
        if "control_ci" in res and res.get("ms_se"):
            cz, czs = control_z_tables(comp, res["control_ci"], res["ms_se"]["collapsed"])
            cz.to_csv(out / "control_z.csv", index=False)
            czs.to_csv(out / "control_z_summary.csv", index=False)
            res.update(control_z=cz, control_z_summary=czs)
        aa = alphabet_adjustment(comp, (res.get("ms_se") or {}).get("collapsed"))
        aa.to_csv(out / "alphabet_adjusted.csv", index=False)
        res["alphabet"] = aa
        size = size_sensitivity(ms_rows, plain)
        size.to_csv(out / "size_sensitivity.csv", index=False)
        res["size"] = size
    (out / "comparison.md").write_text(report_markdown(res, out), encoding="utf-8")
    if make_plots:
        from . import controls_plots
        controls_plots.make_all(res, samples, out / "figures")
    log("wrote", out)
    return res


# ------------------------------------------------------------------ family screening

def _expand(comp: pd.DataFrame, memberships: dict | None) -> pd.DataFrame:
    """Rows of the control table, one copy per family they belong to (``family`` column = that family);
    MS 408 rows and non-hypothesis families dropped."""
    parts = []
    for name, r in comp.iterrows():
        fams = (memberships or {}).get(name) or [r["family"]]
        for f in fams:
            if f in NOT_HYPOTHESES:
                continue
            row = r.copy()
            row["family"] = f
            row["_name"] = name
            parts.append(row)
    return pd.DataFrame(parts)


def family_verdicts(comp: pd.DataFrame, ms_se: dict | None = None, memberships: dict | None = None):
    """Per family and metric: prediction-interval verdict of MS 408 (collapsed and raw EVA units).
    ``ms_se`` = ``{"collapsed": {metric: se}, "raw": {...}}`` (bootstrap SEs; ``None`` = 0)."""
    ctrl = _expand(comp, memberships)
    ranges, verd = [], []
    for fam, g in ctrl.groupby("family", sort=False):
        for m, (label, tol, group) in METRIC_INFO.items():
            vals = g[m].astype(float).values
            row = {"family": fam, "metric": m, "group": group}
            for tag, key in (("collapsed", MS_MAIN), ("raw", MS_RAW)):
                v = float(comp.loc[key, m])
                se = ((ms_se or {}).get(tag) or {}).get(m, 0.0)
                iv = CI.interval_verdict(v, se, vals)
                row[f"ms_{tag}"], row[f"se_{tag}"] = v, se
                row[f"z_{tag}"], row[f"pi_lo_{tag}"], row[f"pi_hi_{tag}"] = iv["z"], iv["pi_lo"], iv["pi_hi"]
                row[f"verdict_{tag}"], row[f"pct_{tag}"] = iv["verdict"], iv["ms_percentile"]
            row.update(n_members=iv["n_members"], family_mean=iv["family_mean"], family_sd=iv["family_sd"],
                       family_min=iv["family_min"], family_max=iv["family_max"])
            ranges.append({"family": fam, "metric": m, "n_members": iv["n_members"], "mean": iv["family_mean"],
                           "sd": iv["family_sd"], "min": iv["family_min"], "max": iv["family_max"]})
            verd.append(row)
    ranges_df, verd_df = pd.DataFrame(ranges), pd.DataFrame(verd)
    summ = []
    for fam, g in verd_df.groupby("family", sort=False):
        row = {"family": fam, "n_members": int(g["n_members"].iloc[0])}
        for tag in ("collapsed", "raw"):
            v = g[f"verdict_{tag}"]
            row[f"within_{tag}"] = int((v == "≈").sum())
            row[f"outside_{tag}"] = int(v.isin(["↑", "↓"]).sum())
            row[f"undetermined_{tag}"] = int(v.isin(["?", "–"]).sum())
        row["n_metrics"] = len(g)
        row["outside_metrics_collapsed"] = "; ".join(f"{m}{v}" for m, v in zip(g["metric"], g["verdict_collapsed"]) if v in ("↑", "↓"))
        summ.append(row)
    summ_df = pd.DataFrame(summ).sort_values(["within_collapsed", "n_members"], ascending=False).reset_index(drop=True)
    return ranges_df, verd_df, summ_df


def _is_abjad_row(comp: pd.DataFrame) -> pd.Series:
    return comp["base"].isin(ABJAD) | comp["family"].isin([FAMILY_ABJAD, FAMILY_ABJAD_VARIANT])


def verdict_shift(comp: pd.DataFrame, ms_se: dict | None = None, memberships: dict | None = None) -> pd.DataFrame | None:
    """Per family and metric: MS 408's verdict (collapsed units) computed WITHOUT the Hebrew/Arabic
    controls vs WITH them, plus both bands. ``None`` if there are no Hebrew/Arabic rows."""
    is_ab = _is_abjad_row(comp)
    if not is_ab.any():
        return None
    ms_rows = comp.index.isin([MS_MAIN, MS_RAW])
    _, before, _ = family_verdicts(comp[~is_ab | ms_rows], ms_se, memberships)
    _, after, _ = family_verdicts(comp, ms_se, memberships)
    b = before[["family", "metric", "family_mean", "family_sd", "verdict_collapsed"]].rename(
        columns={"family_mean": "mean_before", "family_sd": "sd_before", "verdict_collapsed": "verdict_before"})
    a = after[["family", "metric", "n_members", "family_mean", "family_sd", "ms_collapsed", "verdict_collapsed"]].rename(
        columns={"family_mean": "mean_after", "family_sd": "sd_after", "verdict_collapsed": "verdict_after"})
    m = a.merge(b, on=["family", "metric"], how="left")
    m["verdict_before"] = m["verdict_before"].fillna("(family is new)")
    m["changed"] = m["verdict_before"] != m["verdict_after"]
    return m


def control_z_tables(comp: pd.DataFrame, cci: pd.DataFrame, ms_se: dict):
    """MS 408 vs each single control row (window 0): z from the two bootstrap SEs. Returns (long table,
    per-control summary with the number of metrics where |z| < 2)."""
    se = {(r.name, r.metric): r.se for r in cci.itertuples()}
    rows = []
    for name, r in comp.iterrows():
        if r["family"] == "MS 408" or (name, "type_token_ratio") not in se:
            continue
        for m in METRIC_INFO:
            z = CI.control_z(float(comp.loc[MS_MAIN, m]), ms_se.get(m, 0.0), float(r[m]), se.get((name, m), float("nan")))
            rows.append({"name": name, "family": r["family"], "metric": m, "control": float(r[m]), "control_se": se.get((name, m)),
                         "ms408": float(comp.loc[MS_MAIN, m]), "ms408_se": ms_se.get(m), "z": z})
    cz = pd.DataFrame(rows)
    if cz.empty:
        return cz, cz
    g = cz.groupby(["name", "family"], sort=False)["z"]
    summ = pd.DataFrame({"n_metrics": g.apply(lambda s: int(s.notna().sum())),
                         "within_2se": g.apply(lambda s: int((s.abs() < 2).sum())),
                         "median_abs_z": g.apply(lambda s: float(s.abs().median()))}).reset_index()
    return cz, summ.sort_values(["within_2se", "median_abs_z"], ascending=[False, True]).reset_index(drop=True)


ALPHABET_METRICS = ["unit_H1", "unit_h2", "unit_h3", "shuffle_gap_h2", "unit_mi_adjacent", "unit_h2_over_H1", "unit_h3_over_H1",
                    "mean_word_length_units"]


def alphabet_adjustment(comp: pd.DataFrame, ms_se: dict | None) -> pd.DataFrame:
    """OLS of each metric on log2(alphabet size >= 20 tokens) over natural-language rows (Latin/Italian/
    German + Hebrew/Arabic main normalisation, all full-size windows); MS 408's value vs the prediction
    interval at its own alphabet size."""
    nat = comp[comp["family"].isin([FAMILY_PLAIN, FAMILY_ABJAD])]
    if nat.empty or MS_MAIN not in comp.index:
        return pd.DataFrame()
    x = np.log2(nat["alphabet_size_ge20"].astype(float).values)
    x_ms = math.log2(float(comp.loc[MS_MAIN, "alphabet_size_ge20"]))
    rows = []
    for m in ALPHABET_METRICS:
        a = CI.alphabet_adjusted(x, nat[m].astype(float).values, x_ms, float(comp.loc[MS_MAIN, m]),
                                 ((ms_se or {}).get(m, 0.0)))
        rows.append({"metric": m, "ms408": float(comp.loc[MS_MAIN, m]), "ms_alphabet": float(comp.loc[MS_MAIN, "alphabet_size_ge20"]),
                     "natural_alphabet_min": float(nat["alphabet_size_ge20"].min()),
                     "natural_alphabet_max": float(nat["alphabet_size_ge20"].max()), **a})
    return pd.DataFrame(rows)


def size_sensitivity(ms_rows, plain, n_small: int = 9000) -> pd.DataFrame:
    """Same metrics on the first ``n_small`` tokens of MS 408 (manuscript order) and of the plain
    controls (window 0), to show how much each number moves with sample size alone."""
    rows = []
    P, coll = ms_rows[MS_MAIN]
    cids = [c for c in PLAIN + ABJAD if c in plain]
    for name, w, seg in [("MS408 P first %d" % n_small, P[:n_small], coll)] + \
                        [(f"plain:{c} first {n_small}", plain[c][:n_small], None) for c in cids]:
        m = metrics(w, seg, seed=1)
        rows.append({"name": name, **{k: m[k] for k in ("n_tokens", "type_token_ratio", "zipf_mle_s_r10_1000",
                                                      "heaps_beta_in_order", "unit_H1", "unit_h2", "unit_h3",
                                                      "shuffle_gap_h2", "pos_skewed_unit_share")}})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ markdown

SHOW = ["n_tokens", "type_token_ratio", "zipf_mle_s_r10_1000", "heaps_beta_shuffled", "mean_word_length_units",
        "unit_H1", "unit_h2", "unit_h3", "shuffle_gap_h2", "sukhotin_vowel_like_share", "pos_skewed_unit_share",
        "adjacent_edit1_rate"]
SHORT = {"n_tokens": "tokens", "type_token_ratio": "TTR", "zipf_mle_s_r10_1000": "Zipf s", "heaps_beta_shuffled": "Heaps β",
         "mean_word_length_units": "len", "unit_H1": "H1", "unit_h2": "h2", "unit_h3": "h3", "shuffle_gap_h2": "Δh2 shuf",
         "sukhotin_vowel_like_share": "vowel-like", "pos_skewed_unit_share": "pos-skew", "adjacent_edit1_rate": "adj-edit1"}
KEY = ["unit_h2", "unit_h3", "shuffle_gap_h2", "unit_h2_over_H1", "zipf_mle_s_r10_1000", "type_token_ratio",
       "pos_skewed_unit_share", "adjacent_edit1_rate"]
ABJAD_SHOW = ["n_tokens", "type_token_ratio", "zipf_mle_s_r10_1000", "heaps_beta_shuffled", "mean_word_length_units",
              "alphabet_size_ge20", "unit_H1", "unit_h2", "unit_h3", "shuffle_gap_h2", "sukhotin_vowel_like_share",
              "pos_skewed_unit_share", "pos_jsd_initial_final"]
ABJAD_SHORT = {**SHORT, "alphabet_size_ge20": "alphabet", "pos_jsd_initial_final": "JSD ini/fin"}


def _fmt_ci(r) -> str:
    return f"{r['estimate']:.3f} [{r['ci_lo']:.3f}, {r['ci_hi']:.3f}]"


def report_markdown(res: dict, out: Path) -> str:
    comp: pd.DataFrame = res["comparison"]
    L = ["# Control comparison: MS 408 vs controls", "",
         "> **MS 408 is undeciphered.** This is a screening comparison of descriptive statistics, not a decipherment, "
         "and no single metric is decisive. Controls are built from a modest number of base texts (Latin incl. herbal/medical, "
         "Italian, German, Hebrew and Arabic prose); transformations are simplified illustrations of each family, NOT reproductions "
         "of published ciphers; generators are not fitted to MS 408. See [docs/CONTROLS.md](../../docs/CONTROLS.md).", "",
         f"Target size {res['n_tokens']} tokens per sample (MS 408 running text: "
         f"{int(comp.loc[MS_MAIN, 'n_tokens']) if MS_MAIN in comp.index else 'n/a'} readable tokens). Plain texts are sampled in up to 3 "
         f"non-overlapping size-matched windows; stochastic controls are means over {res['seeds']} seeds. Controls use single characters "
         "as units; MS 408 uses the collapsed EVA segmentation (ch, sh, cth, ckh, cph, cfh as single units) unless marked raw. "
         "Tables: `comparison.csv` (means, all windows), `comparison_sd.csv`, `comparison_runs.csv`, `comparison_ci.csv` (jackknife SE per control row), `ms408_ci.csv`.", ""]
    first = comp[comp["window"] == 0] if "window" in comp else comp
    t = first.reset_index()[["name", "family"] + SHOW].rename(columns=SHORT)
    L += ["## 1. All corpora (window 0), selected metrics", "",
          f"{len(comp) - len(first)} further rows (later windows of the plain texts) are in `comparison.csv`.", "", md_table(t), ""]
    if "ms_ci" in res:
        L += ms_ci_section(res)
    if "verdicts" in res:
        verd, summ = res["verdicts"], res["summary"]
        L += ["## 3. Which hypothesis families is MS 408 consistent with? (prediction-interval verdicts)", "",
              "For each family and metric the members (one per base text × window, seeds averaged) give a mean and an SD. MS 408 is `≈` when "
              "it lies in the 95% prediction interval, `↑`/`↓` when above/below, `?` when the family has fewer than 3 members. "
              "The interval includes MS 408's own sampling uncertainty (jackknife SE, larger of the page and 8-page-block versions). "
              "Excluded as hypotheses: the Markov model trained on MS 408 (circular), the folded-alphabet sensitivity rows and undersized texts. "
              "This **replaces** the earlier min/max-plus-arbitrary-tolerance bands.", ""]
        piv = verd.pivot(index="metric", columns="family", values="verdict_collapsed")
        cols = list(summ["family"])
        piv = piv.loc[list(METRIC_INFO), cols]
        piv.index = [METRIC_INFO[m][0] for m in piv.index]
        short_cols = {c: (c if len(c) < 24 else c[:22] + "…") for c in cols}
        t2 = piv.rename(columns=short_cols).reset_index().rename(columns={"index": "metric"})
        L += [md_table(t2), "", "Column order = number of metrics inside the interval (highest first):", ""]
        L += [f"{i + 1}. {c}" for i, c in enumerate(cols)] + [""]
        s2 = summ[["family", "n_members", "within_collapsed", "outside_collapsed", "undetermined_collapsed", "within_raw", "outside_raw", "n_metrics"]]
        s2 = s2.rename(columns={"within_collapsed": "inside (collapsed units)", "outside_collapsed": "outside (collapsed)",
                                "undetermined_collapsed": "? (collapsed)", "within_raw": "inside (raw EVA)", "outside_raw": "outside (raw)"})
        L += ["### Summary per family", "", md_table(s2), ""]
        L += ["### Metrics where MS 408 falls OUTSIDE each family's prediction interval (collapsed units)", ""]
        for _, r in summ.iterrows():
            L.append(f"- **{r['family']}** (n={int(r['n_members'])}; {int(r['within_collapsed'])}/{int(r['n_metrics'])} inside): "
                     f"{r['outside_metrics_collapsed'] or 'none'}")
        L += [""] + interpretation(res) + [""]
        L += z_table(res)
        L += herbal_section(res)
        L += alphabet_section(res)
        L += control_z_section(res)
        L += abjad_section(res)
        L += ["## 8. Sample-size sensitivity (first 9,000 tokens of each)", "", md_table(res["size"]), "",
              "The first 9,000 tokens of MS 408 are mostly herbal-section text in manuscript order; the point is only how far "
              "TTR, Zipf, Heaps and entropies move when the sample shrinks to the size of the smallest controls.", ""]
    L += ["## Caveats", "",
          "- Family members are a handful of base texts (several windows of the same book are not independent), so prediction intervals understate the true spread of 'all texts of that kind'; `?` means fewer than 3 members.",
          "- SEs are delete-one-block jackknife SEs (MS 408: pages and 8-page blocks; controls: 20 contiguous groups). They capture sampling noise only: not transcription uncertainty, not model misspecification, not the choice of unit segmentation. For smooth metrics the jackknife is reliable; for rank/threshold statistics (Zipf fit, Sukhotin share) it is only indicative.",
          "- The 8-page block approximates quire structure only (the repo has no folio→quire map); the page jackknife is usually the lower SE, the block jackknife the larger. The larger is used.",
          "- Per-control z-scores use only the two jackknife SEs; they say 'distinguishable from this one text at this noise level', not 'is this kind of text'.",
          "- Hebrew/Arabic: consonantal normalisation is our choice (maqaf/hyphen splits words, Arabic clitics like و- and ال- stay attached, Quranic marks and diacritics dropped); none is a model of whatever language MS 408 may encode.",
          "- Tokenization is a free choice: controls are normalised to a-z with diacritics folded; MS 408 uses a transcription (ZL 3b) with uncertain spaces split and unreadable tokens dropped, and unit segmentation (collapsed vs raw) changes unit-level metrics (see the `raw` columns in `verdict_summary.csv`).",
          "- Poetry (Dante, Ariosto, Faust, Walther, Macer) and prose differ; MS 408 pages are not independent samples (sections, hands, Currier A/B).",
          "- `Markov o2 trained on MS 408` reproduces h2 by construction and is not a hypothesis. The slot-grammar generator's inventories were written with published descriptions of Voynichese in mind, so its match is expected, not independent evidence.",
          "- The verbose / Naibbe-inspired controls are measured on single symbols; the cipher's natural unit (a 2-3 symbol group) would give different unit statistics. The self-citation generator is a copy-and-mutate toy (parameters 0.15/0.3/0.5, not fitted).",
          "- Ranking families by the count of metrics inside the interval is only a convenience for ordering columns; the metrics are strongly correlated, so the count is not a likelihood.",
          "- No metric here is decisive; several hypotheses (self-citation generators, verbose ciphers) are known to reproduce parts of the profile.", ""]
    return "\n".join(L)


def ms_ci_section(res: dict) -> list[str]:
    ci = res["ms_ci"]
    c = ci[ci["units"] == "collapsed"].set_index("metric")
    rows = [{"metric": METRIC_INFO[m][0], "estimate [95% CI = estimate ± 1.96 SE]": _fmt_ci(c.loc[m]),
             "SE jackknife page": c.loc[m, "se_jack_page"], "SE jackknife 8-page block": c.loc[m, "se_jack_block8"],
             "SE bootstrap 8-page block": c.loc[m, "boot_se_block8"]} for m in METRIC_INFO]
    L = ["## 2. MS 408 confidence intervals (collapsed units)", "",
         f"Delete-one-page jackknife (one replicate per folio) and delete-one-block jackknife (blocks of {BOOT_BLOCK_PAGES} consecutive folios, a stand-in for quires), "
         f"plus {res['boot']} bootstrap resamples by page and by block. The **jackknife SE is the one used** (larger of the two): resampling with replacement duplicates "
         "text and lowers the number of distinct types, which biases vocabulary-richness metrics (type/token ratio, hapax share, Heaps beta, word entropy) "
         "and makes their percentile CIs off-centre (see `ms408_ci.csv`, columns `boot_*`); the jackknife drops data instead.", "",
         md_table(pd.DataFrame(rows), floatfmt="{:.4f}"), ""]
    if "control_ci" in res:
        cci = res["control_ci"]
        L += [f"Controls: delete-one-group jackknife ({res['control_jack']} contiguous groups) per window-0 row, SE per metric in `comparison_ci.csv`. "
              "Median SE across controls for the key metrics: " +
              ", ".join(f"{METRIC_INFO[m][0]} {cci[cci['metric'] == m]['se'].median():.4f}" for m in ("unit_h2", "unit_h3", "type_token_ratio", "zipf_mle_s_r10_1000")) + ".", ""]
    return L


def z_table(res: dict) -> list[str]:
    verd = res["verdicts"]
    fams = [f for f in (FAMILY_PLAIN, FAMILY_PLAIN_LATIN, FAMILY_PLAIN_HERBAL, FAMILY_ABJAD) if f in set(verd["family"])]
    if not fams:
        return []
    L = ["### z-scores of MS 408 against the natural-text families (collapsed units)", "",
         "z = (MS − family mean) / sqrt(SD²(1+1/n) + SE²); |z| beyond roughly 2-3 (t-limit by n) = outside.", ""]
    rows = []
    for m in METRIC_INFO:
        r = {"metric": METRIC_INFO[m][0], "MS 408": verd[verd["metric"] == m]["ms_collapsed"].iloc[0]}
        for f in fams:
            g = verd[(verd["family"] == f) & (verd["metric"] == m)]
            r[f.split("(")[0].strip()[:34] + f" n={int(g['n_members'].iloc[0])}"] = g["z_collapsed"].iloc[0] if len(g) else float("nan")
        rows.append(r)
    return L + [md_table(pd.DataFrame(rows), floatfmt="{:.2f}"), ""]


def herbal_section(res: dict) -> list[str]:
    comp = res["comparison"]
    h = comp[comp["base"].isin(["la_pliny_herbal", "la_celsus", "la_macer", "la_pliny_general", "la_isidore"]) & comp.index.str.startswith("plain:")]
    if h.empty:
        return []
    t = pd.concat([comp.loc[[MS_MAIN]], h]).reset_index()[["name", "family"] + SHOW].rename(columns=SHORT)
    return ["## 4. Herbal / medical / encyclopaedic Latin controls", "",
            "Added because MS 408's herbal section is a large part of the text. Pliny XX-XXVII (plant remedies, Perseus/Mayhoff), Celsus "
            "*De medicina*, Macer Floridus *De viribus herbarum* (verse, only ~14k tokens: undersized), Pliny VII-XI (non-botanical) and Isidore "
            "*Etymologiae* for comparison. Vocabulary-level numbers (TTR, Zipf, Heaps) depend on topic: a plant catalogue has many rare names.", "",
            md_table(t), ""]


def alphabet_section(res: dict) -> list[str]:
    aa = res.get("alphabet")
    comp = res["comparison"]
    L = ["## 5. Alphabet-size normalisation", "",
         "Raw entropies grow with alphabet size. Two corrections: (i) normalised metrics in the main table (`H1/log2 A`, `h2/H1`, `h3/H1`, "
         "`H1−h2`, shuffle-gap/H1), and (ii) an OLS of each metric on log2(alphabet size) over the natural-language rows (Latin/Italian/German + "
         "Hebrew/Arabic, full-size windows) and MS 408's value vs the prediction interval at MS 408's own alphabet size."]
    if aa is not None and len(aa):
        ms_a = int(aa["ms_alphabet"].iloc[0])
        L += ["", f"MS 408 has {ms_a} unit types with ≥20 tokens (collapsed EVA); natural texts range {int(aa['natural_alphabet_min'].iloc[0])}-{int(aa['natural_alphabet_max'].iloc[0])}. "
              "'extrapolated' = MS 408 outside that range.", ""]
        t = aa[["metric", "ms408", "pred", "slope", "r", "z", "verdict", "extrapolated", "n"]].copy()
        t["metric"] = t["metric"].map(lambda m: METRIC_INFO[m][0] if m in METRIC_INFO else m)
        t = t.rename(columns={"ms408": "MS 408", "pred": "predicted at MS alphabet", "slope": "slope per log2 A"})
        L += [md_table(t), ""]
    rows = []
    sel = ["unit_H1_norm", "unit_h2_over_H1", "unit_h3_over_H1", "unit_mi_adjacent", "shuffle_gap_over_H1"]
    summ = []
    nat = comp[comp["family"].isin([FAMILY_PLAIN, FAMILY_ABJAD])]
    ms = comp.loc[MS_MAIN]
    for m in sel:
        summ.append({"metric": METRIC_INFO[m][0], "MS 408": ms[m], "natural min": nat[m].min(), "natural median": nat[m].median(), "natural max": nat[m].max()})
    L += ["Normalised metrics, MS 408 vs the natural-text rows (all windows):", "", md_table(pd.DataFrame(summ)), ""]
    return L


def control_z_section(res: dict) -> list[str]:
    cz = res.get("control_z_summary")
    if cz is None or not len(cz):
        return []
    top = cz.head(10).copy()
    L = ["## 6. MS 408 vs each single control (bootstrap z)", "",
         "Per control row (window 0): number of the 23 metrics where |z| < 2 using only the two bootstrap SEs, and the median |z|. "
         "Ten closest controls (full table: `control_z_summary.csv`, per metric `control_z.csv`). Note that very small SEs make |z| large "
         "even for modest differences.", "", md_table(top, floatfmt="{:.2f}"), ""]
    return L


def abjad_section(res: dict) -> list[str]:
    """Hebrew/Arabic: key numbers, folded-alphabet sensitivity, and what they change in the verdicts."""
    comp: pd.DataFrame = res["comparison"]
    ab = comp[comp["family"].isin([FAMILY_ABJAD, FAMILY_ABJAD_VARIANT])]
    if ab.empty:
        return []
    ms = comp.loc[MS_MAIN]
    t = pd.concat([comp.loc[[MS_MAIN]], ab]).reset_index()[["name"] + ABJAD_SHOW]
    for c in ("n_tokens", "alphabet_size_ge20"):
        t[c] = t[c].round().astype(int)
    t = t.rename(columns=ABJAD_SHORT)
    L = ["## 7. Natural abjad texts (Hebrew, Arabic)", "",
         "Consonantal Hebrew (Tanakh Genesis+Exodus; Maimonides, *Mishneh Torah*) and Arabic (Quran; Ibn Khaldun, *Muqaddimah*), one native "
         "letter = one unit, vowel points/diacritics removed. `plain:` rows use the main normalisation (Hebrew final forms ך ם ן ף ץ "
         "kept as separate letters; Arabic alif-hamza variants folded into alif); `plain_folded:` rows fold Hebrew final forms into the "
         "medial letters and reduce the Arabic alphabet further (ى→ي, ة→ه, ؤ→و, ئ→ي, hamza deleted), as a sensitivity check. "
         "A 1-to-1 Latin transliteration would give the same numbers (tested), so no separate transliterated run is shown.", "",
         md_table(t), ""]
    main = ab[ab["family"] == FAMILY_ABJAD]
    fold = ab[ab["family"] == FAMILY_ABJAD_VARIANT]

    def rng(df, m, nd=2):
        return f"{df[m].min():.{nd}f}-{df[m].max():.{nd}f}"
    L += ["Auto-generated summary (hedged; 4 texts, 2 languages, two sizes of corpus):", "",
          f"- h2: MS 408 {ms['unit_h2']:.2f} bits; Hebrew/Arabic {rng(main, 'unit_h2')} (folded variants {rng(fold, 'unit_h2')}). "
          f"h3: MS 408 {ms['unit_h3']:.2f}; abjad {rng(main, 'unit_h3')}.",
          f"- h2 rise after within-word letter shuffle: MS 408 {ms['shuffle_gap_h2']:.2f} bits; abjad {rng(main, 'shuffle_gap_h2')} "
          f"(Latin/Italian/German plain texts: {rng(comp[comp['family'] == FAMILY_PLAIN], 'shuffle_gap_h2')}).",
          f"- Share of positionally skewed units: MS 408 {ms['pos_skewed_unit_share']:.2f}; abjad {rng(main, 'pos_skewed_unit_share')} "
          f"(folded {rng(fold, 'pos_skewed_unit_share')}).",
          f"- Zipf s: MS 408 {ms['zipf_mle_s_r10_1000']:.2f}; abjad {rng(main, 'zipf_mle_s_r10_1000')}. Heaps beta (shuffled): "
          f"MS 408 {ms['heaps_beta_shuffled']:.2f}; abjad {rng(main, 'heaps_beta_shuffled')}. TTR: MS 408 {ms['type_token_ratio']:.2f}; "
          f"abjad {rng(main, 'type_token_ratio')}.",
          f"- Mean word length: MS 408 {ms['mean_word_length_units']:.2f} units; abjad {rng(main, 'mean_word_length_units')}.", ""]
    sh = res.get("shift")
    if sh is not None:
        ch = sh[sh["changed"] & (sh["verdict_before"] != "(family is new)")]
        names = {m: METRIC_INFO[m][0] for m in METRIC_INFO}
        L += ["### What adding Hebrew/Arabic changes in the family verdicts", "",
              "Verdicts for MS 408 (collapsed units) per family and metric, computed without and with "
              "the Hebrew/Arabic bases/transformations (`verdict_shift_abjad.csv`). Families that gain Hebrew/Arabic members get wider intervals.", ""]
        if ch.empty:
            L += ["No existing family verdict changes."]
        else:
            tab = ch[["family", "metric", "verdict_before", "verdict_after"]].copy()
            tab["metric"] = tab["metric"].map(names)
            L += [f"{len(ch)} of {int((sh['verdict_before'] != '(family is new)').sum())} existing family-metric verdicts change:", "",
                  md_table(tab.reset_index(drop=True))]
        new = sh[sh["verdict_before"] == "(family is new)"]
        if len(new):
            ins = new[new["verdict_after"] == "≈"]["metric"].map(names).tolist()
            outs = new[new["verdict_after"].isin(["↑", "↓"])]
            L += ["", f"New family \"{FAMILY_ABJAD}\": MS 408 is inside the prediction interval for {len(ins)} of {len(new)} metrics"
                  + (": " + ", ".join(ins) + "." if ins else "."),
                  "Outside: " + ", ".join(f"{names[r.metric]}{r.verdict_after}" for r in outs.itertuples()) + "." if len(outs) else ""]
        L += [""]
    return L



def interpretation(res: dict) -> list[str]:
    """Data-driven, hedged reading of the verdict matrix."""
    verd, comp = res["verdicts"], res["comparison"]
    ms = comp.loc[MS_MAIN]
    L = ["### Reading the matrix (auto-generated from the numbers above; hedged)", "",
         f"MS 408 (collapsed units): h2 = {ms['unit_h2']:.2f} bits, h3 = {ms['unit_h3']:.2f}, h2 rise after within-word "
         f"shuffle = {ms['shuffle_gap_h2']:.2f} bits, Zipf s = {ms['zipf_mle_s_r10_1000']:.2f}, TTR = {ms['type_token_ratio']:.2f}, "
         f"{ms['pos_skewed_unit_share']:.0%} of units positionally skewed, adjacent edit-distance-1 rate {ms['adjacent_edit1_rate']:.3f}.", ""]
    for m in KEY:
        g = verd[verd["metric"] == m]
        inside = list(g.loc[g["verdict_collapsed"] == "≈", "family"])
        lab = METRIC_INFO[m][0]
        L.append(f"- **{lab}**: MS 408 is inside the prediction interval of " + (", ".join(inside) if inside else "**no** control family") + ".")
    allm = verd.groupby("metric")["verdict_collapsed"].apply(lambda v: (v == "≈").all())
    nonm = [METRIC_INFO[m][0] for m in METRIC_INFO if allm.get(m, False)]
    none_in = verd.groupby("metric")["verdict_collapsed"].apply(lambda v: (v == "≈").sum() == 0)
    outm = [METRIC_INFO[m][0] for m in METRIC_INFO if none_in.get(m, False)]
    L += ["", "- Metrics where MS 408 is inside **every** family interval (non-discriminating here): " + (", ".join(nonm) or "none") + ".",
          "- Metrics where MS 408 is outside **every** family interval (no control family reproduces it with these settings): "
          + (", ".join(outm) or "none") + ".", "",
          "What this does and does not say: the table shows which simplified control families have statistics consistent with MS 408's on each "
          "metric. Families with `?` have too few members to judge. No family matches on all metrics, and the families that match on the most metrics (e.g. the slot-grammar generator) "
          "were designed with Voynichese structure in mind, so their match is not independent evidence. Matching on many metrics "
          "is not proof of a mechanism, and mismatching is not refutation: the controls are crude, intervals optimistic and "
          "several families (verbose/homophonic ciphers, self-citation generators) have parameters that could be tuned toward MS 408."]
    return L
