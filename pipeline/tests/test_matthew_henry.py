import sqlite3

from sevenreadings_pipeline import cli
from sevenreadings_pipeline.context import FIXTURES_DIR
from sevenreadings_pipeline.refs import verse_id
from sevenreadings_pipeline.sources import ccel_mhc

FIX = FIXTURES_DIR / "commentaries" / "matthew_henry"


def test_chapter_page_yields_intro_and_sections():
    html = (FIX / "MHC01001.HTM").read_text(encoding="utf-8")
    entries = list(ccel_mhc.parse_chapter(html, 1, 1))
    assert [(e.start_verse_id, e.end_verse_id) for e in entries] == [
        (verse_id(1, 1, 0), verse_id(1, 1, 999)),  # chapter introduction
        (verse_id(1, 1, 1), verse_id(1, 1, 2)),
        (verse_id(1, 1, 3), verse_id(1, 1, 5)),
    ]
    intro, first, second = entries
    assert intro.heading == "Genesis 1: introduction"
    assert "foundation of all religion" in intro.body and "CHAP" not in intro.body
    assert first.heading == "The Creation. B. C. 4004." and first.citation == "Genesis 1:1-2"
    assert "*the heaven and the earth,*" in first.body  # italics kept as Markdown
    assert "Creator, it was fit" in intro.body  # source line wraps joined
    assert "In the beginning God created" not in first.body  # KJV text not duplicated
    assert "Table of Contents" not in first.body
    assert second.citation == "Genesis 1:3-5"


def test_book_introduction_anchors_at_chapter_one_title():
    html = (FIX / "MHC01000.HTM").read_text(encoding="utf-8")
    (entry,) = ccel_mhc.parse_chapter(html, 1, 0)
    assert entry.start_verse_id == entry.end_verse_id == verse_id(1, 1, 0)
    assert entry.body.startswith("WE have now before us the holy Bible")
    assert "EXPOSITION" not in entry.body and "Chapter 1" not in entry.body


def test_sample_build_loads_matthew_henry(tmp_path):
    out = tmp_path / "content.sqlite"
    assert cli.main(["build", "--sample", "--version", "0.0.0-test", "--out", str(out)]) == 0
    conn = sqlite3.connect(out)
    n = conn.execute("SELECT COUNT(*) FROM commentary_entries WHERE source_id='matthew_henry'")
    assert n.fetchone()[0] == 4
    hits = conn.execute(
        "SELECT rowid FROM commentary_fts WHERE commentary_fts MATCH 'epitome'"
    ).fetchall()
    assert len(hits) == 1
