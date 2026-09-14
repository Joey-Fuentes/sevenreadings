import sqlite3

from sevenreadings_pipeline import cli, versification
from sevenreadings_pipeline.context import FIXTURES_DIR
from sevenreadings_pipeline.refs import BY_OSIS, verse_id
from sevenreadings_pipeline.sources import haydock

FIX = FIXTURES_DIR / "commentaries" / "haydock"


def _page(title: str) -> str:
    return f"<html><head><title>{title}</title></head><body>{haydock.HEADER}</body></html>"


TITLES = [
    ("GENESIS - Chapter 1", (1, 1)),
    ("ST. MATTHEW - Chapter 18", (40, 18)),
    ("ST. JOHN - Introduction.", (43, 0)),
    ("ACTS OF THE APOSTLES - Chapter 1", (44, 1)),
    ("1 KINGS - Chapter 3", (9, 3)),  # Douay 1 Kings is 1 Samuel
    ("3 KINGS - Chapter 22", (11, 22)),
    ("JOSUE [now known as JOSHUA] - Chapter 2", (6, 2)),
    ("2 ESDRAS, alias NEHEMIAS - Chapter 1", (16, 1)),
    ("CANTICLE OF CANTICLES - Introduction", (22, 0)),
    ("APOCALYPSE (REVELATION) - Chapter 22", (66, 22)),
    ("Psalm 150", (19, 150)),
    ("PSALMS - Introduction", (19, 0)),
    ("ST. MATTHEW - INTRODUCTION", (40, 0)),
    ("GENESIS - Chapter III.", (1, 3)),  # Roman numeral
    ("Numbers 28", (4, 28)),  # bare "Book N" title
    ("BIBLE: MATTHEW - Chapter 13", (40, 13)),
]


def test_identify_chapter_titles():
    for title, expected in TITLES:
        page = haydock.identify(_page(title))
        assert (page.book, page.chapter) == expected, title


def test_identify_ignores_other_pages_and_reports_unknown_books():
    assert haydock.identify(_page("OLD TESTAMENT")) is None
    assert haydock.identify(_page("Transcriber's Notes")) is None
    assert haydock.identify(_page("BOOK OF ENOCH - Chapter 1")) == "BOOK OF ENOCH"
    # The Confraternity sister site has the same title shape but not the header.
    html = "<html><head><title>MATTHEW - Chapter 1</title></head><body>x</body></html>"
    assert haydock.identify(html) is None


def test_index_pages_map_files_to_chapters():
    pages, unknown = haydock.parse_index((FIX / "id330.html").read_text(encoding="utf-8"))
    assert pages["id327.html"] == haydock.Page(1, 1)
    assert pages["id326.html"] == haydock.Page(1, 0)
    assert pages["id534.html"] == haydock.Page(6, 0)  # "[now known as JOSHUA]" ignored
    assert pages["id728.html"] == haydock.Page(19, 3)  # psalm link reads "<b>3</b> [3]"
    assert pages["id734.html"] == haydock.Page(19, 9)
    assert unknown == set()  # "OLD TESTAMENT", "Douay-Rheims Numbering" are not books
    pages, _ = haydock.parse_index((FIX / "index.html").read_text(encoding="utf-8"))
    assert pages["id91.html"] == haydock.Page(43, 0) and pages["id92.html"] == haydock.Page(43, 1)
    assert pages["id287.html"] == haydock.Page(66, 1)  # APOCALYPSE (REVELATION)
    assert "id26.html" not in pages  # "General Preface"


def test_verse_markers_need_not_be_bold():
    text = (
        "**Notes & Commentary:**\nVer. 1. Plain marker. (Witham)\n"
        "  **Ver. 2.** Bold marker, mentions ver. 14 in passing.\n"
        "**Ver.** 3-4. Bold label only.\nVer 5 No periods at all.\n"
    )
    notes = haydock.parse_notes(text[len("**Notes & Commentary:**\n") :])
    assert [n.verses for n in notes] == [(1, 1), (2, 2), (3, 4), (5, 5)]
    assert notes[1].body == "Bold marker, mentions ver. 14 in passing."


def test_bible_header_spellings():
    for header in (
        "Bible Text & Cross-references:",
        "Bible Text &amp;&nbsp;Cross-references:",
        "Bible Text and Cross-references:",
        "Bible Text & Commentary:",
        "Bible Text&nbsp;&amp; Cross-references:",
    ):
        html = (
            "<html><head><title>JOB - Chapter 1</title></head><body>"
            f"{haydock.HEADER}<b>Next Chapter</b> <b>&gt;</b><br>"
            "<b>Notes &amp; Commentary:</b><br><b>Ver. 1.</b> note<br>"
            f"<b>{header}</b><br>1 There was a man in the land of Hus.<br></body></html>"
        )
        commentary, bible = haydock.sections(html)
        assert "note" in commentary and "There was a man" not in commentary, header
        assert [v.verse for v in haydock.parse_bible(bible, 18, 1)] == [1], header


