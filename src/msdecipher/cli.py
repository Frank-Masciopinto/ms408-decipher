"""Command line: ``python -m msdecipher <command>``."""
from __future__ import annotations

import argparse
import sys


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", help="transcription file (default data/transcriptions/ZL3b-n.txt)")
    p.add_argument("--units", default=None,
                   help="unit segmentation: preset (raw, basic, collapsed, extended) or comma list "
                        "such as ch,sh,cth (default: collapsed)")
    p.add_argument("--uncertain-spaces", choices=["split", "join"], default="split",
                   help="treat ',' as a word space (split, default) or ignore it (join)")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m msdecipher",
        description="Descriptive analysis of MS 408 (Voynich) transcriptions. MS 408 is undeciphered; "
                    "nothing here decodes it.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fetch", help="download voynich.nu IVTFF files into data/transcriptions/ + SHA256 manifest")
    sub.add_parser("verify", help="check downloaded files against data/transcriptions/MANIFEST.json")

    p = sub.add_parser("parse", help="parse a transcription and print an inventory")
    p.add_argument("--file")

    p = sub.add_parser("catalog", help="glyph catalogue -> glyphs/catalog.csv + glyphs/REPORT.md")
    _add_common(p)

    p = sub.add_parser("stats", help="all statistics -> reports/ (same as run-all)")
    _add_common(p)
    p.add_argument("--no-replicate", action="store_true")
    p.add_argument("--no-plots", action="store_true")
    p.add_argument("--seed", type=int, default=1)

    p = sub.add_parser("run-all", help="catalogue + statistics + reports (fetching first with --fetch)")
    _add_common(p)
    p.add_argument("--fetch", action="store_true", help="download the data first if missing")
    p.add_argument("--no-replicate", action="store_true")
    p.add_argument("--no-plots", action="store_true")
    p.add_argument("--seed", type=int, default=1)

    p = sub.add_parser("images", help="render PDF pages to data/images/ (best effort; PDF page numbers)")
    p.add_argument("--dpi", type=int, default=100)
    p.add_argument("--first", type=int)
    p.add_argument("--last", type=int)
    p.add_argument("--native", action="store_true",
                   help="instead extract the embedded scans at native resolution (data/images/native/*.jpg)")

    sub.add_parser("page-index", help="PDF page -> folio index (pdftotext captions) -> data/page_index.csv")

    p = sub.add_parser("segment-glyphs",
                       help="image glyph stage: lines/words/glyph candidates, clustering, QA report (best effort)")
    p.add_argument("--pages", help="comma list of PDF page numbers (default: text-dominant pages of the index)")
    p.add_argument("--mode", choices=["text", "exact"], default="text",
                   help="page selection when --pages is absent: text = text-only/stars pages (default), "
                        "exact = every 1:1 folio page")
    p.add_argument("--units", default="collapsed", help="EVA unit segmentation used to label crops (default: collapsed)")
    p.add_argument("--no-report", action="store_true", help="only segment; skip clustering/QA report")
    p.add_argument("--seed", type=int, default=1)

    p = sub.add_parser("controls-fetch", help="download public-domain control texts into data/controls/ (git-ignored) + manifest")
    p.add_argument("--only", nargs="+", metavar="ID", help="fetch only these control ids (the manifest keeps the other entries)")
    sub.add_parser("controls-verify", help="check data/controls/ against its MANIFEST.json")
    p = sub.add_parser("controls-run", help="run the stats suite on MS 408 and all controls -> reports/controls/")
    p.add_argument("--tokens", type=int, default=35000, help="tokens per control (default 35000)")
    p.add_argument("--seeds", type=int, default=3, help="seeds for stochastic controls (default 3)")
    p.add_argument("--file", help="MS 408 transcription (default data/transcriptions/ZL3b-n.txt)")
    p.add_argument("--no-plots", action="store_true")
    p.add_argument("--boot", type=int, default=100, help="MS 408 bootstrap resamples per scheme (page / 8-page block; default 100, 0 = skip all MS 408 CIs); the delete-one-page/block jackknives always run when > 0")
    p.add_argument("--control-jack", type=int, default=20, help="delete-one-group jackknife groups per control row (default 20, 0 = skip)")
    p.add_argument("--workers", type=int, default=None, help="parallel workers (default: all cores up to 8)")

    p = sub.add_parser("word-structure", help="Stage 6+7: slot grammar / affixes / behavioural clusters on MS 408 and all controls -> reports/word_structure/")
    p.add_argument("--k", type=int, default=12, help="number of slots (default 12)")
    p.add_argument("--no-jackknife", action="store_true", help="skip the MS 408 delete-one-block jackknife (CIs)")
    p.add_argument("--reuse", action="store_true", help="re-use comparison.csv / jackknife replicates already in reports/word_structure (re-do verdicts, report, plots only)")
    p.add_argument("--tokens", type=int, default=35000)
    p.add_argument("--file", help="MS 408 transcription (default data/transcriptions/ZL3b-n.txt)")
    p.add_argument("--workers", type=int, default=None)
    p.add_argument("--no-plots", action="store_true")
    p.add_argument("--no-sweep", action="store_true", help="skip the slot-count sweep over controls")

    p = sub.add_parser("mechanisms-run", help="candidate generating mechanisms (Naibbe, self-citation, Zattera/Stolfi grammars, slot-conditioned bigram) through the full metric suite -> reports/mechanisms/")
    p.add_argument("--seeds", type=int, default=5, help="seeds (runs) per mechanism variant")
    p.add_argument("--tokens", type=int, default=35000)
    p.add_argument("--no-sweep", action="store_true", help="skip the self-citation parameter search (re-use selfcitation_best_params.json if present)")
    p.add_argument("--reuse", action="store_true", help="re-use runs.csv / sweep tables already in reports/mechanisms (redo verdicts, grammar comparison, report only)")
    p.add_argument("--file", help="MS 408 transcription")
    p.add_argument("--workers", type=int, default=None)
    p.add_argument("--no-plots", action="store_true")

    p = sub.add_parser("hybrid-run", help="hybrid generators (cipher-like plaintext dependence + copy-and-modify reuse): fit on training folios, held-out full-suite test, penalised comparison -> reports/mechanisms/hybrid/")
    p.add_argument("--runs", type=int, default=5, help="fresh-seed runs per model per fold")
    p.add_argument("--reuse", action="store_true", help="rebuild the report from the CSVs already present")
    p.add_argument("--file", help="MS 408 transcription")
    p.add_argument("--workers", type=int, default=None)

    p = sub.add_parser("hybrid-topics", help="plaintext-signal test: section vocabulary of MS 408 vs topic-driven hybrids vs pure generators -> reports/mechanisms/hybrid/topics/")
    p.add_argument("--perms", type=int, default=1000)
    p.add_argument("--seeds", type=int, default=10)
    p.add_argument("--file", help="MS 408 transcription")
    p.add_argument("--workers", type=int, default=None)

    return ap


