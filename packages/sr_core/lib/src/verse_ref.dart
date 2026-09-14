import 'canon.dart';

/// A single verse in canonical (English/Protestant) versification.
///
/// Encoded as `book * 1_000_000 + chapter * 1_000 + verse`. Ids sort in
/// canonical order and leave room for 999 chapters and 999 verses, which is
/// what lets commentary anchor to a range with a plain `BETWEEN`.
///
/// Verse 0 is reserved for chapter-level material (Psalm superscriptions,
/// commentary introducing a whole chapter). Verse 999 is the chapter end
/// sentinel used by [chapterEnd].
///
/// Mirrored by `pipeline/sevenreadings_pipeline/refs.py`; both have tests
/// against the same fixtures. Change one, change both.
class VerseRef implements Comparable<VerseRef> {
  const VerseRef(this.book, this.chapter, this.verse)
      : assert(book >= 1 && book <= maxBookId),
        assert(chapter >= 1 && chapter <= 999),
        assert(verse >= 0 && verse <= 999);

  factory VerseRef.fromId(int id) {
    final book = id ~/ _bookFactor;
    final chapter = (id % _bookFactor) ~/ _chapterFactor;
    final verse = id % _chapterFactor;
    return VerseRef(book, chapter, verse);
  }

  static const int _bookFactor = 1000000;
  static const int _chapterFactor = 1000;

  final int book;
  final int chapter;
  final int verse;

  int get id => book * _bookFactor + chapter * _chapterFactor + verse;

  CanonBook get bookInfo => bookById(book);

  /// Inclusive lower bound for everything in this chapter.
  VerseRef get chapterStart => VerseRef(book, chapter, 0);

  /// Inclusive upper bound for everything in this chapter.
  VerseRef get chapterEnd => VerseRef(book, chapter, 999);

  /// `Genesis 1:1`; `Psalms 3` for verse 0.
  String get label => verse == 0
      ? '${bookInfo.name} $chapter'
      : '${bookInfo.name} $chapter:$verse';

  @override
  int compareTo(VerseRef other) => id.compareTo(other.id);

  @override
  bool operator ==(Object other) => other is VerseRef && other.id == id;

  @override
  int get hashCode => id;

  @override
  String toString() => label;
}
