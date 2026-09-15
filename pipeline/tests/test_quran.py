import sqlite3

from sevenreadings_pipeline import cli
from sevenreadings_pipeline.context import FIXTURES_DIR
from sevenreadings_pipeline.refs import verse_id
from sevenreadings_pipeline.sources import quran

FIX = FIXTURES_DIR / "commentaries" / "quran"


def test_gutenberg_layout_yields_one_translation():
    verses, names = quran.parse_gutenberg((FIX / "pg16955_sample.txt").read_text(encoding="utf-8"))
    assert names == {1: "Al-Fatiha (The Opening)", 2: "Al-Baqara (The Cow)", 12: "Yusuf (Joseph)"}
    assert verses[(1, 1)] == "In the name of Allah, the Beneficent, the Merciful."
    assert verses[(1, 7)].startswith("The path of those whom Thou hast favoured;")
    assert "Cherisher" not in " ".join(verses.values())  # Yusuf Ali's lines are not read
    assert verses[(2, 30)].endswith("Surely I know that which ye know not.")  # wrapped lines joined
    assert (12, 6) in verses and len(verses) == 14


def test_passages_and_rendering():
    assert quran.parse_passage("12:4-6") == quran.Passage(12, 4, 6)
    assert quran.parse_passage(" 1:1 ").ref == "1:1"
    assert quran.parse_passage("38:31-30").last == 31  # inverted range collapses
    verses, names = quran.parse_gutenberg((FIX / "pg16955_sample.txt").read_text(encoding="utf-8"))
    text = quran.render(quran.Passage(12, 4, 6), verses, names)
    assert text.startswith("**Surah 12, Yusuf (Joseph), 4-6.** 4 When Joseph said unto his father")
    assert " 5 He said: O my dear son!" in text and " 6 Thus thy Lord" in text


def test_shipped_parallels_file_resolves_and_parses():
    from sevenreadings_pipeline.context import BuildContext
    from sevenreadings_pipeline.refs import parse_ref

    src = quran.QuranParallelsSource("quran", {"kind": "quran_parallels"})
    path = src._parallels(BuildContext(conn=None, version="t", sample=False))
    assert path.name == "quran_parallels.tsv" and path.exists(), path
    rows = list(quran.load_parallels(path))
    assert len(rows) > 150
    for bible, passages, note in rows:
        parse_ref(bible)
        assert passages and note


def test_sample_build_loads_the_quran_parallels(tmp_path, capsys):
    out = tmp_path / "content.sqlite"
    assert cli.main(["build", "--sample", "--version", "0.0.0-test", "--out", str(out)]) == 0
    log = capsys.readouterr().out
    assert "quran: 14 verses in 3 surahs from Pickthall" in log
    assert "quran: 5 entries, 5 parallels" in log
    assert "2 passages with verses absent" in log
    assert "['99:6-8: 6, 7, 8 (Rev 20:11-15)', '2:30-35: 34, 35 (Ps 33:6-9)']" in log
    conn = sqlite3.connect(out)
    rows = conn.execute(
        "SELECT heading, citation, body FROM commentary_entries WHERE source_id='quran' "
        "AND start_verse_id <= ? AND end_verse_id >= ?",
        (verse_id(1, 37, 7), verse_id(1, 37, 7)),
    ).fetchall()
    assert len(rows) == 1
    heading, citation, body = rows[0]
    assert heading == "Joseph's dream of the sun, moon and eleven stars"
    assert citation == "Qur'an 12:4-6, Pickthall (1930)"
    assert body.startswith("**Surah 12, Yusuf (Joseph), 4-6.** 4 When Joseph")
    par = conn.execute(
        "SELECT external_ref, note, entry_id IS NOT NULL FROM parallels "
        "WHERE source_id='quran' ORDER BY id"
    ).fetchall()
    assert par[1] == ("Qur'an 12:4-6", "Joseph's dream of the sun, moon and eleven stars", 1)
    assert par[3][0] == "Qur'an 1:1-3"  # the row for the passage that was found; 99:6-8 has none
    assert par[4][0] == "Qur'an 2:30-35"  # two of six verses absent: kept, with the gap reported
    assert conn.execute("SELECT perspective_id FROM sources WHERE id='quran'").fetchone() == (
        "islamic",
    )
