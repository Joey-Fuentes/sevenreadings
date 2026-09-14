"""Commentary sources not yet wired. Each documents the upstream shape and the
mapping plan so the next person (or model) can implement it without research.

Implementing one means: fetch the pinned upstream, parse it into `Entry`
records with canonical verse-id ranges, call db.add_source + db.add_entries.
Use refs.parse_ref for references and the versification_map table when the
upstream numbers verses differently (rashi, ibn_ezra: Masoretic; haydock: Vulgate).
"""

from __future__ import annotations

from ..context import BuildContext
from .base import Source


class NotWired(Source):
    plan = ""

    def build(self, ctx: BuildContext) -> None:
        raise NotImplementedError(f"{self.id} is not wired yet.\n{self.plan}")


class SefariaExportSource(NotWired):
    plan = """
    Upstream: Sefaria-Export, json/Commentary/Tanakh/<Author>/<Book>/{Hebrew,English}/*.json
    Shape: nested arrays text[chapter][verse][comment_index] (Masoretic numbering),
    plus per-file metadata with the license of that specific text.
    Plan: one Entry per (chapter, verse) joining comments with blank lines;
    map (book, chapter, verse) through versification_map scheme='mt';
    read the license field per file and refuse files whose license is not on the
    allow-list in sources.toml.
    """


class HaydockSource(NotWired):
    plan = """
    Upstream: the_depositum repo (Markdown per chapter) or johnblood.gitlab.io/haydock.
    Shape: "Ver. N." paragraphs per chapter, Douay-Rheims (Vulgate) numbering.
    Plan: split on 'Ver. N' markers; anchor to (chapter, N) via scheme='vul';
    strip Douay verse quotations that precede the note.
    """


class HcfDatabaseSource(NotWired):
    plan = """
    Upstream: HistoricalChristianFaith/Commentaries-Database (SQLite / JSON dumps).
    Shape: rows with father_name, source_title, book, location_start, location_end, txt.
    Plan: filter by father (Chrysostom) or source (Matthew Henry); location_* are
    already ranges; map book names via refs.BY_NAME; body is plain text -> Markdown.
    Chrysostom entries carry the homily as citation.
    """


class TafsirApiSource(NotWired):
    plan = """
    Upstream: spa5k/tafsir_api (JSON per surah/ayah). Not Bible-anchored.
    Plan: BLOCKED on an English text with a shippable license. When resolved,
    build a curated Quran->Bible parallels table (e.g. Hud 11 <-> Genesis 6-9)
    and insert Parallel rows pointing at entries; entries themselves anchor to
    the Bible range of the parallel.
    """


class IccSource(NotWired):
    plan = """
    Upstream: Internet Archive / Wikisource OCR of pre-1929 ICC volumes.
    Shape: per-volume text with verse-numbered notes; OCR quality varies.
    Plan: one volume at a time, pinned by archive.org identifier; segment on
    verse headings; keep volume + page as citation. Exclude volumes published
    1929 or later.
    """
