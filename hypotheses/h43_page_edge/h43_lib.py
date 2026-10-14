"""h43: vocabulary break at the folio edge (PREREG.md).

A window is 80 consecutive tokens on one folio. Pairs sit at start-distance
80 or 160. Effect is mean same-folio cosine minus mean cross-boundary cosine.
The null rotates each quire's tokens against its fixed folio lengths.
"""
from __future__ import annotations

import os

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import html
import io
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _rel in (
    "src",
    "hypotheses/h20_generators_vs_italian",
    "hypotheses/h09_image_context_cribs",
    "hypotheses/h13_top_word_context",
    "hypotheses/h14_line_position_controls",
):
    sys.path.insert(0, str(ROOT / _rel))

import h09_lib  # noqa: E402
import h13_lib  # noqa: E402
import h14_lib  # noqa: E402
from fetch_italian import OUT as ITALIAN_DIR  # noqa: E402
from fetch_italian import SOURCES as ITALIAN_SOURCES  # noqa: E402
from fetch_italian import html_to_text, load_italian  # noqa: E402
from msdecipher.controls_fetch import controls_dir  # noqa: E402
from msdecipher.controls_text import load_tokens, normalise_word_text, source_by_id, strip_gutenberg  # noqa: E402

WINDOW = 80
DISTANCES = (80, 160)
MIN_PAIRS = 30
N_NULL = 100
NULL_SEED = 43
HANDS = ("1A", "2B", "3B")
TRANSCRIPTION = "ZL3b-n.txt"
TEI = "{http://www.tei-c.org/ns/1.0}"
NOTE = TEI + "note"
DIV = TEI + "div"
PAGE_SPLIT = "\n<!-- page -->\n"
CUCINA_EQ = re.compile(r"^=.+=$")
CUCINA_IT = re.compile(r"^_.+_$")
FOOTNOTE_LINE = re.compile(r"^\s+[¹²³⁴⁵⁶⁷⁸⁹\d]")
NOVELLA_HEAD = re.compile(r'<div class="intest-sezione">(.*?)</div>', re.S)


@dataclass
class Quire:
    ids: np.ndarray
    folio_lengths: tuple[int, ...]
    lag: dict[int, np.ndarray]


@dataclass
class Stream:
    name: str
    quires: tuple[Quire, ...]
    folio: np.ndarray
    quire_index: np.ndarray
    quire_start: np.ndarray
    same: dict[int, np.ndarray]
    cross: dict[int, np.ndarray]
    within_same: dict[int, dict[int, np.ndarray]]
    within_cross: dict[int, dict[int, np.ndarray]]
    across_cross: dict[int, tuple[tuple[int, int, int, int], ...]]


def cosine_counts(a: dict, b: dict) -> float:
    """Cosine of two word-count maps. Empty maps are not used on real windows."""
    if len(a) > len(b):
        a, b = b, a
    dot = 0
    for key, count in a.items():
        other = b.get(key)
        if other:
            dot += count * other
    norm_a = 0
    for count in a.values():
        norm_a += count * count
    norm_b = 0
    for count in b.values():
        norm_b += count * count
    return dot / math.sqrt(norm_a * norm_b)


def rotate_tokens(tokens: list[str], shift: int) -> list[str]:
    """Circular rotation. Local order stays fixed; the cut point moves."""
    n = len(tokens)
    if n == 0:
        return []
    r = shift % n
    if r == 0:
        return list(tokens)
    return list(tokens[r:]) + list(tokens[:r])


def split_lengths(tokens: list[str], lengths: list[int]) -> list[list[str]]:
    """Cut a token list into folios of the given lengths."""
    out: list[list[str]] = []
    cursor = 0
    for length in lengths:
        if length < 0:
            raise ValueError("negative folio length")
        nxt = cursor + length
        out.append(list(tokens[cursor:nxt]))
        cursor = nxt
    if cursor != len(tokens):
        raise ValueError("folio lengths do not sum to the token count")
    return out


def is_pass(n_same: int, n_cross: int, effect: float | None, p95: float | None) -> bool:
    """Scored only with at least 30 pairs on each side, and only if effect exceeds the null 95th."""
    if n_same < MIN_PAIRS or n_cross < MIN_PAIRS:
        return False
    if effect is None or p95 is None:
        return False
    return float(effect) > float(p95)


