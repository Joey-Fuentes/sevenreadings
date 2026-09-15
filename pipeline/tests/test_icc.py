import sqlite3

from sevenreadings_pipeline import cli
from sevenreadings_pipeline.context import FIXTURES_DIR
from sevenreadings_pipeline.refs import verse_id
from sevenreadings_pipeline.sources import ia_hocr

FIX = FIXTURES_DIR / "commentaries" / "icc" / "criticalexegetic00sanduoft_hocr.html"


def test_running_heads_and_page_numbers():
    assert ia_hocr.roman("XLVII") == 47 and ia_hocr.roman("IX") == 9
    left = ia_hocr.read_page(["2 EPISTLE TO THE ROMANS [I. 1", "text", "2"])
    assert (left.chapter, left.first, left.last, left.lines) == (1, 1, 1, ["text"])
    right = ia_hocr.read_page(["XIV. 13-23] THE STRONG AND THE WEAK 389", "text"])
    assert (right.chapter, right.first, right.last) == (14, 13, 23)
    none = ia_hocr.read_page(["xii INTRODUCTION", "text"])
    assert none.chapter is None and none.lines == ["xii INTRODUCTION", "text"]
    # Heads with the bracket lost or misread by the OCR.
    for head, want in [
        ("2 EPISTLE TO THE ROMANS I. 1", (1, 1, 1)),
        ("I. 8-15 ST. PAUL AND THE ROMAN CHURCH 5", (1, 8, 15)),
        ("6 EPISTLE TO THE ROMANS (I. 9", (1, 9, 9)),
        ("XII. 1-8] THE CHRISTIAN LIFE 351", (12, 1, 8)),
    ]:
        page = ia_hocr.read_page([head, "body text of the page"])
        assert (page.chapter, page.first, page.last) == want, head
        assert page.lines == ["body text of the page"], head
    # A body line mentioning a reference is not a head.
    body = ia_hocr.read_page(["cf. the discussion of ch. ix. 5 and of I. 3 below, where", "text"])
    assert body.chapter is None


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
    assert len(pages) == 7
    report = {}
    got = list(ia_hocr.notes(pages, report))
    assert [(n.chapter, n.verse, n.last) for n in got] == [
        (1, 1, 7),
        (1, 1, 1),
        (1, 2, 2),
        (1, 3, 3),
        (1, 5, 5),  # no note on verse 4 in this volume
        (1, 8, 15),
        (1, 8, 8),
        (2, 1, 16),
        (2, 1, 1),
    ]
    assert got[0].heading == "THE APOSTOLIC SALUTATION"
    body = ia_hocr.paragraphs(got[1].lines)
    assert "concurrently" in body  # hyphenation rejoined
    assert body.startswith("Παῦλος.") and "δοῦλος" in body  # lemma lines stay in the note
    three = ia_hocr.paragraphs(got[3].lines)
    assert "1. as Messiah" in three  # a numbered list inside a note is not verse 1 again
    eight = ia_hocr.paragraphs(got[6].lines)
    assert "lost the running head" in eight  # the blind page attached to the open note
    assert report == {"skipped": 2, "kept_blind": 1}


def test_sample_build_loads_icc(tmp_path, capsys):
    out = tmp_path / "content.sqlite"
    assert cli.main(["build", "--sample", "--version", "0.0.0-test", "--out", str(out)]) == 0
    log = capsys.readouterr().out
    assert "icc: Rom (W. Sanday and A. C. Headlam): 9 notes from 7 pages" in log
    assert "notes per chapter (of verses): 1:7/0, 2:2/0" in log  # no Romans in the sample WEB
    conn = sqlite3.connect(out)
    rows = conn.execute(
        "SELECT citation, heading FROM commentary_entries WHERE source_id='icc' "
        "AND start_verse_id <= ? AND end_verse_id >= ? ORDER BY start_verse_id, end_verse_id DESC",
        (verse_id(45, 1, 3), verse_id(45, 1, 3)),
    ).fetchall()
    assert rows == [
        ("W. Sanday and A. C. Headlam, Romans 1:1-7", "THE APOSTOLIC SALUTATION"),
        ("W. Sanday and A. C. Headlam, Romans 1:3", None),
    ]