def test_hebrew_vulgate_dual_numbering_and_bible_above_notes():
    html = (FIX / "id840.html").read_text(encoding="utf-8")
    commentary, bible = haydock.sections(html)  # Bible text printed first on this page
    assert [n.verses for n in haydock.parse_notes(commentary)] == [(1, 1), (2, 2)]
    verses = haydock.parse_bible(bible, 19, 115)
    assert [v.verse for v in verses] == [1, 2, 3]  # the Vulgate number, not the Hebrew
    assert verses[0].text.startswith("I have believed") and verses[2].text.startswith("What")
    assert "2 Cor" not in " ".join(v.text for v in verses)


def test_notes_split_on_verse_markers_and_keep_footnotes():
    commentary, bible = haydock.sections((FIX / "id92.html").read_text(encoding="utf-8"))
    notes = haydock.parse_notes(commentary)
    assert [n.verses for n in notes] == [(1, 1), (2, 2), (8, 9), (14, 14), ()]
    first = notes[0].body
    assert first.startswith("*In the beginning was the word:*[1] or rather")  # italics kept
    assert "Philo Judæus" in first  # entity decoded
    assert "\n\n[1] Ver. 1. Et Deus erat Verbum" in first  # footnote joined to its verse
    assert "[3] Ver. 14. Gloriam" in notes[3].body and "[3] Ver. 14" not in first
    assert notes[4].body == "[5] A note the transcriber attached to no verse."
    assert "Bible Text" not in first and "Next Chapter" not in first


def test_bible_text_is_douay_in_vulgate_numbering():
    _, bible = haydock.sections((FIX / "id92.html").read_text(encoding="utf-8"))
    verses = haydock.parse_bible(bible, 43, 1)
    assert [v.verse for v in verses] == [1, 2, 3, 6, 8, 9, 14, 15]
    assert verses[3].text == "There was a man sent from God, whose name was John."  # '*' gone
    assert verses[6].text.endswith("full of grace and truth.")  # wrapped line joined
    _, bible = haydock.sections((FIX / "id728.html").read_text(encoding="utf-8"))
    psalm = haydock.parse_bible(bible, 19, 3)
    assert psalm[0].text.endswith("his son Absalom.")  # bracketed reference dropped
    assert "The prophet's danger" not in " ".join(v.text for v in psalm)  # summary dropped
    # Lines break at the English verse boundary; the Vulgate number sits mid-line.
    assert [v.verse for v in psalm] == [1, 2, 3]
    assert psalm[1].text.endswith("many are they who rise up against me.")
    assert psalm[2].text.startswith("Many say to my soul")


def test_inline_verse_numbers_split_only_in_sequence():
    sec = (
        "9 The Lord judgeth the people. 10 The wickedness of sinners. 11 Is my help\n"
        "21 Arise. 1(22) Why, O Lord, hast thou retired afar off? 2(23) Whilst the wicked.\n"
        "24 In the year 70 of the [2 Kings] there were 3 men; 12 is not next. 25 Next.\n"
        "26 thy sword 27 from the enemies of thy hand.\n"  # no punctuation at the boundary
        "*\n"
        "9: Matthew v. 8.\n"
    )
    verses = haydock.parse_bible(sec, 19, 9)
    assert [v.verse for v in verses] == [9, 10, 11, 21, 22, 23, 24, 25, 26, 27]
    assert verses[3].text == "Arise." and verses[4].text.startswith("Why, O Lord")
    assert verses[6].text == "In the year 70 of the there were 3 men; 12 is not next."
    assert verses[8].text == "thy sword" and verses[9].text.startswith("from the enemies")


def test_cross_reference_list_without_a_rule_is_not_verse_text():
    sec = (
        "*The duties of husbands and wives.\n"
        "*\n"  # the summary's italics close after a <br>: a lone star before verse 1
        "33 Nevertheless let every one of you love his wife as himself.\n"
        "*\n"
        "2: John xiii. 34. and xv. 12.; 1 John iv. 21.\n"
    )
    (v,) = haydock.parse_bible(sec, 49, 5)
    assert v.verse == 33 and "John" not in v.text  # no invented Ephesians 5:34
    # A verse typed with a colon after its number (Genesis 40:9) is still a verse.
    sec = (
        "8 And they answered: We have dreamed a dream.\n"
        "9: The chief butler first told his dream.\n"
        "10 In which I saw.\n*\n10(1): 2 Cor. iv. 13.\n"
    )
    assert [v.verse for v in haydock.parse_bible(sec, 1, 40)] == [8, 9, 10]
    for line in ("6: Matthew iii. 1.; Mark i. 4.", "45: Genesis xlix 10.", "10(1): 2 Cor. iv. 13."):
        assert haydock._XREF_LINE.match(line), line
    for line in ("9: The chief butler first told his dream", "3: I will not fear", "7: In vain"):
        assert not haydock._XREF_LINE.match(line), line


