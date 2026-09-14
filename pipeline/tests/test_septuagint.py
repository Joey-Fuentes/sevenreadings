import sqlite3

from sevenreadings_pipeline import cli, versification
from sevenreadings_pipeline.context import FIXTURES_DIR
from sevenreadings_pipeline.refs import BY_OSIS, verse_id
from sevenreadings_pipeline.sources import swete_lxx

PS, JER, K1, EZRA, NEH, DAG = (BY_OSIS[c].id for c in ("Ps", "Jer", "1Kgs", "Ezra", "Neh", "DanGr"))


def _tokens(name: str, target: str):
    text = (FIXTURES_DIR / "bibles" / "lxx" / name).read_text(encoding="utf-8")
    return list(swete_lxx.parse_tokens(text, target, name))


def test_tokens_group_into_verses_and_letter_suffixes_fold():
    verses = _tokens("01.Genesis.txt", "Gen")
    assert [(v.chapter, v.verse) for v in verses][:2] == [(1, 1), (1, 2)]
    assert verses[0].text == "ΕΝ ΑΡΧΗ ἐποίησεν ὁ θεὸς τὸν οὐρανὸν καὶ τὴν γῆν."
    kings = _tokens("13.Regnorum_III.txt", "1Kgs")
    assert [(v.chapter, v.verse, v.text) for v in kings][:1] == [(2, 35, "Καὶ ἔδωκεν κύριος")]


def test_second_esdras_splits_into_ezra_and_nehemiah():
    verses = _tokens("18.Esdras_B.txt", "EsdrasB")
    assert [(v.book, v.chapter) for v in verses] == [(EZRA, 1), (NEH, 1)]


def test_lxx_psalm_numbering():
    m = versification._lxx_psalm
    assert m(9, 21) == (9, 21) and m(9, 22) == (10, 1)
    assert m(10, 1) == (11, 1) and m(112, 1) == (113, 1)
    assert m(113, 8) == (114, 8) and m(113, 9) == (115, 1)
    assert m(114, 9) == (116, 9) and m(115, 1) == (116, 10)
    assert m(146, 11) == (147, 11) and m(147, 1) == (147, 12)
    assert m(150, 6) == (150, 6) and m(151, 1) == (151, 1)


def test_lxx_jeremiah_and_kingdoms():
    def m(book: int, chapter: int, verse: int) -> tuple[int, int]:
        return versification._lxx_map(book, chapter, verse)[1:]  # drop the book

    assert m(JER, 26, 2) == (46, 2)
    assert m(JER, 51, 31) == (45, 1)
    assert m(JER, 40, 3) == (33, 3)
    assert m(JER, 1, 1) == (1, 1)
    assert m(K1, 20, 1) == (21, 1)
    assert m(K1, 21, 1) == (20, 1)
    # Swete follows the English chapter breaks: no Hebrew shift in Joel or Malachi.
    assert m(BY_OSIS["Joel"].id, 3, 1) == (3, 1)
    assert m(BY_OSIS["Mal"].id, 4, 1) == (4, 1)


def test_sample_build_with_lxx(tmp_path, capsys):
    out = tmp_path / "content.sqlite"
    assert cli.main(["build", "--sample", "--version", "0.0.0-test", "--out", str(out)]) == 0
    log = capsys.readouterr().out
    assert "lxx: skipped: Odae" in log
    conn = sqlite3.connect(out)
    rows = dict(
        conn.execute(
            "SELECT verse_id, native_ref FROM verses WHERE translation_id='lxx'"
        ).fetchall()
    )
    assert rows[verse_id(PS, 10, 1)] == "9:22"  # LXX 9:22 is Psalm 10:1
    assert verse_id(PS, 151, 1) in rows  # kept, outside the canon's chapters
    assert rows[verse_id(JER, 46, 2)] == "26:2"
    assert verse_id(DAG, 13, 1) in rows  # Susanna (Theodotion) at DanGr 13
    assert rows[verse_id(K1, 21, 1)] == "20:1"


def test_chapter_zero_becomes_verse_zero_of_chapter_one():
    dropped: list[str] = []
    text = (FIXTURES_DIR / "bibles" / "lxx" / "01.Genesis.txt").read_text(encoding="utf-8")
    verses = list(swete_lxx.parse_tokens(text, "Gen", "01.Genesis.txt", dropped))
    assert [(v.chapter, v.verse) for v in verses] == [(1, 1), (1, 2), (1, 0)]
    assert verses[-1].text == "ΓΕΝΕΣΙΣ"
    assert dropped == ["01.Genesis.txt 1.0.0 ΓΕΝΕΣΙΣ"]


def test_lxx_rules_map_straight_to_english():
    def m(book: int, chapter: int, verse: int) -> tuple[int, int]:
        return versification._lxx_map(book, chapter, verse)[1:]  # drop the book

    num, sam, job, lev, hos = (BY_OSIS[c].id for c in ("Num", "1Sam", "Job", "Lev", "Hos"))
    assert m(num, 13, 1) == (12, 16) and m(num, 13, 34) == (13, 33)
    assert m(sam, 20, 43) == (20, 42) and m(sam, 24, 1) == (23, 29)
    assert m(job, 39, 31) == (40, 1) and m(job, 40, 20) == (41, 1) and m(job, 41, 1) == (41, 9)
    assert m(lev, 6, 31) == (7, 1) and m(lev, 7, 1) == (7, 11)
    assert m(hos, 14, 1) == (13, 16)
    assert versification.summarize(["1:2:25", "1:5:32", "2:8:1"]).startswith(
        "Gen 2 (2:25, 5:32); Exod 1"
    )


def test_stray_chapter_boundary_fragment_is_reattached():
    text = "27.21.31 a\n27.21.32 b\n27.22.32 c\n27.22.1 d\n27.22.2 e\n"
    repaired: list[str] = []
    verses = list(swete_lxx.parse_tokens(text, "Ps", "27.Psalmi.txt", None, repaired))
    assert [(v.chapter, v.verse, v.text) for v in verses] == [
        (21, 31, "a"),
        (21, 32, "b c"),
        (22, 1, "d"),
        (22, 2, "e"),
    ]
    assert repaired == ["27.Psalmi.txt 22.32"]
