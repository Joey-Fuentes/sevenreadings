"""Bible texts fetched as a zip archive (typically a pinned GitHub commit).

Config keys: url, sha256, glob (fnmatch over archive member paths, `*`
crosses directories), format, optionally versification ("mt"), and `align`
("ot" or "nt": which testament to compare with the reference translation
after loading; "mt" sources default to "ot").

Formats:
  ref_tab_text  one verse per line: `Matt 1:1<TAB>text` (SBLGNT plain text)
  oshb_osis     Open Scriptures Hebrew Bible OSIS XML, one book per file
  byz_csv       byztxt/byzantine-majority-text `csv-unicode/ccat/no-variants`:
                one book per file named by a three-letter code, header
                `chapter,verse,text`, a pilcrow opening paragraph-initial verses
"""

from __future__ import annotations

import csv
import fnmatch
import io
import re
import zipfile
from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree as ET

from .. import db, fetch, versification
from ..context import BuildContext
from ..refs import BY_OSIS, BY_USFM
from ..usfm import Verse
from .base import Source

_REF_LINE = re.compile(r"^\s*([1-3]?[A-Za-z]+)\s+(\d+):(\d+)\s*\t?\s+(.*\S)\s*$")

# byztxt file stems that are not USFM codes.
_BYZ_CODES = {"MAR": "MRK", "JOH": "JHN", "JAM": "JAS", "1JO": "1JN", "2JO": "2JN", "3JO": "3JN"}
_PILCROW = "\u00b6"


def parse_ref_tab_text(text: str, name: str, skipped: list[str] | None = None) -> Iterator[Verse]:
    """Yield verses; lines that are not `Book c:v<TAB>text` (book titles,
    section headings) are appended to `skipped` when given."""
    for line in text.splitlines():
        if not line.strip():
            continue
        m = _REF_LINE.match(line)
        if not m:
            if skipped is not None:
                skipped.append(f"{name}: {line.strip()[:40]}")
            continue
        book = BY_OSIS.get(m.group(1))
        if book is None:
            continue
        yield Verse(book.id, int(m.group(2)), int(m.group(3)), m.group(4))


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _collect(el: ET.Element, out: list[str]) -> None:
    for child in el:
        tag = _local(child.tag)
        if tag == "note":  # ketiv/qere and apparatus: skip the subtree
            continue
        if tag == "w":
            out.append((child.text or "").replace("/", ""))  # '/' marks morphemes
        elif tag == "seg":
            # maqqef and sof pasuq attach to the preceding word; pe/samekh dropped
            if child.get("type") in ("x-maqqef", "x-sof-pasuq") and out:
                out[-1] += child.text or ""
        else:
            _collect(child, out)


def _oshb_verse_text(verse: ET.Element) -> str:
    out: list[str] = []
    _collect(verse, out)
    return " ".join(w for w in out if w).replace("\u05be ", "\u05be")


def parse_oshb_osis(data: bytes, name: str) -> Iterator[Verse]:
    root = ET.fromstring(data)
    for verse in root.iter():
        if _local(verse.tag) != "verse" or "osisID" not in verse.attrib:
            continue
        osis, chapter, number = verse.attrib["osisID"].split(".")
        book = BY_OSIS.get(osis)
        if book is None:
            continue
        text = _oshb_verse_text(verse)
        if text:
            yield Verse(book.id, int(chapter), int(number), text)


def parse_byz_csv(text: str, name: str, skipped: list[str] | None = None) -> Iterator[Verse]:
    """Yield verses from one byztxt CSV. The book comes from the file stem
    (`MAT.csv`, `1JO.csv`); rows whose chapter or verse is not a number are
    appended to `skipped` when given."""
    stem = Path(name).stem.upper()
    book = BY_USFM.get(_BYZ_CODES.get(stem, stem))
    if book is None:
        if skipped is not None:
            skipped.append(f"{name}: unknown book code")
        return
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header is None or [h.strip().lower() for h in header[:3]] != ["chapter", "verse", "text"]:
        raise SystemExit(f"{name}: expected a `chapter,verse,text` header, got {header!r}")
    for row in reader:
        if len(row) < 3 or not (row[0].strip().isdigit() and row[1].strip().isdigit()):
            if skipped is not None and any(cell.strip() for cell in row):
                skipped.append(f"{name}: {','.join(row)[:40]}")
            continue
        body = " ".join(row[2].replace(_PILCROW, " ").split())
        if body:
            yield Verse(book.id, int(row[0]), int(row[1]), body)


