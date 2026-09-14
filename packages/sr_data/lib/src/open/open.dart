import 'package:drift/drift.dart';

import '../content_db.dart';
import 'open_unsupported.dart'
    if (dart.library.ffi) 'open_native.dart'
    if (dart.library.js_interop) 'open_web.dart' as impl;

/// Opens the bundled content database.
///
/// [assetKey] is the Flutter asset path of the SQLite file (declared by the
/// app, not this package). [version] is the content version from the
/// bundled manifest; it keys the on-device copy so a new content release
/// replaces the old one on first launch.
Future<ContentDb> openContentDb({
  required String assetKey,
  required String version,
}) async {
  final executor = await openContentExecutor(
    assetKey: assetKey,
    version: version,
  );
  return ContentDb(executor);
}

Future<QueryExecutor> openContentExecutor({
  required String assetKey,
  required String version,
}) =>
    impl.openContentExecutor(assetKey: assetKey, version: version);
