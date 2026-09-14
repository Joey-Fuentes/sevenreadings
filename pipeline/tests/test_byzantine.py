import sqlite3

import pytest

from sevenreadings_pipeline import cli
from sevenreadings_pipeline.context import FIXTURES_DIR
from sevenreadings_pipeline.refs import verse_id
from sevenreadings_pipeline.sources import archive_bible

FIX = FIXTURES_DIR / "bibles" / "byz"


def test_byz_csv_maps_codes_and_drops_pilcrows():
    text = (FIX / "1JO.csv").read_text(encoding="utf-8")
    verses = list(archive_bible.parse_byz_csv(text, "1JO.csv"))
    assert [(v.book, v.chapter, v.verse) for v in verses] == [
        (62, 1, 4),
        (62, 1, 5),
        (62, 1, 6),
        (62, 3, 15),
    ]
    assert verses[1].text.startswith("Καὶ ἔστιν αὕτη")  # ¶ removed, no leading space
    assert verses[3].text.endswith("μένουσαν.")  # unquoted row
    (matt,) = archive_bible.parse_byz_csv((FIX / "MAT.csv").read_text(encoding="utf-8"), "MAT.csv")
    assert (matt.book, matt.chapter, matt.verse) == (40, 1, 1)


def test_byz_csv_rejects_other_layouts():
    skipped: list[str] = []
    assert list(archive_bible.parse_byz_csv("chapter,verse,text\n", "ENO.csv", skipped)) == []
    assert skipped == ["ENO.csv: unknown book code"]
    with pytest.raises(SystemExit, match="chapter,verse,text"):
        list(archive_bible.parse_byz_csv("book,chapter,verse,text\n", "MAT.csv"))


def test_sample_build_has_byzantine_text(tmp_path, capsys):
    out = tmp_path / "content.sqlite"
    assert cli.main(["build", "--sample", "--version", "0.0.0-test", "--out", str(out)]) == 0
    log = capsys.readouterr().out
    assert "byz: 5 verses in 2 books from 2 files" in log
    assert "byz: 5 verses with no web counterpart" in log  # NT alignment is reported
    conn = sqlite3.connect(out)
    row = conn.execute(
        "SELECT body, native_ref FROM verses WHERE translation_id='byz' AND verse_id=?",
        (verse_id(40, 1, 1),),
    ).fetchone()
    assert row[0].startswith("Βίβλος γενέσεως") and row[1] is None
    order = [r[0] for r in conn.execute("SELECT id FROM translations ORDER BY sort_order")]
    assert order.index("byz") == order.index("sblgnt") + 1