def _lag_cosine(ids: np.ndarray, distance: int, window: int) -> np.ndarray:
    """cosine(circular window s, circular window (s+distance) mod n) for every s."""
    n = len(ids)
    out = np.empty(n, dtype=np.float64)
    if n < window:
        raise ValueError("lag cosine needs at least one full window")
    ext = np.empty(n + window - 1, dtype=np.int32)
    ext[:n] = ids
    if window > 1:
        ext[n:] = ids[: window - 1]
    counts: dict[int, int] = {}
    for token in ext[:window].tolist():
        token = int(token)
        counts[token] = counts.get(token, 0) + 1
    first: list[dict[int, int]] = []
    recent: deque[dict[int, int]] = deque()
    for start in range(n):
        if start:
            old = int(ext[start - 1])
            new = int(ext[start + window - 1])
            counts[old] -= 1
            if counts[old] == 0:
                del counts[old]
            counts[new] = counts.get(new, 0) + 1
        if len(recent) == distance:
            out[start - distance] = cosine_counts(recent[0], counts)
            recent.popleft()
        snap = dict(counts)
        if len(first) < distance:
            first.append(snap)
        recent.append(snap)
    if n > distance:
        last = list(recent)
        if len(last) != distance:
            raise RuntimeError("rotation buffer lost a window")
        for k, snap in enumerate(last):
            start = n - distance + k
            partner = (start + distance) % n
            out[start] = cosine_counts(snap, first[partner])
    else:
        if len(first) != n:
            raise RuntimeError("short quire did not keep every window")
        for start in range(n):
            out[start] = cosine_counts(first[start], first[(start + distance) % n])
    return out


def _window(ids: np.ndarray, start: int, shift: int, window: int = WINDOW) -> np.ndarray:
    n = len(ids)
    begin = (int(start) + int(shift)) % n
    end = begin + window
    if end <= n:
        return ids[begin:end]
    return np.concatenate([ids[begin:], ids[: end - n]])


def _cosine_ids(a: np.ndarray, b: np.ndarray) -> float:
    left: dict[int, int] = {}
    for token in a.tolist():
        token = int(token)
        left[token] = left.get(token, 0) + 1
    right: dict[int, int] = {}
    for token in b.tolist():
        token = int(token)
        right[token] = right.get(token, 0) + 1
    return cosine_counts(left, right)


def _classify(folio: np.ndarray, distance: int, window: int = WINDOW) -> tuple[np.ndarray, np.ndarray]:
    n = len(folio)
    last = n - distance - window
    same: list[int] = []
    cross: list[int] = []
    if last < 0:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)
    for start in range(last + 1):
        if folio[start] != folio[start + window - 1]:
            continue
        other = start + distance
        if folio[other] != folio[other + window - 1]:
            continue
        if folio[start] == folio[other]:
            same.append(start)
        else:
            cross.append(start)
    return np.asarray(same, dtype=np.int32), np.asarray(cross, dtype=np.int32)


def _split_local(
    starts: np.ndarray,
    distance: int,
    quire_index: np.ndarray,
    quire_start: np.ndarray,
) -> tuple[dict[int, np.ndarray], tuple[tuple[int, int, int, int], ...]]:
    """Split global starts into within-quire local starts and cross-quire tuples."""
    n_quires = len(quire_start)
    within = {q: np.zeros(0, dtype=np.int64) for q in range(n_quires)}
    if len(starts) == 0:
        return within, ()
    left = quire_index[starts]
    right = quire_index[starts + distance]
    loc = starts.astype(np.int64) - quire_start[left]
    for q in range(n_quires):
        mask = (left == q) & (right == q)
        within[q] = loc[mask]
    mask = left != right
    if not np.any(mask):
        return within, ()
    loc2 = (starts + distance).astype(np.int64) - quire_start[right]
    across = tuple(
        (int(a), int(b), int(c), int(d))
        for a, b, c, d in zip(left[mask].tolist(), loc[mask].tolist(), right[mask].tolist(), loc2[mask].tolist())
    )
    return within, across


