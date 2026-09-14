"""Book-code and numbering remaps for editions that carry the deuterocanon.

Catholic editions present Greek Daniel as one book whose chapter 3 has 97
verses (1-23 Hebrew, 24-90 the Prayer of Azariah and Song of the Three,
91-97 = Hebrew 24-30) plus chapters 13 (Susanna) and 14 (Bel and the Dragon).
We store what overlaps Hebrew Daniel under Daniel, at the canonical numbers,
and only the additions under DanGr, so the reader aligns Daniel 3:24 across
every translation and Susanna lives at DanGr 13.

The Letter of Jeremiah is Baruch 6 in the Catholic canon. Editions that ship
S3Y/SUS/BEL as separate books are folded into DanGr the same way.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

from .refs import BY_USFM
from .usfm import Verse

DAN = BY_USFM["DAN"].id
DAG = BY_USFM["DAG"].id
BAR = BY_USFM["BAR"].id

# Codes that are not books in our canon but map into one. Negative ids keep
# them distinct from real books until remap() runs.
_FOLDED = {"LJE": -1, "S3Y": -2, "SUS": -3, "BEL": -4}


def resolve_catholic(code: str) -> int | None:
    b = BY_USFM.get(code)
    return b.id if b else _FOLDED.get(code)


def _at(v: Verse, book: int, chapter: int, verse: int, native: str) -> Verse:
    return Verse(book, chapter, verse, v.text, native_ref=native)


def remap_catholic(verses: Iterator[Verse]) -> Iterator[Verse]:
    for v in verses:
        b, c, n = v.book, v.chapter, v.verse
        if b == -1:  # Letter of Jeremiah -> Baruch 6
            yield _at(v, BAR, 6, n, f"LJE {c}:{n}")
        elif b == -2:  # Song of the Three -> DanGr 3:24-90
            yield _at(v, DAG, 3, n + 23, f"S3Y {c}:{n}")
        elif b == -3:
            yield _at(v, DAG, 13, n, f"SUS {c}:{n}")
        elif b == -4:
            yield _at(v, DAG, 14, n, f"BEL {c}:{n}")
        elif b == DAG:
            if c in (13, 14) or (c == 3 and 24 <= n <= 90):
                yield v  # the additions stay in DanGr, native numbering
            elif c == 3 and n > 90:
                yield _at(v, DAN, 3, n - 67, f"3:{n}")  # 91-97 -> 24-30
            else:
                yield _at(v, DAN, c, n, f"DanGr {c}:{n}")
        else:
            yield v


Resolver = Callable[[str], int | None]
Remapper = Callable[[Iterator[Verse]], Iterator[Verse]]

PROFILES: dict[str, tuple[Resolver, Remapper]] = {
    "catholic": (resolve_catholic, remap_catholic),
}
