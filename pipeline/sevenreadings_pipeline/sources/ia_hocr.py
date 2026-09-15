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
# Running heads as this OCR renders them: "[I. 1", "I. 1.]", "I. 17.J", "[l. 7.",
# "1. 16, 17.]", "[I 10, 17.", "[I. 1 7". A chapter numeral (with l or 1 for I),
# an optional period, a verse number, and a bracket on one side or the other,
# which may have become J or gone missing.
_CH = r"([IVXLC]+|[l1])"
_HEAD_LEFT = re.compile(r"\[\s*" + _CH + r"\.?\s*(\d+)")
_HEAD_RIGHT = re.compile(r"(?<![A-Za-z])" + _CH + r"\.?\s+(\d+)(?:\s*[-–,]\s*(\d+))?\.?\s*[\]J]")
# A short line in capitals with a chapter-and-verse in it is a running head even
# when both brackets are gone.
_HEAD_ANY = re.compile(r"(?<![A-Za-z])" + _CH + r"\.?\s+(\d+)(?:\s*[-–,]\s*(\d+))?\b")
# Section headings: "I. 1-7. THE APOSTOLIC SALUTATION.", "I. 16, 17. That message".
_SECTION = re.compile(r"^([IVXLC]+)\.\s*(\d+)(?:\s*[-–,]\s*(\d+))*\.\s+(\S.*)$")
# The section's own note, a bare range: "1-7. In writing to the Church".
_RANGE = re.compile(r"^(\d{1,3})\s*[-–,]\s*(\d{1,3})\.\s+((?!\d+\b)\S.*)$")
# A verse note: the number, a period, then a word ("4. 6pia0«Vros" is Greek the
# OCR turned into digits) but not a bare number ("37. 52 ;" is a wrapped
# scripture reference). "I." for "1." at the start of a chapter.
_NOTE = re.compile(r"^(\d{1,3})\.\s+((?!\d+\b)\S.*)$")
_NOTE_ONE = re.compile(r"^[Il]\.\s+((?!\d+\b)\S.*)$")
_PAGE_NUMBER = re.compile(r"^\s*(?:\d{1,4}|[ivxlc]{1,7})\s*$")
_SKIP_HEAD = re.compile(r"\b(INDEX|INTRODUCTION|PREFACE|CONTENTS|ABBREVIATIONS)\b")


def roman(numeral: str) -> int:
    if numeral in ("l", "1"):
        return 1
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
        if m:
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


def _section_range(m: re.Match) -> tuple[int, int]:
    """First and last verse of a heading like "I. 1-7." or "I. 16, 17."."""
    numbers = [int(x) for x in re.findall(r"\d+", m.group(0).split(".", 2)[1])]
    v1, v2 = numbers[0], max(numbers)
    return v1, max(v1, v2)  # "VIII. 31-30.": the OCR read a 9 as a 0


def _section_chapter(lines: list[str], limit: int = 12) -> int | None:
    """The chapter of the first section heading on the page, if any. Page 1
    of a volume carries the book title where the running head would be and
    is recognised this way ("I. 1-7. THE APOSTOLIC SALUTATION.")."""
    for line in lines[:limit]:
        m = _SECTION.match(line)
        if m and all(c in _ROMAN for c in m.group(1)):
            return roman(m.group(1))
    return None


def notes(
    pages: list[list[str]],
    report: dict | None = None,
    limits: dict[int, int] | None = None,
) -> Iterator[Note]:
    """Walk the pages in order. A page with a chapter head opens or continues
    that chapter; pages without one are skipped until the commentary has
    started and afterwards attached to the current note (a garbled head
    should not lose a page). `limits` maps chapter to its verse count, so a
    stray number ("37. 52;", a wrapped reference) cannot become a verse."""
    limits = limits or {}
    current: Note | None = None
    chapter: int | None = None
    last_verse = 0
    seen_one = False  # a note on verse 1 of the current chapter has been made
    started = False
    skipped = kept_blind = 0

    def cap() -> int:
        return limits.get(chapter or 0, 176)

    for raw in pages:
        page = read_page(raw)
        head = page.chapter
        if head is None and not started:
            head = _section_chapter(page.lines)
        # A head continues the chapter, or advances it by one with evidence: a
        # verse number that opens a chapter, a section heading for the new
        # chapter on the page, or the old chapter at its end. "II 7.J" in the
        # middle of chapter I is a misread I, not chapter II.
        if head is not None and chapter is not None and head != chapter:
            advancing = head == chapter + 1 and (
                (page.first is not None and page.first <= 3)
                or _section_chapter(page.lines, 40) == head
                or last_verse >= cap() - 3
            )
            if not advancing:
                head = None
        if head is None:
            if not started or (page.lines and _SKIP_HEAD.search(page.lines[0])):
                skipped += 1
                continue
            kept_blind += 1
        else:
            started = True
            if head != chapter:
                chapter = head
                last_verse = 0
                seen_one = False
        for line in join_lines(page.lines):
            s = _SECTION.match(line)
            if s and all(c in _ROMAN for c in s.group(1)) and chapter is not None:
                ch = roman(s.group(1))
                if ch == chapter or ch == chapter + 1:
                    if current is not None:
                        yield current
                    if ch != chapter:
                        seen_one = False
                    chapter = ch
                    v1, v2 = _section_range(s)
                    text = s.group(4).strip(" .")
                    # "I. 1-7. THE APOSTOLIC SALUTATION." names the section; "I. 16, 17.
                    # That message, humble as it may seem," opens its paraphrase.
                    if text.isupper():
                        current = Note(ch, v1, v2, text or None)
                    else:
                        current = Note(ch, v1, v2, None, [text])
                    last_verse = v1 - 1
                    continue
            r = _RANGE.match(line)
            if r and chapter is not None:
                v1, v2 = int(r.group(1)), int(r.group(2))
                if last_verse <= v1 <= v2 <= cap() and v1 <= last_verse + 10:
                    if current is not None:
                        yield current
                    current = Note(chapter, v1, v2, None, [r.group(3)])
                    last_verse = max(last_verse, v1)
                    continue
            n = _NOTE.match(line)
            if n:
                v, text = int(n.group(1)), n.group(2)
                ok = last_verse < v <= min(last_verse + 12, cap())
            else:
                one = _NOTE_ONE.match(line) if last_verse <= 1 and not seen_one else None
                v, text, ok = 1, one.group(1) if one else "", one is not None
            if ok and chapter is not None:
                if current is not None:
                    yield current
                current = Note(chapter, v, v, None, [text])
                last_verse = max(last_verse, v)
                seen_one = seen_one or v == 1
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
            limits = self._limits(ctx, self.cfg.get("reference", "web"), book.id)
            for note in notes(pages, report, limits):
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
            chapters = ", ".join(
                f"{c}:{n}/{limits.get(c, 0)}" for c, n in sorted(per_chapter.items())
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
    def _limits(ctx: BuildContext, ref: str, book: int) -> dict[int, int]:
        """Verse count per chapter of `book` in the reference translation."""
        rows = ctx.conn.execute(
            "SELECT verse_id / 1000 % 1000 AS c, MAX(verse_id % 1000) FROM verses "
            "WHERE translation_id=? AND verse_id BETWEEN ? AND ? GROUP BY c",
            (ref, verse_id(book, 1, 1), verse_id(book, 150, 998)),
        ).fetchall()
        return {int(c): int(v) for c, v in rows}

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
