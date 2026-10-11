"""Stage 6 evaluation: how well does a position-by-position word grammar explain the vocabulary,
fitted on some blocks of text and tested on others? Identical for MS 408 and every control.

For each corpus (a list of unit tuples, one per token, plus a block id per token = folio for MS 408,
500-token chunk for a control) the function :func:`structure_metrics` runs ``n_folds``-fold
cross-validation by block and reports, as means over folds:

* held-out bits per word (token level: tokens weighted by frequency, grammar fitted with token weights;
  type level: each distinct held-out word once, grammar fitted on distinct training types) for
  (i) the slot grammar, (ii) a within-word unit bigram, (iii) a unit unigram, (iv) a token lexicon
  with escape to the bigram (token level only), (v) the prefix-core-suffix model (type level);
* the same slot-grammar number after shuffling units *inside every word* (the null: same units,
  same word lengths, no positional structure);
* coverage: share of held-out tokens / types that the pruned slot grammar can generate at all, versus the
  share whose unit bigrams were all seen in training (the baseline "grammar"), and the share of
  held-out *new* types (not in the training vocabulary) that each can generate -- the generalisation
  that a pure lexicon cannot give;
* description length (MDL): training data bits + 0.5 log2(N) bits per used parameter, per word, on the
  full corpus, for slot / bigram / unigram and for the shuffled null.

Words longer than ``K`` units are excluded everywhere (their share is reported).
Nothing here assigns meaning to a slot or a word; slots are numbered positions only.
"""
from __future__ import annotations

import math
import random
from collections import Counter
from typing import Sequence

import numpy as np

from .slot_grammar import (AffixModel, SlotGrammar, UnitNgram, shuffle_within_words, word_counts)

LAMBDAS = (1e-4, 1e-3, 1e-2, 5e-2)
ALPHAS = (0.01, 0.05, 0.2, 1.0)


def _tune(model_fit, scorer, grid, train_counts, val_words):
    """Pick the smoothing value with the best validation bits."""
    best = None
    for g in grid:
        s = float(np.mean(scorer(g)))
        if best is None or s > best[0]:
            best = (s, g)
    return best[1]


def _split_counts(tokens: Sequence[tuple], blocks: Sequence, train_blocks: set):
    tr = [t for t, b in zip(tokens, blocks) if b in train_blocks]
    te = [t for t, b in zip(tokens, blocks) if b not in train_blocks]
    return tr, te


def _bits(lp: np.ndarray) -> float:
    ok = np.isfinite(lp)
    return float(-lp[ok].mean()) if ok.any() else float("nan")


def _fit_models(train: list[tuple], K: int, level: str, iters: int, seed: int, restarts: int = 1):
    counts = word_counts(train)
    wts = dict(counts) if level == "tok" else {w: 1.0 for w in counts}
    slot = SlotGrammar(K=K).fit(wts, iters=iters, restarts=restarts, seed=seed)
    big = UnitNgram(1).fit(wts)
    uni = UnitNgram(0).fit(wts)
    return counts, wts, slot, big, uni


