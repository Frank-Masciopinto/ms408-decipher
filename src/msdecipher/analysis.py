"""End-to-end descriptive analysis: catalogue, units, statistics, Currier A/B, Sukhotin.

Writes CSV + Markdown + PNG into ``reports/`` and ``glyphs/``. Everything produced here is a
description of a transcription; none of it is a decoding (see docs/STATS_NOTE.md).
"""
from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from . import glyphs as G
from . import stats as S
from .corpus_view import Line, lines_for, readable_words
from .ivtff import Corpus, parse_file, render
from .paths import glyphs_dir, reports_dir, transcription_dir
from .segment import DEFAULT_PRESET, Segmenter

MAIN_FILE = "ZL3b-n.txt"
REPLICATION_FILES = ["ZL3b-n.txt", "IT2a-n.txt", "RF1b-e.txt"]
SEG_PRESETS_FOR_SUKHOTIN = ["raw", "basic", "collapsed", "extended"]
EVA_ALPHABETS = {"Eva-", "EvaT"}


# ------------------------------------------------------------------ helpers

def md_table(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    cols = list(df.columns)
    def cell(v):
        if isinstance(v, (float, np.floating)):
            if math.isnan(v):
                return "–"
            if float(v).is_integer() and abs(v) >= 1000:
                return str(int(v))
            return floatfmt.format(v)
        return str(v)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(cell(r[c]) for c in cols) + " |")
    return "\n".join(out)


def load_corpus(name_or_path: str | Path | None = None) -> Corpus:
    p = Path(name_or_path) if name_or_path else transcription_dir() / MAIN_FILE
    if not p.exists():
        alt = transcription_dir() / str(name_or_path)
        if alt.exists():
            p = alt
        else:
            raise FileNotFoundError(f"{p} not found; run `python -m msdecipher fetch` first")
    return parse_file(p)


def check_eva(corpus: Corpus) -> None:
    if corpus.alphabet not in EVA_ALPHABETS:
        raise ValueError(f"{corpus.path}: alphabet {corpus.alphabet!r} is not EVA; the digraph and "
                         "EVA-based statistics here are only meaningful for EVA transcriptions")


def groups(corpus: Corpus, uncertain: str = "split") -> dict[str, list[Line]]:
    """Standard line groups. P = running paragraph text; A/B = Currier language of P text."""
    return {
        "P": lines_for(corpus, uncertain, generic="P"),
        "A": lines_for(corpus, uncertain, generic="P", language="A"),
        "B": lines_for(corpus, uncertain, generic="P", language="B"),
        "labels": lines_for(corpus, uncertain, generic="L"),
        "all_loci": lines_for(corpus, uncertain, generic="PLCR"),
    }


def unit_seqs(lines: list[Line], seg: Segmenter) -> list[tuple]:
    return [seg(w) for w in readable_words(lines)]


def profile(lines: list[Line], seg: Segmenter, seed: int = 1) -> dict:
    words = readable_words(lines)
    d = S.word_stats(words, seg, seed)
    d.update({f"unit_{k}": v for k, v in S.entropy_profile(unit_seqs(lines, seg), seed).items()})
    return d


def subsample_lines(lines: list[Line], target_tokens: int, rng: random.Random) -> list[Line]:
    order = list(range(len(lines)))
    rng.shuffle(order)
    out, n = [], 0
    for i in order:
        out.append(lines[i])
        n += sum(1 for w in lines[i].words if "?" not in w)
        if n >= target_tokens:
            break
    # restore manuscript order (needed for the order-dependent Heaps metric)
    pos = {id(ln): k for k, ln in enumerate(lines)}
    out.sort(key=lambda ln: pos[id(ln)])
    return out


def matched_profile(lines: list[Line], target_tokens: int, seg: Segmenter, reps: int = 8, seed: int = 1) -> dict:
    rng = random.Random(seed)
    profs = [profile(subsample_lines(lines, target_tokens, rng), seg, seed + i) for i in range(reps)]
    keys = profs[0].keys()
    return {k: float(np.mean([p[k] for p in profs])) for k in keys}


