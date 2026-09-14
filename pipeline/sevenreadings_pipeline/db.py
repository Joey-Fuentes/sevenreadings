"""Create, populate and finalize the content database."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from .model import Entry, Parallel
from .refs import CANON
from .usfm import Verse

PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_DIR.parents[1]
SCHEMA_PATH = REPO_ROOT / "packages" / "sr_data" / "lib" / "src" / "schema" / "content.drift"
FTS_PATH = PIPELINE_DIR / "sql" / "fts.sql"

# Must match ContentDb.contentSchemaVersion in packages/sr_data.
SCHEMA_VERSION = 1

PERSPECTIVES = [
    ("jewish_literal", 1, "Jewish: Literal (Peshat)", "Judaism"),
    ("jewish_rational", 2, "Jewish: Rationalist", "Judaism"),
    ("catholic", 3, "Roman Catholic", "Christianity"),
    ("orthodox", 4, "Eastern Orthodox", "Christianity"),
    ("protestant", 5, "Protestant / Reformed", "Christianity"),
    ("islamic", 6, "Islamic", "Islam"),
    ("academic", 7, "Secular / Academic", "Academic"),
]


def create(path: Path) -> sqlite3.Connection:
    if path.exists():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.executemany(
        "INSERT INTO books (id, usfm, osis, name, chapters) VALUES (?, ?, ?, ?, ?)",
        [(b.id, b.usfm, b.osis, b.name, b.chapters) for b in CANON],
    )
    conn.executemany(
        "INSERT INTO perspectives (id, sort_order, name, tradition) VALUES (?, ?, ?, ?)",
        PERSPECTIVES,
    )
    conn.commit()
    return conn


def add_translation(conn: sqlite3.Connection, tid: str, cfg: dict, version: str) -> None:
    conn.execute(
        "INSERT INTO translations (id, name, abbreviation, language, license, source_url, "
        "source_version) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (tid, cfg["name"], cfg["abbreviation"], cfg["language"], cfg["license"],
         cfg.get("url") or cfg.get("repo", ""), version),
    )


def add_verses(conn: sqlite3.Connection, tid: str, verses: Iterable[Verse]) -> int:
    rows = [(tid, v.id, v.text) for v in verses]
    conn.executemany(
        "INSERT INTO verses (translation_id, verse_id, body) VALUES (?, ?, ?)", rows
    )
    return len(rows)


def add_source(conn: sqlite3.Connection, sid: str, cfg: dict, version: str) -> None:
    conn.execute(
        "INSERT INTO sources (id, perspective_id, author, title, license, license_status, "
        "source_url, source_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (sid, cfg["perspective"], cfg["author"], cfg["title"], cfg["license"],
         cfg["license_status"], cfg.get("url") or cfg.get("repo", ""), version),
    )


def add_entries(conn: sqlite3.Connection, entries: Iterable[Entry]) -> int:
    n = 0
    for e in entries:
        if e.end_verse_id < e.start_verse_id:
            raise ValueError(
                f"inverted range in {e.source_id}: {e.start_verse_id}>{e.end_verse_id}"
            )
        conn.execute(
            "INSERT INTO commentary_entries (source_id, start_verse_id, end_verse_id, heading, "
            "body, citation) VALUES (?, ?, ?, ?, ?, ?)",
            (e.source_id, e.start_verse_id, e.end_verse_id, e.heading, e.body, e.citation),
        )
        n += 1
    return n


def add_parallels(conn: sqlite3.Connection, parallels: Iterable[Parallel]) -> int:
    rows = [
        (p.source_id, p.start_verse_id, p.end_verse_id, p.external_ref, p.entry_id, p.note)
        for p in parallels
    ]
    conn.executemany(
        "INSERT INTO parallels (source_id, start_verse_id, end_verse_id, external_ref, entry_id, "
        "note) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def finalize(conn: sqlite3.Connection, path: Path, version: str, sources: list[str]) -> dict:
    built_at = datetime.now(UTC).isoformat(timespec="seconds")
    conn.executescript(FTS_PATH.read_text(encoding="utf-8"))
    conn.executemany(
        "INSERT INTO meta (name, value) VALUES (?, ?)",
        [
            ("content_version", version),
            ("schema_version", str(SCHEMA_VERSION)),
            ("built_at", built_at),
            ("sources", ",".join(sources)),
        ],
    )
    # drift compares this to ContentDb.schemaVersion; without it the app would
    # try to run onCreate against a populated file.
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()
    conn.execute("VACUUM")
    conn.execute("PRAGMA optimize")
    conn.close()

    counts = _counts(path)
    manifest = {
        "version": version,
        "schema_version": SCHEMA_VERSION,
        "built_at": built_at,
        "sources": sources,
        "counts": counts,
    }
    (path.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def _counts(path: Path) -> dict[str, int]:
    conn = sqlite3.connect(path)
    try:
        out = {}
        for table in ("verses", "commentary_entries", "parallels"):
            out[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        return out
    finally:
        conn.close()
