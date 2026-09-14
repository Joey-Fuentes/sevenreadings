import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// Android, iOS, macOS, Windows, Linux.
///
/// Assets cannot be opened in place (on Android they live inside the APK), so
/// the file is copied once into the app-support directory, keyed by content
/// version. Older copies are deleted.
Future<QueryExecutor> openContentExecutor({
  required String assetKey,
  required String version,
}) async {
  final support = await getApplicationSupportDirectory();
  final dir = Directory(p.join(support.path, 'content'));
  final target = File(p.join(dir.path, 'content-$version.sqlite'));

  if (!await target.exists()) {
    await dir.create(recursive: true);
    // Load into memory then write. Assets do not stream on all platforms; a
    // 100-200 MB one-time copy is acceptable, and this only runs on first
    // launch after install or content update.
    final data = await rootBundle.load(assetKey);
    final tmp = File('${target.path}.part');
    await tmp.writeAsBytes(
      data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes),
      flush: true,
    );
    await tmp.rename(target.path);
    await for (final entity in dir.list()) {
      if (entity is File &&
          entity.path != target.path &&
          entity.path.endsWith('.sqlite')) {
        await entity.delete();
      }
    }
  }

  return NativeDatabase.createInBackground(
    target,
    // The content file is never written by the app.
    setup: (raw) => raw.execute('PRAGMA query_only = 1'),
  );
}