def build_catalog(corpus: Corpus, grp: dict, seg: Segmenter, out_g: Path):
    """Write glyphs/catalog.csv, digraph_candidates.csv, top_pmi_bigrams.csv, REPORT.md."""
    out_g.mkdir(parents=True, exist_ok=True)
    cat = G.glyph_table({k: grp[k] for k in ("P", "all_loci", "A", "B", "labels")}, main="P")
    cat.to_csv(out_g / "catalog.csv", index=False)
    dig = G.digraph_table(grp["P"])
    dig.to_csv(out_g / "digraph_candidates.csv", index=False)
    bg = G.top_bigrams(grp["P"])
    bg.to_csv(out_g / "top_pmi_bigrams.csv", index=False)
    (out_g / "REPORT.md").write_text(_glyph_report(corpus, grp, cat, dig, bg, seg), encoding="utf-8")
    return cat, dig, bg


def catalog_only(main_file=None, preset: str = DEFAULT_PRESET, units: str | None = None,
                 uncertain: str = "split", out_glyphs: Path | None = None):
    corpus = load_corpus(main_file)
    check_eva(corpus)
    seg = Segmenter.from_spec(units) if units else Segmenter.preset(preset)
    return build_catalog(corpus, groups(corpus, uncertain), seg, Path(out_glyphs) if out_glyphs else glyphs_dir())


# ------------------------------------------------------------------ main run

