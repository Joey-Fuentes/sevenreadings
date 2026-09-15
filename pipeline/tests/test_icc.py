import sqlite3

from sevenreadings_pipeline import cli
from sevenreadings_pipeline.context import FIXTURES_DIR
from sevenreadings_pipeline.refs import verse_id
from sevenreadings_pipeline.sources import ia_hocr

FIX = FIXTURES_DIR / "commentaries" / "icc" / "criticalexegetic00sanduoft_hocr.html"


def test_running_heads_as_this_ocr_renders_them():
    assert ia_hocr.roman("XLVII") == 47 and ia_hocr.roman("IX") == 9 and ia_hocr.roman("l") == 1
    for head, want in [
        ("2 EPISTLE TO THE ROMANS [I. 1", 1),
        ("2 EPISTLE TO THE ROMA [I. 1 7", 1),  # the dash of "1-7" lost
        ("I. 1.] THE APOSTOLIC SALUTATION", 1),  # period before the bracket
        ("I. 17.J RIGHTEOUSNESS OF COD BY FAITH 27", 1),  # bracket read as J
        ("1 6 EPISTLE TO THE ROMA [l. 7.", 1),  # I read as l
        ("1. 16, 17.] RIGHTEOUSNESS OF GOD BY FAITH 35", 1),  # I read as 1
        ("^4 I HE ROMA [I 10, 17.", 1),  # no period after the numeral
        ("I. 17.]", 1),  # nothing but the reference
        ("3* [I. 17.", 1),
        ("XIV. 13-23] THE STRONG AND THE WEAK 389", 14),
        ("II 7.J TIIK APOSTOLIC SALUTATION 17", 2),  # a misread; the walker guards it
    ]:
        page = ia_hocr.read_page([head, "body text of the page"])
        assert page.chapter == want, head
        assert page.lines == ["body text of the page"], head
    for head in [
        "xii INTRODUCTION",
        ". 20.] FAILURE OF THE GENTILES 43",  # numeral gone: kept blind, not a chapter
        "cvi i: TO TJI MS [§ 10.",
        "III. GREEK WORDS",
        "T. and T. Clark's Publications.",
        "cf. the discussion of ch. ix. 5 and of I. 3 below, where",
    ]:
        assert ia_hocr.read_page([head, "text"]).chapter is None, head


def test_note_starts():
    assert ia_hocr._NOTE.match("4. 6pia0«Vros: 'designated.'")  # Greek as digits
    assert ia_hocr._NOTE.match("12. oujiirapaiiXi)0Tii'ai : the subject")
    assert not ia_hocr._NOTE.match("37. 52 ; xiv. 9, in all which places")  # a wrapped reference
    assert ia_hocr._RANGE.match("1-7. In writing to the Church")
    assert ia_hocr._SECTION.match("I. 16, 17. That message, humble as it may seem")


def test_inverted_ocr_range_collapses_to_its_start():
    pages = [
        [
            "VIII. 31-39] THE SECURITY OF THE CHRISTIAN 219",
            "VIII. 31-30. THE SECURITY OF THE CHRISTIAN.",
            "What then shall we say to these things? If God is for us, who is against us?",
        ]
    ]
    (note,) = ia_hocr.notes(pages)
    assert (note.chapter, note.verse, note.last) == (8, 31, 31)


def test_notes_follow_heads_sections_and_verse_numbers():
    pages = ia_hocr.parse_pages(FIX.read_text(encoding="utf-8"))
    assert len(pages) == 8
    report = {}
    got = list(ia_hocr.notes(pages, report, limits={1: 32, 2: 29}))
    assert [(n.chapter, n.verse, n.last) for n in got] == [
        (1, 1, 7),  # section heading on page 1, which has no running head
        (1, 1, 7),  # "1-7." the section's own note
        (1, 1, 1),  # "I. IlavXor": verse 1 read as I
        (1, 2, 2),
        (1, 3, 3),
        (1, 4, 4),  # "6pia0«Vros" after the period is Greek, not a number
        (1, 5, 5),
        (1, 8, 15),
        (1, 8, 8),
        (1, 16, 17),  # "I. 16, 17." comma list; page head "II 7.J" did not open chapter 2
        (1, 16, 16),
        (2, 1, 16),
        (2, 1, 1),
    ]
    assert got[0].heading == "THE APOSTOLIC SALUTATION"
    body = ia_hocr.paragraphs(got[2].lines)
    assert "concurrently" in body  # hyphenation rejoined
    assert body.startswith("IlavXor.") and "δοῦλος" in body  # lemma lines stay in the note
    three = ia_hocr.paragraphs(got[4].lines)
    assert "1. as Messiah" in three and "37. 52" in three  # neither is a verse
    eight = ia_hocr.paragraphs(got[8].lines)
    assert "lost the running head" in eight  # the blind page attached to the open note
    assert got[9].heading is None and ia_hocr.paragraphs(got[9].lines).startswith("That message")
    assert report == {"skipped": 2, "kept_blind": 2}  # the "II 7.J" page counts as blind


def test_sample_build_loads_icc(tmp_path, capsys):
    out = tmp_path / "content.sqlite"
    assert cli.main(["build", "--sample", "--version", "0.0.0-test", "--out", str(out)]) == 0
    log = capsys.readouterr().out
    assert "icc: Rom (W. Sanday and A. C. Headlam): 13 notes from 8 pages" in log
    conn = sqlite3.connect(out)
    rows = conn.execute(
        "SELECT citation, heading FROM commentary_entries WHERE source_id='icc' "
        "AND start_verse_id <= ? AND end_verse_id >= ? ORDER BY end_verse_id DESC, id",
        (verse_id(45, 1, 1), verse_id(45, 1, 1)),
    ).fetchall()
    assert rows == [
        ("W. Sanday and A. C. Headlam, Romans 1:1-7", "THE APOSTOLIC SALUTATION"),
        ("W. Sanday and A. C. Headlam, Romans 1:1-7", None),
        ("W. Sanday and A. C. Headlam, Romans 1:1", None),
    ]
