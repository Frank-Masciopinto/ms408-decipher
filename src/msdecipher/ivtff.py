"""Parser for IVTFF 2.0 (Intermediate Voynich Transliteration File Format, R. Zandbergen).

Format reference: https://www.voynich.nu/software/ivtt/IVTFF_format.pdf

What is handled
---------------
* file header ``#=IVTFF <alphabet> <version> <mode>``; ``#`` comment lines
* page headers ``<f1r>  <! $Q=A $I=T $L=A $H=1 ...>`` (page variables)
* locus identifiers ``<f1r.3,+P0;T>`` -> folio, number, locator, locus type, transcriber id
* ``/`` line continuation (literal reading: the pieces are concatenated with no implied space; the
  real voynich.nu files contain no wrapped lines)
* in-line free comments ``<!...>``, text tags ``<@H=2>``, paragraph marks ``<%>`` ``<$>``,
  drawing intrusions ``<->`` and ``<~>`` (both count as word spaces)
* word spaces: ``.`` certain, ``,`` uncertain (kept as data, see :class:`Token`)
* alternative readings ``[a:o]`` (first, most likely, option is used; all are recorded)
* ligatures ``{ct}`` (braces dropped, flagged)
* rare / high-ASCII glyph codes ``@254;`` (mapped to one private-use code point each so a
  word stays a plain ``str``; use :func:`render` to get the ``@nnn;`` form back)
* unreadable glyphs ``?`` and ``???`` (flagged on the token)

Nothing here interprets the text; it only structures a transcription.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

RARE_BASE = 0xE000  # '@nnn;' -> chr(RARE_BASE + nnn)

HEADER_RE = re.compile(r"^#=IVTFF\s+(?P<alphabet>\S{1,4})\s+(?P<version>\d+\.\d+)\s*(?P<mode>[MDA])?")
PAGE_RE = re.compile(r"^<(?P<page>[^<>.,\s]+)>\s*(?:<!(?P<vars>.*)>)?\s*$")
LOCUS_RE = re.compile(
    r"^<(?P<page>[^<>.,\s]+)\.(?P<num>\d+),(?P<locator>[@+*=&~/!])(?P<type>[A-Z][0-9a-z])"
    r"(?:;(?P<transcriber>\S))?>\s*(?P<text>.*)$"
)
VAR_RE = re.compile(r"\$([A-Z])=(\S)")
TAG_RE = re.compile(r"^<@([A-Z])=(\S)>$")
RARE_RE = re.compile(r"@(\d{3});")

# $I page variable (illustration type); IVTFF format doc Table 6
ILLUSTRATION = {
    "A": "astronomical", "B": "biological", "C": "cosmological", "H": "herbal",
    "P": "pharmaceutical", "S": "stars", "T": "text-only", "Z": "zodiac",
}


def rare_char(code: int) -> str:
    return chr(RARE_BASE + code)


def is_rare(ch: str) -> bool:
    return RARE_BASE + 128 <= ord(ch) <= RARE_BASE + 255


def render(text: str) -> str:
    """Show private-use rare glyph code points as ``@nnn;`` again."""
    return "".join(f"@{ord(c) - RARE_BASE:03d};" if is_rare(c) else c for c in text)


@dataclass
class Token:
    """One blank-delimited chunk of transcription (not proven to be a 'word')."""
    text: str                       # glyphs only; rare codes are private-use chars
    space_after: str | None = None  # '.', ',', '<->', '<~>' or None at end of line
    ligature: bool = False
    unreadable: bool = False        # contains '?'
    alternatives: list[tuple[str, ...]] = field(default_factory=list)  # each [a:b:c] group

    @property
    def uncertain_reading(self) -> bool:
        return bool(self.alternatives)

    @property
    def has_rare(self) -> bool:
        return any(is_rare(c) for c in self.text)


@dataclass
class Locus:
    folio: str
    num: int
    locator: str
    ltype: str                      # e.g. 'P0', 'Lz', 'Cc'
    transcriber: str | None
    raw: str                        # text exactly as in the file (after joining continuations)
    tokens: list[Token]
    comments: list[str]
    paragraph_start: bool
    paragraph_end: bool
    vars: dict[str, str]            # effective page variables + text tags for this line
    tags: dict[str, str]            # text tags set on this line
    warnings: list[str] = field(default_factory=list)

    @property
    def generic(self) -> str:
        return self.ltype[0]

    @property
    def locus_id(self) -> str:
        return f"{self.folio}.{self.num}"

    @property
    def language(self) -> str | None:   # Currier A/B ($L)
        return self.vars.get("L")

    @property
    def hand(self) -> str | None:       # Fagin Davis hand ($H)
        return self.vars.get("H")

    @property
    def currier_hand(self) -> str | None:  # $C
        return self.vars.get("C")

    @property
    def section(self) -> str | None:    # from illustration type ($I)
        i = self.vars.get("I")
        return ILLUSTRATION.get(i, i) if i else None

    @property
    def starts_own_line(self) -> bool:
        return self.locator in "@+*"


@dataclass
class Page:
    folio: str
    vars: dict[str, str]
    comments: list[str] = field(default_factory=list)


@dataclass
class Corpus:
    path: str
    alphabet: str
    version: str
    mode: str | None
    pages: dict[str, Page]
    loci: list[Locus]

    def select(self, generic: str | Iterable[str] | None = "P", language: str | None = None,
               hand: str | None = None, section: str | None = None, folios: Iterable[str] | None = None,
               exclude_nonexistent: bool = True, exclude_extraneous: bool = True) -> list[Locus]:
        """Filter loci. ``generic``: 'P' (running text), 'L' labels, 'C' circular, 'R' radial,
        a string of several (e.g. 'PCR'), or None for all."""
        gen = None if generic is None else set(generic)
        fol = None if folios is None else set(folios)
        out = []
        for lc in self.loci:
            if gen is not None and lc.generic not in gen:
                continue
            if exclude_nonexistent and lc.locator == "!":
                continue
            if exclude_extraneous and lc.ltype == "Lx":
                continue
            if language is not None and lc.language != language:
                continue
            if hand is not None and lc.hand != hand:
                continue
            if section is not None and lc.section != section:
                continue
            if fol is not None and lc.folio not in fol:
                continue
            out.append(lc)
        return out

    def locus_type_counts(self) -> Counter:
        c = Counter(lc.generic for lc in self.loci)
        c["total"] = len(self.loci)
        return c


def _scan_text(raw: str):
    """Tokenise one locus' transliterated text. Returns
    (tokens, comments, para_start, para_end, tags, warnings)."""
    tokens: list[Token] = []
    comments: list[str] = []
    tags: dict[str, str] = {}
    warnings: list[str] = []
    para_start = para_end = False

    buf: list[str] = []
    cur = {"lig": False, "unread": False, "alts": []}

    def flush(sep: str | None):
        if buf:
            tokens.append(Token("".join(buf), sep, cur["lig"], cur["unread"], list(cur["alts"])))
            buf.clear()
            cur.update(lig=False, unread=False, alts=[])
        elif sep is not None:
            if tokens and tokens[-1].space_after is None:
                tokens[-1].space_after = sep
            else:
                warnings.append(f"empty token before separator {sep!r}")

    def add_plain(s: str):
        """Append already-unwrapped glyph text (may hold @nnn; codes and '?')."""
        i = 0
        while i < len(s):
            m = RARE_RE.match(s, i)
            if m:
                buf.append(rare_char(int(m.group(1))))
                i = m.end()
            elif s[i] == "?":
                j = i
                while j < len(s) and s[j] == "?":
                    j += 1
                buf.append("?")        # '?' and '???' both become one unreadable marker
                cur["unread"] = True
                i = j
            elif s[i] in "{}":
                if s[i] == "{":
                    cur["lig"] = True
                i += 1
            elif s[i].isspace():
                i += 1
            else:
                buf.append(s[i])
                i += 1

    i, n = 0, len(raw)
    while i < n:
        c = raw[i]
        if c == "<":
            j = raw.find(">", i)
            if j < 0:
                warnings.append("unclosed '<'")
                break
            inner = raw[i:j + 1]
            if inner.startswith("<!"):
                comments.append(inner[2:-1].strip())
            elif inner == "<%>":
                para_start = True
            elif inner == "<$>":
                para_end = True
            elif inner in ("<->", "<~>"):
                flush(inner)
            elif (m := TAG_RE.match(inner)):
                tags[m.group(1)] = m.group(2)
            else:
                warnings.append(f"unknown in-line item {inner!r}")
            i = j + 1
        elif c == "[":
            j = raw.find("]", i)
            if j < 0:
                warnings.append("unclosed '['")
                break
            opts = tuple(raw[i + 1:j].split(":"))
            cur["alts"].append(tuple(render_plain(o) for o in opts))
            add_plain(opts[0])
            i = j + 1
        elif c == "{":
            j = raw.find("}", i)
            if j < 0:
                warnings.append("unclosed '{'")
                break
            cur["lig"] = True
            add_plain(raw[i + 1:j])
            i = j + 1
        elif c == "." or c == ",":
            flush(c)
            i += 1
        elif c == "@":
            m = RARE_RE.match(raw, i)
            if m:
                buf.append(rare_char(int(m.group(1))))
                i = m.end()
            else:
                warnings.append("stray '@'")
                i += 1
        elif c == "?":
            add_plain("?")
            i += 1
            while i < n and raw[i] == "?":
                i += 1
        elif c.isspace():
            i += 1
        else:
            buf.append(c)
            i += 1
    flush(None)
    return tokens, comments, para_start, para_end, tags, warnings


def render_plain(s: str) -> str:
    """Option string (may contain braces / @nnn;) -> stored alternative with rare codes mapped."""
    s = s.replace("{", "").replace("}", "")
    return RARE_RE.sub(lambda m: rare_char(int(m.group(1))), s)


def parse_text(raw: str):
    """Public wrapper around the in-line scanner (useful for tests)."""
    return _scan_text(raw)


def _parse_vars(s: str | None) -> dict[str, str]:
    return {k: v for k, v in VAR_RE.findall(s or "")}


def parse_lines(lines: Iterable[str], path: str = "<memory>") -> Corpus:
    """Parse the lines of an IVTFF file."""
    alphabet, version, mode = "????", "?", None
    pages: dict[str, Page] = {}
    loci: list[Locus] = []
    page_vars: dict[str, str] = {}
    cur_page: Page | None = None
    tag_state: dict[str, str] = {}
    first = True

    # join '/'-continued lines first (a data line ending in '/' continues on a line starting '/')
    logical: list[str] = []
    cont_open = False
    for line in lines:
        line = line.rstrip("\r\n").rstrip()
        if cont_open:
            if line.startswith("/"):
                piece = line[1:].strip()
                cont_open = piece.endswith("/")
                if cont_open:
                    piece = piece[:-1].rstrip()
                logical[-1] += piece
                continue
            cont_open = False  # malformed continuation: treat the line normally
        if line.startswith("<") and line.endswith("/"):
            line = line[:-1].rstrip()
            cont_open = True
        logical.append(line)

    for line in logical:
        if first:
            first = False
            m = HEADER_RE.match(line)
            if m:
                alphabet, version, mode = m.group("alphabet"), m.group("version"), m.group("mode")
                continue
        if not line.strip():
            continue
        if line.startswith("#"):
            if cur_page is not None and line[1:].strip():
                cur_page.comments.append(line[1:].strip())
            continue
        if not line.startswith("<"):
            continue
        m = LOCUS_RE.match(line)
        if m:
            tokens, comments, ps, pe, tags, warns = _scan_text(m.group("text"))
            tag_state.update({k: v for k, v in tags.items() if v != "@"})
            for k, v in tags.items():
                if v == "@":
                    tag_state.pop(k, None)
            eff = dict(page_vars)
            eff.update(tag_state)
            eff = {k: v for k, v in eff.items() if v != "@"}   # '@' = 'set by text tags, not yet set'
            loci.append(Locus(
                folio=m.group("page"), num=int(m.group("num")), locator=m.group("locator"),
                ltype=m.group("type"), transcriber=m.group("transcriber"), raw=m.group("text"),
                tokens=tokens, comments=comments, paragraph_start=ps, paragraph_end=pe,
                vars=eff, tags=tags, warnings=warns))
            continue
        m = PAGE_RE.match(line)
        if m:
            page_vars = _parse_vars(m.group("vars"))
            tag_state = {}
            cur_page = Page(m.group("page"), dict(page_vars))
            pages[cur_page.folio] = cur_page
            continue
    return Corpus(path, alphabet, version, mode, pages, loci)


def parse_file(path: str | Path) -> Corpus:
    p = Path(path)
    with open(p, encoding="utf-8", errors="replace") as fh:
        return parse_lines(fh, str(p))


# ----- convenience views used by the statistics code -------------------------------------

def words_of(locus: Locus, uncertain: str = "split") -> list[str]:
    """Word strings of a locus. ``uncertain='split'``: a comma is a word space (default);
    ``'join'``: tokens separated only by an uncertain space are concatenated."""
    if uncertain not in ("split", "join"):
        raise ValueError("uncertain must be 'split' or 'join'")
    out: list[str] = []
    glue = False
    for t in locus.tokens:
        if glue and out:
            out[-1] += t.text
        else:
            out.append(t.text)
        glue = uncertain == "join" and t.space_after == ","
    return out


def iter_word_lines(loci: Iterable[Locus], uncertain: str = "split") -> Iterator[list[str]]:
    for lc in loci:
        w = words_of(lc, uncertain)
        if w:
            yield w


def readable(word: str) -> bool:
    return "?" not in word
