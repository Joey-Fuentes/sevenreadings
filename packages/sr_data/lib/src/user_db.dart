import 'package:drift/drift.dart';
import 'package:drift_flutter/drift_flutter.dart';

part 'user_db.g.dart';

/// Per-user database: notes, bookmarks, reading positions, settings.
///
/// Created on first launch and migrated in place. Kept separate from
/// [ContentDb] so content can be swapped without touching user data.
@DriftDatabase(include: {'schema/user.drift'})
class UserDb extends _$UserDb {
  UserDb(super.executor);

  /// Opens (or creates) the user database in the platform's app-data folder.
  factory UserDb.open() => UserDb(
        driftDatabase(
          name: 'sevenreadings_user',
          web: DriftWebOptions(
            sqlite3Wasm: Uri.parse('sqlite3.wasm'),
            driftWorker: Uri.parse('drift_worker.js'),
          ),
        ),
      );

  @override
  int get schemaVersion => 1;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onCreate: (m) => m.createAll(),
        // Add onUpgrade steps here as the user schema evolves. Never break
        // an existing user database.
      );

  static int _now() => DateTime.now().millisecondsSinceEpoch;

  /// Adds a bookmark on [verseId], or removes the existing one. Returns
  /// whether the verse is bookmarked afterwards.
  Future<bool> toggleBookmark(int verseId) async {
    final existing = await bookmarkForVerse(verseId).getSingleOrNull();
    if (existing != null) {
      await (delete(bookmarks)..where((b) => b.id.equals(existing.id))).go();
      return false;
    }
    await into(bookmarks).insert(
      BookmarksCompanion.insert(verseId: verseId, createdAt: _now()),
    );
    return true;
  }

  Future<void> deleteBookmark(int id) =>
      (delete(bookmarks)..where((b) => b.id.equals(id))).go();

  /// A note on a single verse. Notes may span ranges in the schema; the
  /// reader creates them one verse at a time.
  Future<int> addNote(int verseId, String body) {
    final now = _now();
    return into(notes).insert(
      NotesCompanion.insert(
        startVerseId: verseId,
        endVerseId: verseId,
        body: body,
        createdAt: now,
        updatedAt: now,
      ),
    );
  }

  Future<void> updateNote(int id, String body) =>
      (update(notes)..where((n) => n.id.equals(id))).write(
        NotesCompanion(body: Value(body), updatedAt: Value(_now())),
      );

  Future<void> deleteNote(int id) =>
      (delete(notes)..where((n) => n.id.equals(id))).go();
}
