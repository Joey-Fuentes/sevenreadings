"""Bible translations distributed as a zip of USFM files (BSB, WEB via eBible)."""

from __future__ import annotations

from .. import db, fetch, usfm
from ..context import BuildContext
from .base import Source


class UsfmBibleSource(Source):
    def build(self, ctx: BuildContext) -> None:
        db.add_translation(ctx.conn, self.id, self.cfg, self._version())
        total = 0
        for _name, handle in self._files(ctx):
            n = db.add_verses(ctx.conn, self.id, usfm.parse(handle))
            total += n
        ctx.conn.commit()
        ctx.log(f"{self.id}: {total} verses")

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
