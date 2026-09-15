// Host side of `flutter drive` for integration_test/app_test.dart: writes
// every screenshot the test takes to screenshots/<name>.png and the test's
// report (launch timings) to build/integration_response_data.json, both
// relative to the working directory (app/). Screenshots are written whether
// the tests passed or not, so a failing run still shows what it saw.
import 'dart:io';

import 'package:integration_test/integration_test_driver.dart'
    show writeResponseData;
import 'package:integration_test/integration_test_driver_extended.dart';

Future<void> main() async {
  final dir = Directory('screenshots');
  await dir.create(recursive: true);
  await integrationDriver(
    onScreenshot: (name, bytes, [args]) async {
      final file = File('${dir.path}/$name.png');
      await file.writeAsBytes(bytes);
      stdout.writeln('screenshot: ${file.path}');
      return true;
    },
    responseDataCallback: (data) async {
      // The raw screenshot bytes are already on disk; keep the report small.
      final report = <String, dynamic>{...?data}..remove('screenshots');
      await writeResponseData(report);
    },
    writeResponseOnFailure: true,
  );
}