def run_all(main_file: str | Path | None = None, preset: str = DEFAULT_PRESET, units: str | None = None,
            uncertain: str = "split", seed: int = 1, out_reports: Path | None = None,
            out_glyphs: Path | None = None, replicate: bool = True, boot: int = 200,
            perms: int = 300, make_plots: bool = True, quiet: bool = False) -> dict:
    out_r = Path(out_reports) if out_reports else reports_dir()
    out_g = Path(out_glyphs) if out_glyphs else glyphs_dir()
    for d in (out_r, out_r / "figures", out_g):
        d.mkdir(parents=True, exist_ok=True)
    log = (lambda *a: None) if quiet else (lambda *a: print(*a, flush=True))

    corpus = load_corpus(main_file)
    check_eva(corpus)
    seg = Segmenter.from_spec(units) if units else Segmenter.preset(preset)
    grp = groups(corpus, uncertain)
    P, A, B = grp["P"], grp["A"], grp["B"]
    res: dict = {"corpus": corpus, "segmenter": seg, "uncertain": uncertain, "seed": seed}
    log(f"[{Path(corpus.path).name}] {len(corpus.loci)} loci; running-text lines: {len(P)} "
        f"(A {len(A)}, B {len(B)}); units: {seg}")

    # ---- 1. glyph catalogue
    cat, dig, bg = build_catalog(corpus, grp, seg, out_g)
    res["catalog"], res["digraphs"], res["bigrams"] = cat, dig, bg
    log(f"  glyph catalogue: {len(cat)} symbols -> {out_g/'catalog.csv'}")

    # ---- 2. unit & word frequencies
    uc = Counter(u for s in unit_seqs(P, seg) for u in s)
    ucA = Counter(u for s in unit_seqs(A, seg) for u in s)
    ucB = Counter(u for s in unit_seqs(B, seg) for u in s)
    tot = sum(uc.values())
    uf = pd.DataFrame([{"unit": render(u), "count": v, "share": v / tot, "count_A": ucA[u], "count_B": ucB[u]}
                       for u, v in uc.most_common()])
    uf.to_csv(out_r / "unit_frequencies.csv", index=False)
    words = readable_words(P)
    wc = Counter(words)
    wf = pd.DataFrame([{"rank": i, "word": render(w), "count": c, "share": c / len(words),
                        "length_units": len(seg(w)), "count_A": 0, "count_B": 0}
                       for i, (w, c) in enumerate(wc.most_common(), 1)])
    wcA, wcB = Counter(readable_words(A)), Counter(readable_words(B))
    wf["count_A"] = [wcA[w] for w in [x for x, _ in wc.most_common()]]
    wf["count_B"] = [wcB[w] for w in [x for x, _ in wc.most_common()]]
    wf.head(1000).to_csv(out_r / "word_frequencies_top1000.csv", index=False)
    lenc = Counter(len(seg(w)) for w in words)
    pd.DataFrame({"length_units": sorted(lenc), "tokens": [lenc[k] for k in sorted(lenc)],
                  "share": [lenc[k] / len(words) for k in sorted(lenc)]}).to_csv(
        out_r / "word_length_distribution.csv", index=False)
    res["unit_freq"], res["word_freq"] = uf, wf

    # ---- 3. summary statistics (all, A, B, size-matched A/B, uncertain spaces joined)
    rows = {}
    rows["P (all running text)"] = profile(P, seg, seed)
    rows["Currier A"] = profile(A, seg, seed)
    rows["Currier B"] = profile(B, seg, seed)
    nA, nB = len(readable_words(A)), len(readable_words(B))
    small = min(nA, nB)
    log(f"  stats computed for P/A/B; size-matching A/B to ~{small} tokens ...")
    rows[f"A matched (~{small} tok)"] = (profile(A, seg, seed) if nA <= nB
                                        else matched_profile(A, small, seg, 6, seed))
    rows[f"B matched (~{small} tok)"] = (profile(B, seg, seed) if nB <= nA
                                        else matched_profile(B, small, seg, 6, seed))
    if uncertain == "split":
        Pj = lines_for(corpus, "join", generic="P")
        rows["P, uncertain spaces joined"] = profile(Pj, seg, seed)
    else:
        Ps = lines_for(corpus, "split", generic="P")
        rows["P, uncertain spaces split"] = profile(Ps, seg, seed)
    summary = pd.DataFrame(rows).T
    summary.index.name = "subset"
    summary.reset_index().to_csv(out_r / "summary_stats.csv", index=False)
    res["summary"] = summary
    log("  summary_stats.csv written")

    # ---- 4. positional distributions
    pos_rows = []
    for name, lines in (("P", P), ("A", A), ("B", B)):
        wl = [ln.words for ln in lines]
        fl = [{"own_line": ln.locus.starts_own_line, "para_start": ln.locus.paragraph_start} for ln in lines]
        tab = S.positional_table(wl, seg, fl)
        for u, c in tab.items():
            inw = c["initial"] + c["medial"] + c["final"] + c["sole"]
            r = {"subset": name, "unit": render(u), "n_in_words": inw}
            for k in ("initial", "medial", "final", "sole"):
                r[f"{k}_share"] = c[k] / inw if inw else float("nan")
            for k in ("line_initial", "line_final", "para_initial"):
                r[f"{k}_n"] = c[k]
            pos_rows.append(r)
    pos = pd.DataFrame(pos_rows).sort_values(["subset", "n_in_words"], ascending=[True, False])
    pos.to_csv(out_r / "positional_units.csv", index=False)
    res["positional"] = pos

    # ---- 5. Currier A vs B
    ab = _currier_ab(A, B, seg, uc, ucA, ucB, seed, perms, out_r)
    res["currier_ab"] = ab
    log(f"  Currier A/B: unit JSD={ab['unit_jsd']:.4f} (perm p={ab['unit_perm_p']:.3f}); "
        f"word JSD={ab['word_jsd']:.4f} (perm p={ab['word_perm_p']:.3f})")

    # ---- 6. Sukhotin after segmentation (+ unsegmented / partially segmented for contrast)
    suk = _sukhotin_all(corpus, uncertain, seed, boot)
    suk.to_csv(out_r / "sukhotin.csv", index=False)
    res["sukhotin"] = suk
    log("  Sukhotin done")

    # ---- 7. replication on other EVA transcriptions
    rep = None
    if replicate:
        rep = _replication(seg, uncertain, seed, log)
        if rep is not None:
            rep.to_csv(out_r / "replication.csv", index=False)
    res["replication"] = rep

    # ---- 8. plots + markdown
    if make_plots:
        from . import plots
        res["figures"] = plots.make_all(res, out_r / "figures", P, A, B, seg, words)
    (out_r / "stats_report.md").write_text(_stats_report(res, seg, uncertain, seed), encoding="utf-8")
    log(f"  report -> {out_r/'stats_report.md'}")
    return res


