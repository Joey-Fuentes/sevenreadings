"""Canon and verse-id encoding. Mirrors packages/sr_core exactly.

Verse id = book*1_000_000 + chapter*1_000 + verse. Verse 0 is chapter-level
material (superscriptions, whole-chapter commentary); 999 is the chapter-end
sentinel. Both Dart and Python have tests on the same fixtures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

BOOK_FACTOR = 1_000_000
CHAPTER_FACTOR = 1_000
CHAPTER_END = 999


@dataclass(frozen=True, slots=True)
class Book:
    id: int
    usfm: str
    osis: str
    name: str
    chapters: int


# fmt: off
CANON: tuple[Book, ...] = tuple(Book(*row) for row in [
    (1, "GEN", "Gen", "Genesis", 50), (2, "EXO", "Exod", "Exodus", 40),
    (3, "LEV", "Lev", "Leviticus", 27), (4, "NUM", "Num", "Numbers", 36),
    (5, "DEU", "Deut", "Deuteronomy", 34), (6, "JOS", "Josh", "Joshua", 24),
    (7, "JDG", "Judg", "Judges", 21), (8, "RUT", "Ruth", "Ruth", 4),
    (9, "1SA", "1Sam", "1 Samuel", 31), (10, "2SA", "2Sam", "2 Samuel", 24),
    (11, "1KI", "1Kgs", "1 Kings", 22), (12, "2KI", "2Kgs", "2 Kings", 25),
    (13, "1CH", "1Chr", "1 Chronicles", 29), (14, "2CH", "2Chr", "2 Chronicles", 36),
    (15, "EZR", "Ezra", "Ezra", 10), (16, "NEH", "Neh", "Nehemiah", 13),
    (17, "EST", "Esth", "Esther", 10), (18, "JOB", "Job", "Job", 42),
    (19, "PSA", "Ps", "Psalms", 150), (20, "PRO", "Prov", "Proverbs", 31),
    (21, "ECC", "Eccl", "Ecclesiastes", 12), (22, "SNG", "Song", "Song of Songs", 8),
    (23, "ISA", "Isa", "Isaiah", 66), (24, "JER", "Jer", "Jeremiah", 52),
    (25, "LAM", "Lam", "Lamentations", 5), (26, "EZK", "Ezek", "Ezekiel", 48),
    (27, "DAN", "Dan", "Daniel", 12), (28, "HOS", "Hos", "Hosea", 14),
    (29, "JOL", "Joel", "Joel", 3), (30, "AMO", "Amos", "Amos", 9),
    (31, "OBA", "Obad", "Obadiah", 1), (32, "JON", "Jonah", "Jonah", 4),
    (33, "MIC", "Mic", "Micah", 7), (34, "NAM", "Nah", "Nahum", 3),
    (35, "HAB", "Hab", "Habakkuk", 3), (36, "ZEP", "Zeph", "Zephaniah", 3),
    (37, "HAG", "Hag", "Haggai", 2), (38, "ZEC", "Zech", "Zechariah", 14),
    (39, "MAL", "Mal", "Malachi", 4), (40, "MAT", "Matt", "Matthew", 28),
    (41, "MRK", "Mark", "Mark", 16), (42, "LUK", "Luke", "Luke", 24),
    (43, "JHN", "John", "John", 21), (44, "ACT", "Acts", "Acts", 28),
    (45, "ROM", "Rom", "Romans", 16), (46, "1CO", "1Cor", "1 Corinthians", 16),
    (47, "2CO", "2Cor", "2 Corinthians", 13), (48, "GAL", "Gal", "Galatians", 6),
    (49, "EPH", "Eph", "Ephesians", 6), (50, "PHP", "Phil", "Philippians", 4),
    (51, "COL", "Col", "Colossians", 4), (52, "1TH", "1Thess", "1 Thessalonians", 5),
    (53, "2TH", "2Thess", "2 Thessalonians", 3), (54, "1TI", "1Tim", "1 Timothy", 6),
    (55, "2TI", "2Tim", "2 Timothy", 4), (56, "TIT", "Titus", "Titus", 3),
    (57, "PHM", "Phlm", "Philemon", 1), (58, "HEB", "Heb", "Hebrews", 13),
    (59, "JAS", "Jas", "James", 5), (60, "1PE", "1Pet", "1 Peter", 5),
    (61, "2PE", "2Pet", "2 Peter", 3), (62, "1JN", "1John", "1 John", 5),
    (63, "2JN", "2John", "2 John", 1), (64, "3JN", "3John", "3 John", 1),
    (65, "JUD", "Jude", "Jude", 1), (66, "REV", "Rev", "Revelation", 22),
    # Deuterocanon (see packages/sr_core canon.dart for the rationale)
    (67, "TOB", "Tob", "Tobit", 14), (68, "JDT", "Jdt", "Judith", 16),
    (69, "ESG", "EsthGr", "Esther (Greek)", 16), (70, "WIS", "Wis", "Wisdom of Solomon", 19),
    (71, "SIR", "Sir", "Sirach", 51), (72, "BAR", "Bar", "Baruch", 6),
    (73, "1MA", "1Macc", "1 Maccabees", 16), (74, "2MA", "2Macc", "2 Maccabees", 15),
    (75, "DAG", "DanGr", "Daniel (Greek additions)", 14),
])
# fmt: on
MAX_BOOK_ID = CANON[-1].id

BY_USFM = {b.usfm: b for b in CANON}
BY_OSIS = {b.osis: b for b in CANON}
BY_NAME = {b.name.lower(): b for b in CANON}

# Display order per tradition. Ids never move; only these lists do.
PROTESTANT_ORDER = list(range(1, 67))
CATHOLIC_ORDER = (
    list(range(1, 17))  # Genesis - Nehemiah
    + [67, 68, 69, 73, 74]  # Tobit, Judith, Esther (Greek), 1-2 Maccabees
    + [18, 19, 20, 21, 22, 70, 71]  # Job - Song, Wisdom, Sirach
    + [23, 24, 25, 72, 26, 27, 75]  # Isaiah - Lamentations, Baruch, Ezekiel, Daniel (+Greek)
    + list(range(28, 40))  # Hosea - Malachi
    + list(range(40, 67))  # New Testament
)
BOOK_ORDERS = {"protestant": PROTESTANT_ORDER, "catholic": CATHOLIC_ORDER}


def verse_id(book: int, chapter: int, verse: int) -> int:
    if not 1 <= book <= MAX_BOOK_ID:
        raise ValueError(f"book out of range: {book}")
    if not 1 <= chapter <= 999 or not 0 <= verse <= 999:
        raise ValueError(f"chapter/verse out of range: {chapter}:{verse}")
    return book * BOOK_FACTOR + chapter * CHAPTER_FACTOR + verse


def decode(vid: int) -> tuple[int, int, int]:
    return vid // BOOK_FACTOR, (vid % BOOK_FACTOR) // CHAPTER_FACTOR, vid % CHAPTER_FACTOR


def chapter_range(book: int, chapter: int) -> tuple[int, int]:
    return verse_id(book, chapter, 0), verse_id(book, chapter, CHAPTER_END)


_REF = re.compile(
    r"^\s*([1-3]?\s?[A-Za-z ]+?)\s+(\d+)(?::(\d+))?(?:\s*[-–]\s*(?:(\d+):)?(\d+))?\s*$"
)


def parse_ref(text: str) -> tuple[int, int]:
    """Parse 'Gen 1:1', 'Genesis 1:1-5', 'Ps 3', 'John 3:16-4:2' into an id range.

    Book may be an OSIS id, USFM code or English name. A bare chapter maps to
    the whole chapter (verse 0..999).
    """
    m = _REF.match(text)
    if not m:
        raise ValueError(f"unparseable reference: {text!r}")
    raw_book, chapter, verse, end_chapter, end_verse = m.groups()
    key = raw_book.replace(" ", "")
    book = BY_OSIS.get(key) or BY_USFM.get(key.upper()) or BY_NAME.get(raw_book.strip().lower())
    if book is None:
        raise ValueError(f"unknown book in reference: {text!r}")
    c = int(chapter)
    if verse is None:
        return chapter_range(book.id, c)
    start = verse_id(book.id, c, int(verse))
    if end_verse is None:
        return start, start
    ec = int(end_chapter) if end_chapter else c
    return start, verse_id(book.id, ec, int(end_verse))