def test_hebrew_numbers_alias_to_vulgate_ones_for_notes():
    aliases: dict[int, int] = {}
    sec = "10(1) I have believed. 11(2) I said in my excess.\n12(3) What shall I render.\n"
    assert [v.verse for v in haydock.parse_bible(sec, 19, 115, aliases)] == [1, 2, 3]
    assert aliases == {10: 1, 11: 2, 12: 3}
    aliases = {}
    sec = "1 Unto the end.\n2 I will give praise.\n21 Arise.\n1(22) Why, O Lord?\n2(23) Whilst.\n"
    assert [v.verse for v in haydock.parse_bible(sec, 19, 9, aliases)] == [1, 2, 21, 22, 23]
    assert aliases == {}  # 1 and 2 are real verses of the page: no alias


def test_stray_bible_header_above_the_notes_is_ignored():
    html = (
        "<html><head><title>PROVERBS - Chapter 15</title></head><body>"
        f"{haydock.HEADER}<b>Next Chapter</b> <b>&gt;</b><br>"
        "<b>Bible Text &amp; Cross-references:</b><br>"
        "<b>Ver. 1.</b> A note.<br><b>Ver. 2.</b> Another.<br>"
        "<b>Bible Text &amp; Cross-references:</b><br>1 A mild answer breaketh wrath.<br>"
        "</body></html>"
    )
    commentary, bible = haydock.sections(html)
    assert [n.verses for n in haydock.parse_notes(commentary)] == [(1, 1), (2, 2)]
    assert "Bible Text" not in commentary
    assert [v.verse for v in haydock.parse_bible(bible, 20, 15)] == [1]


def test_vulgate_rules_and_deuterocanon_routing():
    m = versification.vul_map
    num, job, dan, esth, ps = (BY_OSIS[c].id for c in ("Num", "Job", "Dan", "Esth", "Ps"))
    assert m(num, 13, 1) == (num, 12, 16) and m(num, 13, 2) == (num, 13, 1)
    assert m(num, 30, 1) == (num, 29, 40) and m(num, 30, 2) == (num, 30, 1)
    song, hag, mark = (BY_OSIS[c].id for c in ("Song", "Hag", "Mark"))
    assert m(song, 1, 1) == (song, 1, 2) and m(song, 5, 17) == (song, 6, 1)
    assert m(song, 6, 1) == (song, 6, 2) and m(song, 6, 12) == (song, 6, 13)
    assert m(hag, 2, 1) == (hag, 1, 15) and m(hag, 2, 2) == (hag, 2, 1)
    assert m(mark, 8, 39) == (mark, 9, 1) and m(mark, 9, 1) == (mark, 9, 2)
    assert m(job, 40, 20) == (job, 41, 1) and m(job, 41, 1) == (job, 41, 10)
    assert m(dan, 3, 24) == (BY_OSIS["DanGr"].id, 3, 24)
    assert m(dan, 3, 91) == (dan, 3, 24) and m(dan, 3, 98) == (dan, 4, 1)
    assert m(dan, 13, 1) == (BY_OSIS["DanGr"].id, 13, 1)
    assert m(esth, 10, 3) == (esth, 10, 3) and m(esth, 11, 1) == (BY_OSIS["EsthGr"].id, 11, 1)
    assert m(ps, 9, 22) == (ps, 10, 1) and m(ps, 22, 1) == (ps, 23, 1)
    assert m(BY_OSIS["Gen"].id, 32, 1) == (BY_OSIS["Gen"].id, 32, 1)  # no MT shift


def test_no_title_offset_when_the_english_psalm_has_no_title():
    conn = _conn()
    ps = BY_OSIS["Ps"].id
    from sevenreadings_pipeline.usfm import Verse

    # English Psalm 2: no title, 12 verses. Vulgate: 13 (a split), not a title.
    conn.executemany(
        "INSERT INTO verses (translation_id, verse_id, body) VALUES ('web', ?, 'x')",
        [(verse_id(ps, 2, v),) for v in range(1, 13)],
    )
    douay = [Verse(ps, 2, v, f"v{v}") for v in range(1, 14)]
    out = list(versification.apply_vul(douay, conn, "web"))
    assert [v.verse for v in out] == list(range(1, 14))  # verse 13 reported, not shifted