# ------------------------------------------------------------------ Currier A/B

def _page_counters(lines: list[Line], seg: Segmenter):
    unit_c: dict[str, Counter] = defaultdict(Counter)
    word_c: dict[str, Counter] = defaultdict(Counter)
    for ln in lines:
        for w in ln.words:
            if "?" in w:
                continue
            unit_c[ln.page].update(seg(w))
            word_c[ln.page][w] += 1
    return unit_c, word_c


def _currier_ab(A, B, seg, uc, ucA, ucB, seed, perms, out_r) -> dict:
    ua, wa = _page_counters(A, seg)
    ub, wb = _page_counters(B, seg)
    pages = [("A", p) for p in ua] + [("B", p) for p in ub]
    unit_pg = {**{("A", p): c for p, c in ua.items()}, **{("B", p): c for p, c in ub.items()}}
    word_pg = {**{("A", p): c for p, c in wa.items()}, **{("B", p): c for p, c in wb.items()}}
    labels = [k[0] for k in pages]
    nA = labels.count("A")

    def pooled(src, idxs):
        c = Counter()
        for i in idxs:
            c.update(src[pages[i]])
        return c

    all_idx = list(range(len(pages)))
    obs_u = S.js_divergence(pooled(unit_pg, [i for i in all_idx if labels[i] == "A"]),
                            pooled(unit_pg, [i for i in all_idx if labels[i] == "B"]))
    obs_w = S.js_divergence(pooled(word_pg, [i for i in all_idx if labels[i] == "A"]),
                            pooled(word_pg, [i for i in all_idx if labels[i] == "B"]))
    rng = random.Random(seed)
    null_u, null_w = [], []
    for _ in range(perms):
        sh = all_idx[:]
        rng.shuffle(sh)
        ia, ib = sh[:nA], sh[nA:]
        null_u.append(S.js_divergence(pooled(unit_pg, ia), pooled(unit_pg, ib)))
        null_w.append(S.js_divergence(pooled(word_pg, ia), pooled(word_pg, ib)))
    pu = (1 + sum(1 for x in null_u if x >= obs_u)) / (1 + perms)
    pw = (1 + sum(1 for x in null_w if x >= obs_w)) / (1 + perms)

    # per-unit comparison
    nA_u, nB_u = sum(ucA.values()), sum(ucB.values())
    rows = []
    for u in sorted(set(ucA) | set(ucB), key=lambda x: -(ucA[x] + ucB[x])):
        fa, fb = (ucA[u] + 0.5) / (nA_u + 0.5), (ucB[u] + 0.5) / (nB_u + 0.5)
        rows.append({"unit": render(u), "count_A": ucA[u], "count_B": ucB[u],
                     "share_A": ucA[u] / nA_u, "share_B": ucB[u] / nB_u, "log2_ratio_B_over_A": math.log2(fb / fa)})
    pd.DataFrame(rows).to_csv(out_r / "currier_ab_units.csv", index=False)

    # per-word comparison (words with >=20 tokens in A+B)
    wca, wcb = Counter(), Counter()
    for c in wa.values():
        wca.update(c)
    for c in wb.values():
        wcb.update(c)
    tA, tB = sum(wca.values()), sum(wcb.values())
    wrows = []
    for w in set(wca) | set(wcb):
        n = wca[w] + wcb[w]
        if n < 20:
            continue
        fa, fb = (wca[w] + 0.5) / (tA + 0.5), (wcb[w] + 0.5) / (tB + 0.5)
        wrows.append({"word": render(w), "count_A": wca[w], "count_B": wcb[w],
                      "per_1000_A": 1000 * wca[w] / tA, "per_1000_B": 1000 * wcb[w] / tB,
                      "log2_ratio_B_over_A": math.log2(fb / fa)})
    wdf = pd.DataFrame(wrows, columns=["word", "count_A", "count_B", "per_1000_A", "per_1000_B",
                                       "log2_ratio_B_over_A"]).sort_values("log2_ratio_B_over_A")
    wdf.to_csv(out_r / "currier_ab_words.csv", index=False)
    return {"unit_jsd": obs_u, "unit_perm_p": pu, "unit_null_mean": float(np.mean(null_u)),
            "word_jsd": obs_w, "word_perm_p": pw, "word_null_mean": float(np.mean(null_w)),
            "n_pages_A": nA, "n_pages_B": len(pages) - nA, "perms": perms,
            "words_df": wdf, "units_df": pd.DataFrame(rows)}


