"""Hand-coded word grammars from the literature (Zattera slot alphabet, Stolfi crust-mantle-core grammar),
a slot-conditioned bigram model, and a common held-out comparison against the learned slot grammar and the
letter-pair baseline.

Everything here scores / samples *EVA word strings*, so models that use different unit inventories are compared in
the same currency: bits per held-out word (an honest comparison, because every model defines a distribution over
strings; the unit parse of a string is unique for every model below).

Sources (tables transcribed by hand, not learned):
* **Zattera slot alphabet** -- M. Zattera (2022), "A new transliteration alphabet brings new evidence of word structure and
  multiple 'languages' in the Voynich manuscript", Cryptologia 46(2); table as reproduced by R. Zandbergen,
  voynich.nu/a3_para.html sec. 3.5.4 (12 slots, each empty or one glyph/digraph):
  ``0 q s d | 1 o y | 2 l r | 3 t k p f | 4 ch sh | 5 cth ckh cph cfh | 6 e ee eee | 7 s d | 8 o a | 9 i ii iii | 10 d l r m n | 11 y``.
  The paper's own coverage figure is 86.6 % of tokens (on its transliteration); the paper's *probabilities*
  are not published, so slot / item probabilities are fitted by EM here (structure fixed, probabilities learned).
* **Stolfi grammar** -- J. Stolfi (2000), "A Grammar for Voynichese Words" (probabilistic context-free grammar of
  crust / mantle / core layers, rule counts from the 1998 interlinear; data/mechanisms/stolfi_word_grammar_2000.txt).
  Only the *normal-word* part is a grammar; Stolfi's "abnormal words" (3.7 % of tokens) are explicit word lists in the note
  and are treated here as uncovered. Two variants: published rule probabilities (fitted by Stolfi on the whole text, so *not*
  held out) and the same structure with rule probabilities re-estimated by counting on the training folds (held-out).
"""
from __future__ import annotations

import math
import random
import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

from .paths import repo_root
from .slot_grammar import SlotGrammar, UnitNgram, word_counts, _group_by_length

LOG2 = math.log(2.0)

ZATTERA_SLOTS: list[list[str]] = [
    ["q", "s", "d"], ["o", "y"], ["l", "r"], ["t", "k", "p", "f"], ["ch", "sh"], ["cth", "ckh", "cph", "cfh"],
    ["e", "ee", "eee"], ["s", "d"], ["o", "a"], ["i", "ii", "iii"], ["d", "l", "r", "m", "n"], ["y"],
]
ZATTERA_UNITS = sorted({u for s in ZATTERA_SLOTS for u in s}, key=lambda u: (-len(u), u))


def zattera_segment(word: str) -> tuple | None:
    """Greedy longest-match parse of an EVA word into Zattera slot-alphabet units (unique for this table);
    ``None`` if a character is outside the alphabet."""
    out, i = [], 0
    while i < len(word):
        for u in ZATTERA_UNITS:
            if word.startswith(u, i):
                out.append(u)
                i += len(u)
                break
        else:
            return None
    return tuple(out)


# ----------------------------------------------------------------------------- slot model (fixed or learned, order 0 / 1)

def _em_ctx(E: np.ndarray, e: np.ndarray, U: np.ndarray, CTX: np.ndarray, w: np.ndarray, posteriors: bool = True):
    """Forward(-backward) for words of equal length with emission ``E[k, ctx, v]`` (context = previous unit of the word)."""
    K = E.shape[0]
    n, L = U.shape
    em = np.stack([e[k] * E[k][CTX, U] if L else np.zeros((n, 0)) for k in range(K)])      # (K, n, L)
    sk = 1.0 - e
    f = np.zeros((K + 1, n, L + 1))
    f[0, :, 0] = 1.0
    for k in range(K):
        cur = f[k] * sk[k]
        if L:
            cur[:, 1:] += f[k][:, :-1] * em[k]
        f[k + 1] = cur
    tot = f[K, :, L]
    if not posteriors:
        return tot, None, None
    b = np.zeros((K + 1, n, L + 1))
    b[K, :, L] = 1.0
    for k in range(K, 0, -1):
        cur = b[k] * sk[k - 1]
        if L:
            cur[:, :-1] += b[k][:, 1:] * em[k - 1]
        b[k - 1] = cur
    inv = w / np.maximum(tot, 1e-300)
    post_e = np.stack([f[k][:, :-1] * em[k] * b[k + 1][:, 1:] * inv[:, None] for k in range(K)])
    post_s = np.array([(f[k] * sk[k] * b[k + 1] * inv[:, None]).sum() for k in range(K)])
    return tot, post_e, post_s


