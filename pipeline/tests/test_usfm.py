from sevenreadings_pipeline import usfm
from sevenreadings_pipeline.context import FIXTURES_DIR


def _parse(name: str):
    with (FIXTURES_DIR / "bibles" / "web" / name).open(encoding="utf-8") as f:
        return list(usfm.parse(f))


def test_genesis_fixture():
    verses = _parse("GEN.usfm")
    assert [(v.chapter, v.verse) for v in verses] == [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2)]
    assert verses[0].text == "In the beginning, God created the heavens and the earth."
    assert verses[2].text == "God said, “Let there be light,” and there was light."
    assert verses[0].id == 1_001_001


def test_psalm_superscription_and_poetry():
    verses = _parse("PSA.usfm")
    assert verses[0].verse == 0
    assert verses[0].text.startswith("A Psalm by David")
    assert verses[1].text == (
        "Yahweh, how my adversaries have increased! Many are those who rise up against me."
    )
    assert "Selah" not in verses[2].text


def test_clean_strips_notes_and_unwraps_char_markers():
    assert usfm.clean(r"a \f + \fr 1:1 \ft note\f* b") == "a b"
    assert usfm.clean(r'\w word|lemma="x"\w* here') == "word here"
    assert usfm.clean(r"\nd Lord\nd* \add is\add* good") == "Lord is good"


def test_split_verse_segments_merge():
    verses = _parse("GEN.usfm")
    assert verses[-1].text == "Segment one of a split verse, and segment two."


def test_true_duplicate_is_an_error():
    import pytest

    lines = ["\\id GEN", "\\c 1", "\\v 1 first", "\\v 2 second", "\\v 1 again"]
    with pytest.raises(ValueError, match="duplicate verse 1:1"):
        list(usfm.parse(lines, "GEN.usfm"))


def test_psalm_119_stanza_headings_are_not_superscriptions():
    verses = [v for v in _parse("PSA.usfm") if v.chapter == 119]
    assert [v.verse for v in verses] == [1, 9]
    assert all("ALEPH" not in v.text and "BETH" not in v.text for v in verses)
