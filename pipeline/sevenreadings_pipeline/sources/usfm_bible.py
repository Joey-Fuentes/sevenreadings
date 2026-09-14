"""Bible translations distributed as a zip of USFM files (BSB, WEB via eBible)."""

from __future__ import annotations

from .. import db, fetch, usfm
from ..context import BuildContext
from .base import Source


class UsfmBibleSource(Source):
    def build(self, ctx: BuildContext) -> None:
        db.add_translation(ctx.conn, self.id, self.cfg, self._version())
        total = 0
        loaded: dict[int, str] = {}  # book id -> file it came from
        for name, handle in self._files(ctx):
            verses = list(usfm.parse(handle, name))
            if not verses:
                continue
            books = {v.book for v in verses}
            dup = {b for b in books if b in loaded}
            if dup:
                came_from = ", ".join(sorted({loaded[b] for b in dup}))
                ctx.log(
                    f"{self.id}: skipping {name}; book(s) {sorted(dup)} already loaded "
                    f"from {came_from}"
                )
                continue
            for b in books:
                loaded[b] = name
            total += db.add_verses(ctx.conn, self.id, verses)
        ctx.conn.commit()
        ctx.log(f"{self.id}: {total} verses in {len(loaded)} books")

    def _version(self) -> str:
        return self.cfg.get("sha256", "")[:12] or "sample"

    def _files(self, ctx: BuildContext):
        if ctx.sample:
            folder = ctx.fixtures / "bibles" / self.id
            for path in sorted(folder.glob("*.usfm")):
                with path.open(encoding="utf-8-sig") as f:
                    yield path.name, f
            return
        archive = fetch.fetch(self.cfg["url"], self.cfg.get("sha256"))
        yield from fetch.zip_members(archive, ".usfm")
