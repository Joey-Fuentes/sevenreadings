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
}
