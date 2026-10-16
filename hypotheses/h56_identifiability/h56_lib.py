"""h56: identifiability of a semantic layer after the copying routine (PREREG.md).

No translation is fit. Stage 7 stops when no grounded association survives.
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from msdecipher.ivtff import parse_file, words_of  # noqa: E402
from msdecipher.segment import PRESETS, Segmenter  # noqa: E402

SEG = Segmenter(PRESETS["collapsed"], name="collapsed")
HANDS = ("1A", "2B", "3B")
TAGS = ("jars", "roots", "nymphs", "stars")
SPECIAL = {"d", "s", "p", "t", "k", "f"}
SEED = 56
N_PERM = 2000


def lev(a: str, b: str) -> int:
    """Character Levenshtein distance, capped at 2."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return 2
    if la > lb:
        a, b = b, a
        la, lb = lb, la
    if la == lb:
        diff = 0
        for x, y in zip(a, b):
            if x != y:
                diff += 1
                if diff > 1:
                    return 2
        return diff
    i = j = 0
    used = False
    while i < la and j < lb:
        if a[i] == b[j]:
            i += 1
            j += 1
        elif used:
            return 2
        else:
            used = True
            j += 1
    return 1


def holm(pvals: list[float]) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    running = 0.0
    for i, k in enumerate(order):
        running = max(running, (m - i) * float(p[k]))
        adj[k] = min(1.0, running)
    return adj


def onset_unit(word: str) -> str:
    units = list(SEG(word))
    return units[0] if units else ""


def substitute_one(word: str, rng: np.random.Generator) -> str:
    alphabet = ["a", "b", "c", "d", "e", "f"]
    chars = list(word)
    i = int(rng.integers(0, len(chars)))
    choices = [c for c in alphabet if c != chars[i]]
    chars[i] = choices[int(rng.integers(0, len(choices)))]
    return "".join(chars)


def load_quire_table() -> pd.DataFrame:
    q = pd.read_csv(ROOT / "data" / "quires.csv", dtype=str).set_index("page")
    return q


def hand_of(page: str, quires: pd.DataFrame) -> str:
    if page not in quires.index:
        return "?"
    return f"{quires.at[page, 'lfd_hand']}{quires.at[page, 'currier_language']}"


def quire_of(page: str, quires: pd.DataFrame) -> str:
    if page not in quires.index:
        return "?"
    return str(quires.at[page, "quire"])


def token_text(token, reading: str) -> str:
    text = token.text
    if reading == "alternate" and token.alternatives and len(token.alternatives[0]) >= 2:
        old, new = token.alternatives[0][0], token.alternatives[0][1]
        if old and old in text:
            text = text.replace(old, new, 1)
    return text


def iter_lines(path: Path, reading: str, quires: pd.DataFrame, generic: str) -> list[dict]:
    corpus = parse_file(path)
    rows = []
    for locus in corpus.select(generic=generic):
        if reading == "joined":
            words = [w for w in words_of(locus, "join") if w and "?" not in w]
        else:
            words = []
            for token in locus.tokens:
                if not token.text or "?" in token.text:
                    continue
                words.append(token_text(token, reading))
            words = [w for w in words if w]
        if not words:
            continue
        folio = locus.folio
        rows.append({
            "folio": folio,
            "quire": quire_of(folio, quires),
            "hand": hand_of(folio, quires),
            "words": words,
            "num": locus.num,
        })
    return rows


def folio_order(lines: list[dict]) -> list[str]:
    seen = []
    for line in lines:
        if line["folio"] not in seen:
            seen.append(line["folio"])
    return seen


