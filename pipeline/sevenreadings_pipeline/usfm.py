"""Minimal USFM 3 reader: enough for clean verse text from BSB and WEB.

Keeps: verse text, Psalm superscriptions (\\d -> verse 0).
Drops: footnotes, cross references, figures, headings, front matter, formatting.
Character markers (\\w, \\wj, \\nd, \\add ...) are unwrapped; the attribute part
after '|' in \\w is discarded.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from .refs import BY_USFM, verse_id


@dataclass(frozen=True, slots=True)
class Verse:
    book: int
    chapter: int
    verse: int
    text: str

    @property
    def id(self) -> int:
        return verse_id(self.book, self.chapter, self.verse)


_MARKER_LINE = re.compile(r"^\\(\+?[a-z]+[0-9]*)\*?(?:\s+|$)(.*)$", re.S)
_SPLIT_V = re.compile(r"(?=\\v\s)")
_NOTE = re.compile(r"\\(f|fe|x|fig|ef|ex)\s.*?\\\1\*", re.S)
_CHAR = re.compile(r"\\\+?([a-z]+[0-9]*)\s([^\\]*?)\\\+?\1\*", re.S)
_LEFTOVER = re.compile(r"\\\+?[a-z]+[0-9]*\*?")
_WS = re.compile(r"\s+")

# Paragraph-level markers whose text continues the current verse.
_CONTINUE = frozenset(
    """
    p m po pr cls pmo pm pmc pmr pi pi1 pi2 pi3 mi nb pc ph ph1 ph2 b
    q q1 q2 q3 q4 qr qc qm qm1 qm2 qm3 qd li li1 li2 li3 li4 lim lim1 lim2
    tr th1 th2 th3 th4 tc1 tc2 tc3 tc4 lh lf
    """.split()
)
# Markers whose whole line is dropped (headings, front matter, references).
_DROP = frozenset(
    """
    ide usfm sts rem h h1 h2 h3 toc1 toc2 toc3 toca1 toca2 toca3
    mt mt1 mt2 mt3 mt4 mte mte1 mte2 ms ms1 ms2 ms3 mr s s1 s2 s3 s4 sr r sp
    sd sd1 sd2 sd3 cl cp cd ca va vp periph
    imt imt1 imt2 is is1 is2 ip ipi im imi ipq imq ipr iq iq1 iq2 ib
    ili ili1 ili2 iot io io1 io2 io3 iex imte ie qa qs
    """.split()
)


def clean(text: str) -> str:
    text = _NOTE.sub("", text)
    # Unwrap character markers repeatedly (they nest: \wj ... \w ...\w* ... \wj*).
    prev = None
    while prev != text:
        prev = text
        text = _CHAR.sub(lambda m: m.group(2).split("|", 1)[0], text)
    text = _LEFTOVER.sub("", text)
    return _WS.sub(" ", text).strip()


def parse(lines: Iterable[str]) -> Iterator[Verse]:
    book: int | None = None
    chapter = 0
    current: tuple[int, list[str]] | None = None  # (verse number, text parts)

    def flush() -> Iterator[Verse]:
        nonlocal current
        if current is not None and book is not None:
            num, parts = current
            text = clean(" ".join(parts))
            if text:
                yield Verse(book, chapter, num, text)
        current = None

    for raw in lines:
        for line in _SPLIT_V.split(raw.rstrip("\n")):
            if not line.strip():
                continue
            m = _MARKER_LINE.match(line)
            if not m:
                if current is not None:
                    current[1].append(line)
                continue
            marker, rest = m.group(1), m.group(2)
            if marker == "id":
                yield from flush()
                code = rest.split()[0].upper() if rest.split() else ""
                b = BY_USFM.get(code)
                book = b.id if b else None
                chapter = 0
            elif book is None:
                continue  # non-canonical book (Apocrypha, front matter)
            elif marker == "c":
                yield from flush()
                chapter = int(rest.split()[0])
            elif marker == "v":
                yield from flush()
                head, _, text = rest.partition(" ")
                # "1-2" bridged verses take the first number; "1a" drops the suffix.
                num = int(re.match(r"\d+", head).group(0))
                current = (num, [text])
            elif marker == "d":
                yield from flush()
                current = (0, [rest])
            elif marker in _CONTINUE:
                if current is not None and rest:
                    current[1].append(rest)
            elif marker in _DROP:
                continue
            else:
                # Unknown paragraph-level marker: keep text conservatively.
                if current is not None and rest:
                    current[1].append(rest)
    yield from flush()
