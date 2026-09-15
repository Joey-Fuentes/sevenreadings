"""St. John Chrysostom's New Testament homilies from the Christian Classics
Ethereal Library's ThML editions of the Nicene and Post-Nicene Fathers,
series 1, volumes 10-14 (Schaff, 1886-1890): Matthew (10), Acts and Romans
(11), 1-2 Corinthians (12), Galatians to Philemon (13), John and Hebrews (14).

ThML is XML-shaped HTML. What matters here: nested `<div1>`..`<div4>`
elements carry `title`, `shorttitle` and `type` ("Homily", "Chapter"); a
homily's first child is `<scripCom passage="Matt. 1:1" parsed="|Matt|1|1|0|0"
osisRef="Bible:Matt.1.1"/>` naming the passage preached on; `<p>` holds the
text, `<note>` the editors' footnotes (dropped), `<pb>` page breaks (dropped),
`<scripRef>` inline citations (text kept). The file header states
`<DC.Rights>Public Domain</DC.Rights>`; CCEL's own staff description in the
header is not shipped.

Anchoring: a homily covers its passage up to the verse before the next
homily's passage in the same book (the chapter-end sentinel when the next
one opens a chapter); two homilies on the same verse each cover that verse.
A leading homily with no passage is the series' introduction and sits on
verse 0 of the book's first chapter.
"""

from __future__ import annotations

import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from html.parser import HTMLParser

from .. import db, fetch
from ..context import BuildContext
from ..model import Entry
from ..refs import BY_NAME, BY_OSIS, CANON, CHAPTER_END, decode, verse_id
from .base import Source

_DIV = re.compile(r"^div(\d)$")
_PARSED = re.compile(r"^\|?([1-3]?[A-Za-z]+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)")
_OSIS = re.compile(r"Bible:([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)")
# Division titles that carry the passage when there is no scripCom (volume
# 13 throughout, a few homilies elsewhere): "Ephesians 1:1--2",
# "Ephesians 2:11,12", "Matthew XXVI. 26, 27, 28", "Matthew 1. 22, 23".
_TITLE = re.compile(
    r"^(?P<book>(?:[1-3]\s)?[A-Za-z]+(?:\s[A-Za-z]+)?)\.?\s+(?P<ch>[IVXLC]+|\d+)[.:]\s*(?P<v>\d+)"
)
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def _int(numeral: str) -> int:
    if numeral.isdigit():
        return int(numeral)
    total = 0
    for i, ch in enumerate(numeral):
        value = _ROMAN[ch]
        nxt = _ROMAN[numeral[i + 1]] if i + 1 < len(numeral) else 0
        total += -value if value < nxt else value
    return total


def passage_from_title(title: str) -> tuple[int, int, int] | None:
    m = _TITLE.match(title.strip())
    if not m:
        return None
    book = BY_NAME.get(m.group("book").lower())
    if book is None:
        return None
    return book.id, _int(m.group("ch")), int(m.group("v"))


@dataclass
class Unit:
    """One division of the file with its passage (book, chapter, verse) if any."""

    level: int
    title: str
    shorttitle: str
    kind: str
    passage: tuple[int, int, int] | None = None
    paragraphs: list[str] = field(default_factory=list)
    top: int = 0  # index of the enclosing div1, to group a series

    @property
    def heading(self) -> str:
        return self.shorttitle or self.title


def _passage(attrs: dict[str, str]) -> tuple[int, int, int] | None:
    m = _PARSED.match(attrs.get("parsed") or "") or _OSIS.search(attrs.get("osisref") or "")
    if not m:
        return None
    book = BY_OSIS.get(m.group(1))
    if book is None:
        return None
    return book.id, int(m.group(2)), int(m.group(3))


