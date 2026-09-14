import 'package:drift/drift.dart';
import 'package:drift/wasm.dart';
import 'package:flutter/services.dart' show rootBundle;

/// Web. Requires `sqlite3.wasm` and `drift_worker.js` next to index.html
/// (see tools/web-assets.sh). The asset is fetched once and imported into
/// OPFS (or IndexedDB where OPFS is unavailable), keyed by content version.
Future<QueryExecutor> openContentExecutor({
  required String assetKey,
  required String version,
}) async {
  final result = await WasmDatabase.open(
    databaseName: 'sevenreadings-content-$version',
    sqlite3Uri: Uri.parse('sqlite3.wasm'),
    driftWorkerUri: Uri.parse('drift_worker.js'),
    initializeDatabase: () async {
      final data = await rootBundle.load(assetKey);
      return data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes);
    },
  );
  return result.resolvedExecutor;
}
