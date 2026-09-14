"""Records every parser produces. The loader in db.py writes them."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Entry:
    """One commentary unit anchored to an inclusive canonical verse-id range."""

    source_id: str
    start_verse_id: int
    end_verse_id: int
    body: str  # Markdown
    heading: str | None = None
    citation: str | None = None


@dataclass(frozen=True, slots=True)
class Parallel:
    """A Bible range linked to non-verse-anchored material (e.g. a Quran passage)."""

    source_id: str
    start_verse_id: int
    end_verse_id: int
    external_ref: str
    entry_id: int | None = None
    note: str | None = None
