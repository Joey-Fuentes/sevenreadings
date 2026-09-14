import sqlite3

from sevenreadings_pipeline import cli, db


def test_schema_is_plain_sql():
    conn = sqlite3.connect(":memory:")
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        "books",
        "translations",
        "verses",
        "perspectives",
        "sources",
        "commentary_entries",
        "parallels",
        "versification_map",
        "meta",
    } <= tables


def test_sample_build(tmp_path):
    out = tmp_path / "content.sqlite"
    assert cli.main(["build", "--sample", "--version", "0.0.0-test", "--out", str(out)]) == 0
    assert (tmp_path / "manifest.json").exists()

    conn = sqlite3.connect(out)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
    assert conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 75
    assert conn.execute("SELECT COUNT(*) FROM perspectives").fetchone()[0] == 7
    web = conn.execute("SELECT COUNT(*) FROM verses WHERE translation_id='web'").fetchone()[0]
    assert web == 10

    # Range anchoring: Gen 1:2 sees the chapter note and the 1:1-2 note, not 1:3.
    rows = conn.execute(
        "SELECT body FROM commentary_entries WHERE source_id='sample'"
        " AND start_verse_id <= ? AND end_verse_id >= ? ORDER BY start_verse_id DESC",
        (1_001_002, 1_001_002),
    ).fetchall()
    assert len(rows) == 2 and "1:3" not in rows[0][0] + rows[1][0]

    # Every built source's NOTICE.md travels with the content, for the About screen.
    notices = conn.execute("SELECT value FROM meta WHERE name='notices'").fetchone()[0]
    assert "# Byzantine Majority Text" in notices and "The Unlicense" in notices
    assert "# Haydock's Catholic Bible Commentary" in notices
    assert notices.index("# World English Bible (WEB)") < notices.index("# Byzantine")

    # FTS works and points back at real rows.
    hit = conn.execute(
        "SELECT v.verse_id FROM verses_fts JOIN verses v ON v.id = verses_fts.rowid"
        " WHERE verses_fts MATCH 'adversaries'"
    ).fetchone()
    assert hit[0] == 19_003_001
    hit = conn.execute(
        "SELECT rowid FROM commentary_fts WHERE commentary_fts MATCH 'superscription'"
    ).fetchall()
    assert len(hit) == 1


def test_sample_build_deuterocanon(tmp_path, capsys):
    out = tmp_path / "content.sqlite"
    assert cli.main(["build", "--sample", "--version", "0.0.0-test", "--out", str(out)]) == 0
    assert "skipped (not in canon): ENO" in capsys.readouterr().out
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 75
    orders = conn.execute(
        "SELECT tradition, COUNT(*) FROM book_orders GROUP BY tradition ORDER BY tradition"
    ).fetchall()
    # 73 Catholic books, plus DanGr holding the Greek additions separately.
    assert orders == [("catholic", 74), ("protestant", 66), ("tanakh", 39)]
    # Greek Daniel 3:91 landed on canonical Daniel 3:24 with its native label.
    row = conn.execute(
        "SELECT native_ref FROM verses WHERE translation_id='webc' AND verse_id=?", (27_003_024,)
    ).fetchone()
    assert row == ("3:91",)


def test_write_pin_updates_every_entry_sharing_the_url():
    from sevenreadings_pipeline import fetch

    toml = (
        '[a]\nurl = "https://x/y.zip"\nsha256 = "TODO"\n\n'
        '[b]\nurl = "https://x/y.zip"   # shared\nsha256 = "TODO"   # keep me\n\n'
        '[c]\nurl = "https://x/z.zip"\nsha256 = "old"\n'
    )
    out, n = fetch.write_pin(toml, "https://x/y.zip", "abc")
    assert n == 2  # both entries, comments on either line kept
    assert 'url = "https://x/y.zip"\nsha256 = "abc"\n' in out
    assert 'sha256 = "abc"   # keep me' in out
    assert 'sha256 = "old"' in out
    assert fetch.write_pin(toml, "https://x/none.zip", "abc")[1] == 0
