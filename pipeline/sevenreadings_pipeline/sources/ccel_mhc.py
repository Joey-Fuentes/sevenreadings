"""Matthew Henry's Commentary on the Whole Bible, from CCEL's public-domain
HTML edition (ccel.org/h/henry/mhc2/, six volume ZIPs).

Files are MHC<bb><ccc>.HTM: bb = book 01-66 in Protestant order (our ids),
ccc = chapter, 000 = the book's introduction. A chapter page holds an
introduction, then sections: a heading like "The Creation. B. C. 4004.",
the KJV text of the verses covered, then the exposition. Verse ranges are
read off the quoted KJV text.

Anchoring: book introduction -> chapter 1 verse 0; chapter introduction ->
the whole chapter (0-999); each section -> its verse range.
"""

from __future__ import annotations

import re
import zipfile
from collections.abc import Iterator

from .. import db, fetch, htmltext
from ..context import BuildContext
from ..model import Entry
from ..refs import CANON, verse_id
from .base import Source

_NAME = re.compile(r"MHC(\d\d)(\d\d\d)\.HTM$", re.I)
# The edition marks each section with anchors: one per verse covered
# (<A NAME="Ge1_1">), then <A NAME="Sec1">. The heading is a table whose
# first <I> is the title and whose second cell holds "B. C." / "A. D." + year.
_ANCHOR = re.compile(r'<A\s+NAME="(?P<name>[^"]+)"\s*>', re.I)
_VERSE_ANCHOR = re.compile(r"^[A-Za-z0-9]+?\d+_(\d+)$")
_SEC_ANCHOR = re.compile(r"^Sec\d+$", re.I)
_TABLE = re.compile(r"<TABLE.*?</TABLE>", re.I | re.S)
_TITLE = re.compile(r"<I>(.*?)</I>", re.I | re.S)
_DATE = re.compile(r"(B\. ?C\.|A\. ?D\.)\s*(?:</FONT>)?\s*(\d{1,4})", re.I)
_TAGS = re.compile(r"<[^>]+>")
_KJV = re.compile(r"<FONT\s+SIZE=\+1>", re.I)
_BODY_START = re.compile(r"<!--\s*\(Begin Body\)\s*-->", re.I)
_CHAP = re.compile(r"^\*?\*?CHAP\.\s+[IVXLC]+\.?\*?\*?$")
_NAV = re.compile(
    r"Table of Contents|^\[?\[?Previous|^\[?\[?Next|Commentary on the Whole Bible"
    r"|^Chapter \d+$|Christian Classics Ethereal Library|Public domain text"
)


def _clean_blocks(html: str, name: str) -> list[str]:
    out = []
    for block in htmltext.blocks(html):
        if _NAV.search(block) or _CHAP.match(block) or len(block) < 2:
            continue
        if len(block) < 120 and not re.search(r"[a-z]", block):
            continue  # display headings: "G E N E S I S", "AN", "EXPOSITION,"
        if block.strip("* ").lower() == name.lower():
            continue  # the book-name heading on introduction pages
        out.append(block)
    return out


def _sections(html: str) -> Iterator[tuple[list[int], str]]:
    """Yield (verse numbers, section html) for each Sec anchor; the first
    item is the introduction with an empty verse list."""
    starts: list[tuple[int, int, list[int]]] = []  # (content start, anchor start, verses)
    pending: list[int] = []
    pending_pos: int | None = None
    for m in _ANCHOR.finditer(html):
        n = m.group("name")
        if _SEC_ANCHOR.match(n):
            starts.append((m.end(), pending_pos if pending_pos is not None else m.start(), pending))
            pending, pending_pos = [], None
        elif (v := _VERSE_ANCHOR.match(n)) and v.group(1) != "0":
            if pending_pos is None:
                pending_pos = m.start()
            pending.append(int(v.group(1)))
    body_start = _BODY_START.search(html)
    first = body_start.end() if body_start else 0
    yield [], html[first : starts[0][1] if starts else len(html)]
    for i, (content, _, verses) in enumerate(starts):
        stop = starts[i + 1][1] if i + 1 < len(starts) else len(html)
        yield verses, html[content:stop]