class SlotModel:
    """Skip-HMM slot model: K ordered slots, slot k is skipped (1 - e_k) or emits one unit from
    ``P(v | slot k, previous unit of the word)``.

    * ``order=0``: the emission ignores the previous unit = the slot grammar of :class:`SlotGrammar`.
    * ``order=1``: the **slot-conditioned bigram model**: emission is the slot-k unit distribution *conditioned on the
      previous unit*, hierarchically smoothed ``(c_k(u,v) + beta P_k(v)) / (c_k(u) + beta)``; slots stay hidden and are
      summed out by the forward algorithm (so the model is a proper distribution over unit strings).
    * ``mask``: per-slot sets of allowed units (a hand-coded table, e.g. Zattera's); probabilities outside the mask are
      exactly zero, inside it they are fitted by EM. Without a mask every slot may emit every unit (learned slots; the
      slot structure is initialised from a fitted :class:`SlotGrammar` if given)."""

    def __init__(self, K: int = 12, mask: Sequence[Sequence] | None = None, order: int = 0, beta: float = 2.0,
                 floor: float = 0.02, prune: float = 0.002, min_emit: float = 0.005):
        self.K, self.order, self.beta, self.floor, self.prune, self.min_emit = K, order, beta, floor, prune, min_emit
        self.mask_spec = None if mask is None else [list(s) for s in mask]
        if mask is not None:
            self.K = len(mask)

    # -- fitting
    def fit(self, counts: dict[tuple, float], iters: int = 25, init: SlotGrammar | None = None, seed: int = 0, tol: float = 1e-4):
        K = self.K
        obs = {u for w in counts for u in w}
        allowed = {u for s in (self.mask_spec or []) for u in s}
        self.units = sorted(obs | allowed, key=str)
        self.idx = {u: i for i, u in enumerate(self.units)}
        A = self.A = len(self.units)
        M = np.ones((K, A), bool)
        if self.mask_spec is not None:
            M = np.zeros((K, A), bool)
            for k, s in enumerate(self.mask_spec):
                for u in s:
                    M[k, self.idx[u]] = True
        self.M = M
        words = [w for w in counts if 0 < len(w) <= K and all(u in self.idx for u in w)]
        if self.mask_spec is not None:
            ok = self._hard_cover(words, M)
            words = [w for w, o in zip(words, ok) if o]
        if not words:
            raise ValueError("no word of the training set is covered by the grammar")
        wts = np.array([counts[w] for w in words], dtype=float)
        groups = _group_by_length(words, self.idx)
        ctx = {}
        for L, (ids, U) in groups.items():
            C = np.concatenate([np.full((len(ids), 1), A), U[:, :-1]], axis=1) if L else U
            ctx[L] = C
        rng = np.random.default_rng(seed)
        rel = np.zeros(A)
        cnt = np.zeros(A)
        for i, w in enumerate(words):
            Lw = len(w)
            for j, u in enumerate(w):
                rel[self.idx[u]] += wts[i] * (j / (Lw - 1) if Lw > 1 else 0.5)
                cnt[self.idx[u]] += wts[i]
        rel /= np.maximum(cnt, 1e-9)
        if init is not None and self.mask_spec is None and init.K == K:
            P = np.full((K, A), 1e-3)
            for u, i in self.idx.items():
                if u in init.idx:
                    P[:, i] += init.P[:, init.idx[u]]
            e = init.e.copy()
        else:
            slot_pos = np.arange(K)[:, None]
            P = np.exp(-((rel[None, :] * (K - 1) - slot_pos) ** 2) / (2 * 1.5 ** 2)) + 0.05 * rng.random((K, A))
            e = np.full(K, 0.5)
        P = P * M
        P /= P.sum(1, keepdims=True)
        Cc = None
        prev = -np.inf
        E = self._cond(P, None)
        for it in range(iters):
            Cc = np.zeros((K, A + 2, A + 1))
            Ce = np.full(K, 1e-3)
            Cs = np.full(K, 1e-3)
            ll = 0.0
            for L, (ids, U) in groups.items():
                w = wts[ids]
                tot, pe, ps = _em_ctx(E, e, U, ctx[L], w)
                ll += float((w * np.log(np.maximum(tot, 1e-300))).sum())
                Ce += pe.sum((1, 2))
                Cs += ps
                flat = (ctx[L] * (A + 1) + U).ravel()
                for k in range(K):
                    Cc[k].reshape(-1)[:] += np.bincount(flat, weights=pe[k].ravel(), minlength=(A + 2) * (A + 1))
            Cu = Cc[:, : A + 1, :A].sum(1) + 1e-3 * M
            P = Cu / Cu.sum(1, keepdims=True)
            e = Ce / (Ce + Cs)
            E = self._cond(P, Cc)
            if abs(ll - prev) < tol * abs(ll):
                prev = ll
                break
            prev = ll
        self.P, self.e, self.Cc, self.loglik_train, self.iterations = P, e, Cc, prev / LOG2, it + 1
        self.train_weight = float(wts.sum())
        return self

    def _cond(self, P, Cc, floor: float | None = None):
        """E[k, ctx, v] for ctx in 0..A+1 (A = start, A+1 = unknown), v in 0..A (A = unknown unit)."""
        K, A = self.K, self.A
        fl = 0.0 if floor is None else floor
        if self.mask_spec is not None:
            base = (1 - fl) * P + fl * self.M / self.M.sum(1, keepdims=True)
            unk = np.zeros((K, 1))
        else:
            base = (1 - fl) * P + fl / (A + 1)
            unk = np.full((K, 1), fl / (A + 1))
        Pb = np.concatenate([base, unk], axis=1)                     # (K, A+1)
        if self.order == 0 or Cc is None:
            return np.repeat(Pb[:, None, :], A + 2, axis=1)
        row = Cc.sum(2, keepdims=True)
        return (Cc + self.beta * Pb[:, None, :]) / (row + self.beta)

    # -- scoring
    def _words_idx(self, words):
        unk = self.A
        return [tuple(self.idx.get(u, unk) for u in w) for w in words]

    def logprob2(self, words: Sequence[tuple], floor: float | None = None) -> np.ndarray:
        K, A = self.K, self.A
        fl = self.floor if floor is None else floor
        E = self._cond(self.P, self.Cc, fl)
        e = np.clip(self.e, 1e-4, 1 - 1e-4)
        out = np.full(len(words), -np.inf)
        for L, ids in _by_len(words).items():
            if L == 0 or L > K:
                continue
            U = np.array([[self.idx.get(u, A) for u in words[i]] for i in ids], dtype=np.int64)
            CTX = np.concatenate([np.full((len(ids), 1), A), np.where(U[:, :-1] == A, A + 1, U[:, :-1])], axis=1)
            tot, _, _ = _em_ctx(E, e, U, CTX, np.ones(len(ids)), posteriors=False)
            out[ids] = np.log2(np.maximum(tot, 1e-300))
        return out

    def _hard_cover(self, words, M: np.ndarray) -> np.ndarray:
        ok = np.zeros(len(words), dtype=bool)
        K = self.K
        for L, (ids, U) in _group_by_length(words, self.idx).items():
            if L == 0 or L > K:
                continue
            f = np.zeros((len(ids), L + 1), dtype=bool)
            f[:, 0] = True
            for k in range(K):
                g = f.copy()
                Mk = np.concatenate([M[k], [False]])
                g[:, 1:] |= f[:, :-1] & Mk[U]
                f = g
            ok[ids] = f[:, L]
        return ok

    def covered(self, words: Sequence[tuple]) -> np.ndarray:
        """Can the (pruned) grammar generate the word at all?"""
        if self.mask_spec is not None:
            M = self.M
        else:
            M = (self.P >= self.prune) & (self.e[:, None] >= self.min_emit)
        return self._hard_cover(list(words), M)

    def n_params(self) -> int:
        act = self.e >= self.min_emit
        n = int((self.P[act] >= self.prune).sum() + act.sum())
        if self.order == 1:
            n += int((self.Cc[act][:, : self.A + 1, : self.A] >= 1.0).sum())
        return n

    def structure_cells(self) -> int:
        """Entries of a hand-coded table (cost of *writing the structure down*)."""
        return int(self.M.sum()) if self.mask_spec is not None else 0

    def sample(self, n: int, rng: random.Random) -> list[tuple]:
        K, A = self.K, self.A
        E = self._cond(self.P, self.Cc, 0.0)
        out = []
        while len(out) < n:
            w, ctx = [], A
            for k in range(K):
                if rng.random() < self.e[k]:
                    p = np.asarray(E[k, ctx, :A], float)
                    if p.sum() <= 0:
                        continue
                    v = rng.choices(range(A), weights=p / p.sum())[0]
                    w.append(self.units[v])
                    ctx = v
            if w:
                out.append(tuple(w))
        return out