def build_stream(quires: list[list[list[str]]], name: str = "") -> Stream:
    """quires[quire][folio] is that folio's tokens in reading order."""
    if not quires or any(len(folio) == 0 for quire in quires for folio in quire):
        raise ValueError("every folio needs at least one token")
    vocab: dict[str, int] = {}

    def intern(token: str) -> int:
        idx = vocab.get(token)
        if idx is None:
            idx = len(vocab)
            vocab[token] = idx
        return idx

    built: list[Quire] = []
    folio_ids: list[int] = []
    quire_ids: list[int] = []
    next_folio = 0
    for qi, folios in enumerate(quires):
        lengths = tuple(len(folio) for folio in folios)
        ids = np.empty(sum(lengths), dtype=np.int32)
        cursor = 0
        for length, folio in zip(lengths, folios):
            for token in folio:
                ids[cursor] = intern(token)
                cursor += 1
            folio_ids.extend([next_folio] * length)
            quire_ids.extend([qi] * length)
            next_folio += 1
        lag = {}
        if len(ids) >= WINDOW:
            for distance in DISTANCES:
                lag[distance] = _lag_cosine(ids, distance, WINDOW)
        built.append(Quire(ids=ids, folio_lengths=lengths, lag=lag))
    folio = np.asarray(folio_ids, dtype=np.int32)
    quire_index = np.asarray(quire_ids, dtype=np.int32)
    quire_start = np.zeros(len(built), dtype=np.int64)
    cursor = 0
    for qi, quire in enumerate(built):
        quire_start[qi] = cursor
        cursor += len(quire.ids)
    same: dict[int, np.ndarray] = {}
    cross: dict[int, np.ndarray] = {}
    within_same: dict[int, dict[int, np.ndarray]] = {}
    within_cross: dict[int, dict[int, np.ndarray]] = {}
    across_cross: dict[int, tuple[tuple[int, int, int, int], ...]] = {}
    for distance in DISTANCES:
        same_idx, cross_idx = _classify(folio, distance)
        same[distance] = same_idx
        cross[distance] = cross_idx
        within_same[distance], across_same = _split_local(same_idx, distance, quire_index, quire_start)
        if across_same:
            raise RuntimeError("a same-folio pair crossed a quire")
        within_cross[distance], across_cross[distance] = _split_local(cross_idx, distance, quire_index, quire_start)
    return Stream(
        name=name,
        quires=tuple(built),
        folio=folio,
        quire_index=quire_index,
        quire_start=quire_start,
        same=same,
        cross=cross,
        within_same=within_same,
        within_cross=within_cross,
        across_cross=across_cross,
    )


def _gather(
    stream: Stream,
    distance: int,
    shifts: list[int],
    within: dict[int, np.ndarray],
    across: tuple[tuple[int, int, int, int], ...],
) -> np.ndarray:
    chunks: list[np.ndarray] = []
    for qi, locs in within.items():
        if len(locs) == 0:
            continue
        lag = stream.quires[qi].lag.get(distance)
        if lag is None:
            raise RuntimeError("pair in a quire shorter than one window")
        n = len(lag)
        idx = (locs.astype(np.int64) + np.int64(shifts[qi])) % np.int64(n)
        chunks.append(lag[idx])
    if across:
        vals = np.empty(len(across), dtype=np.float64)
        for k, (q1, loc1, q2, loc2) in enumerate(across):
            left = _window(stream.quires[q1].ids, loc1, shifts[q1])
            right = _window(stream.quires[q2].ids, loc2, shifts[q2])
            vals[k] = _cosine_ids(left, right)
        chunks.append(vals)
    if not chunks:
        return np.empty(0, dtype=np.float64)
    return np.concatenate(chunks)


def effect_at(stream: Stream, distance: int, shifts: list[int]) -> float | None:
    """Mean same cosine minus mean cross cosine. None when either side is empty."""
    if len(shifts) != len(stream.quires):
        raise ValueError("one shift per quire")
    same = _gather(stream, distance, shifts, stream.within_same[distance], ())
    cross = _gather(stream, distance, shifts, stream.within_cross[distance], stream.across_cross[distance])
    if len(same) == 0 or len(cross) == 0:
        return None
    return float(same.mean() - cross.mean())


def _draw_shifts(stream: Stream, rng: np.random.Generator) -> list[list[int]]:
    shifts: list[list[int]] = []
    for _ in range(N_NULL):
        one: list[int] = []
        for quire in stream.quires:
            n = len(quire.ids)
            if n <= 0:
                raise RuntimeError("empty quire")
            one.append(int(rng.integers(0, n)))
        shifts.append(one)
    return shifts