def parse_chapter(html: str, book: int, chapter: int) -> Iterator[Entry]:
    """Yield entries for one chapter page (or a book introduction if chapter == 0)."""
    name = CANON[book - 1].name
    for verses, part in _sections(html):
        title = None
        if verses:
            table = _TABLE.search(part)
            if table:
                head = table.group(0)
                t = _TITLE.search(head)
                d = _DATE.search(head)
                title = _TAGS.sub("", t.group(1)).strip(" .") if t else None
                if title and d:
                    title = f"{title}. {d.group(1)} {d.group(2)}."
                part = part[: table.start()] + part[table.end() :]
            kjv = _KJV.search(part)
            if kjv:  # drop the quoted KJV paragraph; the reader has its own Bibles
                close = part.find("</P>", kjv.end())
                open_ = part.rfind("<P", 0, kjv.start())
                part = (
                    part[: open_ if open_ >= 0 else kjv.start()]
                    + part[close + 4 if close >= 0 else kjv.end() :]
                )
        text = "\n\n".join(_clean_blocks(part, name)).strip()
        if not text:
            continue
        if chapter == 0:
            yield Entry(
                "matthew_henry",
                verse_id(book, 1, 0),
                verse_id(book, 1, 0),
                text,
                heading=f"{name}: introduction",
                citation=f"{name}, introduction",
            )
        elif not verses:
            yield Entry(
                "matthew_henry",
                verse_id(book, chapter, 0),
                verse_id(book, chapter, 999),
                text,
                heading=f"{name} {chapter}: introduction",
                citation=f"{name} {chapter}",
            )
        else:
            a, b = min(verses), max(verses)
            ref = f"{name} {chapter}:{a}" + (f"-{b}" if b != a else "")
            yield Entry(
                "matthew_henry",
                verse_id(book, chapter, a),
                verse_id(book, chapter, b),
                text,
                heading=title,
                citation=ref,
            )


class CcelMhcSource(Source):
    def build(self, ctx: BuildContext) -> None:
        db.add_source(ctx.conn, self.id, self.cfg, str(self.cfg.get("sha256", "sample"))[:12])
        total = 0
        unanchored: dict[int, int] = {}
        for fname, html in self._pages(ctx):
            m = _NAME.search(fname)
            if not m or not 1 <= int(m.group(1)) <= 66:
                continue
            book, chapter = int(m.group(1)), int(m.group(2))
            entries = list(parse_chapter(html, book, chapter))
            if chapter and not any(
                e.start_verse_id % 1000 or e.end_verse_id % 1000 != 999 for e in entries
            ):
                unanchored[book] = unanchored.get(book, 0) + 1
            total += db.add_entries(ctx.conn, entries)
        ctx.conn.commit()
        ctx.log(f"{self.id}: {total} entries")
        if unanchored:
            worst = ", ".join(f"{CANON[b - 1].osis} {n}" for b, n in sorted(unanchored.items()))
            ctx.log(f"{self.id}: chapters with no verse-anchored section (intro only): {worst}")

    def _pages(self, ctx: BuildContext) -> Iterator[tuple[str, str]]:
        if ctx.sample:
            folder = ctx.fixtures / "commentaries" / self.id
            for path in sorted(folder.glob("*.HTM")):
                yield path.name, path.read_text(encoding="utf-8")
            return
        urls = self.cfg["urls"]
        shas = self.cfg.get("sha256", ["TODO"] * len(urls))
        for url, sha in zip(urls, shas, strict=True):
            archive = fetch.fetch(url, sha)
            with zipfile.ZipFile(archive) as z:
                for info in sorted(z.infolist(), key=lambda i: i.filename):
                    if info.filename.upper().endswith(".HTM"):
                        raw = z.read(info)
                        try:
                            yield info.filename, raw.decode("utf-8")
                        except UnicodeDecodeError:
                            yield info.filename, raw.decode("cp1252", errors="replace")