def bigram_gain(lines: list[dict]) -> float:
    order = folio_order(lines)
    train_folios = set(order[0::2])
    test_folios = set(order[1::2])
    train_tokens = [w for line in lines if line["folio"] in train_folios for w in line["words"]]
    uni = Counter(train_tokens)
    if not uni:
        return float("nan")
    vocab_n = len(uni)
    total_n = sum(uni.values())
    bi = Counter()
    prev_n = Counter()
    by_folio: dict[str, list[str]] = defaultdict(list)
    for line in lines:
        by_folio[line["folio"]].extend(line["words"])
    for folio in train_folios:
        toks = by_folio[folio]
        for a, b in zip(toks, toks[1:]):
            bi[(a, b)] += 1
            prev_n[a] += 1
    num = 0.0
    count = 0
    for folio in test_folios:
        toks = by_folio[folio]
        for prev, word in zip(toks, toks[1:]):
            p_uni = (uni[word] + 0.5) / (total_n + 0.5 * vocab_n)
            p_bi = (bi[(prev, word)] + 0.5) / (prev_n[prev] + 0.5 * vocab_n)
            num += math.log2(p_bi) - math.log2(p_uni)
            count += 1
    return num / count if count else float("nan")


def edit_rate(lines: list[dict]) -> float:
    hits = 0
    total = 0
    by_folio: dict[str, list[str]] = defaultdict(list)
    for line in lines:
        by_folio[line["folio"]].extend(line["words"])
    for toks in by_folio.values():
        for a, b in zip(toks, toks[1:]):
            total += 1
            if lev(a, b) == 1:
                hits += 1
    return hits / total if total else float("nan")


def onset_excess(lines: list[dict]) -> float:
    init = mid = 0
    init_n = mid_n = 0
    for line in lines:
        for i, word in enumerate(line["words"]):
            flag = onset_unit(word) in SPECIAL
            if i == 0:
                init += int(flag)
                init_n += 1
            else:
                mid += int(flag)
                mid_n += 1
    if not init_n or not mid_n:
        return float("nan")
    return init / init_n - mid / mid_n


def stage1(quires: pd.DataFrame) -> dict:
    readings = {
        "primary": (ROOT / "data" / "transcriptions" / "ZL3b-n.txt", "primary"),
        "alternate": (ROOT / "data" / "transcriptions" / "ZL3b-n.txt", "alternate"),
        "joined": (ROOT / "data" / "transcriptions" / "ZL3b-n.txt", "joined"),
        "it2a": (ROOT / "data" / "transcriptions" / "IT2a-n.txt", "primary"),
    }
    out = {}
    signs_ok = True
    for name, (path, reading) in readings.items():
        lines = [ln for ln in iter_lines(path, reading, quires, "P") if ln["hand"] in HANDS]
        by_hand = {h: [ln for ln in lines if ln["hand"] == h] for h in HANDS}
        out[name] = {}
        for hand in HANDS:
            stats_h = {
                "G": bigram_gain(by_hand[hand]),
                "E": edit_rate(by_hand[hand]),
                "O": onset_excess(by_hand[hand]),
            }
            ok = stats_h["G"] < 0 and stats_h["E"] > 0.03 and stats_h["O"] > 0
            stats_h["pass"] = bool(ok)
            signs_ok = signs_ok and ok
            out[name][hand] = stats_h
    corpus = parse_file(ROOT / "data" / "transcriptions" / "ZL3b-n.txt")
    n = alt = 0
    for locus in corpus.select(generic="P"):
        for token in locus.tokens:
            if not token.text:
                continue
            n += 1
            if token.alternatives:
                alt += 1
    out["alt_fraction"] = alt / n if n else float("nan")
    out["n_paragraph_tokens"] = n
    out["U1"] = bool(signs_ok)
    return out


def smooth(counts: Counter, word: str, vocab: set[str], total: int) -> float:
    support = len(vocab) + 1
    key = word if word in vocab else "OTHER"
    return (counts[key] + 0.5) / (total + 0.5 * support)


def neighborhoods(counts: Counter) -> dict[str, list[str]]:
    types = [w for w, c in counts.items() if c >= 3]
    by_len: dict[int, list[str]] = defaultdict(list)
    for word in types:
        by_len[len(word)].append(word)
    adj = {w: [] for w in types}
    for length, words in by_len.items():
        for i, left in enumerate(words):
            for right in words[i + 1:]:
                if lev(left, right) == 1:
                    adj[left].append(right)
                    adj[right].append(left)
        for right in by_len.get(length + 1, []):
            for left in words:
                if lev(left, right) == 1:
                    adj[left].append(right)
                    adj[right].append(left)
    return adj


