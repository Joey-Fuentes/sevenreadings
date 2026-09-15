"""The International Critical Commentary, from the Internet Archive's OCR
of public-domain volumes (T&T Clark / Scribner's, 1895-1928).

Input: one `<id>_hocr.html` per volume (archive.org/download/<id>/...), the
Archive's own OCR with explicit pages and lines. What the parser relies on
is the series' page furniture, present on every commentary page:

    2 EPISTLE TO THE ROMANS [I. 1          (left-hand page: chapter. verse)
    I. 1-7] THE APOSTOLIC SALUTATION 3     (right-hand page: chapter. range)

That head gives every page its chapter, and the notes on the page start
with the verse number in bold: "1. Παῦλος." The section paraphrase opens
with "I. 1-7. THE APOSTOLIC SALUTATION." Introductions, appendices and
indexes have no such head and are skipped.

The OCR is unproofread and it shows (this edition's ABBYY pass reads
"are" as "arc" and clips the first word of some lines); the text ships as
it is, labelled so. A cleaner text would take proofreading, which is
work, not code.

Config: urls/sha256 (hOCR files), books (OSIS code per file), authors (the
volume's author line per file).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from html.parser import HTMLParser

from .. import db, fetch
from ..context import BuildContext
from ..model import Entry
from ..refs import BY_OSIS, verse_id
from .base import Source

_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
# "[I. 1" on a left page, "I. 1-7]" on a right one; OCR often loses the bracket's
# partner, so either bracket alone is accepted next to the numeral.
_HEAD_LEFT = re.compile(r"\[\s*([IVXLC]+)\.\s*(\d+)")
_HEAD_RIGHT = re.compile(r"\b([IVXLC]+)\.\s*(\d+)(?:\s*[-–]\s*(\d+))?\s*\]")
# The OCR drops or misreads the bracket on most pages ("I. 1", "(I. 1", "l. 1-7");
# a short line in capitals with a chapter-and-verse in it is a running head.
_HEAD_ANY = re.compile(r"\b([IVXLC]+)\.\s*(\d+)(?:\s*[-–]\s*(\d+))?\b")
_SECTION = re.compile(r"^([IVXLC]+)\.\s*(\d+)(?:\s*[-–]\s*(\d+))?\.\s+(\S.*)$")
_NOTE = re.compile(r"^(\d{1,3})\.\s+(\S.*)$")
_PAGE_NUMBER = re.compile(r"^\s*(?:\d{1,4}|[ivxlc]{1,7})\s*$")
_SKIP_HEAD = re.compile(r"\b(INDEX|INTRODUCTION|PREFACE|CONTENTS|ABBREVIATIONS)\b")


def roman(numeral: str) -> int:
    total = 0
    for i, ch in enumerate(numeral):
        value = _ROMAN[ch]
        nxt = _ROMAN[numeral[i + 1]] if i + 1 < len(numeral) else 0
        total += -value if value < nxt else value
    return total


class _Hocr(HTMLParser):
    """Pages of lines of words from an hOCR file (IA's ABBYY or Tesseract
    conversions both use ocr_page / ocr_line / ocrx_word)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pages: list[list[str]] = []
        self._line: list[str] | None = None
        self._word: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class") or ""
        if "ocr_page" in cls:
            self.pages.append([])
        elif cls.startswith("ocr_line") or cls in ("ocr_header", "ocr_textfloat", "ocr_caption"):
            self._line = []
        elif "ocrx_word" in cls:
            self._word = []

    def handle_endtag(self, tag):
        if self._word is not None and tag == "span":
            text = "".join(self._word).strip()
            if text and self._line is not None:
                self._line.append(text)
            self._word = None
        elif self._line is not None and tag in ("span", "div", "p"):
            if self._line:
                if not self.pages:
                    self.pages.append([])
                self.pages[-1].append(" ".join(self._line))
            self._line = None

    def handle_data(self, data):
        if self._word is not None:
            self._word.append(data)
        elif self._line is not None and data.strip():
            self._line.append(data.strip())  # a line without word spans


def parse_pages(html: str) -> list[list[str]]:
    p = _Hocr()
    p.feed(html)
    p.close()
    return [page for page in p.pages if page]


@dataclass
class Page:
    chapter: int | None
    first: int | None
    last: int | None
    lines: list[str] = field(default_factory=list)


def _is_head(line: str) -> bool:
    letters = [c for c in line if c.isalpha()]
    return (
        len(line) < 70
        and len(letters) >= 4
        and sum(c.isupper() for c in letters) / len(letters) >= 0.7
    )


def read_page(lines: list[str]) -> Page:
    """Strip the running head and page number; return what the head said."""
    chapter = first = last = None
    body = list(lines)
    for i in range(min(2, len(body))):
        m = _HEAD_LEFT.search(body[i]) or _HEAD_RIGHT.search(body[i])
        if m is None and _is_head(body[i]):
            m = _HEAD_ANY.search(body[i])
        if m and all(c in _ROMAN for c in m.group(1)):
            chapter = roman(m.group(1))
            first = int(m.group(2))
            last = int(m.group(3)) if m.re.groups >= 3 and m.group(3) else first
            del body[i]
            break
    while body and _PAGE_NUMBER.match(body[-1]):
        body.pop()
    while body and _PAGE_NUMBER.match(body[0]):
        body.pop(0)
    return Page(chapter, first, last, body)


