from sevenreadings_pipeline import deuterocanon, usfm
from sevenreadings_pipeline.context import FIXTURES_DIR
from sevenreadings_pipeline.refs import BY_USFM, CANON, MAX_BOOK_ID, verse_id

DAN, DAG, BAR = (BY_USFM[c].id for c in ("DAN", "DAG", "BAR"))


def _remapped(name: str):
    with (FIXTURES_DIR / "bibles" / "webc" / name).open(encoding="utf-8") as f:
        return list(deuterocanon.remap_catholic(usfm.parse(f, name, deuterocanon.resolve_catholic)))


def test_canon_extension():
    assert MAX_BOOK_ID == 75 and len(CANON) == 75
    assert sum(b.chapters for b in CANON[:66]) == 1189
    assert BY_USFM["DAG"].id == 75 and BY_USFM["TOB"].id == 67


def test_greek_daniel_split():
    got = {(v.book, v.chapter, v.verse): v.native_ref for v in _remapped("DAG.usfm")}
    assert got[(DAN, 1, 1)] == "DanGr 1:1"
    assert got[(DAN, 3, 23)] == "DanGr 3:23"
    assert (DAG, 3, 24) in got and (DAG, 3, 90) in got  # additions stay in DanGr
    assert got[(DAN, 3, 24)] == "3:91"  # Greek 91 is Hebrew 24
    assert got[(DAN, 3, 30)] == "3:97"
    assert (DAG, 13, 1) in got and (DAG, 14, 1) in got
    assert verse_id(DAG, 13, 1) == 75_013_001


def test_letter_of_jeremiah_is_baruch_6():
    (v,) = _remapped("LJE.usfm")
    assert (v.book, v.chapter, v.verse, v.native_ref) == (BAR, 6, 1, "LJE 1:1")


def test_unknown_book_is_skipped():
    assert _remapped("ENO.usfm") == []