def _tune_smoothing(tokens, blocks, K, level, iters, seed):
    """lambda (slot) and alpha (bigram, unigram) chosen on a validation split of the first training fold."""
    bl = sorted(set(blocks), key=str)
    rng = random.Random(seed + 99)
    rng.shuffle(bl)
    val = set(bl[: max(1, len(bl) // 6)])
    tr = [t for t, b in zip(tokens, blocks) if b not in val]
    va = [t for t, b in zip(tokens, blocks) if b in val]
    counts, wts, slot, big, uni = _fit_models(tr, K, level, iters, seed)
    ev = list(counts_unique(va)) if level == "type" else va
    lam = _tune(None, lambda g: slot.logprob2(ev, g), LAMBDAS, None, None)
    a1 = _tune(None, lambda g: big.logprob2(ev, g), ALPHAS, None, None)
    a0 = _tune(None, lambda g: uni.logprob2(ev, g), ALPHAS, None, None)
    return lam, a1, a0


def counts_unique(words):
    return list(dict.fromkeys(words))


def _mdl(slot: SlotGrammar, big: UnitNgram, uni: UnitNgram, wts: dict) -> dict:
    """Two-part description length per word (bits): ML data cost + 0.5 log2(N) per used parameter."""
    N = float(sum(wts.values()))
    pen = 0.5 * math.log2(max(N, 2))
    ws = list(wts)
    w = np.array([wts[x] for x in ws], dtype=float)
    ll_slot = -slot.loglik_train
    ll_big = float((w * -big.logprob2(ws, 1e-9)).sum())
    ll_uni = float((w * -uni.logprob2(ws, 1e-9)).sum())
    return {"slot": (ll_slot + pen * slot.n_params()) / N, "bigram": (ll_big + pen * big.n_params()) / N,
            "unigram": (ll_uni + pen * uni.n_params()) / N,
            "slot_data": ll_slot / N, "bigram_data": ll_big / N, "unigram_data": ll_uni / N,
            "slot_params": slot.n_params(), "bigram_params": big.n_params(), "unigram_params": uni.n_params()}


def structure_metrics(tokens: Sequence[tuple], blocks: Sequence, K: int = 12, n_folds: int = 4, seed: int = 1,
                      iters: int = 25, null: bool = True, affix: bool = True, return_models: bool = False) -> dict:
    """Cross-validated word-structure metrics (see module docstring)."""
    all_n = len(tokens)
    keep = [i for i, t in enumerate(tokens) if 1 <= len(t) <= K]
    out: dict = {"share_over_K": 1 - len(keep) / max(all_n, 1), "n_tokens_used": len(keep)}
    tokens = [tuple(tokens[i]) for i in keep]
    blocks = [blocks[i] for i in keep]
    rng = random.Random(seed)
    ub = sorted(set(blocks), key=str)
    rng.shuffle(ub)
    fold_of = {b: i % n_folds for i, b in enumerate(ub)}

    variants = [("", tokens)]
    if null:
        variants.append(("null_", shuffle_within_words(tokens, random.Random(seed + 5))))
    acc: dict[str, list[float]] = {}

    def add(k, v):
        acc.setdefault(k, []).append(v)

    tune = {}
    for pref, toks in variants:
        for level in ("tok", "type"):
            tune[(pref, level)] = _tune_smoothing(toks, blocks, K, level, iters, seed)

    models_full = {}
    for f in range(n_folds):
        train_blocks = {b for b in ub if fold_of[b] != f}
        for pref, toks in variants:
            tr, te = _split_counts(toks, blocks, train_blocks)
            if not tr or not te:
                continue
            te_types = counts_unique(te)
            tr_types = set(tr)
            new_types = [w for w in te_types if w not in tr_types]
            for level in ("tok", "type"):
                lam, a1, a0 = tune[(pref, level)]
                counts, wts, slot, big, uni = _fit_models(tr, K, level, iters, seed + f)
                ev = te if level == "tok" else te_types
                add(f"{pref}bits_{level}_slot", _bits(slot.logprob2(ev, lam)))
                add(f"{pref}bits_{level}_bigram", _bits(big.logprob2(ev, a1)))
                add(f"{pref}bits_{level}_unigram", _bits(uni.logprob2(ev, a0)))
                if level == "tok":
                    # token lexicon with escape (PPM method C) to the bigram model
                    N = sum(counts.values())
                    T = len(counts)
                    lp_big = big.logprob2(te, a1)
                    lex = np.array([math.log2(counts[w] / (N + T)) if w in counts else math.log2(T / (N + T)) + lp for w, lp in zip(te, lp_big)])
                    add(f"{pref}bits_tok_lexicon", _bits(lex))
                    add(f"{pref}cov_slot_tok", float(slot.covered(te).mean()))
                    add(f"{pref}cov_bigram_tok", float(big.seen_bigrams_cover(te).mean()))
                else:
                    add(f"{pref}cov_slot_type", float(slot.covered(te_types).mean()))
                    add(f"{pref}cov_bigram_type", float(big.seen_bigrams_cover(te_types).mean()))
                    add(f"{pref}oov_type_share", len(new_types) / max(len(te_types), 1))
                    if new_types:
                        add(f"{pref}bits_newtype_slot", _bits(slot.logprob2(new_types, lam)))
                        add(f"{pref}bits_newtype_bigram", _bits(big.logprob2(new_types, a1)))
                        add(f"{pref}bits_newtype_unigram", _bits(uni.logprob2(new_types, a0)))
                        add(f"{pref}gen_slot_newtype", float(slot.covered(new_types).mean()))
                        add(f"{pref}gen_bigram_newtype", float(big.seen_bigrams_cover(new_types).mean()))
                    if affix and not pref:
                        am = AffixModel().fit(wts)
                        add("bits_type_affix", _bits(am.logprob2(te_types)))
                        if new_types:
                            add("bits_newtype_affix", _bits(am.logprob2(new_types)))
    for k, v in acc.items():
        out[k] = float(np.mean(v))
        out[k + "__fold_sd"] = float(np.std(v, ddof=1)) if len(v) > 1 else float("nan")
    out["n_folds"] = n_folds

    # full-data fits: MDL and descriptive statistics
    for pref, toks in variants:
        for level in ("tok", "type"):
            counts, wts, slot, big, uni = _fit_models(toks, K, level, iters, seed, restarts=2)
            md = _mdl(slot, big, uni, wts)
            for k in ("slot", "bigram", "unigram"):
                out[f"{pref}mdl_{level}_{k}"] = md[k]
            out[f"{pref}mdl_{level}_slot_params"] = md["slot_params"]
            out[f"{pref}mdl_{level}_bigram_params"] = md["bigram_params"]
            if not pref:
                models_full[level] = (slot, big, uni, counts)
                if level == "type":
                    out["slot_mean_emit_prob"] = float(np.mean(slot.e))
                    out["slot_n_active"] = int((slot.e >= 0.05).sum())
                    out["slot_mean_unit_entropy_bits"] = float(np.mean([-(slot.P[k] * np.log2(slot.P[k] + 1e-12)).sum() for k in range(K)]))
                    if affix:
                        am = AffixModel().fit(wts)
                        out.update({f"affix_{k}": v for k, v in am.stats(counts).items()})
                        models_full["affix"] = am
    derived(out)
    if return_models:
        out["_models"] = models_full
    return out


def derived(o: dict) -> None:
    """Contrasts between the cross-validated quantities."""
    for lv in ("tok", "type"):
        s, b, u = o.get(f"bits_{lv}_slot"), o.get(f"bits_{lv}_bigram"), o.get(f"bits_{lv}_unigram")
        if s is not None:
            o[f"slot_minus_bigram_{lv}"] = s - b
            o[f"slot_gain_frac_{lv}"] = (u - s) / (u - b) if u != b else float("nan")
            o[f"slot_gain_vs_unigram_{lv}"] = u - s
        ns = o.get(f"null_bits_{lv}_slot")
        if ns is not None and s is not None:
            o[f"slot_null_gap_{lv}"] = ns - s
        nb = o.get(f"null_bits_{lv}_bigram")
        if nb is not None and b is not None:
            o[f"bigram_null_gap_{lv}"] = nb - b
    if "cov_slot_type" in o:
        o["cov_slot_minus_bigram_type"] = o["cov_slot_type"] - o["cov_bigram_type"]
    if "gen_slot_newtype" in o:
        o["gen_slot_minus_bigram_newtype"] = o["gen_slot_newtype"] - o["gen_bigram_newtype"]
    if "bits_newtype_slot" in o:
        o["newtype_slot_minus_bigram"] = o["bits_newtype_slot"] - o["bits_newtype_bigram"]
    if "bits_type_affix" in o:
        o["affix_minus_bigram_type"] = o["bits_type_affix"] - o["bits_type_bigram"]
    for lv in ("tok", "type"):
        if f"mdl_{lv}_slot" in o:
            o[f"mdl_{lv}_slot_minus_bigram"] = o[f"mdl_{lv}_slot"] - o[f"mdl_{lv}_bigram"]
            if f"null_mdl_{lv}_slot" in o:
                o[f"mdl_{lv}_slot_null_gap"] = o[f"null_mdl_{lv}_slot"] - o[f"mdl_{lv}_slot"]


# metric -> (label, group); used for tables/verdicts
STRUCT_INFO: dict[str, tuple[str, str]] = {
    "bits_type_slot": ("held-out bits/type, slot grammar", "slot grammar"),
    "bits_type_bigram": ("held-out bits/type, unit bigram", "slot grammar"),
    "bits_type_unigram": ("held-out bits/type, unit unigram", "slot grammar"),
    "slot_minus_bigram_type": ("slot − bigram bits/type (negative = slot better)", "slot grammar"),
    "slot_gain_frac_type": ("share of unigram→bigram gain reached by slots (type)", "slot grammar"),
    "slot_null_gap_type": ("shuffled-null − real, slot bits/type", "slot grammar"),
    "slot_gain_frac_tok": ("share of unigram→bigram gain reached by slots (token)", "slot grammar"),
    "bits_newtype_slot": ("bits per NEW type, slot grammar", "generalisation"),
    "newtype_slot_minus_bigram": ("slot − bigram bits per new type", "generalisation"),
    "bits_tok_slot": ("held-out bits/token, slot grammar", "slot grammar"),
    "slot_minus_bigram_tok": ("slot − bigram bits/token", "slot grammar"),
    "slot_null_gap_tok": ("shuffled-null − real, slot bits/token", "slot grammar"),
    "cov_slot_type": ("held-out type coverage, slot grammar", "coverage"),
    "cov_bigram_type": ("held-out type coverage, seen-bigram grammar", "coverage"),
    "cov_slot_minus_bigram_type": ("slot − bigram type coverage", "coverage"),
    "cov_slot_tok": ("held-out token coverage, slot grammar", "coverage"),
    "oov_type_share": ("held-out types unseen in training", "coverage"),
    "gen_slot_newtype": ("new types generated by slot grammar", "coverage"),
    "gen_slot_minus_bigram_newtype": ("new types: slot − bigram coverage", "coverage"),
    "mdl_type_slot": ("MDL bits/type, slot grammar", "MDL"),
    "mdl_type_slot_minus_bigram": ("MDL slot − bigram, bits/type", "MDL"),
    "mdl_type_slot_null_gap": ("MDL shuffled-null − real, slot, bits/type", "MDL"),
    "mdl_tok_slot_minus_bigram": ("MDL slot − bigram, bits/token", "MDL"),
    "affix_minus_bigram_type": ("prefix-core-suffix − bigram bits/type", "affix"),
    "affix_prefix_type_share": ("types with a learned prefix", "affix"),
    "affix_suffix_type_share": ("types with a learned suffix", "affix"),
    "affix_cores_per_type": ("distinct cores per type", "affix"),
    "slot_mean_unit_entropy_bits": ("mean per-slot unit entropy (bits)", "slot grammar"),
    "slot_n_active": ("slots emitting with p ≥ 0.05", "slot grammar"),
    "share_over_K": ("tokens longer than K units (excluded)", "data"),
}
