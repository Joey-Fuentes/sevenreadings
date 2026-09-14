"""Swete's Septuagint from nathans/lxx-swete: one token per line,
`book.chapter.verse word`, in files named `NN.LatinTitle.txt`.

Book selection follows the Catholic canon we ship: 1 Esdras, 3-4 Maccabees,
Odes, Psalms of Solomon and the Old Greek Daniel/Susanna/Bel are skipped
(Theodotion is used for Daniel). 2 Esdras is split into Ezra and Nehemiah.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from .. import db, deuterocanon, versification
from ..context import BuildContext
from ..refs import BY_OSIS
from ..usfm import Verse
from .archive_bible import ArchiveBibleSource

# Swete file number -> target. OSIS id, or a code handled by deuterocanon.
FILES: dict[int, str] = {
    1: "Gen", 2: "Exod", 3: "Lev", 4: "Num", 5: "Deut", 6: "Josh", 8: "Judg", 10: "Ruth",
    11: "1Sam", 12: "2Sam", 13: "1Kgs", 14: "2Kgs", 15: "1Chr", 16: "2Chr",
    18: "EsdrasB", 19: "EsthGr", 20: "Jdt", 21: "Tob", 23: "1Macc", 24: "2Macc",
    27: "Ps", 29: "Prov", 31: "Song", 32: "Job", 33: "Wis", 34: "Sir",
    36: "Hos", 37: "Amos", 38: "Mic", 39: "Joel", 40: "Obad", 41: "Jonah", 42: "Nah",
    43: "Hab", 44: "Zeph", 45: "Hag", 46: "Zech", 47: "Mal", 48: "Isa", 49: "Jer",
    50: "Bar", 51: "Lam", 52: "LJE", 53: "Ezek", 55: "SUS", 57: "DAG", 59: "BEL",
}  # fmt: skip

_LINE = re.compile(r"^(\d+)\.(\d+)\.(\d+)[a-z]*\s+(\S.*)$")
_NAME = re.compile(r"(?:^|/)(\d+)\.([^/]+)\.txt$")


def parse_tokens(
    text: str,
    target: str,
    name: str,
    dropped: list[str] | None = None,
    repaired: list[str] | None = None,
) -> Iterator[Verse]:
    """Group tokens into verses. Letter-suffixed verses (2:35a) fold into
    their base number; the LXX-only material is then joined at ingest.
    Chapter 0 (Sirach's prologue, the Letter's superscription) is kept as
    verse 0 of chapter 1, the slot for chapter-level material; files where
    that happened are reported through `dropped`.

    The digitisation sometimes advances the chapter number one line early,
    labelling the tail of a chapter's last verse as `N+1.<same verse>`
    before `N+1.1` begins. A chapter cannot start at its predecessor's last
    verse number, so such lines are reattached to the verse they belong to;
    `repaired` counts them."""
    current: tuple[int, int] | None = None
    words: list[str] = []

    def book_for(chapter: int) -> tuple[int, int]:
        if target == "EsdrasB":  # 2 Esdras = Ezra 1-10 + Nehemiah 1-13
            return (
                (BY_OSIS["Ezra"].id, chapter)
                if chapter <= 10
                else (BY_OSIS["Neh"].id, chapter - 10)
            )
        return deuterocanon.resolve_catholic(target) or BY_OSIS[target].id, chapter

    def flush() -> Iterator[Verse]:
        if current is not None and words:
            book, chapter = book_for(current[0])
            yield Verse(book, chapter, current[1], " ".join(words))
        words.clear()

    for line in text.splitlines():
        m = _LINE.match(line)
        if not m:
            continue
        key = (int(m.group(2)), int(m.group(3)))
        if key[0] == 0:
            key = (1, 0)
            if dropped is not None and (not dropped or not dropped[-1].startswith(name)):
                dropped.append(f"{name} {m.group(1)}.{m.group(2)}.{m.group(3)} {m.group(4)[:30]}")
        if current is not None and key == (current[0] + 1, current[1]) and key[1] > 1:
            key = current  # stray fragment of the previous verse
            if repaired is not None:
                repaired.append(f"{name.rsplit('/', 1)[-1]} {key[0] + 1}.{key[1]}")
        if key != current:
            yield from flush()
            current = key
        words.append(m.group(4).strip())
    yield from flush()


class SweteLxxSource(ArchiveBibleSource):
    def build(self, ctx: BuildContext) -> None:
        db.add_translation(ctx.conn, self.id, self.cfg, self.cfg.get("sha256", "sample")[:12])
        ref = self.cfg.get("reference", "web")
        verses: list[Verse] = []
        skipped: list[str] = []
        dropped: list[str] = []
        repaired: list[str] = []
        for name, data in self._members(ctx):
            m = _NAME.search(name)
            target = FILES.get(int(m.group(1))) if m else None
            if target is None:
                skipped.append(m.group(2) if m else name)
                continue
            verses.extend(parse_tokens(data.decode("utf-8-sig"), target, name, dropped, repaired))
        if repaired:
            boundaries = sorted(set(repaired))
            files = sorted({b.split(" ")[0] for b in boundaries})
            ctx.log(
                f"{self.id}: {len(boundaries)} stray chapter-boundary fragments reattached "
                f"in {', '.join(files)}"
            )
        if dropped:
            short = [d.rsplit("/", 1)[-1] for d in dropped]
            ctx.log(f"{self.id}: chapter-0 material kept as 1:0 in {len(short)} files: {short}")
        verses = list(deuterocanon.remap_catholic(iter(verses)))
        notes: list[str] = []
        verses = list(versification.apply_lxx(verses, ctx.conn, ref, notes))
        n = db.add_verses(ctx.conn, self.id, verses)
        ctx.conn.commit()
        ctx.log(f"{self.id}: {n} verses in {len({v.book for v in verses})} books")
        if skipped:
            ctx.log(f"{self.id}: skipped: {', '.join(skipped)}")
        for note in notes:
            ctx.log(f"{self.id}: {note}")
        only_t, only_r = versification.check_alignment(ctx.conn, self.id, ref)
        esther = f"{BY_OSIS['Esth'].id}:"
        only_r = [r for r in only_r if not r.startswith(esther)]  # LXX Esther is book 69
        for label, ids in (
            (f"verses with no {ref} counterpart", only_t),
            (f"{ref} OT verses with no {self.id} text", only_r),
        ):
            if ids:
                ctx.log(f"{self.id}: {len(ids)} {label}: {versification.summarize(ids)}")