FORMATS = {"ref_tab_text": "text", "oshb_osis": "bytes", "byz_csv": "text"}
NT_BOOKS = (BY_OSIS["Matt"].id, BY_OSIS["Rev"].id)


class ArchiveBibleSource(Source):
    def build(self, ctx: BuildContext) -> None:
        fmt = self.cfg["format"]
        if fmt not in FORMATS:
            raise SystemExit(f"{self.id}: unknown format {fmt!r}")
        db.add_translation(ctx.conn, self.id, self.cfg, self.cfg.get("sha256", "sample")[:12])

        verses: list[Verse] = []
        skipped: list[str] = []
        matched = 0
        for name, data in self._members(ctx):
            matched += 1
            if fmt == "ref_tab_text":
                verses.extend(parse_ref_tab_text(data.decode("utf-8-sig"), name, skipped))
            elif fmt == "byz_csv":
                verses.extend(parse_byz_csv(data.decode("utf-8-sig"), name, skipped))
            else:
                verses.extend(parse_oshb_osis(data, name))
        if not matched:
            raise SystemExit(f"{self.id}: glob {self.cfg['glob']!r} matched nothing")
        if skipped:
            ctx.log(f"{self.id}: {len(skipped)} non-verse lines skipped, e.g. {skipped[:3]}")

        if self.cfg.get("versification") == "mt":
            ref = self.cfg.get("reference", "web")
            notes: list[str] = []
            verses = list(versification.apply_mt(verses, ctx.conn, ref, notes))
            for note in notes:
                ctx.log(f"{self.id}: {note}")
        n = db.add_verses(ctx.conn, self.id, verses)
        ctx.conn.commit()
        books = len({v.book for v in verses})
        ctx.log(f"{self.id}: {n} verses in {books} books from {matched} files")

        align = self.cfg.get("align", "ot" if self.cfg.get("versification") == "mt" else None)
        if align in ("ot", "nt"):
            ref = self.cfg.get("reference", "web")
            books = NT_BOOKS if align == "nt" else (1, BY_OSIS["Mal"].id)
            only_t, only_r = versification.check_alignment(ctx.conn, self.id, ref, books)
            for label, ids in (
                (f"verses with no {ref} counterpart", only_t),
                (f"{ref} {align.upper()} verses with no {self.id} text", only_r),
            ):
                if ids:
                    ctx.log(f"{self.id}: {len(ids)} {label}: {versification.summarize(ids)}")

    def _members(self, ctx: BuildContext) -> Iterator[tuple[str, bytes]]:
        pattern = self.cfg["glob"]
        if ctx.sample:
            folder = ctx.fixtures / "bibles" / self.id
            for path in sorted(folder.iterdir()):
                if fnmatch.fnmatch(path.name, Path(pattern).name):
                    yield path.name, path.read_bytes()
            return
        archive = fetch.fetch(self.cfg["url"], self.cfg.get("sha256"))
        with zipfile.ZipFile(archive) as z:
            names = sorted(i.filename for i in z.infolist() if not i.is_dir())
            hits = [n for n in names if fnmatch.fnmatch(n, pattern)]
            if not hits:
                preview = "\n  ".join(names[:40])
                raise SystemExit(
                    f"{self.id}: glob {pattern!r} matched none of {len(names)} members. "
                    f"First entries:\n  {preview}\nAdjust `glob` in sources.toml."
                )
            for n in hits:
                yield n, z.read(n)
