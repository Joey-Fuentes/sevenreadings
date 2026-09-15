import sqlite3

from sevenreadings_pipeline import cli
from sevenreadings_pipeline.context import FIXTURES_DIR
from sevenreadings_pipeline.refs import verse_id
from sevenreadings_pipeline.sources import ccel_thml

FIX = FIXTURES_DIR / "commentaries" / "chrysostom" / "npnf110.xml"


def test_thml_divisions_and_passages():
    units = ccel_thml.parse_units(FIX.read_text(encoding="utf-8"))
    homilies = [u for u in units if u.kind == "Homily"]
    assert [u.heading for u in homilies] == ["Homily I", "Homily II", "Homily III", "Homily IV"]
    assert [u.passage for u in homilies] == [None, (40, 1, 1), (40, 1, 1), (40, 1, 17)]
    assert units[-1].heading == "Homily V" and units[-1].passage is None  # title only
    body = " ".join(homilies[0].paragraphs)
    assert "require the aid of the written Word" in body  # footnote dropped, spacing kept
    assert "not even to need" not in body and "Staff Writer" not in body


def test_passage_from_title():
    assert ccel_thml.passage_from_title("Ephesians 1:1--2") == (49, 1, 1)
    assert ccel_thml.passage_from_title("Ephesians 2:11,12") == (49, 2, 11)
    assert ccel_thml.passage_from_title("1 Thessalonians 4:13") == (52, 4, 13)
    assert ccel_thml.passage_from_title("Matthew XXVI. 26, 27, 28.") == (40, 26, 26)
    assert ccel_thml.passage_from_title("Matthew 1. 22, 23.") == (40, 1, 22)
    assert ccel_thml.passage_from_title("Homily 1") is None
    assert ccel_thml.passage_from_title("Preface to the American Edition.") is None


def test_homilies_cover_up_to_the_next_passage():
    units = ccel_thml.parse_units(FIX.read_text(encoding="utf-8"))
    got = list(ccel_thml.entries(units, "chrysostom"))
    assert [(e.start_verse_id, e.end_verse_id) for e in got] == [
        (verse_id(40, 1, 0), verse_id(40, 1, 0)),  # introduction
        (verse_id(40, 1, 1), verse_id(40, 1, 1)),  # II: III is on the same verse
        (verse_id(40, 1, 1), verse_id(40, 1, 16)),  # III runs to the verse before IV
        (verse_id(40, 1, 17), verse_id(40, 1, 999)),  # IV runs to its chapter end
        (verse_id(40, 2, 1), verse_id(40, 2, 999)),  # V: passage parsed from the title
    ]
    assert [e.citation for e in got] == [
        "Homily I (introduction to Matthew)",
        "Homily II, Matthew 1:1",
        "Homily III, Matthew 1:1-16",
        "Homily IV, Matthew 1:17ff.",
        "Homily V, Matthew 2:1ff.",
    ]
    assert got[1].body.startswith("Do ye indeed remember")  # heading lines dropped
    assert "*Esaias*" in got[1].body  # italics kept as Markdown
    assert "The book of the generation" not in got[1].body.split("\n\n")[0]


def test_sample_build_loads_chrysostom(tmp_path, capsys):
    out = tmp_path / "content.sqlite"
    assert cli.main(["build", "--sample", "--version", "0.0.0-test", "--out", str(out)]) == 0
    assert "chrysostom: 5 entries in 1 books: Matt" in capsys.readouterr().out
    conn = sqlite3.connect(out)
    rows = conn.execute(
        "SELECT citation FROM commentary_entries WHERE source_id='chrysostom' "
        "AND start_verse_id <= ? AND end_verse_id >= ? ORDER BY start_verse_id",
        (verse_id(40, 1, 5), verse_id(40, 1, 5)),
    ).fetchall()
    assert rows == [("Homily III, Matthew 1:1-16",)]
