"""Commentary sources not yet wired. Each documents the upstream shape and the
mapping plan so the next person (or model) can implement it without research.

Implementing one means: fetch the pinned upstream, parse it into `Entry`
records with canonical verse-id ranges, call db.add_source + db.add_entries.
Use refs.parse_ref for references and the versification_map table when the
upstream numbers verses differently. See sources/haydock.py and
sources/sefaria.py for worked examples of anchoring notes through a
translation that shares the upstream's numbering.
"""

from __future__ import annotations

from ..context import BuildContext
from .base import Source


class NotWired(Source):
    plan = ""

    def build(self, ctx: BuildContext) -> None:
        raise NotImplementedError(f"{self.id} is not wired yet.\n{self.plan}")


class TafsirApiSource(NotWired):
    plan = """
    Upstream: spa5k/tafsir_api (JSON per surah/ayah). Not Bible-anchored.
    Plan: BLOCKED on an English text with a shippable license. When resolved,
    build a curated Quran->Bible parallels table (e.g. Hud 11 <-> Genesis 6-9)
    and insert Parallel rows pointing at entries; entries themselves anchor to
    the Bible range of the parallel.
    """