def _cmd_mechanisms(a) -> int:
    from .mechanisms_run import run_mechanisms
    res = run_mechanisms(n_tokens=a.tokens, seeds=a.seeds, workers=a.workers, sweep=not a.no_sweep, reuse=a.reuse,
                         make_plots=not a.no_plots, main_file=a.file)
    print("report:", res["out"] / "REPORT.md")
    return 0


def _cmd_hybrid(a) -> int:
    from .mech_hybrid_run import run_hybrid
    res = run_hybrid(n_runs=a.runs, workers=a.workers, reuse=a.reuse, main_file=a.file)
    print("report:", res["out"] / "REPORT.md")
    return 0


def _cmd_hybrid_topics(a) -> int:
    from .mech_hybrid_topics import run_topics
    res = run_topics(n_perm=a.perms, n_seeds=a.seeds, workers=a.workers, main_file=a.file)
    print("report:", res["out"] / "REPORT.md")
    return 0


def _cmd_fetch(a) -> int:
    from .fetch import fetch_all
    m = fetch_all()
    for e in m["files"]:
        print(f"{e['file']:16s} {e['bytes']:>8d} B  sha256:{e['sha256'][:16]}…")
    print("manifest written; downloaded files are git-ignored (no open licence stated).")
    return 0


def _cmd_verify(a) -> int:
    from .fetch import verify
    res = verify()
    bad = 0
    for f, st in res:
        print(f"{f:16s} {st}")
        bad += st != "ok"
    if not res:
        print("no manifest entries")
        return 1
    return 1 if bad else 0


