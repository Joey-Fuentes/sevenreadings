import 'package:drift/drift.dart';

Future<QueryExecutor> openContentExecutor({
  required String assetKey,
  required String version,
}) {
  throw UnsupportedError('No content database opener for this platform.');
}