class _Thml(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.units: list[Unit] = []
        self._open: list[Unit] = []
        self._body = False
        self._skip = 0  # inside <note> or the head
        self._buf: list[str] | None = None
        self._top = -1

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        tag = tag.lower()
        if tag == "thml.body":
            self._body = True
            return
        if not self._body:
            return
        if tag == "note":
            self._skip += 1
            if self._buf is not None:
                self._buf.append(" ")  # footnotes sit between words without spaces
            return
        if self._skip:
            return
        if m := _DIV.match(tag):
            level = int(m.group(1))
            if level == 1:
                self._top += 1
            unit = Unit(level, a.get("title", ""), a.get("shorttitle", ""), a.get("type", ""))
            unit.top = self._top
            self._open.append(unit)
            self.units.append(unit)
        elif tag == "scripcom" and self._open and self._open[-1].passage is None:
            self._open[-1].passage = _passage(a)
        elif tag == "p":
            self._buf = []
        elif self._buf is not None:
            if tag == "br":
                self._buf.append("\n")
            elif tag in ("i", "em"):
                self._buf.append("*")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "note":
            self._skip = max(0, self._skip - 1)
            return
        if self._skip or not self._body:
            return
        if _DIV.match(tag):
            if self._open:
                self._open.pop()
        elif tag == "p":
            if self._buf is not None and self._open:
                text = " ".join("".join(self._buf).split())
                text = re.sub(r"\*\s*\*", "", text).strip()
                if text:
                    self._open[-1].paragraphs.append(text)
            self._buf = None
        elif tag in ("i", "em") and self._buf is not None:
            self._buf.append("*")

    def handle_data(self, data):
        if self._buf is not None and not self._skip:
            self._buf.append(data)


def parse_units(text: str) -> list[Unit]:
    p = _Thml()
    p.feed(text)
    p.close()
    return p.units


def _body(unit: Unit) -> str:
    """Drop the short heading lines that open a homily ("Homily II.",
    "Matt. I. 1.", the quoted verse) and join the rest as Markdown."""
    paras = list(unit.paragraphs)
    while paras and len(paras[0]) < 120:
        paras.pop(0)
    return "\n\n".join(paras)


def _label(name: str, start: int, end: int) -> str:
    _, c, v = decode(start)
    _, ec, ev = decode(end)
    if end == start:
        return f"{name} {c}:{v}"
    if ev == CHAPTER_END:
        return f"{name} {c}:{v}ff." if ec == c else f"{name} {c}:{v}-{ec}"  # to a chapter end
    if ec == c:
        return f"{name} {c}:{v}-{ev}"
    return f"{name} {c}:{v}-{ec}:{ev}"


def entries(units: list[Unit], source_id: str, skipped: list[str] | None = None) -> Iterator[Entry]:
    """Anchor every unit that names a passage (scripCom first, title second);
    report the substantial ones that don't."""
    for u in units:
        if u.passage is None and u.paragraphs:
            u.passage = passage_from_title(u.title)
    anchored = [u for u in units if u.passage is not None and u.paragraphs]
    first_of: dict[int, Unit] = {}
    for u in anchored:
        first_of.setdefault(u.top, u)
    for u in units:
        if u.passage is not None or not u.paragraphs or u.level < 2:
            continue
        first = first_of.get(u.top)
        if u.kind.lower() == "homily" and first is not None and units.index(u) < units.index(first):
            book = first.passage[0]  # type: ignore[index]
            name = CANON[book - 1].name
            yield Entry(
                source_id,
                verse_id(book, 1, 0),
                verse_id(book, 1, 0),
                _body(u),
                heading=u.heading,
                citation=f"{u.heading} (introduction to {name})",
            )
        elif skipped is not None and len(u.paragraphs) >= 3:
            skipped.append(u.title[:40])
    for i, u in enumerate(anchored):
        book, ch, v = u.passage  # type: ignore[misc]
        start = verse_id(book, ch, v)
        nxt = anchored[i + 1] if i + 1 < len(anchored) else None
        if nxt is None or nxt.passage[0] != book:  # type: ignore[index]
            end = verse_id(book, ch, CHAPTER_END)  # the last homily runs to its chapter end
        else:
            _, nc, nv = nxt.passage  # type: ignore[misc]
            if (nc, nv) > (ch, v):
                end = verse_id(book, nc, nv - 1) if nv > 1 else verse_id(book, nc - 1, CHAPTER_END)
            else:
                end = start  # another homily on the same verse
        text = _body(u)
        if not text:
            continue
        label = _label(CANON[book - 1].name, start, end)
        yield Entry(
            source_id, start, end, text, heading=u.heading, citation=f"{u.heading}, {label}"
        )


class CcelThmlSource(Source):
    def build(self, ctx: BuildContext) -> None:
        db.add_source(ctx.conn, self.id, self.cfg, self._version())
        total = 0
        skipped: list[str] = []
        books: set[int] = set()
        for name, text in self._files(ctx):
            units = parse_units(text)
            got = list(entries(units, self.id, skipped))
            books |= {e.start_verse_id // 1_000_000 for e in got}
            n = db.add_entries(ctx.conn, got)
            total += n
            ctx.log(
                f"{self.id}: {name.rsplit('/', 1)[-1]}: {n} entries from {len(units)} divisions"
            )
        ctx.conn.commit()
        names = ", ".join(CANON[b - 1].osis for b in sorted(books))
        ctx.log(f"{self.id}: {total} entries in {len(books)} books: {names}")
        if skipped:
            ctx.log(f"{self.id}: {len(skipped)} divisions with no passage skipped: {skipped[:10]}")

    def _version(self) -> str:
        shas = self.cfg.get("sha256")
        if isinstance(shas, list):
            return shas[0][:12] if shas else "sample"
        return str(shas or "sample")[:12]

    def _files(self, ctx: BuildContext) -> Iterator[tuple[str, str]]:
        if ctx.sample:
            folder = ctx.fixtures / "commentaries" / self.id
            for path in sorted(folder.glob("*.xml")):
                yield path.name, path.read_text(encoding="utf-8")
            return
        urls = self.cfg["urls"]
        shas = self.cfg.get("sha256", ["TODO"] * len(urls))
        for url, sha in zip(urls, shas, strict=True):
            path = fetch.fetch(url, sha)
            if url.lower().endswith(".zip"):
                with zipfile.ZipFile(path) as z:
                    for info in z.infolist():
                        if info.filename.lower().endswith(".xml"):
                            yield info.filename, z.read(info).decode("utf-8", errors="replace")
            else:
                yield url.rsplit("/", 1)[-1], path.read_text(encoding="utf-8", errors="replace")
