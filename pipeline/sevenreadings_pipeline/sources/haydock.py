"""Haydock's Catholic Bible Commentary (1859) and the Douay-Rheims text it
quotes, from John Paul Wohlscheid's transcription: gitlab.com/JohnBlood/haydock,
served at johnblood.gitlab.io/haydock (Trellix-era HTML, one page per chapter).

Pages are `idNNN.html`; the number carries no meaning. Which page is which
chapter comes from the site's two index pages (`index.html` for the New
Testament, `id330.html` for the Old): a bold book name followed by links
"Introduction", "1", "2", ... Stale duplicates exist (two pages titled
"ST. MATTHEW - Chapter 1", a "Numbers 28", a mis-titled Ecclesiastes 3), so
the index is the source of truth and page titles (`GENESIS - Chapter 1`,
`ST. JOHN - Introduction.`, `Psalm 3`, occasionally `Chapter III.`) are
only parsed to report disagreements. Books carry their Douay names (1 KINGS
is 1 Samuel, CANTICLE OF CANTICLES, APOCALYPSE). Numbering is the Vulgate's:
LXX psalm numbers with the title as verse 1, Daniel 13-14 and Esther 11-16
inside those books. A chapter page holds a navigation line, "Notes &
Commentary:" with a "Ver. N." (usually bold) opening each note, footnotes
after a rule of underscores, then a table "Bible Text & Cross-references:"
(spelled five ways) with the Douay-Rheims chapter one verse per line. The
sister Confraternity site under `confraternity/` has the same shape and is
skipped by path.

Two sources read the same archive: `haydock_bible` loads the Douay verses
as a translation, `haydock` loads the notes. Both renumber through
versification.apply_vul; the commentary anchors every note to the canonical
id the Douay verse it comments on landed on, so the two never disagree.
"""

from __future__ import annotations

import fnmatch
import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from html.parser import HTMLParser

from .. import db, fetch, htmltext, versification
from ..context import BuildContext
from ..model import Entry
from ..refs import BY_OSIS, CANON, verse_id
from ..usfm import Verse
from .base import Source

HEADER = "Haydock's Catholic Bible Commentary"
PSALMS = BY_OSIS["Ps"].id

# Douay book names as they appear in page titles -> OSIS. Titles are
# upper-cased and stripped of "ST." and bracketed asides before lookup.
DOUAY_BOOKS: dict[str, str] = {
    "GENESIS": "Gen", "EXODUS": "Exod", "LEVITICUS": "Lev", "NUMBERS": "Num",
    "DEUTERONOMY": "Deut", "JOSUE": "Josh", "JOSHUA": "Josh", "JUDGES": "Judg", "RUTH": "Ruth",
    "1 KINGS": "1Sam", "2 KINGS": "2Sam", "3 KINGS": "1Kgs", "4 KINGS": "2Kgs",
    "1 PARALIPOMENON": "1Chr", "2 PARALIPOMENON": "2Chr",
    "1 ESDRAS": "Ezra", "2 ESDRAS": "Neh", "NEHEMIAS": "Neh",
    "TOBIAS": "Tob", "JUDITH": "Jdt", "ESTHER": "Esth", "JOB": "Job", "PSALMS": "Ps",
    "PROVERBS": "Prov", "ECCLESIASTES": "Eccl",
    "CANTICLE OF CANTICLES": "Song", "CANTICLES": "Song", "CANTICLE": "Song",
    "WISDOM": "Wis", "ECCLESIASTICUS": "Sir", "ISAIAS": "Isa", "JEREMIAS": "Jer",
    "LAMENTATIONS": "Lam", "BARUCH": "Bar", "EZECHIEL": "Ezek", "DANIEL": "Dan",
    "OSEE": "Hos", "JOEL": "Joel", "AMOS": "Amos", "ABDIAS": "Obad", "JONAS": "Jonah",
    "MICHEAS": "Mic", "NAHUM": "Nah", "HABACUC": "Hab", "SOPHONIAS": "Zeph",
    "AGGEUS": "Hag", "ZACHARIAS": "Zech", "MALACHIAS": "Mal",
    "1 MACHABEES": "1Macc", "2 MACHABEES": "2Macc",
    "MATTHEW": "Matt", "MARK": "Mark", "LUKE": "Luke", "JOHN": "John",
    "ACTS OF THE APOSTLES": "Acts", "ACTS": "Acts", "ROMANS": "Rom",
    "1 CORINTHIANS": "1Cor", "2 CORINTHIANS": "2Cor", "GALATIANS": "Gal",
    "EPHESIANS": "Eph", "PHILIPPIANS": "Phil", "COLOSSIANS": "Col",
    "1 THESSALONIANS": "1Thess", "2 THESSALONIANS": "2Thess",
    "1 TIMOTHY": "1Tim", "2 TIMOTHY": "2Tim", "TITUS": "Titus", "PHILEMON": "Phlm",
    "HEBREWS": "Heb", "JAMES": "Jas", "1 PETER": "1Pet", "2 PETER": "2Pet",
    "1 JOHN": "1John", "2 JOHN": "2John", "3 JOHN": "3John", "JUDE": "Jude",
    "APOCALYPSE": "Rev", "REVELATION": "Rev",
}  # fmt: skip