def _cmd_parse(a) -> int:
    from .analysis import load_corpus
    c = load_corpus(a.file)
    print(f"{c.path}: alphabet={c.alphabet} IVTFF {c.version} mode={c.mode}")
    print(f"pages={len(c.pages)} loci={len(c.loci)} types={dict(c.locus_type_counts())}")
    toks = sum(len(l.tokens) for l in c.loci)
    print(f"tokens={toks} warnings={sum(len(l.warnings) for l in c.loci)}")
    print("uncertain-space tokens=%d, alternative-reading tokens=%d, ligature tokens=%d, unreadable tokens=%d, rare-glyph tokens=%d" % (
        sum(1 for l in c.loci for t in l.tokens if t.space_after == ","),
        sum(1 for l in c.loci for t in l.tokens if t.alternatives),
        sum(1 for l in c.loci for t in l.tokens if t.ligature),
        sum(1 for l in c.loci for t in l.tokens if t.unreadable),
        sum(1 for l in c.loci for t in l.tokens if t.has_rare)))
    return 0


def _cmd_catalog(a) -> int:
    from .analysis import catalog_only
    cat, dig, bg = catalog_only(a.file, units=a.units, uncertain=a.uncertain_spaces)
    print(cat.head(20).to_string(index=False))
    print("wrote glyphs/catalog.csv, digraph_candidates.csv, top_pmi_bigrams.csv, REPORT.md")
    return 0


def _cmd_run(a) -> int:
    from .analysis import run_all
    if getattr(a, "fetch", False):
        from .fetch import verify
        from .fetch import fetch_all
        if any(st == "missing" for _, st in verify()) or not verify():
            fetch_all()
    run_all(a.file, units=a.units, uncertain=a.uncertain_spaces, seed=a.seed,
            replicate=not a.no_replicate, make_plots=not a.no_plots)
    return 0


def _cmd_images(a) -> int:
    if a.native:
        from .images import extract_native
        out = extract_native(first=a.first, last=a.last)
        print(f"{len(out)} native-resolution scans in data/images/native/ (git-ignored)")
        return 0
    from .images import extract_pages
    out = extract_pages(dpi=a.dpi, first=a.first, last=a.last)
    print(f"wrote {len(out)} page images (PDF page numbers, not folio ids) to data/images/ (git-ignored)")
    print("NOTE: PDF page -> folio index is not built; glyph segmentation is not implemented.")
    return 0


def _cmd_page_index(a) -> int:
    from .pageindex import build_index, summarize, index_path
    rows = build_index()
    print(f"wrote {index_path()} ({len(rows)} PDF pages): {summarize(rows)}")
    return 0


def _cmd_segment(a) -> int:
    from .image_report import run_image_stage
    pages = [int(x) for x in a.pages.split(",")] if a.pages else None
    run_image_stage(pages=pages, mode=a.mode, units=a.units, report=not a.no_report, seed=a.seed)
    return 0


def _cmd_controls_fetch(a) -> int:
    from .controls_fetch import fetch_all
    for e in fetch_all(only=a.only)["files"]:
        print(f"{e['id']:16s} {e['bytes']:>9d} B  sha256:{e['sha256'][:16]}…")
    return 0


def _cmd_controls_verify(a) -> int:
    from .controls_fetch import verify
    res = verify()
    for f, st in res:
        print(f"{f:34s} {st}")
    return 1 if (not res or any(st != "ok" for _, st in res)) else 0


def _cmd_controls_run(a) -> int:
    from .controls_run import run_controls
    run_controls(n_tokens=a.tokens, seeds=a.seeds, main_file=a.file, make_plots=not a.no_plots,
                 boot=a.boot, control_jack=a.control_jack, workers=a.workers)
    return 0


def _cmd_word_structure(a) -> int:
    from .word_structure_run import run_word_structure
    run_word_structure(n_tokens=a.tokens, main_file=a.file, K=a.k, jackknife=not a.no_jackknife, workers=a.workers, make_plots=not a.no_plots,
                       do_sweep=not a.no_sweep, reuse=a.reuse)
    return 0


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    try:
        return {"fetch": _cmd_fetch, "verify": _cmd_verify, "parse": _cmd_parse, "catalog": _cmd_catalog,
                "stats": _cmd_run, "run-all": _cmd_run, "images": _cmd_images,
                "segment-glyphs": _cmd_segment, "page-index": _cmd_page_index,
                "controls-fetch": _cmd_controls_fetch, "controls-verify": _cmd_controls_verify,
                "controls-run": _cmd_controls_run, "word-structure": _cmd_word_structure,
                "mechanisms-run": _cmd_mechanisms, "hybrid-run": _cmd_hybrid,
                "hybrid-topics": _cmd_hybrid_topics}[a.cmd](a)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
