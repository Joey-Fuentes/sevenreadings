from sevenreadings_pipeline import refs

# Keep identical to packages/sr_core/test/verse_ref_test.dart.
FIXTURES = [
    (1, 1, 1, 1_001_001),
    (19, 3, 0, 19_003_000),
    (19, 150, 6, 19_150_006),
    (39, 4, 6, 39_004_006),
    (40, 1, 1, 40_001_001),
    (66, 22, 21, 66_022_021),
]


def test_canon_shape():
    assert len(refs.CANON) == refs.MAX_BOOK_ID == 75
    assert sum(b.chapters for b in refs.CANON[:66]) == 1189
    assert [b.id for b in refs.CANON] == list(range(1, 76))


def test_encoding_round_trip():
    for b, c, v, vid in FIXTURES:
        assert refs.verse_id(b, c, v) == vid
        assert refs.decode(vid) == (b, c, v)


def test_parse_ref():
    assert refs.parse_ref("Gen 1:1") == (1_001_001, 1_001_001)
    assert refs.parse_ref("Genesis 1:1-5") == (1_001_001, 1_001_005)
    assert refs.parse_ref("Ps 3") == (19_003_000, 19_003_999)
    assert refs.parse_ref("John 3:16-4:2") == (43_003_016, 43_004_002)
    assert refs.parse_ref("1 Cor 13:4") == (46_013_004, 46_013_004)
    assert refs.parse_ref("1Cor 13:4") == (46_013_004, 46_013_004)
    assert refs.parse_ref("SNG 2:1") == (22_002_001, 22_002_001)