def _local_prob(prev: str | None, word: str, hand_counts: Counter, vocab: set[str], total: int, neigh: dict[str, list[str]]) -> float:
    weights = []
    dists = []
    if prev in vocab:
        weights.append(0.5)
        dists.append({prev: 1.0})
    neighbors = [w for w in neigh.get(prev or "", []) if w in vocab]
    if neighbors:
        weights.append(0.5)
        dists.append({w: 1.0 / len(neighbors) for w in neighbors})
    if not weights:
        return smooth(hand_counts, word, vocab, total)
    scale = sum(weights)
    target = word if word in vocab else "OTHER"
    prob = 0.0
    for weight, dist in zip(weights, dists):
        prob += (weight / scale) * dist.get(target, 0.0)
    return prob


def project_counts(tokens: list[str], vocab: set[str]) -> Counter:
    counts = Counter()
    for word in tokens:
        counts[word if word in vocab else "OTHER"] += 1
    return counts


def fit_hand(lines: list[dict], train_quires: set[str]) -> dict:
    train = [ln for ln in lines if ln["quire"] in train_quires]
    tokens = [w for ln in train for w in ln["words"]]
    hand_counts = Counter(tokens)
    vocab = set(hand_counts)
    pos_counts = {k: Counter() for k in ("init", "mid", "final")}
    pos_n = Counter()
    for ln in train:
        words = ln["words"]
        for i, word in enumerate(words):
            slot = "init" if i == 0 else "final" if i == len(words) - 1 else "mid"
            pos_counts[slot][word] += 1
            pos_n[slot] += 1
    return {
        "hand_counts": hand_counts,
        "vocab": vocab,
        "total": len(tokens),
        "pos_counts": pos_counts,
        "pos_n": pos_n,
        "neigh": neighborhoods(hand_counts),
    }


def token_surprise(word: str, prev: str | None, slot: str, folio_counts: Counter, folio_n: int, model: dict) -> float:
    vocab = model["vocab"]
    total = model["total"]
    p_folio = smooth(folio_counts, word, vocab, folio_n) if folio_n else smooth(model["hand_counts"], word, vocab, total)
    p_hand = smooth(model["hand_counts"], word, vocab, total)
    p_pos = smooth(model["pos_counts"][slot], word, vocab, model["pos_n"][slot]) if model["pos_n"][slot] else p_hand
    p_local = _local_prob(prev, word, model["hand_counts"], vocab, total, model["neigh"])
    prob = 0.40 * p_folio + 0.20 * p_hand + 0.25 * p_pos + 0.15 * p_local
    return -math.log2(max(prob, 1e-15))


def label_surprise(word: str, folio_counts: Counter, folio_n: int, model: dict) -> float:
    vocab = model["vocab"]
    p_folio = smooth(folio_counts, word, vocab, folio_n) if folio_n else smooth(model["hand_counts"], word, vocab, model["total"])
    p_hand = smooth(model["hand_counts"], word, vocab, model["total"])
    return -math.log2(max(0.5 * p_folio + 0.5 * p_hand, 1e-15))