def test_apply_vul_traces_and_offsets_psalm_titles():
    conn = _conn()
    ps = BY_OSIS["Ps"].id
    conn.executemany(
        "INSERT INTO verses (translation_id, verse_id, body) VALUES ('web', ?, 'x')",
        [(verse_id(ps, 3, v),) for v in range(0, 9)],
    )
    from sevenreadings_pipeline.usfm import Verse

    douay = [Verse(ps, 3, v, f"v{v}") for v in range(1, 10)]
    trace: versification.Trace = {}
    out = list(versification.apply_vul(douay, conn, "web", trace=trace))
    assert [(v.verse, v.native_ref) for v in out][:2] == [(0, "3:1"), (1, "3:2")]
    assert trace[(ps, 3, 1)] == verse_id(ps, 3, 0) and trace[(ps, 3, 9)] == verse_id(ps, 3, 8)


def test_notes_on_missing_douay_verses_fall_back_to_the_rule_table():
    src = haydock.HaydockSource("haydock", {})
    page = haydock.Page(BY_OSIS["Num"].id, 13)
    unanchored: list[str] = []
    e = src._entry(page, haydock.Note((1, 2), "x"), {}, unanchored)
    num = BY_OSIS["Num"].id
    assert (e.start_verse_id, e.end_verse_id) == (verse_id(num, 12, 16), verse_id(num, 13, 1))
    assert e.citation == "Numbers 12:16 (Douay 13:1)-Numbers 13:1"
    assert unanchored == ["Numbers 13:1"]


def test_sample_build_loads_douay_and_haydock(tmp_path, capsys):
    out = tmp_path / "content.sqlite"
    assert cli.main(["build", "--sample", "--version", "0.0.0-test", "--out", str(out)]) == 0
    log = capsys.readouterr().out
    assert "haydock: 11 entries" in log and "douay: 14 verses in 2 books" in log
    # The stale duplicate id11.html (titled like John 1) is not in the index.
    assert "1 archived pages not in the index were skipped: ['id11.html: ST. JOHN" in log
    assert "id326.html" in log  # indexed but absent from the archive: reported
    conn = sqlite3.connect(out)
    # Douay Psalm 3:2 sits on canonical 3:1 with WEB 3:1 and WLC 3:2.
    rows = conn.execute(
        "SELECT translation_id, native_ref FROM verses WHERE verse_id=? ORDER BY 1",
        (verse_id(19, 3, 1),),
    ).fetchall()
    assert ("douay", "3:2") in rows and ("web", None) in rows and ("wlc", "3:2") in rows
    # Vulgate Psalm 115:1 ("10(1)") lands on canonical 116:10.
    row = conn.execute(
        "SELECT native_ref FROM verses WHERE translation_id='douay' AND verse_id=?",
        (verse_id(19, 116, 10),),
    ).fetchone()
    assert row == ("115:1",)
    anchors = conn.execute(
        "SELECT start_verse_id, end_verse_id, citation FROM commentary_entries "
        "WHERE source_id='haydock' ORDER BY start_verse_id"
    ).fetchall()
    assert (verse_id(19, 3, 0), verse_id(19, 3, 0), "Psalms 3 (Douay 3:1)") in anchors
    assert (verse_id(19, 3, 1), verse_id(19, 3, 1), "Psalms 3:1 (Douay 3:2)") in anchors
    assert (verse_id(43, 1, 0), verse_id(43, 1, 0), "John, introduction") in anchors
    assert (verse_id(43, 1, 8), verse_id(43, 1, 9), "John 1:8-9") in anchors
    assert (verse_id(43, 1, 0), verse_id(43, 1, 999), "John 1") in anchors  # orphan footnote
    bodies = " ".join(r[0] for r in conn.execute("SELECT body FROM commentary_entries"))
    assert "sister site" not in bodies  # confraternity/ excluded
    assert "stale duplicate" not in bodies  # id11.html skipped: not in the index
    hit = conn.execute(
        "SELECT v.translation_id FROM verses_fts JOIN verses v ON v.id = verses_fts.rowid"
        " WHERE verses_fts MATCH 'Absalom' ORDER BY 1"
    ).fetchall()
    assert hit == [("douay",), ("web",)]


def _conn() -> sqlite3.Connection:
    from sevenreadings_pipeline import db

    conn = sqlite3.connect(":memory:")
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("INSERT INTO translations VALUES ('web','WEB','WEB','en','ltr','PD','x','v',0)")
    return conn