def _by_len(words) -> dict[int, list[int]]:
    d: dict[int, list[int]] = defaultdict(list)
    for i, w in enumerate(words):
        d[len(w)].append(i)
    return d


# ----------------------------------------------------------------------------- Stolfi probabilistic CFG

class StolfiGrammar:
    """Stolfi's (2000) normal-word grammar as a PCFG over EVA strings (memoised inside algorithm)."""

    START = "NormalWord"

    def __init__(self, path: Path | None = None, alpha: float = 0.0):
        path = Path(path) if path else repo_root() / "data" / "mechanisms" / "stolfi_word_grammar_2000.txt"
        self.rules: dict[str, list[tuple[float, tuple[str, ...]]]] = {}
        cur = None
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.endswith(":"):
                cur = line[:-1]
                self.rules[cur] = []
                continue
            cnt, _freq, _cum, rhs = line.split(None, 3)
            sym = () if rhs.strip() == "." else tuple(rhs.strip().split("."))
            self.rules[cur].append((float(cnt), sym))
        self.rules.pop("Word", None)
        self.alpha = alpha
        self.set_probs({nt: [c for c, _ in alts] for nt, alts in self.rules.items()})
        self.published = {nt: list(p) for nt, p in self.probs.items()}

    @staticmethod
    def is_terminal(sym: str) -> bool:
        return sym[0].islower()

    def set_probs(self, counts: dict[str, list[float]], alpha: float | None = None):
        a = self.alpha if alpha is None else alpha
        self.probs = {}
        for nt, cs in counts.items():
            tot = sum(cs) + a * len(cs)
            self.probs[nt] = [(c + a) / tot if tot > 0 else 1.0 / len(cs) for c in cs]
        self._cache: dict = {}

    def n_rules(self) -> int:
        return sum(len(a) for a in self.rules.values())

    def n_free_params(self) -> int:
        return sum(len(a) - 1 for a in self.rules.values())

    def structure_symbols(self) -> int:
        return sum(len(r) + 1 for a in self.rules.values() for _, r in a)

    # inside probability
    def inside_prob(self, word: str) -> float:
        """P(word) = sum over all derivations (exact inside algorithm, slow; used to check the fast path)."""
        if word in self._cache:
            return self._cache[word]
        s = word
        n = len(s)
        memo_nt: dict = {}
        memo_seq: dict = {}
        rules, probs = self.rules, self.probs

        def inside(nt, i, j):
            key = (nt, i, j)
            if key in memo_nt:
                return memo_nt[key]
            memo_nt[key] = 0.0
            tot = 0.0
            for a, (_, rhs) in enumerate(rules[nt]):
                p = probs[nt][a]
                if p > 0:
                    tot += p * seq(rhs, 0, i, j)
            memo_nt[key] = tot
            return tot

        def seq(rhs, r, i, j):
            if r == len(rhs):
                return 1.0 if i == j else 0.0
            key = (id(rhs), r, i, j)
            if key in memo_seq:
                return memo_seq[key]
            sym = rhs[r]
            if self.is_terminal(sym):
                v = seq(rhs, r + 1, i + len(sym), j) if s.startswith(sym, i) else 0.0
            else:
                v = 0.0
                for m in range(i, j + 1):
                    a = inside(sym, i, m)
                    if a > 0:
                        v += a * seq(rhs, r + 1, m, j)
            memo_seq[key] = v
            return v
        p = inside(self.START, 0, n)
        self._cache[word] = p
        return p

    _PARSES: dict = {}

    def rule_uses(self, word: str) -> list[tuple[str, int]] | None:
        """Cached, probability-independent derivation (Stolfi's grammar is unambiguous; ties are broken by the published rule
        probabilities): list of (non-terminal, alternative) uses, ``None`` if the word is not generated."""
        if word not in StolfiGrammar._PARSES:
            ref = StolfiGrammar._REF
            if ref is None:
                ref = StolfiGrammar._REF = StolfiGrammar.__new__(StolfiGrammar)
                ref.__dict__.update({k: v for k, v in self.__dict__.items() if k != '_cache'})
                ref.set_probs({nt: [c for c, _ in alts] for nt, alts in self.rules.items()}, 0.0)
            StolfiGrammar._PARSES[word] = ref._derive(word)
        return StolfiGrammar._PARSES[word]

    _REF = None

    def prob(self, word: str) -> float:
        """P(word) = product of the rule probabilities along its (unique) derivation; 0 if not generated."""
        u = self.rule_uses(word)
        if u is None:
            return 0.0
        p = 1.0
        for nt, a in u:
            p *= self.probs[nt][a]
        return p

    def covers(self, word: str) -> bool:
        return self.rule_uses(word) is not None

    def _derive(self, word: str) -> list[tuple[str, int]] | None:
        """(non-terminal, alternative index) uses in the (most probable) derivation of ``word``; ``None`` if not generated."""
        s = word
        n = len(s)
        if self.inside_prob(word) <= 0:
            return None
        rules, probs = self.rules, self.probs
        memo: dict = {}

        def inside(nt, i, j):
            key = (nt, i, j)
            if key in memo:
                return memo[key]
            memo[key] = (0.0, None)
            best = (0.0, None)
            for a, (_, rhs) in enumerate(rules[nt]):
                p = probs[nt][a]
                if p <= 0:
                    continue
                r = seq(rhs, 0, i, j)
                if r is not None and p * r[0] > best[0]:
                    best = (p * r[0], (a, r[1]))
            memo[key] = best
            return best

        def seq(rhs, r, i, j):
            """-> (prob, list of child spans) of the best way to derive s[i:j] from rhs[r:]"""
            if r == len(rhs):
                return (1.0, []) if i == j else None
            sym = rhs[r]
            if self.is_terminal(sym):
                if s.startswith(sym, i):
                    t = seq(rhs, r + 1, i + len(sym), j)
                    return t
                return None
            best = None
            for m in range(i, j + 1):
                a = inside(sym, i, m)
                if a[0] > 0:
                    t = seq(rhs, r + 1, m, j)
                    if t is not None and (best is None or a[0] * t[0] > best[0]):
                        best = (a[0] * t[0], [(sym, i, m)] + t[1])
            return best
        uses: list[tuple[str, int]] = []

        def collect(nt, i, j):
            p, info = inside(nt, i, j)
            a, children = info
            uses.append((nt, a))
            for (sym, ci, cj) in children:
                collect(sym, ci, cj)
        collect(self.START, 0, n)
        return uses

    def refit(self, wts: dict[str, float], alpha: float = 0.1):
        """Re-estimate the rule probabilities by counting rule uses in the parses of ``wts`` (weighted words)."""
        counts = {nt: [0.0] * len(alts) for nt, alts in self.rules.items()}
        n_cov = 0.0
        for w, c in wts.items():
            u = self.rule_uses(w)
            if u is None:
                continue
            n_cov += c
            for nt, a in u:
                counts[nt][a] += c
        self.set_probs(counts, alpha)
        return n_cov

    def sample(self, n: int, rng: random.Random, max_len: int = 25) -> list[str]:
        out = []

        def gen(nt):
            alts = self.rules[nt]
            a = rng.choices(range(len(alts)), weights=self.probs[nt])[0]
            return "".join(sym if self.is_terminal(sym) else gen(sym) for sym in alts[a][1])
        while len(out) < n:
            w = gen(self.START)
            if w and len(w) <= max_len:
                out.append(w)
        return out