INDEX_PAGES = ("index.html", "id330.html")  # New Testament, Old Testament

_TITLE = re.compile(r"<title>(.*?)</title>", re.I | re.S)
_CHAPTER = re.compile(
    r"^(?P<book>.+?)\s*(?:-\s*(?:Chapter\s+(?P<ch>\d+|[IVXLC]+)|Introduction)|\s(?P<bare>\d+))\.?\s*$",
    re.I,
)
_PSALM = re.compile(r"^Psalm\s+(\d+)\.?\s*$", re.I)
_ASIDE = re.compile(r"\[[^\]]*\]|\([^)]*\)")
_SAINT = re.compile(r"^(?:BIBLE:\s*)?(?:ST\.?|SAINT|THE)\s+|^BIBLE:\s*")
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
# End of the navigation line: "... **Next Chapter** **>**" (or Previous on the last page).
_NAV_END = re.compile(r"Chapter\**\s*\**>\**")
_NOTES = re.compile(r"\**Notes\s*&\s*Commentary:?\**", re.I)
_BIBLE = re.compile(
    r"\**Bible Text\s*(?:&|and)\s*(?:Cross-?\s*references|Commentary)\s*:?\**", re.I
)
_RULE = re.compile(r"^\s*_{5,}\s*$", re.M)
# "Ver. 1." opening a line; bold markers optional (444 pages have none).
_VER = re.compile(r"^[ \t*]*Ver\.?\**\s*(\d+(?:\s*(?:[-–,]|and|&)\s*\d+)*)\.?\**\.?", re.M)
_FOOTNOTE = re.compile(r"^(?=\[\d+\])", re.M)
_FOOTNOTE_LABEL = re.compile(r"^\[(\d+)\]\s*Ver\.?\s*(\d+)")
# "8 text", "*8 text" (a cross-reference mark before the number), or "10(1) text"
# where the psalm is numbered Hebrew(Vulgate): Vulgate 115 is Hebrew 116:10-19.
_VERSE_LINE = re.compile(r"^[*\s]*(\d+)(?:\s*\((\d+)\))?\**[.:]?\s+(\S.*)$")
# A verse number inside a line: the transcription breaks lines at the English
# verse boundaries but numbers the Vulgate's, so "...commanded: 8 and a
# congregation..." (or "thy sword 14 from the enemies", no punctuation at all)
# carries the start of the next verse mid-line. Only the next number in
# sequence splits; bracketed references ("[2 Kings xv.]") have no space
# before the digit, and the Douay spells every other number out.
_INLINE_NUMBER = re.compile(r"(?<=\S)\s+\*?(\d+)(?:\((\d+)\))?\**\.?\s+(?=[^\s:])")
# The cross-reference list under the verses: "6: Matthew iii. 1.", "10(1): 2 Cor.
# iv. 13." A verse typed "9: The chief butler ..." (Genesis 40) is not one: the
# book name and the Roman chapter numeral are required.
_XREF_LINE = re.compile(r"^\d+(?:\(\d+\))?:\s*\d?\s*[A-Z][A-Za-z]*\.?\s+[ivxlc]+\.?(?:\s|$)")
_BRACKETS = re.compile(r"\s*\[[^\]]*\]")
_NUMS = re.compile(r"\d+")


@dataclass(frozen=True, slots=True)
class Page:
    book: int
    chapter: int  # 0 = the book's introduction

    @property
    def name(self) -> str:
        return CANON[self.book - 1].name


@dataclass(frozen=True, slots=True)
class Note:
    verses: tuple[int, ...]  # Vulgate numbers; empty = before the first "Ver." marker
    body: str  # Markdown


def _book_key(raw: str) -> str:
    key = _ASIDE.sub(" ", raw.upper()).split(",")[0]
    key = _SAINT.sub("", " ".join(key.split()))
    return key.strip(" .")