def score_stream(stream: Stream, rng: np.random.Generator) -> dict:
    """Observed effect and 100 rotations. The same shifts are used at both distances."""
    zero = [0] * len(stream.quires)
    shifts = _draw_shifts(stream, rng)
    distances: dict[str, dict] = {}
    n_tokens = int(sum(len(quire.ids) for quire in stream.quires))
    n_folios = int(sum(len(quire.folio_lengths) for quire in stream.quires))
    print(
        f"score {stream.name} tokens={n_tokens} folios={n_folios} quires={len(stream.quires)}",
        flush=True,
    )
    for distance in DISTANCES:
        n_same = int(len(stream.same[distance]))
        n_cross = int(len(stream.cross[distance]))
        observed = effect_at(stream, distance, zero)
        nulls = [effect_at(stream, distance, one) for one in shifts]
        if observed is None:
            if any(value is not None for value in nulls):
                raise RuntimeError("null geometry changed pair counts")
            p95 = None
            null_mean = None
            null_list = None
        else:
            if any(value is None for value in nulls):
                raise RuntimeError("null geometry changed pair counts")
            arr = np.asarray(nulls, dtype=np.float64)
            p95 = float(np.percentile(arr, 95, method="linear"))
            null_mean = float(arr.mean())
            null_list = [float(value) for value in arr.tolist()]
        scored = n_same >= MIN_PAIRS and n_cross >= MIN_PAIRS
        passed = is_pass(n_same, n_cross, observed, p95)
        distances[str(distance)] = {
            "n_same": n_same,
            "n_cross": n_cross,
            "effect": observed,
            "null_p95": p95,
            "null_mean": null_mean,
            "null_effects": null_list,
            "scored": scored,
            "pass": passed,
        }
        print(
            f"  d={distance} same={n_same} cross={n_cross} effect={observed} "
            f"p95={p95} scored={scored} pass={passed}",
            flush=True,
        )
    return {
        "name": stream.name,
        "n_tokens": n_tokens,
        "n_folios": n_folios,
        "n_quires": len(stream.quires),
        "distances": distances,
    }


def predictions(hands: dict, controls: dict) -> dict:
    """E1 and E2 from distance-80 pass flags. E2 is unscored when fewer than two controls are available."""
    hand_pass = [hand for hand in HANDS if hands[hand]["distances"]["80"]["pass"]]
    available = [name for name, rec in controls.items() if rec["available"]]
    e2_scored = len(available) >= 2
    if e2_scored:
        control_pass = [name for name in available if controls[name]["distances"]["80"]["pass"]]
        e2: bool | None = len(control_pass) >= 2
        uncalibrated = False
    else:
        control_pass = []
        e2 = None
        uncalibrated = True
    return {
        "E1": len(hand_pass) >= 2,
        "E1_pass_hands": hand_pass,
        "E2": e2,
        "E2_scored": e2_scored,
        "E2_pass_controls": control_pass,
        "n_controls_available": len(available),
        "available_controls": available,
        "uncalibrated": uncalibrated,
    }


def _bind_zl3b() -> None:
    path = ROOT / "data" / "transcriptions" / TRANSCRIPTION
    if not path.is_file():
        raise FileNotFoundError(path)
    h09_lib.TR = path
    h13_lib.H9.TR = path
    words = [token for token, _ok in h13_lib.tokens_raw("aa,bb cc")[0]]
    if words != ["aa", "bb", "cc"]:
        raise RuntimeError(f"comma is not a word space under the h14 splitter: {words}")


def load_hands() -> dict[str, Stream]:
    """Paragraph words of hands 1A, 2B, 3B from the h14 table. ZL3b, comma splits words."""
    _bind_zl3b()
    table = h14_lib.table()
    streams: dict[str, Stream] = {}
    for hand in HANDS:
        sub = table.loc[table.HL == hand, ["folio", "quire", "w"]]
        quires: list[list[list[str]]] = []
        cur_quire: list[list[str]] = []
        cur_folio: list[str] = []
        seen_quire = None
        seen_folio = None
        for folio, quire, word in zip(sub.folio.tolist(), sub.quire.tolist(), sub.w.tolist()):
            folio = str(folio)
            quire = str(quire)
            if quire != seen_quire:
                if cur_folio:
                    cur_quire.append(cur_folio)
                    cur_folio = []
                if cur_quire:
                    quires.append(cur_quire)
                    cur_quire = []
                seen_quire = quire
                seen_folio = folio
            elif folio != seen_folio:
                cur_quire.append(cur_folio)
                cur_folio = []
                seen_folio = folio
            cur_folio.append(str(word))
        if cur_folio:
            cur_quire.append(cur_folio)
        if cur_quire:
            quires.append(cur_quire)
        streams[hand] = build_stream(quires, name=hand)
    return streams


def _novella_label(page: str) -> str | None:
    match = NOVELLA_HEAD.search(page)
    if match is None:
        return None
    text = re.sub(r"<[^>]+>", " ", match.group(1))
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_novella(label: str | None) -> bool:
    if label is None:
        return False
    return "Novella" in label and "Introduzione" not in label


