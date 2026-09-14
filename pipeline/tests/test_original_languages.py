import sqlite3

from sevenreadings_pipeline import cli, versification
from sevenreadings_pipeline.context import FIXTURES_DIR
from sevenreadings_pipeline.refs import BY_OSIS, verse_id
from sevenreadings_pipeline.sources import archive_bible
from sevenreadings_pipeline.usfm import Verse


def test_ref_tab_text():
    text = (FIXTURES_DIR / "bibles" / "sblgnt" / "Matt.txt").read_text(encoding="utf-8")
    verses = list(archive_bible.parse_ref_tab_text(text, "Matt.txt"))
    assert [(v.book, v.chapter, v.verse) for v in verses] == [(40, 1, 1), (40, 1, 2)]
    assert verses[0].text.startswith("Βίβλος γενέσεως")


def test_oshb_osis_text_assembly():
    data = (FIXTURES_DIR / "bibles" / "wlc" / "Ps.xml").read_bytes()
    verses = list(archive_bible.parse_oshb_osis(data, "Ps.xml"))
    assert [(v.chapter, v.verse) for v in verses] == [(3, 1), (3, 2), (3, 3)]
    # morpheme '/' removed and sof pasuq attached; maqqef binds; qere note skipped
    assert verses[0].text == "מִזְמ֥וֹר לְדָוִ֑ד׃"
    assert verses[1].text == "יְ֭הוָה מָֽה־רַבּ֣וּ׃"


def test_mt_rules_shift_chapter_boundaries():
    joel = BY_OSIS["Joel"].id
    verses = [Verse(joel, 3, 1, "a"), Verse(joel, 4, 1, "b")]
    out = list(versification.apply_mt(verses, _conn(), "web"))
    expected = [(2, 28, "3:1"), (3, 1, "4:1")]
    assert [(v.chapter, v.verse, v.native_ref) for v in out] == expected


def test_mt_collisions_are_joined():
    sam = BY_OSIS["1Sam"].id
    verses = [Verse(sam, 20, 42, "x"), Verse(sam, 21, 1, "y")]
    (v,) = versification.apply_mt(verses, _conn(), "web")
    assert (v.chapter, v.verse, v.text, v.native_ref) == (20, 42, "x y", "20:42, 21:1")


def test_psalm_titles_derived_from_reference():
    conn = _conn()
    ps = BY_OSIS["Ps"].id
    # Reference (English) Psalm 3: title as verse 0, then 2 verses -> MT has 3 -> offset 1.
    conn.executemany(
        "INSERT INTO verses (translation_id, verse_id, body) VALUES ('web', ?, 'x')",
        [(verse_id(ps, 3, 0),), (verse_id(ps, 3, 1),), (verse_id(ps, 3, 2),)],
    )
    verses = [Verse(ps, 3, 1, "t"), Verse(ps, 3, 2, "a"), Verse(ps, 3, 3, "b")]
    out = list(versification.apply_mt(verses, conn, "web"))
    assert [(v.verse, v.native_ref) for v in out] == [(0, "3:1"), (1, "3:2"), (2, "3:3")]


def test_sample_build_has_greek_and_hebrew(tmp_path):
    out = tmp_path / "content.sqlite"
    assert cli.main(["build", "--sample", "--version", "0.0.0-test", "--out", str(out)]) == 0
    conn = sqlite3.connect(out)
    direction = dict(conn.execute("SELECT id, direction FROM translations").fetchall())
    assert direction["wlc"] == "rtl" and direction["sblgnt"] == "ltr"
    # WLC Psalm 3:2 (MT) sits on canonical Psalm 3:1 next to WEB's 3:1.
    rows = conn.execute(
        "SELECT translation_id, native_ref FROM verses WHERE verse_id=? ORDER BY 1",
        (verse_id(BY_OSIS["Ps"].id, 3, 1),),
    ).fetchall()
    assert ("wlc", "3:2") in rows and ("web", None) in rows
    tanakh = conn.execute("SELECT COUNT(*) FROM book_orders WHERE tradition='tanakh'")
    assert tanakh.fetchone()[0] == 39


def _conn() -> sqlite3.Connection:
    from sevenreadings_pipeline import db

    conn = sqlite3.connect(":memory:")
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("INSERT INTO translations VALUES ('web','WEB','WEB','en','ltr','PD','x','v')")
    return conn


def test_psalm_13_title_inferred_when_counts_agree():
    conn = _conn()
    ps = BY_OSIS["Ps"].id
    # English: title (0) + 6 verses. MT: 6 verses, the first being only the title.
    conn.executemany(
        "INSERT INTO verses (translation_id, verse_id, body) VALUES ('web', ?, 'x')",
        [(verse_id(ps, 13, v),) for v in range(0, 7)],
    )
    mt = [Verse(ps, 13, 1, "לַמְנַצֵּחַ מִזְמוֹר לְדָוִד")] + [Verse(ps, 13, v, f"v{v}") for v in range(2, 7)]
    notes: list[str] = []
    out = list(versification.apply_mt(mt, conn, "web", notes))
    assert [v.verse for v in out] == [0, 1, 2, 3, 4, 5]
    assert notes == ["Psalm 13: title verse inferred (equal counts)"]


def test_embedded_short_title_does_not_shift():
    conn = _conn()
    ps = BY_OSIS["Ps"].id
    conn.executemany(
        "INSERT INTO verses (translation_id, verse_id, body) VALUES ('web', ?, 'x')",
        [(verse_id(ps, 100, v),) for v in range(0, 6)],
    )
    mt = [Verse(ps, 100, 1, "מִזְמוֹר לְתוֹדָה הָרִיעוּ לַיהוָה כָּל־הָאָרֶץ")] + [
        Verse(ps, 100, v, f"v{v}") for v in range(2, 6)
    ]
    notes: list[str] = []
    out = list(versification.apply_mt(mt, conn, "web", notes))
    assert [v.verse for v in out] == [1, 2, 3, 4, 5] and notes == []
