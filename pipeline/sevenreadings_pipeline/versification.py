"""Masoretic (MT) and Septuagint (LXX) numbering -> canonical verse ids.

Two mechanisms:
  * Chapter-boundary shifts are a fixed rule table: (osis, mt_chapter,
    mt_from, mt_to, en_chapter, en_from) maps MT verses mt_from..mt_to onto
    English verses starting at en_from. Verses not covered map to themselves.
  * Psalm superscriptions counted as MT verses are derived from data: the
    difference between the MT verse count and the English verse count of the
    same psalm (English titles are stored as verse 0). MT title verses map to
    verse 0; the rest shift down.

Where two MT verses land on one English verse (1 Sam 20:42, Neh 9:38 ...)
their text is joined. `check_alignment` reports any remaining gaps so the
table can be corrected against the data rather than trusted.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterable, Iterator

from .refs import BY_OSIS, CANON, decode, verse_id
from .usfm import Verse

# fmt: off
MT_RULES: list[tuple[str, int, int, int, int, int]] = [
    ("Gen", 32, 1, 1, 31, 55), ("Gen", 32, 2, 33, 32, 1),
    ("Exod", 7, 26, 29, 8, 1), ("Exod", 8, 1, 28, 8, 5),
    ("Exod", 20, 14, 23, 20, 17),
    ("Exod", 21, 37, 37, 22, 1), ("Exod", 22, 1, 30, 22, 2),
    ("Lev", 5, 20, 26, 6, 1), ("Lev", 6, 1, 23, 6, 8),
    ("Num", 17, 1, 15, 16, 36), ("Num", 17, 16, 28, 17, 1),
    ("Num", 25, 19, 19, 26, 1),
    ("Num", 30, 1, 1, 29, 40), ("Num", 30, 2, 17, 30, 1),
    ("Deut", 5, 18, 30, 5, 21),
    ("Deut", 13, 1, 1, 12, 32), ("Deut", 13, 2, 19, 13, 1),
    ("Deut", 23, 1, 1, 22, 30), ("Deut", 23, 2, 26, 23, 1),
    ("Deut", 28, 69, 69, 29, 1), ("Deut", 29, 1, 28, 29, 2),
    ("1Sam", 21, 1, 1, 20, 42), ("1Sam", 21, 2, 16, 21, 1),
    ("1Sam", 24, 1, 1, 23, 29), ("1Sam", 24, 2, 23, 24, 1),
    ("2Sam", 19, 1, 1, 18, 33), ("2Sam", 19, 2, 44, 19, 1),
    ("1Kgs", 5, 1, 14, 4, 21), ("1Kgs", 5, 15, 32, 5, 1),
    ("1Kgs", 22, 44, 44, 22, 43), ("1Kgs", 22, 45, 54, 22, 44),
    ("2Kgs", 12, 1, 1, 11, 21), ("2Kgs", 12, 2, 22, 12, 1),
    ("1Chr", 5, 27, 41, 6, 1), ("1Chr", 6, 1, 66, 6, 16),
    ("1Chr", 12, 5, 5, 12, 4), ("1Chr", 12, 6, 41, 12, 5),
    ("2Chr", 1, 18, 18, 2, 1), ("2Chr", 2, 1, 17, 2, 2),
    ("2Chr", 13, 23, 23, 14, 1), ("2Chr", 14, 1, 14, 14, 2),
    ("Neh", 3, 33, 38, 4, 1), ("Neh", 4, 1, 17, 4, 7),
    ("Neh", 7, 68, 72, 7, 69),
    ("Neh", 10, 1, 1, 9, 38), ("Neh", 10, 2, 40, 10, 1),
    ("Job", 40, 25, 32, 41, 1), ("Job", 41, 1, 26, 41, 9),
    ("Eccl", 4, 17, 17, 5, 1), ("Eccl", 5, 1, 19, 5, 2),
    ("Song", 7, 1, 1, 6, 13), ("Song", 7, 2, 14, 7, 1),
    ("Isa", 8, 23, 23, 9, 1), ("Isa", 9, 1, 20, 9, 2),
    ("Isa", 64, 1, 11, 64, 2),
    ("Jer", 8, 23, 23, 9, 1), ("Jer", 9, 1, 25, 9, 2),
    ("Ezek", 21, 1, 5, 20, 45), ("Ezek", 21, 6, 37, 21, 1),
    ("Dan", 3, 31, 33, 4, 1), ("Dan", 4, 1, 34, 4, 4),
    ("Dan", 6, 1, 1, 5, 31), ("Dan", 6, 2, 29, 6, 1),
    ("Hos", 2, 1, 2, 1, 10), ("Hos", 2, 3, 25, 2, 1),
    ("Hos", 12, 1, 1, 11, 12), ("Hos", 12, 2, 15, 12, 1),
    ("Hos", 14, 1, 1, 13, 16), ("Hos", 14, 2, 10, 14, 1),
    ("Joel", 3, 1, 5, 2, 28), ("Joel", 4, 1, 21, 3, 1),
    ("Jonah", 2, 1, 1, 1, 17), ("Jonah", 2, 2, 11, 2, 1),
    ("Mic", 4, 14, 14, 5, 1), ("Mic", 5, 1, 14, 5, 2),
    ("Nah", 2, 1, 1, 1, 15), ("Nah", 2, 2, 14, 2, 1),
    ("Zech", 2, 1, 4, 1, 18), ("Zech", 2, 5, 17, 2, 1),
    ("Mal", 3, 19, 24, 4, 1),
]
# fmt: on

_RULES_BY_BOOK: dict[int, list[tuple[int, int, int, int, int]]] = {}
for _osis, _c, _a, _b, _ec, _ev in MT_RULES:
    _RULES_BY_BOOK.setdefault(BY_OSIS[_osis].id, []).append((_c, _a, _b, _ec, _ev))

PSALMS = BY_OSIS["Ps"].id


def _shift(book: int, chapter: int, verse: int) -> tuple[int, int]:
    for c, a, b, ec, ev in _RULES_BY_BOOK.get(book, ()):
        if c == chapter and a <= verse <= b:
            return ec, ev + (verse - a)
    return chapter, verse


def psalm_title_offsets(
    conn: sqlite3.Connection,
    reference: str,
    mt_counts: dict[int, int],
    mt_first: dict[int, str],
    notes: list[str] | None = None,
) -> dict[int, int]:
    """Per psalm: how many leading MT verses are the superscription.

    Normally the MT/English verse-count difference. When the counts agree
    but the English has a title (verse 0) and the MT's first verse is at most
    three tokens, the title is a separate MT verse and a split elsewhere in
    the psalm hides it (Psalm 13, "For the choirmaster. A psalm of David.").
    Embedded short titles (Ps 25, 87, 100, 130) run to five tokens or more
    because the verse text follows. Such cases are reported through `notes`.
    """
    rows = conn.execute(
        "SELECT verse_id/1000%1000 AS ch, "
        "SUM(verse_id%1000>0), SUM(verse_id%1000=0) FROM verses "
        "WHERE translation_id=? AND verse_id/1000000=? GROUP BY ch",
        (reference, PSALMS),
    ).fetchall()
    en_counts = {ch: n for ch, n, _ in rows}
    en_titled = {ch for ch, _, t in rows if t}
    out: dict[int, int] = {}
    for ch, n in mt_counts.items():
        off = max(0, n - en_counts.get(ch, n))
        if off == 0 and ch in en_titled and len(mt_first.get(ch, "").split()) <= 3:
            off = 1
            if notes is not None:
                notes.append(f"Psalm {ch}: title verse inferred (equal counts)")
        out[ch] = off
    return out


Mapper = Callable[[int, int, int], tuple[int, int]]


def _renumber(
    verses: Iterable[Verse],
    mapper: Mapper,
    conn: sqlite3.Connection,
    reference: str,
    notes: list[str] | None = None,
) -> Iterator[Verse]:
    """Apply `mapper` (book, chapter, verse) -> (chapter, verse) in MT-style
    numbering, then psalm-title offsets against the reference, then join
    verses that landed on the same canonical id."""
    mapped: list[tuple[Verse, int, int]] = []
    mt_counts: dict[int, int] = {}
    mt_first: dict[int, str] = {}
    for v in verses:
        ch, n = mapper(v.book, v.chapter, v.verse)
        mapped.append((v, ch, n))
        if v.book == PSALMS:
            mt_counts[ch] = max(mt_counts.get(ch, 0), n)
            if n == 1:
                mt_first[ch] = v.text
    offsets = psalm_title_offsets(conn, reference, mt_counts, mt_first, notes) if mt_counts else {}

    merged: dict[int, list[Verse]] = {}
    for v, ch, n in mapped:
        if v.book == PSALMS:
            off = offsets.get(ch, 0)
            n = 0 if n <= off else n - off
        native = None if (ch, n) == (v.chapter, v.verse) else f"{v.chapter}:{v.verse}"
        merged.setdefault(verse_id(v.book, ch, n), []).append(Verse(v.book, ch, n, v.text, native))
    for parts in merged.values():
        first = parts[0]
        if len(parts) == 1:
            yield first
            continue
        text = " ".join(p.text for p in parts)
        natives = ", ".join(p.native_ref or f"{p.chapter}:{p.verse}" for p in parts)
        yield Verse(first.book, first.chapter, first.verse, text, natives)


def apply_mt(
    verses: Iterable[Verse],
    conn: sqlite3.Connection,
    reference: str,
    notes: list[str] | None = None,
) -> Iterator[Verse]:
    """Renumber MT-numbered verses to canonical ids, joining collisions."""
    return _renumber(verses, _shift, conn, reference, notes)


# --- Septuagint ---------------------------------------------------------
# Swete's edition (as digitised) follows the ENGLISH chapter breaks almost
# everywhere the Hebrew and English differ, so MT_RULES do not apply to it.
# Verified against the data (`srp probe`): the Hebrew break survives only in
# the six chapters listed in LXX_MT_STYLE. Everything else here maps Swete's
# own numbering straight to English. Known gaps left at their LXX numbers:
# Exodus 36-40 and Proverbs 24-31 (reordered in the LXX).

JER = BY_OSIS["Jer"].id
KGS1 = BY_OSIS["1Kgs"].id

# fmt: off
# (osis, lxx_chapter, v_from, v_to, en_chapter, en_v_from): LXX -> English.
LXX_RULES: list[tuple[str, int, int, int, int, int]] = [
    ("Lev", 6, 31, 40, 7, 1), ("Lev", 7, 1, 28, 7, 11),
    ("Num", 13, 1, 1, 12, 16), ("Num", 13, 2, 34, 13, 1),
    ("Josh", 9, 28, 33, 8, 30),
    ("1Sam", 20, 43, 43, 20, 42),
    ("1Sam", 24, 1, 1, 23, 29), ("1Sam", 24, 2, 23, 24, 1),
    ("1Kgs", 22, 44, 44, 22, 43), ("1Kgs", 22, 45, 54, 22, 44),
    ("Job", 39, 31, 35, 40, 1), ("Job", 40, 1, 19, 40, 6),
    ("Job", 40, 20, 27, 41, 1), ("Job", 41, 1, 26, 41, 9),
    ("Dan", 3, 31, 33, 4, 1), ("Dan", 4, 1, 34, 4, 4),
    ("Hos", 14, 1, 1, 13, 16), ("Hos", 14, 2, 10, 14, 1),
    ("Jonah", 2, 1, 1, 1, 17), ("Jonah", 2, 2, 11, 2, 1),
    ("Nah", 2, 1, 1, 1, 15), ("Nah", 2, 2, 14, 2, 1),
]
# The oracles against the nations (MT 46-51) sit after 25:13 in the LXX.
LXX_JER_RULES: list[tuple[int, int, int, int, int]] = [
    (25, 14, 20, 49, 34),                      # Elam
    (26, 1, 999, 46, 1),                       # Egypt
    (27, 1, 999, 50, 1), (28, 1, 999, 51, 1),  # Babylon
    (29, 1, 7, 47, 1), (29, 8, 23, 49, 7),     # Philistines, Edom
    (30, 1, 5, 49, 1), (30, 6, 11, 49, 28), (30, 12, 16, 49, 23),  # Ammon, Kedar, Damascus
    (31, 1, 999, 48, 1),                       # Moab
    (32, 1, 999, 25, 15),                      # the cup of wrath
    *[(c, 1, 999, c - 7, 1) for c in range(33, 51)],  # 33-50 -> 26-43
    (51, 1, 30, 44, 1), (51, 31, 35, 45, 1),
]
# fmt: on
_LXX_BY_BOOK: dict[int, list[tuple[int, int, int, int, int]]] = {}
for _osis, _c, _a, _b, _ec, _ev in LXX_RULES:
    _LXX_BY_BOOK.setdefault(BY_OSIS[_osis].id, []).append((_c, _a, _b, _ec, _ev))


def _lxx_psalm(ch: int, v: int) -> tuple[int, int]:
    """LXX psalm numbering -> MT numbering (verses still count the title)."""
    if ch <= 8 or 148 <= ch <= 151:
        return ch, v
    if ch == 9:
        return (9, v) if v <= 21 else (10, v - 21)
    if ch <= 112:
        return ch + 1, v
    if ch == 113:
        return (114, v) if v <= 8 else (115, v - 8)
    if ch == 114:
        return 116, v
    if ch == 115:
        return 116, v + 9
    if ch <= 145:
        return ch + 1, v
    if ch == 146:
        return 147, v
    return 147, v + 11  # 147


def _lxx_map(book: int, chapter: int, verse: int) -> tuple[int, int]:
    if book == PSALMS:
        return _lxx_psalm(chapter, verse)
    if book == JER:
        for c, a, b, mc, mv in LXX_JER_RULES:
            if c == chapter and a <= verse <= b:
                return mc, mv + (verse - a)
    if book == KGS1 and chapter in (20, 21):  # 3 Kingdoms swaps Ahab's chapters
        return 41 - chapter, verse
    for c, a, b, ec, ev in _LXX_BY_BOOK.get(book, ()):
        if c == chapter and a <= verse <= b:
            return ec, ev + (verse - a)
    return chapter, verse


def apply_lxx(
    verses: Iterable[Verse],
    conn: sqlite3.Connection,
    reference: str,
    notes: list[str] | None = None,
) -> Iterator[Verse]:
    """Renumber Septuagint verses to canonical ids, joining collisions."""
    return _renumber(verses, _lxx_map, conn, reference, notes)


def check_alignment(conn: sqlite3.Connection, tid: str, reference: str, ot_only: bool = True):
    """Return (ids only in tid, ids only in reference) restricted to shared books."""
    books = "AND verse_id/1000000 <= 39" if ot_only else ""
    only_t = conn.execute(
        f"SELECT verse_id FROM verses WHERE translation_id=? {books} EXCEPT "
        f"SELECT verse_id FROM verses WHERE translation_id=? {books}",
        (tid, reference),
    ).fetchall()
    only_r = conn.execute(
        f"SELECT verse_id FROM verses WHERE translation_id=? {books} AND verse_id%1000>0 EXCEPT "
        f"SELECT verse_id FROM verses WHERE translation_id=? {books}",
        (reference, tid),
    ).fetchall()

    def fmt(rows):
        return [f"{b}:{c}:{v}" for (b, c, v) in (decode(r[0]) for r in rows)]

    return fmt(only_t), fmt(only_r)


def summarize(ids: list[str], per_book: int = 6) -> str:
    """'Gen 9 (2:25, 5:32, ...), Exod 42 (...)' for a list of b:c:v ids."""
    by_book: dict[int, list[str]] = {}
    for ref in ids:
        b, c, v = ref.split(":")
        by_book.setdefault(int(b), []).append(f"{c}:{v}")
    parts = []
    for b, refs in sorted(by_book.items()):
        name = CANON[b - 1].osis
        more = ", ..." if len(refs) > per_book else ""
        parts.append(f"{name} {len(refs)} ({', '.join(refs[:per_book])}{more})")
    return "; ".join(parts)
