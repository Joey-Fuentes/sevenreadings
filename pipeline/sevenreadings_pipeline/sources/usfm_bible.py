"""Bible translations distributed as a zip of USFM files (BSB, WEB via eBible)."""

from __future__ import annotations

import itertools
import re

from .. import db, deuterocanon, fetch, usfm
from ..context import BuildContext
from .base import Source

_ID = re.compile(r"^\ufeff?\\id\s+(\S+)")


class UsfmBibleSource(Source):
    def build(self, ctx: BuildContext) -> None:
        db.add_translation(ctx.conn, self.id, self.cfg, self._version())
        resolve, remap = deuterocanon.PROFILES.get(
            self.cfg.get("remap", ""), (usfm.canon_book, lambda vs: vs)
        )
        total = 0
        loaded: dict[int, str] = {}  # book id -> file it came from
        skipped: list[str] = []
        for name, handle in self._files(ctx):
            first = handle.readline()
            lines = itertools.chain([first], handle)
            verses = list(remap(usfm.parse(lines, name, resolve)))
            if not verses:
                m = _ID.match(first)
                skipped.append(m.group(1) if m else name)
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
        if skipped:
            ctx.log(f"{self.id}: skipped (not in canon): {', '.join(skipped)}")

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
