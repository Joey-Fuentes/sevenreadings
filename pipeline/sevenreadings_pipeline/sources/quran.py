"""The Islamic reading: what the Qur'an says about a Bible passage, in the
Qur'an's own words.

The Qur'an is not a commentary on the Bible, but it retells and answers a
great deal of it — Adam, Noah, Abraham, Joseph, Moses, David, Solomon,
Jonah, Zechariah, Mary, Jesus, the Law, the Judgement. `data/quran_parallels.tsv`
pairs Bible passages with the Qur'an passages that treat them (project
data, CC0; edited by hand, with the basis of each pairing in its note).
Each pairing becomes one entry on the Bible range, quoting the Qur'an
passage(s) in full, and one row per passage in the `parallels` table.

Text: Marmaduke Pickthall, The Meaning of the Glorious Koran (Knopf, New
York, 1930), from Project Gutenberg's eBook #16955, "Three translations of
the Koran side by side", which interleaves Yusuf Ali (Y:), Pickthall (P:)
and Shakir (S:) verse by verse in standard numbering. Only the P: lines
are read.

Config: url, sha256 (the Gutenberg plain text), parallels (path under
pipeline/), reference.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .. import db, fetch
from ..context import BuildContext
from ..db import PIPELINE_DIR
from ..model import Entry, Parallel
from ..refs import parse_ref
from .base import Source

_VERSE = re.compile(r"^(\d{3})\.(\d{3})\s*$")
_CHAPTER = re.compile(r"^\s*Chapter (\d+):\s*$")
_END = "*** END OF THE PROJECT GUTENBERG"
_PASSAGE = re.compile(r"^\s*(\d{1,3}):(\d{1,3})(?:-(\d{1,3}))?\s*$")


@dataclass(frozen=True, slots=True)
class Passage:
    surah: int
    first: int
    last: int

    @property
    def ref(self) -> str:
        return f"{self.surah}:{self.first}" + (f"-{self.last}" if self.last != self.first else "")


def parse_passage(text: str) -> Passage:
    m = _PASSAGE.match(text)
    if not m:
        raise ValueError(f"unparseable Qur'an reference: {text!r}")
    s, a, b = int(m.group(1)), int(m.group(2)), int(m.group(3) or m.group(2))
    return Passage(s, a, max(a, b))


def parse_gutenberg(
    text: str, marker: str = "P"
) -> tuple[dict[tuple[int, int], str], dict[int, str]]:
    """{(surah, ayah): text} for one translation, and {surah: name}."""
    verses: dict[tuple[int, int], str] = {}
    names: dict[int, str] = {}
    current: tuple[int, int] | None = None
    chapter: int | None = None
    buf: list[str] | None = None
    prefix = f"{marker}: "
    for line in text.splitlines():
        if line.startswith(_END):
            break
        if buf is not None:
            if line.strip():
                buf.append(line.strip())
                continue
            if current is not None:
                verses[current] = " ".join(buf)
            buf = None
        if chapter is not None and line.strip():
            names[chapter] = line.strip().title()
            chapter = None
            continue
        c = _CHAPTER.match(line)
        if c:
            chapter = int(c.group(1))
            continue
        v = _VERSE.match(line)
        if v:
            current = (int(v.group(1)), int(v.group(2)))
            continue
        if line.startswith(prefix) and current is not None:
            buf = [line[len(prefix) :].strip()]
    if buf is not None and current is not None:
        verses[current] = " ".join(buf)
    return verses, names


def load_parallels(path: Path) -> Iterator[tuple[str, list[Passage], str]]:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        bible, quran, note = (part.strip() for part in line.split("\t"))
        yield bible, [parse_passage(q) for q in quran.split(";")], note


def render(passage: Passage, verses: dict[tuple[int, int], str], names: dict[int, str]) -> str:
    """One paragraph: the surah and range in bold, then the verses with
    their numbers."""
    name = names.get(passage.surah, "")
    head = (
        f"**Surah {passage.surah}"
        + (f", {name}" if name else "")
        + f", {passage.ref.split(':')[1]}.**"
    )
    parts = [head]
    for ayah in range(passage.first, passage.last + 1):
        text = verses.get((passage.surah, ayah))
        if text:
            parts.append(f"{ayah} {text}")
    return " ".join(parts)


class QuranParallelsSource(Source):
    def build(self, ctx: BuildContext) -> None:
        db.add_source(ctx.conn, self.id, self.cfg, self._version())
        verses, names = parse_gutenberg(self._text(ctx), self.cfg.get("marker", "P"))
        ctx.log(f"{self.id}: {len(verses)} verses in {len(names)} surahs from Pickthall")
        missing: list[str] = []
        entries = parallels = 0
        for bible, passages, note in load_parallels(self._parallels(ctx)):
            start, end = parse_ref(bible)
            paragraphs = []
            found: list[Passage] = []
            for p in passages:
                absent = [a for a in range(p.first, p.last + 1) if (p.surah, a) not in verses]
                if absent:
                    missing.append(f"{p.ref}: {', '.join(map(str, absent))} ({bible})")
                    if len(absent) * 2 > p.last - p.first + 1:
                        continue  # mostly absent: a wrong reference, not a gap in the text
                paragraphs.append(render(p, verses, names))
                found.append(p)
            if not paragraphs:
                continue
            refs = "; ".join(p.ref for p in found)
            entry = Entry(
                self.id,
                start,
                end,
                "\n\n".join(paragraphs),
                heading=note,
                citation=f"Qur'an {refs}, Pickthall (1930)",
            )
            entry_id = db.add_entry(ctx.conn, entry)
            entries += 1
            parallels += db.add_parallels(
                ctx.conn,
                [Parallel(self.id, start, end, f"Qur'an {p.ref}", entry_id, note) for p in found],
            )
        ctx.conn.commit()
        ctx.log(f"{self.id}: {entries} entries, {parallels} parallels")
        if missing:
            ctx.log(
                f"{self.id}: {len(missing)} passages with verses absent from the text "
                f"(this Gutenberg edition merges a few verses into their neighbours; a "
                f"mostly absent passage is dropped as a wrong reference): {missing[:10]}"
            )

    def _version(self) -> str:
        return str(self.cfg.get("sha256", "sample"))[:12]

    def _text(self, ctx: BuildContext) -> str:
        if ctx.sample:
            return (ctx.fixtures / "commentaries" / self.id / "pg16955_sample.txt").read_text(
                encoding="utf-8"
            )
        return fetch.fetch(self.cfg["url"], self.cfg["sha256"]).read_text(
            encoding="utf-8", errors="replace"
        )

    def _parallels(self, ctx: BuildContext) -> Path:
        if ctx.sample:
            return ctx.fixtures / "commentaries" / self.id / "parallels.tsv"
        # PIPELINE_DIR is the package; the data directory is beside it.
        return PIPELINE_DIR.parent / self.cfg.get("parallels", "data/quran_parallels.tsv")
