import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sr_core/sr_core.dart';
import 'package:sr_data/sr_data.dart';

void main() {
  late UserDb db;

  setUp(() => db = UserDb(NativeDatabase.memory()));
  tearDown(() => db.close());

  test('onCreate can run twice on the same database', () async {
    // A first open interrupted before the schema version was recorded leaves
    // the tables behind; the next open runs onCreate again and must succeed.
    await db.toggleBookmark(const VerseRef(1, 1, 1).id); // opens, creates
    await db.createMigrator().createAll(); // the second run
    expect(await db.toggleBookmark(const VerseRef(1, 1, 1).id), isFalse);
  });

  test('bookmarks toggle and list newest first', () async {
    final a = const VerseRef(43, 3, 16).id;
    final b = const VerseRef(1, 1, 1).id;
    expect(await db.toggleBookmark(a), isTrue);
    expect(await db.toggleBookmark(b), isTrue);
    expect((await db.bookmarkForVerse(a).getSingleOrNull())?.verseId, a);
    expect((await db.allBookmarks().get()).map((x) => x.verseId), [b, a]);
    expect(await db.toggleBookmark(a), isFalse);
    expect(await db.bookmarkForVerse(a).getSingleOrNull(), isNull);
    expect((await db.allBookmarks().get()).length, 1);
  });

  test('notes attach to a verse and can be edited and deleted', () async {
    final v = const VerseRef(19, 23, 1).id;
    final id = await db.addNote(v, 'first thought');
    expect((await db.notesForVerse(v).get()).single.body, 'first thought');
    expect(await db.notesForVerse(const VerseRef(19, 23, 2).id).get(), isEmpty);
    await db.updateNote(id, 'second thought');
    expect((await db.allNotes().get()).single.body, 'second thought');
    await db.deleteNote(id);
    expect(await db.allNotes().get(), isEmpty);
  });
}