def join_lines(lines: list[str]) -> list[str]:
    """Rejoin end-of-line hyphenation; keep line breaks otherwise (the note
    splitter needs to see line starts)."""
    out: list[str] = []
    for line in lines:
        if out and out[-1].endswith("-") and line[:1].islower():
            out[-1] = out[-1][:-1] + line
        else:
            out.append(line)
    return out


@dataclass
class Note:
    chapter: int
    verse: int
    last: int  # == verse for a verse note; the range end for a section
    heading: str | None
    lines: list[str] = field(default_factory=list)


def notes(pages: list[list[str]], report: dict | None = None) -> Iterator[Note]:
    """Walk the pages in order. A page with a chapter head opens or continues
    that chapter; pages without one are skipped until the commentary has
    started and afterwards attached to the current note (a garbled head
    should not lose a page)."""
    current: Note | None = None
    chapter: int | None = None
    last_verse = 0
    started = False
    skipped = kept_blind = 0
    for raw in pages:
        page = read_page(raw)
        if page.chapter is None:
            if not started or (page.lines and _SKIP_HEAD.search(page.lines[0])):
                skipped += 1
                continue
            kept_blind += 1
        else:
            started = True
            if page.chapter != chapter:
                chapter = page.chapter
                last_verse = 0
        for line in join_lines(page.lines):
            s = _SECTION.match(line)
            if s and all(c in _ROMAN for c in s.group(1)) and chapter is not None:
                ch = roman(s.group(1))
                if ch == chapter or ch == chapter + 1:
                    if current is not None:
                        yield current
                    chapter = ch
                    v1 = int(s.group(2))
                    v2 = int(s.group(3)) if s.group(3) else v1
                    if v2 < v1:
                        v2 = v1  # "VIII. 31-30.": the OCR read a 9 as a 0
                    current = Note(ch, v1, v2, s.group(4).strip(" .") or None)
                    last_verse = v1 - 1
                    continue
            n = _NOTE.match(line)
            if n and chapter is not None:
                v = int(n.group(1))
                if last_verse < v <= last_verse + 40 and v <= 176:
                    if current is not None:
                        yield current
                    current = Note(chapter, v, v, None, [n.group(2)])
                    last_verse = v
                    continue
            if current is not None:
                current.lines.append(line)
    if current is not None:
        yield current
    if report is not None:
        report.update(skipped=skipped, kept_blind=kept_blind)


def paragraphs(lines: list[str]) -> str:
    """OCR lines have no paragraph marks; a line that ends a sentence and is
    followed by a line starting a new note-like unit is the best we have.
    Join everything with spaces and let the reader wrap."""
    return " ".join(" ".join(lines).split())


class IccSource(Source):
    def build(self, ctx: BuildContext) -> None:
        db.add_source(ctx.conn, self.id, self.cfg, self._version())
        total = 0
        for osis, author, html in self._volumes(ctx):
            book = BY_OSIS[osis]
            pages = parse_pages(html)
            report: dict = {}
            got: list[Entry] = []
            per_chapter: dict[int, int] = {}
            for note in notes(pages, report):
                text = paragraphs(note.lines)
                if len(text) < 40:
                    continue
                start = verse_id(book.id, note.chapter, note.verse)
                end = max(start, verse_id(book.id, note.chapter, note.last))
                ref = f"{book.name} {note.chapter}:{note.verse}"
                if note.last != note.verse:
                    ref += f"-{note.last}"
                got.append(
                    Entry(
                        self.id, start, end, text, heading=note.heading, citation=f"{author}, {ref}"
                    )
                )
                per_chapter[note.chapter] = per_chapter.get(note.chapter, 0) + 1
            total += db.add_entries(ctx.conn, got)
            ref = self.cfg.get("reference", "web")
            chapters = ", ".join(
                f"{c}:{n}/{self._verses(ctx, ref, book.id, c)}"
                for c, n in sorted(per_chapter.items())
            )
            ctx.log(
                f"{self.id}: {osis} ({author}): {len(got)} notes from {len(pages)} pages; "
                f"{report.get('skipped', 0)} pages without a chapter head skipped, "
                f"{report.get('kept_blind', 0)} kept without one; notes per chapter "
                f"(of verses): {chapters}"
            )
        ctx.conn.commit()
        ctx.log(f"{self.id}: {total} entries")

    @staticmethod
    def _verses(ctx: BuildContext, ref: str, book: int, chapter: int) -> int:
        row = ctx.conn.execute(
            "SELECT COUNT(*) FROM verses WHERE translation_id=? AND verse_id BETWEEN ? AND ?",
            (ref, verse_id(book, chapter, 1), verse_id(book, chapter, 998)),
        ).fetchone()
        return int(row[0]) if row else 0

    def _version(self) -> str:
        shas = self.cfg.get("sha256")
        if isinstance(shas, list) and shas:
            return str(shas[0])[:12]
        return "sample"

    def _volumes(self, ctx: BuildContext) -> Iterator[tuple[str, str, str]]:
        books = list(self.cfg.get("books", []))
        authors = list(self.cfg.get("authors", []))
        if ctx.sample:
            folder = ctx.fixtures / "commentaries" / self.id
            files = sorted(folder.glob("*.html"))
            for i, path in enumerate(files):
                yield books[i], authors[i], path.read_text(encoding="utf-8")
            return
        urls = list(self.cfg["urls"])
        shas = list(self.cfg.get("sha256", ["TODO"] * len(urls)))
        for i, (url, sha) in enumerate(zip(urls, shas, strict=True)):
            yield (
                books[i],
                authors[i],
                fetch.fetch(url, sha).read_text(encoding="utf-8", errors="replace"),
            )