# ----------------------------------------------------------------------------- string-level adapters (common interface)

LAMBDAS = (1e-4, 1e-3, 1e-2, 5e-2)
ALPHAS = (0.01, 0.05, 0.2, 1.0)
BETAS = (0.5, 2.0, 8.0)


def _bits(lp: np.ndarray) -> float:
    ok = np.isfinite(lp)
    return float(-lp[ok].mean()) if ok.any() else float("nan")


class Adapter:
    """Interface: fit(weights over EVA strings) / logprob2(strings) / covered(strings) / n_params / structure bits / sample."""
    name = "?"
    hand_coded = False
    grid: tuple = ()

    def __init__(self, seg: Callable[[str], tuple]):
        self.seg = seg
        self.hyper = None

    def fit(self, wts: dict[str, float], seed: int = 0):  # pragma: no cover
        raise NotImplementedError

    def tune(self, val_words: list[str]) -> None:
        if not self.grid:
            return
        best = None
        for g in self.grid:
            s = float(np.mean(np.where(np.isfinite(l := self.logprob2(val_words, g)), l, -40.0)))
            if best is None or s > best[0]:
                best = (s, g)
        self.hyper = best[1]

    def structure_bits(self) -> float:
        return 0.0


class LearnedUnit(Adapter):
    """Collapsed-unit models: unigram, letter-pair (bigram), learned slot grammar (K slots), learned slot-conditioned bigram."""

    def __init__(self, seg, kind: str, K: int = 12, iters: int = 25):
        super().__init__(seg)
        self.kind, self.K, self.iters = kind, K, iters
        self.name = {"unigram": "letter unigram", "bigram": "letter-pair (bigram) baseline",
                     "slot": "learned slot grammar (K=%d)" % K, "slotbi": "learned slot-conditioned bigram (K=%d)" % K}[kind]
        self.grid = {"unigram": ALPHAS, "bigram": ALPHAS, "slot": LAMBDAS, "slotbi": LAMBDAS}[kind]
        self.hyper = self.grid[len(self.grid) // 2]
        self.m = None

    def fit(self, wts, seed=0):
        uw = {self.seg(w): c for w, c in wts.items()}
        agg: Counter = Counter()
        for k, v in uw.items():
            agg[k] += v
        uw = dict(agg)
        if self.kind == "unigram":
            self.m = UnitNgram(0).fit(uw)
        elif self.kind == "bigram":
            self.m = UnitNgram(1).fit(uw)
        elif self.kind == "slot":
            self.m = SlotGrammar(K=self.K).fit(uw, iters=self.iters, seed=seed)
        else:
            sg = SlotGrammar(K=self.K).fit(uw, iters=self.iters, seed=seed)
            self.m = SlotModel(K=self.K, order=1, beta=2.0).fit(uw, iters=max(8, self.iters // 2), init=sg, seed=seed)
        self.train_weight = float(sum(wts.values()))
        return self

    def logprob2(self, words, hyper=None):
        h = self.hyper if hyper is None else hyper
        return self.m.logprob2([self.seg(w) for w in words], h)

    def covered(self, words):
        t = [self.seg(w) for w in words]
        if self.kind in ("slot", "slotbi"):
            return self.m.covered(t)
        return self.m.seen_bigrams_cover(t) if self.kind == "bigram" else np.ones(len(t), bool)

    def n_params(self):
        return self.m.n_params()

    def data_bits_train(self, wts):
        ws = list(wts)
        w = np.array([wts[x] for x in ws], float)
        lp = self.m.logprob2([self.seg(x) for x in ws], 1e-9 if self.kind in ("slot", "slotbi") else 1e-9)
        return float((w * -np.where(np.isfinite(lp), lp, -60.0)).sum()), float(w.sum())

    def sample(self, n, rng):
        if self.kind == "slot":
            m = SlotModel(K=self.K, order=0)
            m.units, m.idx, m.A, m.M = self.m.units, self.m.idx, len(self.m.units), np.ones_like(self.m.P, bool)
            m.P, m.e, m.Cc = self.m.P, self.m.e, None
            return ["".join(t) for t in m.sample(n, rng)]
        if self.kind == "slotbi":
            return ["".join(t) for t in self.m.sample(n, rng)]
        raise NotImplementedError


class Escaped(Adapter):
    """Hand-coded grammar with an escape to the letter-pair model for words the grammar cannot generate:
    ``P(w) = (1 - eps) P_grammar(w) + eps P_bigram(w)``, ``eps`` = uncovered share of the training weight."""

    def __init__(self, seg, kind: str):
        super().__init__(seg)
        self.kind = kind
        self.hand_coded = True
        self.name = {"zattera": "Zattera slot alphabet (hand-coded slots, EM probs)",
                     "zattera_bi": "Zattera slots + slot-conditioned bigram",
                     "stolfi": "Stolfi grammar (rule probs re-fitted)",
                     "stolfi_pub": "Stolfi grammar (published probs, NOT held out)"}[kind]
        self.grid = {"zattera": LAMBDAS, "zattera_bi": LAMBDAS, "stolfi": (0.02, 0.1, 0.5), "stolfi_pub": ()}[kind]
        self.hyper = self.grid[len(self.grid) // 2] if self.grid else None

    def fit(self, wts, seed=0):
        total = float(sum(wts.values()))
        self.fb = LearnedUnit(self.seg, "bigram").fit(wts)
        if self.kind in ("zattera", "zattera_bi"):
            zw: Counter = Counter()
            for w, c in wts.items():
                z = zattera_segment(w)
                if z is not None:
                    zw[z] += c
            self.m = SlotModel(mask=ZATTERA_SLOTS, order=0 if self.kind == "zattera" else 1).fit(dict(zw), iters=25, seed=seed)
            cov = float(sum(c for w, c in wts.items() if (z := zattera_segment(w)) is not None and self.m.covered([z])[0]))
        else:
            self.m = StolfiGrammar()
            if self.kind == "stolfi":
                self.m.refit(wts, alpha=self.hyper or 0.1)
            cov = float(sum(c for w, c in wts.items() if self.m.covers(w)))
        self.eps = float(np.clip(1.0 - cov / total, 1e-4, 0.9))
        self.train_coverage = 1.0 - self.eps
        self.train_weight = total
        self._wts = wts
        return self

    def _main(self, words, h):
        if self.kind in ("zattera", "zattera_bi"):
            out = np.full(len(words), -np.inf)
            idx, segs = [], []
            for i, w in enumerate(words):
                z = zattera_segment(w)
                if z is not None:
                    idx.append(i)
                    segs.append(z)
            if segs:
                out[idx] = self.m.logprob2(segs, h)
            return out
        with np.errstate(divide="ignore"):
            return np.log2(np.array([self.m.prob(w) for w in words]))

    def tune(self, val_words):
        if self.kind == "stolfi":                       # alpha changes the fit itself: refit then score
            best = None
            for a in self.grid:
                self.m.refit(self._wts, alpha=a)
                s = float(np.mean(self.logprob2(val_words)))
                if best is None or s > best[0]:
                    best = (s, a)
            self.hyper = best[1]
            self.m.refit(self._wts, alpha=self.hyper)
        else:
            super().tune(val_words)

    def logprob2(self, words, hyper=None):
        h = self.hyper if hyper is None else hyper
        lm = self._main(words, h if self.kind in ("zattera", "zattera_bi") else None)
        lf = self.fb.logprob2(words)
        return np.logaddexp2(math.log2(1 - self.eps) + lm, math.log2(self.eps) + lf)

    def covered(self, words):
        if self.kind in ("zattera", "zattera_bi"):
            return np.array([(z := zattera_segment(w)) is not None and bool(self.m.covered([z])[0]) for w in words])
        return np.array([self.m.covers(w) for w in words])

    def n_params(self):
        if self.kind in ("zattera", "zattera_bi"):
            return self.m.n_params() + 1
        return int(sum(1 for nt, a in self.m.rules.items() for p in self.m.probs[nt] if p > 0) - len(self.m.rules)) + 1 \
            if self.kind == "stolfi" else 0

    def structure_bits(self):
        if self.kind in ("zattera", "zattera_bi"):
            return self.m.structure_cells() * math.log2(len(self.m.units) + 1)
        return self.m.structure_symbols() * math.log2(len(self.m.rules) + 40)

    def data_bits_train(self, wts):
        ws = list(wts)
        w = np.array([wts[x] for x in ws], float)
        lp = self.logprob2(ws, 1e-9 if self.kind in ("zattera", "zattera_bi") else None)
        return float((w * -lp).sum()), float(w.sum())

    def sample(self, n, rng):
        if self.kind in ("stolfi", "stolfi_pub"):
            return self.m.sample(n, rng)
        return ["".join(t) for t in self.m.sample(n, rng)]


def make_models(seg: Callable[[str], tuple], K: int = 12, include_published: bool = True) -> list[Adapter]:
    ms: list[Adapter] = [LearnedUnit(seg, "unigram"), LearnedUnit(seg, "bigram"), LearnedUnit(seg, "slot", K),
                         LearnedUnit(seg, "slotbi", K), Escaped(seg, "zattera"), Escaped(seg, "zattera_bi"), Escaped(seg, "stolfi")]
    if include_published:
        ms.append(Escaped(seg, "stolfi_pub"))
    return ms


def compare_grammars(words: Sequence[str], blocks: Sequence, seg: Callable[[str], tuple], K: int = 12, n_folds: int = 4,
                     seed: int = 1, models_fn: Callable | None = None, max_len: int = 12) -> dict:
    """Held-out comparison of every model on the same folds (folds are whole blocks = folios / chunks).

    Returns ``{model: {bits_tok, bits_type, bits_newtype, cov_tok, cov_type, cov_newtype, mdl_*...}}``. ``bits_*`` are mean
    held-out bits per word: *tok* = token weighted (fit with token weights), *type* = every held-out type once (fit on
    distinct training types), *newtype* = held-out types absent from the training vocabulary. ``cov_*`` = share the
    (pruned / hand-coded) grammar can generate. ``mdl_*`` = full-data two-part code per word: data bits + 0.5 log2(N)
    bits per used parameter (+ ``mdl_*_structure``: the extra cost of writing a hand-coded table down)."""
    keep = [i for i, w in enumerate(words) if 1 <= len(seg(w)) <= max_len]
    words = [words[i] for i in keep]
    blocks = [blocks[i] for i in keep]
    rng = random.Random(seed)
    ub = sorted(set(blocks), key=str)
    rng.shuffle(ub)
    fold = {b: i % n_folds for i, b in enumerate(ub)}
    mk = models_fn or (lambda: make_models(seg, K))
    names = [m.name for m in mk()]
    acc: dict[str, dict[str, list]] = {n: defaultdict(list) for n in names}
    for f in range(n_folds):
        tr = [w for w, b in zip(words, blocks) if fold[b] != f]
        te = [w for w, b in zip(words, blocks) if fold[b] == f]
        te_types = list(dict.fromkeys(te))
        tr_types = set(tr)
        new_types = [w for w in te_types if w not in tr_types]
        # tuning split inside the training folds
        tb = [b for b in ub if fold[b] != f]
        val_b = set(tb[: max(1, len(tb) // 6)])
        tr_in = [w for w, b in zip(words, blocks) if fold[b] != f and b not in val_b]
        va = [w for w, b in zip(words, blocks) if b in val_b and fold[b] != f]
        for level in ("tok", "type"):
            c_tr = Counter(tr)
            wts = dict(c_tr) if level == "tok" else {w: 1.0 for w in c_tr}
            c_in = Counter(tr_in)
            wts_in = dict(c_in) if level == "tok" else {w: 1.0 for w in c_in}
            va_ev = va if level == "tok" else list(dict.fromkeys(va))
            ev = te if level == "tok" else te_types
            for m_tune, m in zip(mk(), mk()):
                m_tune.fit(wts_in, seed + f)
                m_tune.tune(va_ev)
                m.hyper = m_tune.hyper
                m.fit(wts, seed + f)
                if isinstance(m, Escaped) and m.kind == "stolfi":
                    m._wts = wts
                    m.m.refit(wts, alpha=m.hyper or 0.1)
                a = acc[m.name]
                a[f"bits_{level}"].append(_bits(m.logprob2(ev)))
                a[f"cov_{level}"].append(float(m.covered(ev).mean()))
                if level == "type" and new_types:
                    a["bits_newtype"].append(_bits(m.logprob2(new_types)))
                    a["cov_newtype"].append(float(m.covered(new_types).mean()))
    out = {}
    for n in names:
        out[n] = {k: float(np.mean(v)) for k, v in acc[n].items()}
        out[n].update({k + "__fold_sd": float(np.std(v, ddof=1)) for k, v in acc[n].items() if len(v) > 1})
    # full-data MDL
    c_all = Counter(words)
    for level in ("tok", "type"):
        wts = dict(c_all) if level == "tok" else {w: 1.0 for w in c_all}
        for m in mk():
            m.fit(wts, seed)
            if isinstance(m, Escaped) and m.kind == "stolfi":
                m._wts = wts
                m.m.refit(wts, alpha=m.hyper or 0.1)
            bits, N = m.data_bits_train(wts)
            pen = 0.5 * math.log2(max(N, 2))
            k = m.n_params()
            out[m.name][f"mdl_{level}"] = (bits + pen * k) / N
            out[m.name][f"mdl_{level}_data"] = bits / N
            out[m.name][f"mdl_{level}_params"] = k
            out[m.name][f"mdl_{level}_structure"] = (bits + pen * k + m.structure_bits()) / N
            out[m.name][f"train_coverage_{level}"] = float(getattr(m, "train_coverage", float(m.covered(list(wts)).dot(np.array([wts[x] for x in wts])) / N)))
    for n in names:
        out[n]["hand_coded"] = n in [m.name for m in mk() if m.hand_coded]
    return out


def zattera_covered(word: str) -> bool:
    """Hard test: can Zattera's 12-slot table generate ``word`` (units assigned to distinct, increasing slots)?"""
    z = zattera_segment(word)
    if z is None or not z:
        return False
    n = len(z)
    f = [True] + [False] * n
    for slot in ZATTERA_SLOTS:
        g = f[:]
        for j in range(n):
            if f[j] and z[j] in slot:
                g[j + 1] = True
        f = g
    return f[n]