# ------------------------------------------------------------------ Sukhotin

def _sukhotin_all(corpus: Corpus, uncertain: str, seed: int, boot: int, min_count: int = 20) -> pd.DataFrame:
    rows = []
    subsets = {"P": "P", "A": "A", "B": "B"}
    g = groups(corpus, uncertain)
    rng = np.random.default_rng(seed)
    for preset in SEG_PRESETS_FOR_SUKHOTIN:
        seg = Segmenter.preset(preset)
        for sname in subsets:
            lines = g[sname]
            per_page: dict[str, list[tuple]] = defaultdict(list)
            for ln in lines:
                for w in ln.words:
                    if "?" not in w:
                        per_page[ln.page].append(seg(w))
            allseq = [s for p in per_page.values() for s in p]
            freq = Counter(u for s in allseq for u in s)
            syms = sorted(u for u, v in freq.items() if v >= min_count)
            idx = {u: i for i, u in enumerate(syms)}
            n = len(syms)
            page_names = sorted(per_page)
            T = np.zeros((len(page_names), n, n), dtype=np.int64)
            for pi, pn in enumerate(page_names):
                for s in per_page[pn]:
                    for a, b in zip(s, s[1:]):
                        if a in idx and b in idx and a != b:
                            T[pi, idx[a], idx[b]] += 1
                            T[pi, idx[b], idx[a]] += 1
            full = T.sum(axis=0)
            vow = S.sukhotin_matrix(syms, full)
            vowset = set(vow)
            hits = Counter()
            for _ in range(boot):
                w = rng.multinomial(len(page_names), [1.0 / len(page_names)] * len(page_names))
                mb = np.tensordot(w, T, axes=(0, 0))
                hits.update(S.sukhotin_matrix(syms, mb))
            for u in sorted(syms, key=lambda x: -freq[x]):
                rows.append({"segmentation": preset, "subset": sname, "unit": render(u), "count": freq[u],
                             "sukhotin_class": "vowel-like" if u in vowset else "consonant-like",
                             "pick_order": (vow.index(u) + 1) if u in vowset else "",
                             "bootstrap_vowel_fraction": hits[u] / boot})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ replication

def _headline(lines: list[Line], seg: Segmenter, seed: int) -> dict:
    words = readable_words(lines)
    ws = S.word_stats(words, seg, seed)
    seqs = unit_seqs(lines, seg)
    ep = S.entropy_profile(seqs, seed, n_shuffles=3)
    vow, _ = S.sukhotin(seqs, min_count=20)
    return {"n_tokens": ws["n_tokens"], "n_types": ws["n_types"],
            "zipf_ols_slope": ws["zipf_ols_slope_r10_1000"], "zipf_mle_s": ws["zipf_mle_s_r10_1000"],
            "heaps_beta_in_order": ws["heaps_beta_in_order"], "heaps_beta_shuffled": ws["heaps_beta_shuffled"],
            "word_entropy": ws["word_entropy_H1"], "unit_H1": ep["H1"], "unit_h2": ep["h2"], "unit_h3": ep["h3"],
            "alphabet_size_ge20": ep["alphabet_size_ge20"], "sukhotin_vowel_like": " ".join(render(v) for v in vow)}


