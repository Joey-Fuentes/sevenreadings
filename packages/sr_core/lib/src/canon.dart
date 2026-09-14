/// Every book the content database can hold, with stable ids.
///
/// Ids 1-66 are the Protestant canon in its traditional order; 67+ are
/// deuterocanonical books, appended as they were added. Ids are baked into
/// every verse id in the content database (see [VerseRef]): never reorder or
/// renumber. Display order per tradition comes from the `book_orders` table,
/// not from this list.
class CanonBook {
  const CanonBook(this.id, this.usfm, this.osis, this.name, this.chapters);

  /// 1..66 in canonical order.
  final int id;

  /// USFM 3-letter code, e.g. `GEN`.
  final String usfm;

  /// OSIS id, e.g. `Gen`.
  final String osis;

  /// English display name.
  final String name;

  /// Number of chapters.
  final int chapters;

  bool get isOldTestament => id <= 39;
  bool get isNewTestament => id > 39 && id <= 66;
  bool get isDeuterocanonical => id > 66;
}

/// Highest book id in [canon]. Bump when appending books.
const int maxBookId = 75;

const List<CanonBook> canon = [
  CanonBook(1, 'GEN', 'Gen', 'Genesis', 50),
  CanonBook(2, 'EXO', 'Exod', 'Exodus', 40),
  CanonBook(3, 'LEV', 'Lev', 'Leviticus', 27),
  CanonBook(4, 'NUM', 'Num', 'Numbers', 36),
  CanonBook(5, 'DEU', 'Deut', 'Deuteronomy', 34),
  CanonBook(6, 'JOS', 'Josh', 'Joshua', 24),
  CanonBook(7, 'JDG', 'Judg', 'Judges', 21),
  CanonBook(8, 'RUT', 'Ruth', 'Ruth', 4),
  CanonBook(9, '1SA', '1Sam', '1 Samuel', 31),
  CanonBook(10, '2SA', '2Sam', '2 Samuel', 24),
  CanonBook(11, '1KI', '1Kgs', '1 Kings', 22),
  CanonBook(12, '2KI', '2Kgs', '2 Kings', 25),
  CanonBook(13, '1CH', '1Chr', '1 Chronicles', 29),
  CanonBook(14, '2CH', '2Chr', '2 Chronicles', 36),
  CanonBook(15, 'EZR', 'Ezra', 'Ezra', 10),
  CanonBook(16, 'NEH', 'Neh', 'Nehemiah', 13),
  CanonBook(17, 'EST', 'Esth', 'Esther', 10),
  CanonBook(18, 'JOB', 'Job', 'Job', 42),
  CanonBook(19, 'PSA', 'Ps', 'Psalms', 150),
  CanonBook(20, 'PRO', 'Prov', 'Proverbs', 31),
  CanonBook(21, 'ECC', 'Eccl', 'Ecclesiastes', 12),
  CanonBook(22, 'SNG', 'Song', 'Song of Songs', 8),
  CanonBook(23, 'ISA', 'Isa', 'Isaiah', 66),
  CanonBook(24, 'JER', 'Jer', 'Jeremiah', 52),
  CanonBook(25, 'LAM', 'Lam', 'Lamentations', 5),
  CanonBook(26, 'EZK', 'Ezek', 'Ezekiel', 48),
  CanonBook(27, 'DAN', 'Dan', 'Daniel', 12),
  CanonBook(28, 'HOS', 'Hos', 'Hosea', 14),
  CanonBook(29, 'JOL', 'Joel', 'Joel', 3),
  CanonBook(30, 'AMO', 'Amos', 'Amos', 9),
  CanonBook(31, 'OBA', 'Obad', 'Obadiah', 1),
  CanonBook(32, 'JON', 'Jonah', 'Jonah', 4),
  CanonBook(33, 'MIC', 'Mic', 'Micah', 7),
  CanonBook(34, 'NAM', 'Nah', 'Nahum', 3),
  CanonBook(35, 'HAB', 'Hab', 'Habakkuk', 3),
  CanonBook(36, 'ZEP', 'Zeph', 'Zephaniah', 3),
  CanonBook(37, 'HAG', 'Hag', 'Haggai', 2),
  CanonBook(38, 'ZEC', 'Zech', 'Zechariah', 14),
  CanonBook(39, 'MAL', 'Mal', 'Malachi', 4),
  CanonBook(40, 'MAT', 'Matt', 'Matthew', 28),
  CanonBook(41, 'MRK', 'Mark', 'Mark', 16),
  CanonBook(42, 'LUK', 'Luke', 'Luke', 24),
  CanonBook(43, 'JHN', 'John', 'John', 21),
  CanonBook(44, 'ACT', 'Acts', 'Acts', 28),
  CanonBook(45, 'ROM', 'Rom', 'Romans', 16),
  CanonBook(46, '1CO', '1Cor', '1 Corinthians', 16),
  CanonBook(47, '2CO', '2Cor', '2 Corinthians', 13),
  CanonBook(48, 'GAL', 'Gal', 'Galatians', 6),
  CanonBook(49, 'EPH', 'Eph', 'Ephesians', 6),
  CanonBook(50, 'PHP', 'Phil', 'Philippians', 4),
  CanonBook(51, 'COL', 'Col', 'Colossians', 4),
  CanonBook(52, '1TH', '1Thess', '1 Thessalonians', 5),
  CanonBook(53, '2TH', '2Thess', '2 Thessalonians', 3),
  CanonBook(54, '1TI', '1Tim', '1 Timothy', 6),
  CanonBook(55, '2TI', '2Tim', '2 Timothy', 4),
  CanonBook(56, 'TIT', 'Titus', 'Titus', 3),
  CanonBook(57, 'PHM', 'Phlm', 'Philemon', 1),
  CanonBook(58, 'HEB', 'Heb', 'Hebrews', 13),
  CanonBook(59, 'JAS', 'Jas', 'James', 5),
  CanonBook(60, '1PE', '1Pet', '1 Peter', 5),
  CanonBook(61, '2PE', '2Pet', '2 Peter', 3),
  CanonBook(62, '1JN', '1John', '1 John', 5),
  CanonBook(63, '2JN', '2John', '2 John', 1),
  CanonBook(64, '3JN', '3John', '3 John', 1),
  CanonBook(65, 'JUD', 'Jude', 'Jude', 1),
  CanonBook(66, 'REV', 'Rev', 'Revelation', 22),
  // Deuterocanon. Greek Esther is a distinct text form and keeps its own
  // numbering. DanGr holds only the Greek additions (3:24-90, 13, 14); the
  // rest of Greek Daniel is stored under Daniel via the pipeline remap.
  CanonBook(67, 'TOB', 'Tob', 'Tobit', 14),
  CanonBook(68, 'JDT', 'Jdt', 'Judith', 16),
  CanonBook(69, 'ESG', 'EsthGr', 'Esther (Greek)', 16),
  CanonBook(70, 'WIS', 'Wis', 'Wisdom of Solomon', 19),
  CanonBook(71, 'SIR', 'Sir', 'Sirach', 51),
  CanonBook(72, 'BAR', 'Bar', 'Baruch', 6),
  CanonBook(73, '1MA', '1Macc', '1 Maccabees', 16),
  CanonBook(74, '2MA', '2Macc', '2 Maccabees', 15),
  CanonBook(75, 'DAG', 'DanGr', 'Daniel (Greek additions)', 14),
];

final Map<String, CanonBook> _byUsfm = {for (final b in canon) b.usfm: b};
final Map<String, CanonBook> _byOsis = {for (final b in canon) b.osis: b};

CanonBook bookById(int id) => canon[id - 1];

CanonBook? bookByUsfm(String code) => _byUsfm[code.toUpperCase()];

CanonBook? bookByOsis(String code) => _byOsis[code];