def folio_groups(lines: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for line in lines:
        grouped[line["folio"]].append(line)
    return grouped


def score_split(lines: list[dict], labels: list[dict], train_quires: set[str]) -> list[dict]:
    """Score test folios. Paragraph and label surprises use the same two-part label formula for R1."""
    model = fit_hand(lines, train_quires)
    test_lines = [ln for ln in lines if ln["quire"] not in train_quires]
    grouped = folio_groups(test_lines)
    label_groups = folio_groups(labels)
    rows = []
    for folio, flines in grouped.items():
        all_tokens = [w for ln in flines for w in ln["words"]]
        folio_counts_full = project_counts(all_tokens, model["vocab"])
        surprises = []
        for ln in flines:
            others = [w for other in flines if other is not ln for w in other["words"]]
            folio_counts = project_counts(others, model["vocab"])
            prev = None
            for i, word in enumerate(ln["words"]):
                slot = "init" if i == 0 else "final" if i == len(ln["words"]) - 1 else "mid"
                surprises.append(token_surprise(word, prev, slot, folio_counts, len(others), model))
                prev = word
        lab_words = [w for ln in label_groups.get(folio, []) for w in ln["words"]]
        matched = []
        lab_s = []
        for word in lab_words:
            partners = [w for w in all_tokens if abs(len(w) - len(word)) <= 1]
            if not partners:
                continue
            lab_s.append(label_surprise(word, folio_counts_full, len(all_tokens), model))
            matched.append(float(np.mean([label_surprise(w, folio_counts_full, len(all_tokens), model) for w in partners])))
        rows.append({
            "folio": folio,
            "quire": flines[0]["quire"],
            "hand": flines[0]["hand"],
            "mean_surprise": float(np.mean(surprises)) if surprises else float("nan"),
            "n_tokens": len(surprises),
            "label_words": lab_words,
            "contrast": float(np.mean(lab_s) - np.mean(matched)) if lab_s else None,
            "model_vocab": model["vocab"],
            "hand_counts": model["hand_counts"],
            "hand_total": model["total"],
            "para_counts": folio_counts_full,
            "para_n": len(all_tokens),
            "para_tokens": all_tokens,
        })
    return rows


def stage2(paragraphs: list[dict], labels: list[dict], tags: pd.DataFrame) -> dict:
    scored = []
    for hand in HANDS:
        h_lines = [ln for ln in paragraphs if ln["hand"] == hand]
        h_labels = [ln for ln in labels if ln["hand"] == hand]
        quires = sorted({ln["quire"] for ln in h_lines})
        even = {q for i, q in enumerate(quires) if i % 2 == 0}
        odd = {q for i, q in enumerate(quires) if i % 2 == 1}
        scored.extend(score_split(h_lines, h_labels, even))
        scored.extend(score_split(h_lines, h_labels, odd))
    contrasts = [r for r in scored if r["contrast"] is not None]
    obs = float(np.mean([r["contrast"] for r in contrasts])) if contrasts else float("nan")
    rng = np.random.default_rng(SEED)
    prepared = []
    for row in contrasts:
        model = {"vocab": row["model_vocab"], "hand_counts": row["hand_counts"], "total": row["hand_total"]}
        by_length: dict[int, list[float]] = defaultdict(list)
        for word in row["para_tokens"]:
            by_length[len(word)].append(label_surprise(word, row["para_counts"], row["para_n"], model))
        prepared.append({
            "quire": row["quire"],
            "words": row["label_words"],
            "model": model,
            "para_counts": row["para_counts"],
            "para_n": row["para_n"],
            "by_length": by_length,
        })
    null = np.empty(N_PERM)
    by_quire = defaultdict(list)
    for i, row in enumerate(prepared):
        by_quire[row["quire"]].append(i)
    for draw in range(N_PERM):
        moved = []
        for idxs in by_quire.values():
            perm = rng.permutation(idxs)
            for dest_i, src_i in zip(idxs, perm):
                dest = prepared[dest_i]
                vals = []
                matched_means = []
                for word in prepared[src_i]["words"]:
                    bucket = []
                    for length in range(len(word) - 1, len(word) + 2):
                        bucket.extend(dest["by_length"].get(length, []))
                    if not bucket:
                        continue
                    vals.append(label_surprise(word, dest["para_counts"], dest["para_n"], dest["model"]))
                    matched_means.append(float(np.mean(bucket)))
                if vals:
                    moved.append(float(np.mean(vals) - np.mean(matched_means)))
        null[draw] = float(np.mean(moved)) if moved else float("nan")
    finite = null[np.isfinite(null)]
    p_r1 = float((1 + np.sum(finite >= obs)) / (len(finite) + 1)) if len(finite) and np.isfinite(obs) else 1.0
    r1 = bool(obs > 0 and p_r1 < 0.05)

    surprise_map = {r["folio"]: r["mean_surprise"] for r in scored}
    r2_rows = []
    for tag in TAGS:
        folios = [f for f in tags.index if f in surprise_map and pd.notna(tags.at[f, tag])]
        values = np.array([float(tags.at[f, tag]) > 0 for f in folios])
        surprise = np.array([surprise_map[f] for f in folios])
        quires = np.array([quire_of(f, tags.attrs["quires"]) for f in folios])
        obs_diff = _group_diff(surprise, values)
        null_diff = _permute_diff(surprise, values, quires, rng)
        p = float((1 + np.sum(null_diff >= obs_diff)) / (N_PERM + 1))
        r2_rows.append({"tag": tag, "diff": obs_diff, "p": p})
    r2_p = holm([r["p"] for r in r2_rows])
    for row, adj in zip(r2_rows, r2_p):
        row["p_holm"] = float(adj)
        row["pass"] = bool(row["diff"] > 0 and adj < 0.05)
    return {
        "R1": {"contrast": obs, "p": p_r1, "pass": r1, "n_folios": len(contrasts)},
        "R2": r2_rows,
        "R2_pass": any(r["pass"] for r in r2_rows),
        "scored": scored,
    }


def _group_diff(values: np.ndarray, mask: np.ndarray) -> float:
    if mask.any() and (~mask).any():
        return float(values[mask].mean() - values[~mask].mean())
    return float("nan")


def _permute_diff(values: np.ndarray, mask: np.ndarray, groups: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = np.empty(N_PERM)
    blocks = {g: np.where(groups == g)[0] for g in np.unique(groups)}
    for draw in range(N_PERM):
        shuffled = mask.copy()
        for idx in blocks.values():
            shuffled[idx] = rng.permutation(shuffled[idx])
        out[draw] = _group_diff(values, shuffled)
    return out


def roots_of(lines: list[dict]) -> dict:
    by_folio: dict[str, list[str]] = defaultdict(list)
    meta = {}
    for ln in lines:
        by_folio[ln["folio"]].extend(ln["words"])
        meta[ln["folio"]] = (ln["quire"], ln["hand"])
    per_folio = {}
    for folio, tokens in by_folio.items():
        counts = Counter(tokens)
        first = {}
        for i, word in enumerate(tokens):
            first.setdefault(word, i)
        types = list(counts)
        parent = {w: w for w in types}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        by_len = defaultdict(list)
        for word in types:
            by_len[len(word)].append(word)
        for length, words in by_len.items():
            for i, left in enumerate(words):
                for right in words[i + 1:]:
                    if lev(left, right) == 1:
                        union(left, right)
            for right in by_len.get(length + 1, []):
                for left in words:
                    if lev(left, right) == 1:
                        union(left, right)
        members = defaultdict(list)
        for word in types:
            members[find(word)].append(word)
        root_tokens = Counter()
        covered = 0
        for group in members.values():
            n_tok = sum(counts[w] for w in group)
            if n_tok < 3:
                continue
            root = sorted(group, key=lambda w: (-counts[w], first[w]))[0]
            root_tokens[root] += n_tok
            covered += n_tok
        per_folio[folio] = {
            "quire": meta[folio][0],
            "hand": meta[folio][1],
            "n": len(tokens),
            "covered": covered,
            "roots": root_tokens,
            "top": root_tokens.most_common(1)[0][0] if root_tokens else None,
        }
    coverage = sum(v["covered"] for v in per_folio.values()) / max(1, sum(v["n"] for v in per_folio.values()))
    return {"folios": per_folio, "coverage": coverage}


def stage3(root_info: dict, tags: pd.DataFrame, quires: pd.DataFrame) -> dict:
    folios = root_info["folios"]
    root_folio_counts = Counter()
    for info in folios.values():
        root_folio_counts.update(info["roots"].keys())
    kept = [r for r, n in root_folio_counts.items() if n >= 8]
    use = [f for f in tags.index if f in folios]
    rates = {}
    for root in kept:
        rates[root] = np.array([
            folios[f]["roots"][root] / folios[f]["n"] if folios[f]["n"] else 0.0 for f in use
        ])
    quires_a = np.array([quire_of(f, quires) for f in use])
    rng = np.random.default_rng(SEED)
    rows = []
    for root in kept:
        for tag in TAGS:
            mask = np.array([float(tags.at[f, tag]) > 0 for f in use])
            diff = _group_diff(rates[root], mask)
            null = _permute_diff(rates[root], mask, quires_a, rng)
            p = float((1 + np.sum(null >= diff)) / (N_PERM + 1)) if np.isfinite(diff) else 1.0
            rows.append({"root": root, "tag": tag, "diff": diff, "p": p})
    if rows:
        adj = holm([r["p"] for r in rows])
        for row, p_adj in zip(rows, adj):
            row["p_holm"] = float(p_adj)
            row["pass"] = bool(np.isfinite(row["diff"]) and row["diff"] > 0 and p_adj < 0.05)
    passed = [r for r in rows if r.get("pass")]
    return {"coverage": root_info["coverage"], "n_roots_tested": len(kept), "tests": rows, "M1": bool(passed), "passed": passed}


def stage4(labels: list[dict], tags: pd.DataFrame, quires: pd.DataFrame) -> dict:
    counts = Counter()
    onsets = defaultdict(list)
    for ln in labels:
        counts[ln["folio"]] += len(ln["words"])
        for word in ln["words"]:
            if len(word) >= 2:
                onsets[ln["folio"]].append(onset_unit(word))
    folios = [f for f in tags.index if counts[f] > 0]
    n_labels = np.array([counts[f] for f in folios], dtype=float)
    groups = np.array([quire_of(f, quires) for f in folios])
    rng = np.random.default_rng(SEED)
    l1 = []
    l2 = []
    for tag in TAGS:
        tag_v = np.array([float(tags.at[f, tag]) for f in folios], dtype=float)
        rho = _spearman(n_labels, tag_v) if len(folios) > 2 else float("nan")
        null = np.empty(N_PERM)
        blocks = {g: np.where(groups == g)[0] for g in np.unique(groups)}
        for draw in range(N_PERM):
            shuffled = tag_v.copy()
            for idx in blocks.values():
                shuffled[idx] = rng.permutation(shuffled[idx])
            null[draw] = _spearman(n_labels, shuffled)
        p = float((1 + np.sum(null >= rho)) / (N_PERM + 1)) if np.isfinite(rho) else 1.0
        l1.append({"tag": tag, "rho": rho, "p": p})
        mask = tag_v > 0
        obs = _onset_js(onsets, folios, mask)
        null_js = np.empty(N_PERM)
        for draw in range(N_PERM):
            shuffled_mask = mask.copy()
            for idx in blocks.values():
                shuffled_mask[idx] = rng.permutation(shuffled_mask[idx])
            null_js[draw] = _onset_js(onsets, folios, shuffled_mask)
        p_js = float((1 + np.sum(null_js >= obs)) / (N_PERM + 1)) if np.isfinite(obs) else 1.0
        l2.append({"tag": tag, "js": obs, "p": p_js, "null_p95": float(np.nanpercentile(null_js, 95))})
    for rows in (l1, l2):
        adj = holm([r["p"] for r in rows])
        for row, p_adj in zip(rows, adj):
            row["p_holm"] = float(p_adj)
    for row in l1:
        row["pass"] = bool(np.isfinite(row["rho"]) and row["rho"] > 0 and row["p_holm"] < 0.05)
    for row in l2:
        row["pass"] = bool(np.isfinite(row["js"]) and row["js"] > row["null_p95"] and row["p_holm"] < 0.05)
    return {"L1": l1, "L2": l2, "pass": any(r["pass"] for r in l1 + l2)}


def _spearman(left: np.ndarray, right: np.ndarray) -> float:
    result = stats.spearmanr(left, right)
    rho = getattr(result, "statistic", None)
    if rho is None:
        rho = result.correlation
    return float(rho)


def _onset_js(onsets: dict, folios: list[str], mask: np.ndarray) -> float:
    pos = Counter(u for f, flag in zip(folios, mask) if flag for u in onsets[f])
    neg = Counter(u for f, flag in zip(folios, mask) if not flag for u in onsets[f])
    if not pos or not neg:
        return float("nan")
    keys = sorted(set(pos) | set(neg))
    p = np.array([pos[k] for k in keys], dtype=float)
    q = np.array([neg[k] for k in keys], dtype=float)
    p /= p.sum()
    q /= q.sum()
    m = 0.5 * (p + q)
    def kl(a, b):
        keep = a > 0
        return float(np.sum(a[keep] * np.log2(a[keep] / b[keep])))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def stage5() -> dict:
    corpus = parse_file(ROOT / "data" / "transcriptions" / "ZL3b-n.txt")
    n_alt = n_short = n_un = n_lig = n_tok = 0
    for locus in corpus.loci:
        for token in locus.tokens:
            if not token.text:
                continue
            n_tok += 1
            if token.unreadable:
                n_un += 1
            if token.ligature:
                n_lig += 1
            if token.alternatives and len(token.alternatives[0]) >= 2:
                n_alt += 1
                a, b = token.alternatives[0][0], token.alternatives[0][1]
                if len(a) <= 3 and len(b) <= 3:
                    n_short += 1
    frac = n_short / n_alt if n_alt else float("nan")
    return {
        "n_tokens": n_tok,
        "n_alternative_groups": n_alt,
        "short_option_fraction": frac,
        "n_unreadable": n_un,
        "n_ligature": n_lig,
        "C1": bool(frac >= 0.80),
        "multispectral": "unavailable",
    }


def synthetic_streams(rng: np.random.Generator) -> dict:
    vocab = [f"w{i:02d}abcd" for i in range(40)]
    markers = {topic: vocab[3 * topic: 3 * topic + 3] for topic in range(4)}

    def build(planted: bool) -> list[list[str]]:
        folios = []
        for folio_i in range(40):
            topic = folio_i % 4
            used: list[str] = []
            tokens = []
            for _ in range(64):
                if planted and rng.random() < 0.25:
                    word = markers[topic][int(rng.integers(0, 3))]
                elif used and rng.random() < 0.7:
                    word = used[int(rng.integers(0, len(used)))]
                else:
                    word = vocab[int(rng.integers(0, 40))]
                if rng.random() < 0.5:
                    word = substitute_one(word, rng)
                used.append(word)
                tokens.append(word)
            folios.append(tokens)
        return folios

    def accuracy(folios: list[list[str]], planted: bool) -> float:
        hits = 0
        for i, tokens in enumerate(folios):
            top = Counter(tokens).most_common(1)[0][0]
            topic = i % 4
            hits += int(top in markers[topic])
        return hits / len(folios)

    planted = build(True)
    null = build(False)
    planted_acc = accuracy(planted, True)
    null_acc = accuracy(null, False)
    return {
        "planted_accuracy": planted_acc,
        "null_accuracy": null_acc,
        "S6": bool(planted_acc >= 0.50 and null_acc <= 0.25),
    }


def confirmed_heldout(kind: str, detail: dict, paragraphs: list[dict], labels: list[dict], tags: pd.DataFrame, quires: pd.DataFrame, roots: dict) -> dict:
    """Recompute one passing association on odd quire indices."""
    quires_sorted = sorted({ln["quire"] for ln in paragraphs if ln["hand"] in HANDS})
    odd = {q for i, q in enumerate(quires_sorted) if i % 2 == 1}
    if kind == "R1":
        # The stored R1 already pooled both splits. Held-out uses odd quires of the observed contrasts only.
        return {"kind": kind, "status": "unconfirmed", "reason": "held-out recomputed below"}
    return {"kind": kind, "status": "unconfirmed"}


def run() -> dict:
    quires = load_quire_table()
    tags = pd.read_csv(ROOT / "hypotheses" / "h09_image_context_cribs" / "data" / "visual_tags.csv")
    tags["folio"] = tags["folio"].astype(str)
    tags = tags.set_index("folio")
    tags.attrs["quires"] = quires
    print("stage 1", flush=True)
    s1 = stage1(quires)
    paragraphs = [ln for ln in iter_lines(ROOT / "data" / "transcriptions" / "ZL3b-n.txt", "primary", quires, "P") if ln["hand"] in HANDS]
    labels = [ln for ln in iter_lines(ROOT / "data" / "transcriptions" / "ZL3b-n.txt", "primary", quires, "L") if ln["hand"] in HANDS]
    print("stage 2", flush=True)
    s2 = stage2(paragraphs, labels, tags)
    print("stage 3", flush=True)
    root_info = roots_of(paragraphs)
    s3 = stage3(root_info, tags, quires)
    print("stage 4", flush=True)
    s4 = stage4(labels, tags, quires)
    print("stage 5", flush=True)
    s5 = stage5()
    print("stage 6", flush=True)
    s6 = synthetic_streams(np.random.default_rng(SEED))
    grounded = []
    if s2["R1"]["pass"]:
        grounded.append("R1")
    if s2["R2_pass"]:
        grounded.append("R2")
    if s3["M1"]:
        grounded.append("M1")
    if s4["pass"]:
        grounded.append("L")
    print("stage 7", flush=True)
    if not s6["S6"]:
        gate = "inconclusive"
    elif not grounded:
        gate = "unidentifiable"
    else:
        held = _heldout(grounded, s2, s3, s4, paragraphs, labels, tags, quires)
        gate = "confirmed" if held["any_confirmed"] else "unconfirmed"
        s6["heldout"] = held
    # Drop heavy per-folio rows from the serialized stage-2 payload.
    s2_public = {k: v for k, v in s2.items() if k != "scored"}
    s3_public = {k: v for k, v in s3.items() if k != "tests"}
    s3_public["n_tests"] = len(s3["tests"])
    s3_public["n_passed"] = len(s3["passed"])
    s3_public["passed"] = s3["passed"][:20]
    return {
        "stage1": s1,
        "stage2": s2_public,
        "stage3": s3_public,
        "stage4": s4,
        "stage5": s5,
        "stage6": s6,
        "grounded": grounded,
        "stage7": gate,
    }


def _heldout(grounded: list[str], s2: dict, s3: dict, s4: dict, paragraphs, labels, tags, quires) -> dict:
    quires_sorted = sorted({ln["quire"] for ln in paragraphs})
    odd = {q for i, q in enumerate(quires_sorted) if i % 2 == 1}
    odd_para = [ln for ln in paragraphs if ln["quire"] in odd]
    odd_labels = [ln for ln in labels if ln["quire"] in odd]
    results = {}
    any_confirmed = False
    if "R2" in grounded or "M1" in grounded or "L" in grounded or "R1" in grounded:
        # Recompute the cheap external tests on odd quires. R1 uses a fresh stage2 on the odd subset
        # only as a sign check against the full-sample direction.
        if "R1" in grounded:
            fresh = stage2(odd_para, odd_labels, tags)
            ok = fresh["R1"]["contrast"] > 0 and fresh["R1"]["p"] < 0.10
            results["R1"] = {"contrast": fresh["R1"]["contrast"], "p": fresh["R1"]["p"], "confirmed": ok}
            any_confirmed = any_confirmed or ok
        if "R2" in grounded:
            fresh = stage2(odd_para, odd_labels, tags)
            ok = fresh["R2_pass"]
            results["R2"] = {"pass": ok, "confirmed": ok}
            any_confirmed = any_confirmed or ok
        if "M1" in grounded:
            info = roots_of(odd_para)
            fresh = stage3(info, tags, quires)
            full_sign = {(r["root"], r["tag"]): r["diff"] > 0 for r in s3["passed"]}
            ok = any(r["pass"] and full_sign.get((r["root"], r["tag"]), False) for r in fresh["passed"])
            results["M1"] = {"n_passed": len(fresh["passed"]), "confirmed": bool(ok)}
            any_confirmed = any_confirmed or bool(ok)
        if "L" in grounded:
            fresh = stage4(odd_labels, tags, quires)
            results["L"] = {"pass": fresh["pass"], "confirmed": fresh["pass"]}
            any_confirmed = any_confirmed or fresh["pass"]
    return {"tests": results, "any_confirmed": any_confirmed}
