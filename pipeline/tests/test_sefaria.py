import sqlite3

from sevenreadings_pipeline import cli
from sevenreadings_pipeline.refs import verse_id
from sevenreadings_pipeline.sources import sefaria


def test_license_keys_and_allow_list():
    assert sefaria.license_key("Public Domain") == "PUBLICDOMAIN"
    assert sefaria.license_key("CC0") == "CC0" and sefaria.license_key("CC0 1.0") == "CC0"
    assert (
        sefaria.license_key("CC-BY 4.0") == "CCBY" and sefaria.license_key("CC BY-SA") == "CCBYSA"
    )
    assert sefaria.license_key("CC-BY-NC") == "CCBYNC" and "CCBYNC" not in sefaria.ALLOWED
    assert sefaria.license_key(None) == "" and "" not in sefaria.ALLOWED


def test_choose_prefers_listed_titles_then_size_and_never_nc():
    v = [
        sefaria.Version("a/English/Big NC.json", "Big NC", "CC-BY-NC", 900),
        sefaria.Version("a/English/Small CC0.json", "Small CC0", "CC0", 10),
        sefaria.Version("a/English/Large PD.json", "Large PD", "Public Domain", 500),
        sefaria.Version("a/English/Foreign [pt].json", "Foreign", "CC0", 800),
    ]
    assert sefaria.choose(v, []).title == "Large PD"
    assert sefaria.choose(v, ["Small CC0"]).title == "Small CC0"
    assert sefaria.choose([v[0]], []) is None


def test_complex_texts_use_the_default_node():
    simple = [[["a"]]]
    assert sefaria.chapters(simple, "Genesis") == (simple, "list")
    complex_ = {"Introduction": ["Ibn Ezra's preface."], "": [[["on 1:1"]]]}
    assert sefaria.chapters(complex_, "Genesis") == ([[["on 1:1"]]], "node ''")
    named = {"Introduction": ["preface"], "Genesis": [[["on 1:1"]]]}
    assert sefaria.chapters(named, "Genesis")[0] == [[["on 1:1"]]]
    odd = {"Introduction": ["preface"], "Chapters": [[["x"]]]}
    got, how = sefaria.chapters(odd, "Genesis")
    assert got == [[["x"]]] and how.startswith("node 'Chapters' (first verse-shaped")
    assert sefaria.chapters({"Introduction": ["only"]}, "Genesis") == (
        [],
        "no verse-shaped node among ['Introduction']",
    )


def test_book_titles():
    assert sefaria.book_id("Rashi on Genesis", "Rashi") == 1
    assert sefaria.book_id("Rashi on I Samuel", "Rashi") == 9
    assert sefaria.book_id("Ibn Ezra on Song of Songs", "Ibn Ezra") == 22
    assert sefaria.book_id("Rashi on Avot", "Rashi") is None


def test_sample_build_loads_rashi_through_the_wlc(tmp_path, capsys):
    out = tmp_path / "content.sqlite"
    assert cli.main(["build", "--sample", "--version", "0.0.0-test", "--out", str(out)]) == 0
    log = capsys.readouterr().out
    assert "rashi: Masoretic numbering mapped through the WLC's ingest" in log
    assert "Gen: Sefaria Community Translation [CC0] 2" in log
    assert "Ps: Public Domain Fixture [Public Domain] 2" in log
    assert "no English version with an allowed license" not in log
    assert "2 references not in the WLC's numbering, placed by the Hebrew rule table" in log
    conn = sqlite3.connect(out)
    rows = conn.execute(
        "SELECT start_verse_id, citation, body FROM commentary_entries "
        "WHERE source_id='rashi' ORDER BY start_verse_id"
    ).fetchall()
    assert [r[0] for r in rows] == [
        verse_id(1, 1, 1),
        verse_id(1, 1, 3),
        verse_id(19, 3, 0),  # Masoretic Psalm 3:1 is the title
        verse_id(19, 3, 1),
    ]
    assert rows[0][2].startswith("**In the beginning:** Rabbi Isaac said")
    assert "\n\nA second comment" in rows[0][2]
    assert rows[2][1] == "Psalms 3 (Hebrew 3:1)" and rows[3][1] == "Psalms 3:1 (Hebrew 3:2)"
    bodies = " ".join(r[2] for r in rows)
    assert "restricted translation" not in bodies and "Não" not in bodies