def load_boccaccio() -> tuple[Stream, dict]:
    """Cut the raw Wikisource file at each Novella heading. One fake quire."""
    spec = next(row for row in ITALIAN_SOURCES if row["id"] == "it_boccaccio")
    raw = (ITALIAN_DIR / spec["file"]).read_text(encoding="utf-8", errors="replace")
    pages = [page for page in raw.split(PAGE_SPLIT) if page.strip()]
    labels: list[str] = []
    folios: list[list[str]] = []
    current: list[str] = []
    for page in pages:
        label = _novella_label(page)
        tokens = normalise_word_text(html_to_text(page), latin=False)
        if _is_novella(label):
            labels.append(label or "")
            if current:
                folios.append(current)
                current = []
        current.extend(tokens)
    if current:
        folios.append(current)
    flat = [token for folio in folios for token in folio]
    loaded = load_italian("it_boccaccio")
    if flat != loaded:
        raise RuntimeError(f"boccaccio stretch tokens {len(flat)} != load_italian {len(loaded)}")
    meta = {
        "available": len(labels) >= 20,
        "n_boundaries": len(labels),
        "boundary": "Novella heading in the raw Wikisource HTML",
        "boundary_labels": labels,
        "quire_structure": "one_fake_quire",
        "quire_note": "The source has no quires. All fake folios are one rotation group.",
        "token_match": True,
        "token_loader": "fetch_italian.load_italian('it_boccaccio')",
    }
    return build_stream([folios], name="it_boccaccio"), meta


def _cucina_body() -> str:
    spec = next(row for row in ITALIAN_SOURCES if row["id"] == "it_cucina")
    raw = (ITALIAN_DIR / spec["file"]).read_text(encoding="utf-8", errors="replace")
    raw = strip_gutenberg(raw)
    start = re.search(spec["start"], raw, flags=re.M)
    if start is None:
        raise RuntimeError("cucina start marker missing")
    raw = raw[start.start():]
    end = re.search(spec["end"], raw, flags=re.M)
    if end is None:
        raise RuntimeError("cucina end marker missing")
    return raw[: end.start()]


def _is_recipe_heading(line: str) -> bool:
    stripped = line.strip()
    return CUCINA_EQ.match(stripped) is not None or CUCINA_IT.match(stripped) is not None


def _tokenise_cucina(stretch: str) -> list[str]:
    kept = [line for line in stretch.splitlines() if FOOTNOTE_LINE.match(line) is None]
    text = re.sub(r"\[\d+\]", " ", "\n".join(kept))
    return normalise_word_text(text, latin=False)


def load_cucina() -> tuple[Stream, dict]:
    """Recipe headings are whole lines of the form =...= or _..._ in the Zambrini body."""
    body = _cucina_body()
    labels: list[str] = []
    groups: list[list[str]] = []
    buf: list[str] = []
    for line in body.splitlines():
        if _is_recipe_heading(line) and buf:
            groups.append(buf)
            buf = [line]
            labels.append(line.strip())
        else:
            if _is_recipe_heading(line) and not buf:
                labels.append(line.strip())
            buf.append(line)
    if buf:
        groups.append(buf)
    folios = [tokens for tokens in (_tokenise_cucina("\n".join(group)) for group in groups) if tokens]
    flat = [token for folio in folios for token in folio]
    loaded = load_italian("it_cucina")
    if flat != loaded:
        raise RuntimeError(f"cucina stretch tokens {len(flat)} != load_italian {len(loaded)}")
    meta = {
        "available": len(labels) >= 20,
        "n_boundaries": len(labels),
        "boundary": "Zambrini recipe heading (=...= or _..._ line) before TAVOLA",
        "boundary_labels": labels,
        "quire_structure": "one_fake_quire",
        "quire_note": "The source has no quires. All fake folios are one rotation group.",
        "token_match": True,
        "token_loader": "fetch_italian.load_italian('it_cucina')",
    }
    return build_stream([folios], name="it_cucina"), meta


def _add_text(parts: list[str], length: int, text: str) -> int:
    if not text:
        return length
    parts.append(text)
    return length + len(text)