def _replication(seg: Segmenter, uncertain: str, seed: int, log):
    rows = []
    for fn in REPLICATION_FILES:
        p = transcription_dir() / fn
        if not p.exists():
            log(f"  replication: {fn} missing, skipped")
            continue
        c = parse_file(p)
        if c.alphabet not in EVA_ALPHABETS:
            continue
        for sub, kw in (("P", {}), ("A", {"language": "A"}), ("B", {"language": "B"})):
            lines = lines_for(c, uncertain, generic="P", **kw)
            rows.append({"file": fn, "alphabet": c.alphabet, "subset": sub, **_headline(lines, seg, seed)})
        log(f"  replication: {fn} done")
    return pd.DataFrame(rows) if rows else None


# ------------------------------------------------------------------ markdown

DISCLAIMER = (
    "> **These are descriptive statistics, not decoding.** MS 408 is undeciphered. Nothing below assigns a "
    "meaning, a part of speech or a language to any glyph or word. Frequency, entropy, Zipf/Heaps and "
    "vowel/consonant-style numbers describe one transcription; meaningless text, hand-made gibberish and "
    "certain ciphers can reproduce several of them, and no control corpora have been run yet.")


def _glyph_report(corpus, grp, cat, dig, bg, seg) -> str:
    top = cat[cat["kind"] == "eva"].head(25)[["rank", "glyph", "count", "share", "initial", "medial", "final", "line_initial_n"]]
    rare = cat[cat["kind"] == "rare-code"]
    n_eva = int((cat["kind"] == "eva").sum())
    lines = [
        "# Glyph catalogue (from the transcription)", "", DISCLAIMER, "",
        f"Source: `{Path(corpus.path).name}` (alphabet `{corpus.alphabet}`, IVTFF {corpus.version}). "
        "Counts are over running paragraph text (`P` loci) unless a column says otherwise; "
        "`all_loci` also includes labels, circular and radial text; `labels` is `L` loci only.", "",
        "**This is a catalogue of symbols a *transcriber* used, not of physical glyph forms.** "
        "Whether the page images support the same classes is untested (image stage not done; see "
        "`docs/IMAGE_STAGE.md`).", "",
        f"* distinct EVA symbols: **{n_eva}**; rare/high-ASCII codes (`@nnn;`): **{len(rare)}**",
        f"* total glyph tokens in `P` text: **{int(cat['count'].sum())}**",
        f"* digraph/composite candidates are *flagged* in `digraph_candidates.csv` and "
        f"`top_pmi_bigrams.csv`; merging is decided in `msdecipher.segment` (default preset: `{seg.name}`).", "",
        "## Most frequent EVA symbols (P text)", "", md_table(top), "",
        "Positional columns are shares of occurrences at word start / middle / end (single-glyph "
        "words are excluded from these three).", "",
        "## Digraph / composite candidates", "", md_table(dig), "",
        "`p_next_given_first` = P(second glyph follows | first glyph); `p_prev_given_second` = P(first "
        "glyph precedes | second glyph). Values near 1 mean the parts hardly occur apart, which supports "
        "treating the pair as one unit but does not prove it.", "",
        "## Highest-PMI adjacent pairs (≥30 occurrences)", "", md_table(bg.head(15)), "",
        "Full tables: `glyphs/catalog.csv`, `glyphs/digraph_candidates.csv`, `glyphs/top_pmi_bigrams.csv`.", ""]
    if len(rare):
        lines += ["## Rare / high-ASCII codes", "",
                  md_table(rare.head(15)[["glyph", "count", "count_all_loci", "count_labels"]]), ""]
    return "\n".join(lines)


