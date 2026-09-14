"""Generic loader for commentary already normalised to JSON Lines.

Each line: {"ref": "Gen 1:1-5", "body": "...", "heading": null, "citation": null}
`ref` uses the grammar in refs.parse_ref. This is both the fixture format for
CI and a convenient intermediate for parsers that want to emit a file first.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from .. import db
from ..context import BuildContext
from ..model import Entry
from ..refs import parse_ref
from .base import Source


def read_jsonl(source_id: str, path: Path) -> Iterator[Entry]:
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            obj = json.loads(line)
            try:
                start, end = parse_ref(obj["ref"])
            except ValueError as e:
                raise ValueError(f"{path}:{line_no}: {e}") from e
            yield Entry(
                source_id=source_id,
                start_verse_id=start,
                end_verse_id=end,
                body=obj["body"],
                heading=obj.get("heading"),
                citation=obj.get("citation"),
            )


class JsonlCommentarySource(Source):
    def build(self, ctx: BuildContext) -> None:
        if ctx.sample:
            path = ctx.fixtures / "commentaries" / f"{self.id}.jsonl"
        else:
            path = Path(self.cfg["path"])
        db.add_source(ctx.conn, self.id, self.cfg, self.cfg.get("sha256", "sample")[:12])
        n = db.add_entries(ctx.conn, read_jsonl(self.id, path))
        ctx.conn.commit()
        ctx.log(f"{self.id}: {n} entries")
