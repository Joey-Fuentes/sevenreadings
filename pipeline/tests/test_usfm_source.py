import io
import sqlite3

from sevenreadings_pipeline import db
from sevenreadings_pipeline.context import BuildContext
from sevenreadings_pipeline.sources.usfm_bible import UsfmBibleSource

GEN = "\\id GEN\n\\c 1\n\\v 1 In the beginning.\n"


class _TwoFilesSameBook(UsfmBibleSource):
    def _files(self, ctx):
        yield "GEN-first.usfm", io.StringIO(GEN)
        yield "GEN-second.usfm", io.StringIO(GEN.replace("beginning", "again"))


def test_second_file_for_same_book_is_skipped(tmp_path, capsys):
    conn = db.create(tmp_path / "t.sqlite")
    cfg = {"name": "T", "abbreviation": "T", "language": "en", "license": "PD", "url": "x"}
    _TwoFilesSameBook("t", cfg).build(BuildContext(conn=conn, version="0", sample=False))
    rows = conn.execute("SELECT body FROM verses").fetchall()
    assert rows == [("In the beginning.",)]
    assert "skipping GEN-second.usfm" in capsys.readouterr().out
    conn.close()
    sqlite3.connect(tmp_path / "t.sqlite").close()
