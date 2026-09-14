import 'package:sr_core/sr_core.dart';
import 'package:test/test.dart';

// Keep these fixtures identical to pipeline/tests/test_refs.py.
const fixtures = <(int, int, int, int)>[
  (1, 1, 1, 1001001),
  (19, 3, 0, 19003000),
  (19, 150, 6, 19150006),
  (39, 4, 6, 39004006),
  (40, 1, 1, 40001001),
  (66, 22, 21, 66022021),
];

void main() {
  test('canon has 66 books and 1189 chapters', () {
    expect(canon.length, 66);
    expect(canon.fold<int>(0, (n, b) => n + b.chapters), 1189);
    for (var i = 0; i < canon.length; i++) {
      expect(canon[i].id, i + 1);
    }
  });

  test('book lookups', () {
    expect(bookByUsfm('gen')!.name, 'Genesis');
    expect(bookByOsis('Rev')!.id, 66);
    expect(bookByUsfm('XYZ'), isNull);
  });

  test('verse id encoding round-trips', () {
    for (final (b, c, v, id) in fixtures) {
      final ref = VerseRef(b, c, v);
      expect(ref.id, id);
      expect(VerseRef.fromId(id), ref);
    }
  });

  test('ids sort canonically', () {
    expect(
      const VerseRef(1, 50, 26).compareTo(const VerseRef(2, 1, 1)),
      lessThan(0),
    );
    expect(
      const VerseRef(19, 9, 20).compareTo(const VerseRef(19, 10, 1)),
      lessThan(0),
    );
  });

  test('chapter bounds bracket every verse', () {
    const ref = VerseRef(43, 3, 16);
    expect(ref.chapterStart.id, 43003000);
    expect(ref.chapterEnd.id, 43003999);
    expect(ref.id, inInclusiveRange(ref.chapterStart.id, ref.chapterEnd.id));
  });

  test('labels', () {
    expect(const VerseRef(43, 3, 16).label, 'John 3:16');
    expect(const VerseRef(19, 3, 0).label, 'Psalms 3');
  });
}