def _number(text: str) -> int:
    if text.isdigit():
        return int(text)
    total = 0
    for i, c in enumerate(text.upper()):  # Roman: "III", "XIV"
        v = _ROMAN[c]
        total += -v if i + 1 < len(text) and _ROMAN[text[i + 1].upper()] > v else v
    return total


def identify(html: str) -> Page | str | None:
    """Classify a page by its <title>: a Page for chapter/introduction pages,
    the unrecognised book name when the title has the chapter shape but the
    book is unknown, None for every other page (indexes, prefaces, notes).
    The index (see parse_index) decides which pages are used; this is the
    fallback and the cross-check."""
    if HEADER not in html:
        return None
    m = _TITLE.search(html)
    if not m:
        return None
    title = " ".join(htmltext.blocks(m.group(1))).strip()
    if ps := _PSALM.match(title):
        return Page(PSALMS, int(ps.group(1)))
    ch = _CHAPTER.match(title)
    if not ch:
        return None
    key = _book_key(ch.group("book"))
    osis = DOUAY_BOOKS.get(key)
    if osis is None:
        return key
    return Page(BY_OSIS[osis].id, _number(ch.group("ch") or ch.group("bare") or "0"))


class _Index(HTMLParser):
    """Bold book names, then links: "Introduction" -> chapter 0, a number
    (Psalm links read "9 [9 & 10]") -> that chapter. Bold inside a link is
    the psalm number, not a book."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pages: dict[str, Page] = {}
        self.unknown: set[str] = set()
        self._book: int | None = None
        self._bold: list[str] | None = None
        self._link: tuple[str, list[str]] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href") or ""
            self._link = (href.rsplit("/", 1)[-1].split("#")[0], [])
        elif tag in ("b", "strong") and self._link is None:
            self._bold = []

    def handle_endtag(self, tag):
        if tag == "a" and self._link is not None:
            name, parts = self._link
            self._link = None
            text = " ".join("".join(parts).split())
            m = re.match(r"(\d+)", text)
            if self._book is None or not name.lower().endswith(".html"):
                return
            if text.lower().startswith("introduction"):
                self.pages.setdefault(name, Page(self._book, 0))
            elif m:
                self.pages.setdefault(name, Page(self._book, int(m.group(1))))
        elif tag in ("b", "strong") and self._bold is not None:
            key = _book_key("".join(self._bold))
            self._bold = None
            osis = DOUAY_BOOKS.get(key)
            if osis is not None:
                self._book = BY_OSIS[osis].id
            elif (
                key and key.replace(" ", "").isalpha() and len(key) < 40 and "TESTAMENT" not in key
            ):
                self.unknown.add(key)

    def handle_data(self, data):
        if self._link is not None:
            self._link[1].append(data)
        elif self._bold is not None:
            self._bold.append(data)


def parse_index(html: str) -> tuple[dict[str, Page], set[str]]:
    """(file name -> Page, bold headings that are not books) for one index page."""
    p = _Index()
    p.feed(html)
    p.close()
    return p.pages, p.unknown


def _text(html: str) -> str:
    return "\n".join(htmltext.blocks(html, keep_bold=True))


def _after_nav(text: str) -> str:
    m = _NAV_END.search(text)
    return text[m.end() :] if m else text


def sections(html: str) -> tuple[str, str]:
    """(commentary text, Bible-text section) of a page, both after the
    navigation line. Introductions have no markers: everything is commentary.
    The last Bible-text header counts (Proverbs 15 has a stray one above its
    notes); a Bible section printed above the notes is handled too."""
    text = _after_nav(_text(html))
    notes = _NOTES.search(text)
    headers = list(_BIBLE.finditer(text))
    bible = headers[-1] if headers else None
    if bible and notes and bible.start() < notes.start():
        return text[notes.end() :], text[bible.end() : notes.start()]
    if bible:
        commentary = text[notes.end() if notes else 0 : bible.start()]
        return _BIBLE.sub("", commentary), text[bible.end() :]
    return text[notes.end() if notes else 0 :], ""


def _clean(body: str) -> str:
    body = _RULE.sub("", body)
    lines = [ln.strip() for ln in body.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def parse_notes(commentary: str) -> list[Note]:
    """Split the commentary on its bold "Ver. N." markers; footnotes (after
    the rule of underscores, "[1] Ver. 1. ...") are appended to the note on
    the verse they name, or kept as a trailing chapter-level note."""
    parts = _RULE.split(commentary, maxsplit=1)
    body, foot = parts[0], parts[1] if len(parts) > 1 else ""
    notes: list[Note] = []
    pieces = _VER.split(body)
    lead = _clean(pieces[0])
    if lead:
        notes.append(Note((), lead))
    for label, chunk in zip(pieces[1::2], pieces[2::2], strict=True):
        nums = tuple(int(n) for n in _NUMS.findall(label))
        text = _clean(chunk)
        if text and nums:
            notes.append(Note((min(nums), max(nums)), text))

    orphans: list[str] = []
    for raw in _FOOTNOTE.split(foot):
        fn = _clean(raw)
        if not fn:
            continue
        m = _FOOTNOTE_LABEL.match(fn)
        target = int(m.group(2)) if m else None
        for i, note in enumerate(notes):
            if note.verses and target is not None and note.verses[0] <= target <= note.verses[-1]:
                notes[i] = Note(note.verses, note.body + "\n\n" + fn)
                break
        else:
            orphans.append(fn)
    if orphans:
        notes.append(Note((), "\n\n".join(orphans)))
    return notes


def parse_bible(
    section: str, book: int, chapter: int, aliases: dict[int, int] | None = None
) -> list[Verse]:
    """The Douay-Rheims verses of a chapter page, in Vulgate numbering.
    Stops at the rule or the first line of the cross-reference list; the
    italic chapter summary before verse 1 is dropped; cross-reference
    asterisks and bracketed references are stripped from the text. Lines
    numbered "10(1)" carry the Hebrew number first and the Vulgate's own in
    brackets; the Vulgate one is kept (the renumbering does the rest) and
    `aliases`, when given, records Hebrew -> Vulgate for the numbers that are
    not also plain verses of the page, because Haydock's notes on those
    psalms say "Ver. 11" meaning 11(2)."""
    verses: list[Verse] = []
    dual: dict[int, int] = {}

    def add(number: int, text: str) -> None:
        verses.append(Verse(book, chapter, number, text))

    def extend(text: str) -> None:
        if verses:
            last = verses[-1]
            verses[-1] = Verse(book, chapter, last.verse, last.text + " " + text)

    for line in section.split("\n"):
        if _RULE.match(line):
            break
        line = line.strip()
        if not line:
            continue
        if verses and _XREF_LINE.match(line):
            break  # the cross-reference list; not every page puts a rule before it
        m = _VERSE_LINE.match(line)
        if m:
            if m.group(2):
                dual[int(m.group(1))] = int(m.group(2))
            add(int(m.group(2) or m.group(1)), m.group(3))
        elif verses and not line.startswith("*"):
            extend(line)
        else:
            continue
        # The rest of the line may hold the next verse, marked mid-line.
        while verses:
            last = verses[-1]
            hit = next(
                (
                    h
                    for h in _INLINE_NUMBER.finditer(last.text)
                    if int(h.group(2) or h.group(1)) == last.verse + 1
                ),
                None,
            )
            if hit is None:
                break
            if hit.group(2):
                dual[int(hit.group(1))] = int(hit.group(2))
            verses[-1] = Verse(book, chapter, last.verse, last.text[: hit.start()])
            add(last.verse + 1, last.text[hit.end() :].strip())
    if aliases is not None:
        plain = {v.verse for v in verses}
        aliases.update({h: v for h, v in dual.items() if h not in plain})
    out = []
    for v in verses:
        text = " ".join(_BRACKETS.sub("", v.text).replace("*", "").split())
        if text:
            out.append(Verse(v.book, v.chapter, v.verse, text))
    return out


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


class _Pages:
    """Shared page iterator: fixtures in sample mode, the pinned archive
    otherwise. Yields (file name, html, Page) for the pages the site index
    links to; falls back to page titles only when no index page is found."""

    def __init__(self, source_id: str, cfg: dict) -> None:
        self.id = source_id
        self.cfg = cfg
        self.notes: list[str] = []  # what the index selection had to decide

    def _members(self, ctx: BuildContext) -> Iterator[tuple[str, str]]:
        if ctx.sample:
            folder = ctx.fixtures / "commentaries" / "haydock"
            for path in sorted(folder.rglob("*.html")):
                name = path.relative_to(folder).as_posix()
                if "confraternity/" not in name:
                    yield name, path.read_text(encoding="utf-8")
            return
        pattern = self.cfg.get("glob", "*/id[0-9]*.html")
        archive = fetch.fetch(self.cfg["url"], self.cfg.get("sha256"))
        with zipfile.ZipFile(archive) as z:
            names = sorted(i.filename for i in z.infolist() if not i.is_dir())
            wanted = [
                n
                for n in names
                if "/confraternity/" not in n
                and (fnmatch.fnmatch(n, pattern) or n.rsplit("/", 1)[-1] in INDEX_PAGES)
            ]
            if not any(fnmatch.fnmatch(n, pattern) for n in wanted):
                preview = "\n  ".join(names[:40])
                raise SystemExit(
                    f"{self.id}: glob {pattern!r} matched none of {len(names)} members. "
                    f"First entries:\n  {preview}\nAdjust `glob` in sources.toml."
                )
            for n in wanted:
                yield n, _decode(z.read(n))

    def pages(self, ctx: BuildContext) -> Iterator[tuple[str, str, Page]]:
        index: dict[str, Page] = {}
        unknown: set[str] = set()
        members: list[tuple[str, str]] = []
        for name, html in self._members(ctx):
            base = name.rsplit("/", 1)[-1]
            if base in INDEX_PAGES:
                found, odd = parse_index(html)
                index.update(found)
                unknown |= odd
            else:
                members.append((name, html))
        if not index:
            self.notes.append("no index page found; pages identified by title only")
            for name, html in members:
                page = identify(html)
                if isinstance(page, str):
                    unknown.add(page)
                elif page is not None:
                    yield name, html, page
        else:
            seen: set[str] = set()
            disagree: list[str] = []
            skipped: list[str] = []
            for name, html in members:
                base = name.rsplit("/", 1)[-1]
                page = index.get(base)
                if page is None:
                    t = _TITLE.search(html)
                    skipped.append(f"{base}: {' '.join(t.group(1).split()) if t else '?'}"[:60])
                    continue
                seen.add(base)
                titled = identify(html)
                if isinstance(titled, Page) and titled != page:
                    disagree.append(f"{base}: title says {titled.name} {titled.chapter}")
                yield name, html, page
            missing = sorted(set(index) - seen)
            self.notes.append(
                f"index lists {len(index)} pages; {len(skipped)} archived pages not in the "
                f"index were skipped: {skipped[:30]}"
            )
            if missing:
                self.notes.append(
                    f"{len(missing)} indexed pages missing from the archive: {missing[:12]}"
                )
            if disagree:
                self.notes.append(
                    f"{len(disagree)} page titles disagree with the index (index wins): "
                    f"{disagree[:12]}"
                )
        if unknown:
            self.notes.append(f"unrecognised book names: {sorted(unknown)}")

    def version(self) -> str:
        return str(self.cfg.get("sha256", "sample"))[:12]


def _check_reference(ctx: BuildContext, sid: str, ref: str) -> None:
    n = ctx.conn.execute("SELECT COUNT(*) FROM verses WHERE translation_id=?", (ref,)).fetchone()
    if not n[0]:
        ctx.log(f"{sid}: reference {ref!r} has no verses; psalm titles stay at Vulgate verse 1")


class DouayRheimsSource(Source):
    """kind = haydock_bible: the Douay text quoted on every Haydock chapter page."""

    def build(self, ctx: BuildContext) -> None:
        pages = _Pages(self.id, self.cfg)
        db.add_translation(ctx.conn, self.id, self.cfg, pages.version())
        ref = self.cfg.get("reference", "web")
        _check_reference(ctx, self.id, ref)
        verses: list[Verse] = []
        empty: list[str] = []
        chapters = 0
        for name, html, page in pages.pages(ctx):
            if page.chapter == 0:
                continue
            chapters += 1
            _, bible = sections(html)
            found = parse_bible(bible, page.book, page.chapter)
            if not found:
                empty.append(f"{page.name} {page.chapter} ({name.rsplit('/', 1)[-1]})")
            verses.extend(found)
        notes: list[str] = []
        verses = list(versification.apply_vul(verses, ctx.conn, ref, notes))
        n = db.add_verses(ctx.conn, self.id, verses)
        ctx.conn.commit()
        books = len({v.book for v in verses})
        ctx.log(f"{self.id}: {n} verses in {books} books from {chapters} chapter pages")
        for note in pages.notes + notes:
            ctx.log(f"{self.id}: {note}")
        if empty:
            ctx.log(f"{self.id}: {len(empty)} chapter pages without Bible text: {empty[:12]}")
        only_t, only_r = versification.check_alignment(ctx.conn, self.id, ref, (1, 66))
        for label, ids in (
            (f"verses with no {ref} counterpart", only_t),
            (f"{ref} verses with no {self.id} text", only_r),
        ):
            if ids:
                ctx.log(f"{self.id}: {len(ids)} {label}: {versification.summarize(ids)}")


class HaydockSource(Source):
    """kind = haydock: the notes, anchored where the Douay verses landed."""

    def build(self, ctx: BuildContext) -> None:
        pages = _Pages(self.id, self.cfg)
        db.add_source(ctx.conn, self.id, self.cfg, pages.version())
        ref = self.cfg.get("reference", "web")
        _check_reference(ctx, self.id, ref)
        total = 0
        no_markers: list[str] = []
        unanchored: list[str] = []
        for name, html, page in pages.pages(ctx):
            commentary, bible = sections(html)
            if page.chapter == 0:
                text = _clean(commentary)
                if text:
                    total += db.add_entries(ctx.conn, [self._intro(page, text)])
                continue
            trace: versification.Trace = {}
            aliases: dict[int, int] = {}
            douay = parse_bible(bible, page.book, page.chapter, aliases)
            list(versification.apply_vul(douay, ctx.conn, ref, None, trace))
            for hebrew, vulgate in aliases.items():
                if (page.book, page.chapter, vulgate) in trace:
                    trace[(page.book, page.chapter, hebrew)] = trace[
                        (page.book, page.chapter, vulgate)
                    ]
            notes = parse_notes(commentary)
            if not any(n.verses for n in notes):
                no_markers.append(f"{page.name} {page.chapter} ({name.rsplit('/', 1)[-1]})")
            entries = [self._entry(page, note, trace, unanchored) for note in notes]
            total += db.add_entries(ctx.conn, entries)
        ctx.conn.commit()
        ctx.log(f"{self.id}: {total} entries")
        for note in pages.notes:
            ctx.log(f"{self.id}: {note}")
        if no_markers:
            ctx.log(
                f"{self.id}: {len(no_markers)} chapter pages without Ver. markers: "
                f"{no_markers[:12]}"
            )
        if unanchored:
            ctx.log(
                f"{self.id}: {len(unanchored)} notes on verses missing from the Douay text, "
                f"placed by rule: {unanchored[:12]}"
            )

    def _intro(self, page: Page, text: str) -> Entry:
        return Entry(
            self.id,
            verse_id(page.book, 1, 0),
            verse_id(page.book, 1, 0),
            text,
            heading=f"{page.name}: introduction",
            citation=f"{page.name}, introduction",
        )

    def _entry(
        self, page: Page, note: Note, trace: versification.Trace, unanchored: list[str]
    ) -> Entry:
        book, chapter = page.book, page.chapter
        if not note.verses:
            if book == PSALMS and (book, chapter, 1) in trace:
                vid = trace[(book, chapter, 1)]  # the psalm's title note
                return Entry(self.id, vid, vid, note.body, citation=self._cite(vid, chapter, 1))
            b, c, _ = versification.vul_map(book, chapter, 1)
            return Entry(
                self.id,
                verse_id(b, c, 0),
                verse_id(b, c, 999),
                note.body,
                heading=f"{page.name} {chapter}: introduction",
                citation=f"{CANON[b - 1].name} {c}",
            )
        a, z = note.verses[0], note.verses[-1]
        start, end = trace.get((book, chapter, a)), trace.get((book, chapter, z))
        if start is None or end is None:
            unanchored.append(f"{page.name} {chapter}:{a}")
            start = start or verse_id(*versification.vul_map(book, chapter, a))
            end = end or verse_id(*versification.vul_map(book, chapter, z))
        if end < start:
            start, end = end, start
        cite = self._cite(start, chapter, a)
        if end != start:
            cite += f"-{end % 1000}" if end // 1000 == start // 1000 else f"-{self._ref(end)}"
        return Entry(self.id, start, end, note.body, citation=cite)

    @staticmethod
    def _ref(vid: int) -> str:
        b, c, v = vid // 1_000_000, vid // 1000 % 1000, vid % 1000
        return f"{CANON[b - 1].name} {c}" if v == 0 else f"{CANON[b - 1].name} {c}:{v}"

    def _cite(self, vid: int, vul_chapter: int, vul_verse: int) -> str:
        c, v = vid // 1000 % 1000, vid % 1000
        cite = self._ref(vid)
        if (c, v) != (vul_chapter, vul_verse):
            cite += f" (Douay {vul_chapter}:{vul_verse})"
        return cite