def _book_text_and_cuts(book: ET.Element) -> tuple[str, list[int]]:
    """Character text of one book, with a cut at each chapter start. The book tail is dropped."""
    parts: list[str] = []
    cuts: list[int] = []
    length = 0

    def walk(el: ET.Element, root: bool) -> None:
        nonlocal length
        if el.tag == NOTE:
            length = _add_text(parts, length, el.tail or "")
            return
        if not root and el.tag == DIV and el.get("subtype") == "chapter":
            cuts.append(length)
        length = _add_text(parts, length, el.text or "")
        for child in list(el):
            walk(child, False)
        if not root:
            length = _add_text(parts, length, el.tail or "")

    walk(book, True)
    return "".join(parts), cuts


def load_pliny() -> tuple[Stream, dict]:
    """Chapter divisions in the Perseus XML for Naturalis Historia XX–XXVII. One fake quire."""
    spec = source_by_id("la_pliny_herbal")
    path = controls_dir() / spec["file"]
    root = ET.parse(io.BytesIO(path.read_bytes())).getroot()
    wanted = [str(book) for book in spec["books"]]
    found: dict[str, ET.Element] = {}
    for node in root.iter(DIV):
        if node.get("subtype") == "book" and node.get("n") in wanted and node.get("n") not in found:
            found[node.get("n")] = node
    missing = [book for book in wanted if book not in found]
    if missing:
        raise RuntimeError(f"Pliny books missing: {missing}")
    pieces: list[str] = []
    cuts: list[int] = []
    cursor = 0
    per_book: dict[str, int] = {}
    for index, book in enumerate(wanted):
        if index:
            pieces.append("\n")
            cursor += 1
        text, local = _book_text_and_cuts(found[book])
        per_book[book] = len(local)
        cuts.extend(cursor + cut for cut in local)
        pieces.append(text)
        cursor += len(text)
    raw = "".join(pieces)
    points = [0]
    for cut in cuts:
        if cut != points[-1]:
            points.append(cut)
    if points[-1] != len(raw):
        points.append(len(raw))
    folios: list[list[str]] = []
    labels: list[str] = []
    for book, count in per_book.items():
        labels.extend(f"book {book} chapter {i + 1}" for i in range(count))
    for left, right in zip(points, points[1:]):
        tokens = normalise_word_text(raw[left:right], latin=True)
        if tokens:
            folios.append(tokens)
    flat = [token for folio in folios for token in folio]
    loaded = load_tokens("la_pliny_herbal", None)
    if flat != loaded:
        raise RuntimeError(f"pliny stretch tokens {len(flat)} != load_tokens {len(loaded)}")
    meta = {
        "available": len(cuts) >= 20,
        "n_boundaries": len(cuts),
        "boundary": "TEI div subtype=chapter in books 20-27",
        "chapters_per_book": per_book,
        "boundary_labels": labels,
        "quire_structure": "one_fake_quire",
        "quire_note": "The source has no quires. All fake folios are one rotation group.",
        "token_match": True,
        "token_loader": "msdecipher.controls_text.load_tokens('la_pliny_herbal')",
    }
    return build_stream([folios], name="la_pliny_herbal"), meta


def load_controls() -> list[tuple[str, Stream, dict]]:
    loaders = (
        ("it_boccaccio", load_boccaccio),
        ("it_cucina", load_cucina),
        ("la_pliny_herbal", load_pliny),
    )
    out = []
    for name, loader in loaders:
        stream, meta = loader()
        print(
            f"control {name} boundaries={meta['n_boundaries']} available={meta['available']} "
            f"tokens={sum(len(quire.ids) for quire in stream.quires)} folios={stream.folio[-1] + 1 if len(stream.folio) else 0}",
            flush=True,
        )
        out.append((name, stream, meta))
    return out


def measure_all(seed: int = NULL_SEED) -> dict:
    """One numpy Generator, seed 43, consumed in hand then control order."""
    rng = np.random.default_rng(seed)
    hands = {}
    for hand, stream in load_hands().items():
        hands[hand] = score_stream(stream, rng)
    controls = {}
    for name, stream, meta in load_controls():
        rec = score_stream(stream, rng)
        rec.update(meta)
        controls[name] = rec
    return {
        "window": WINDOW,
        "distances": list(DISTANCES),
        "min_pairs": MIN_PAIRS,
        "n_null": N_NULL,
        "null_seed": seed,
        "null": "100 circular rotations per text; each quire shifted by an independent uniform draw on 0..n-1; folio lengths fixed",
        "transcription": TRANSCRIPTION,
        "comma": "space",
        "loader": "h14.table paragraph words, ZL3b",
        "hands": hands,
        "controls": controls,
        "predictions": predictions(hands, controls),
        "numpy": np.__version__,
    }