def _fmt_vowels(suk, seg, subset):
    d = suk[(suk.segmentation == seg) & (suk.subset == subset) & (suk.sukhotin_class == "vowel-like")]
    return ", ".join(f"`{u}`" for u in d.sort_values("pick_order", key=lambda s: s.astype(int))["unit"])


def _stats_report(res, seg, uncertain, seed) -> str:
    corpus = res["corpus"]
    S_ = res["summary"]
    ab = res["currier_ab"]
    key_cols = ["n_tokens", "n_types", "type_token_ratio", "hapax_share_of_types", "top10_token_coverage",
                "mean_word_length_units", "zipf_ols_slope_r10_1000", "zipf_mle_s_r10_1000",
                "heaps_beta_in_order", "heaps_beta_shuffled", "word_entropy_H1", "unit_alphabet_size", "unit_alphabet_size_ge20",
                "unit_H1", "unit_h2", "unit_h3", "unit_h2_mm", "unit_h2_with_word_boundaries",
                "unit_h2_within_word_shuffle"]
    t = S_[key_cols].T.reset_index().rename(columns={"index": "metric"})
    suk = res["sukhotin"]
    cmp_rows = []
    for sname in ("P", "A", "B"):
        for p in SEG_PRESETS_FOR_SUKHOTIN:
            cmp_rows.append({"subset": sname, "segmentation": p, "vowel-like units (pick order)": _fmt_vowels(suk, p, sname)})
    cmp_df = pd.DataFrame(cmp_rows)
    stab = suk[(suk.segmentation == seg.name) & (suk.subset == "P")][["unit", "count", "sukhotin_class", "bootstrap_vowel_fraction"]]
    words_df = ab["words_df"]
    A_top = words_df.sort_values("log2_ratio_B_over_A").head(8)[["word", "count_A", "count_B", "log2_ratio_B_over_A"]]
    B_top = words_df.sort_values("log2_ratio_B_over_A").tail(8)[["word", "count_A", "count_B", "log2_ratio_B_over_A"]]
    out = [
        "# Descriptive statistics report", "", DISCLAIMER, "",
        "## Setup", "",
        f"* transcription: `{Path(corpus.path).name}` (alphabet `{corpus.alphabet}`, IVTFF {corpus.version}); "
        "all numbers regenerate with `python -m msdecipher run-all`",
        "* data: running paragraph text (`P` loci). Labels, circular/radial text, extraneous writing (`Lx`) and "
        "non-existent loci (`!`) are excluded. Tokens containing `?` (unreadable) are dropped from word/unit statistics.",
        "* alternative readings `[a:b]`: first (most likely) option; ligature braces removed; rare `@nnn;` codes are single units.",
        f"* uncertain spaces (`,`): **{'treated as word spaces' if uncertain == 'split' else 'joined'}**; "
        f"the table also shows the opposite choice.",
        f"* unit segmentation: `{seg.name}` = {list(seg.composites)} (all other EVA characters are single units); seed {seed}.",
        "* a 'token' is a blank-delimited chunk of the transcription and is **not** proven to be a word; a 'unit' is not proven to be a letter.", "",
        "## Summary table", "", md_table(t, "{:.4g}"), "",
        "Definitions: **Zipf OLS slope** = slope of log10(freq) vs log10(rank), ranks 10–1000 (negative; quick look only). "
        "**Zipf MLE s** = maximum-likelihood exponent of a rank-truncated Zipf law on the same ranks (positive). "
        "**Heaps β** = exponent of V(n)=K·nᵝ (vocabulary growth) in manuscript order and averaged over random token orders. "
        "**H1** = unit entropy (bits); **h2**/**h3** = conditional entropy of a unit given the previous 1/2 units *inside the same token*; "
        "`_mm` = Miller–Madow bias-corrected; `with_word_boundaries` adds start/end markers; `within_word_shuffle` shuffles units inside each token "
        "(a within-token order control: h2 rises toward H1 when order matters). "
        "`A matched`/`B matched` are the two Currier subsets cut to the same token count. `unit_alphabet_size` counts every distinct unit "
        "including rare `@nnn;` codes; `_ge20` counts units seen at least 20 times.", "",
        "Entropy values are plug-in estimates on a finite sample and are biased low, more so for h3 (large alphabet²) than h2. "
        "They are comparable only between equally sized samples and only under the same segmentation.", "",
        "## Currier A vs B", "",
        f"{ab['n_pages_A']} pages are tagged language A and {ab['n_pages_B']} B in the transcription's `$L` variable. "
        f"Jensen–Shannon divergence between the A and B unit distributions is {ab['unit_jsd']:.4f} bits "
        f"(page-label permutation null mean {ab['unit_null_mean']:.4f}, p = {ab['unit_perm_p']:.3f}, {ab['perms']} permutations); "
        f"between word distributions {ab['word_jsd']:.4f} (null mean {ab['word_null_mean']:.4f}, p = {ab['word_perm_p']:.3f}). "
        "The permutation shuffles A/B labels across pages, so it asks whether A/B differ more than arbitrary page groupings do. "
        "Note that Currier's A/B split was originally made from these same texts, so this is a consistency check, not an independent test.", "",
        "Tokens most over-represented in **A** (log2 ratio B/A most negative; ≥20 tokens total):", "", md_table(A_top), "",
        "Tokens most over-represented in **B**:", "", md_table(B_top), "",
        "Per-unit and per-word tables: `currier_ab_units.csv`, `currier_ab_words.csv`.", "",
        "## Sukhotin vowel/consonant test (run after segmentation)", "",
        "Sukhotin's algorithm labels a unit 'vowel-like' if it tends to sit next to units that are not vowel-like, using adjacent pairs inside tokens. "
        "**It is a distributional proposal, not a finding that these glyphs are vowels.** Units with <20 occurrences are ignored. "
        "The table contrasts segmentations on the same text: with raw EVA, `h` is an artefact of splitting `ch`/`sh`, which is why segmentation comes first.", "",
        md_table(cmp_df), "",
        f"Stability under page bootstrap (200 resamples of pages), default segmentation `{seg.name}`, all `P` text "
        "(fraction of resamples in which the unit is labelled vowel-like; values far from 0 or 1 mean the label is unstable):", "",
        md_table(stab.head(30)), "",
        "## Replication on other transcriptions", "",
    ]
    rep = res.get("replication")
    if rep is not None and len(rep):
        out += [md_table(rep.drop(columns=["alphabet"]), "{:.3f}"), "",
                "An effect seen in only one transcription should be treated as a transcription artefact until shown otherwise.", ""]
    else:
        out += ["_not run or files missing_", ""]
    out += [
        "## Figures", "",
        "* `figures/zipf_words.png` – rank–frequency of tokens (log–log) with the fitted range",
        "* `figures/heaps.png` – vocabulary growth, manuscript order vs shuffled",
        "* `figures/unit_frequencies_ab.png` – unit shares, Currier A vs B",
        "* `figures/positional_heatmap.png` – where each unit occurs inside tokens and lines",
        "* `figures/entropies.png` – H1, h2, h3 and the within-token-shuffle control",
        "", "## Not done / limits", "",
        "* No control corpora (Latin, Italian, Hebrew, shuffled text, cipher or gibberish generators) have been run, "
        "so none of these numbers can yet say whether MS 408 resembles a language, a cipher or neither.",
        "* Statistics are pooled over pages that are not independent samples; confidence intervals over quires are not yet computed (only the page bootstrap above).",
        "* Only EVA-based transcriptions were analysed (`GC2a` uses another alphabet and is parse-tested only).",
        "* No word-class, morphology or semantic analysis is attempted or implied.", ""]
    return "\n".join(out)
