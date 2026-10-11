"""Shared helper: turn a parsed corpus selection into lines of readable words."""
from __future__ import annotations

from dataclasses import dataclass

from .ivtff import Corpus, Locus, words_of, readable


@dataclass
class Line:
    locus: Locus
    words: list[str]            # every token of the locus, incl. unreadable ones ('?')

    @property
    def page(self) -> str:
        return self.locus.folio


def lines_for(corpus: Corpus, uncertain: str = "split", **select) -> list[Line]:
    out = []
    for lc in corpus.select(**select):
        w = words_of(lc, uncertain)
        if w:
            out.append(Line(lc, w))
    return out


def readable_words(lines: list[Line]) -> list[str]:
    return [w for ln in lines for w in ln.words if readable(w)]
