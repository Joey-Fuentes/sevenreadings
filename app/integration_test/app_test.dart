// The first-launch checklist (docs/plan.md, section 2) as an integration
// test. On a device, emulator or simulator:
//
//   cd app
//   flutter test integration_test -d <device>              # the checks
//   flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/app_test.dart -d <device>  # + screenshots
//
// Everything asserted holds for sample and release content alike: Genesis 1
// in the WEB and BSB, Matthew Henry and Rashi on Genesis 1:1, the seven
// perspective headings, Genesis 1:1 first for "beginning God created", a
// Matthew Henry Genesis entry first for "creation". Screenshots reach the
// host only through `flutter drive`; `flutter test` hands their bytes to
// the test and drops them. Launch timings go into the driver's report
// (build/integration_response_data.json) and the log.
//
// One test, deliberately: the binding resets the Android screenshot surface
// between tests, so the second launch lives in the same test, after the
// first app is unmounted the way the binding would unmount it. Lists are
// lazy, so anything below the fold is scrolled to before it is expected;
// scrolled programmatically, because synthetic drags moved nothing on the
// Linux build while the same drags worked on the emulator.
//
// Screenshots: Android, iOS and web go through the integration_test
// plugin (proven on the Android emulator). Desktop has no such plugin, so
// there the app is rendered from a RepaintBoundary at its root and the
// bytes are handed to the same driver through the same report list.
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:sevenreadings/app.dart';
import 'package:sevenreadings/features/about/about_screen.dart';
import 'package:sevenreadings/features/reader/reader_screen.dart';

late final IntegrationTestWidgetsFlutterBinding binding;
var surfaceConverted = false;

/// Wraps the app so desktop screenshots can be rendered from it.
final rootBoundaryKey = GlobalKey();

/// The seven readings as the sheet lists them (pipeline db.py PERSPECTIVES).
const perspectives = [
  'Jewish: Literal (Peshat)',
  'Jewish: Rationalist',
  'Roman Catholic',
  'Eastern Orthodox',
  'Protestant / Reformed',
  'Islamic',
  'Secular / Academic',
];

const noteText = 'Written by the integration test';

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;

  testWidgets('first launch, the checklist, second launch', (tester) async {
    // Launch, first content copy, Genesis 1 with the Bible chips.
    final ms = await launch(tester);
    report('first_launch_ms', ms);
    final size = tester.view.physicalSize / tester.view.devicePixelRatio;
    report('view', '${size.width.round()}x${size.height.round()} dp');
    expect(find.text('WEB'), findsWidgets);
    expect(find.text('BSB'), findsWidgets);
    await screenshot(tester, '01-genesis-1');

    // Support Seven Readings: the band under the title row, on every
    // screen of builds that may show outside payment links (all the
    // checklist's builds are direct ones, see support_links.dart).
    await tester.tap(find.text('Support Seven Readings'));
    await waitFor(tester, find.text('Support'));
    expect(find.textContaining('buy.stripe.com'), findsWidgets);
    await screenshot(tester, '02-support');
    await tester.pageBack();
    await waitFor(tester, find.textContaining('In the beginning'));

    // A verse's readings: the sheet opens on Genesis 1:1.
    await openReadings(tester);
    await screenshot(tester, '03-readings-genesis-1-1');

    // A bookmark and a note, from the sheet's header. A device that ran
    // this before already has the bookmark; only add one when it is missing.
    if (find.byTooltip('Remove bookmark').evaluate().isEmpty) {
      await tester.tap(find.byTooltip('Bookmark'));
    }
    await waitFor(tester, find.byTooltip('Remove bookmark'));
    await tester.tap(find.byTooltip('Add a note'));
    await waitFor(tester, find.text('New note'));
    await tester.enterText(find.byType(TextField), noteText);
    await tester.tap(find.text('Save'));
    await waitFor(tester, find.text(noteText));
    await screenshot(tester, '04-bookmark-and-note');

    // Every tradition is listed, with a reading or with "No reading"; the
    // Protestant reading on Genesis 1:1 is Matthew Henry in both contents.
    final sheet = find.byKey(readingsSheetKey);
    for (final name in perspectives) {
      await scrollTo(tester, find.text(name), sheet);
      if (name == 'Protestant / Reformed') {
        await scrollTo(tester, find.textContaining('Matthew Henry'), sheet);
      }
    }
    await closeSheet(tester);

    // Search. A verse hit is listed with its translation; a readings hit
    // opens its chapter and the readings sheet on the verse.
    await tester.tap(find.byTooltip('Search'));
    await waitFor(tester, find.byType(TextField));
    await tester.enterText(find.byType(TextField), 'beginning God created');
    await waitFor(tester, find.textContaining('Genesis 1:1 \u00b7'));
    await screenshot(tester, '05-search-verses');
    await tester.tap(find.text('Readings'));
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.byType(DropdownButton<String?>));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.tap(find.text('Matthew Henry').last);
    await tester.pump(const Duration(milliseconds: 300));
    await tester.enterText(find.byType(TextField), 'creation');
    final hit = find.textContaining('Matthew Henry \u00b7 Genesis');
    await waitFor(tester, hit);
    await screenshot(tester, '06-search-readings');
    await tester.tap(hit.first);
    await waitFor(tester, find.byKey(readingsSheetKey));
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.textContaining(RegExp(r'^Genesis \d+:1$')), findsWidgets);
    await closeSheet(tester);

    // Bookmarks & notes, reached from the book picker.
    await openPicker(tester);
    await scrollTo(
      tester,
      find.text('Bookmarks & notes'),
      find.byKey(bookPickerKey),
    );
    await tester.tap(find.text('Bookmarks & notes'));
    await waitFor(tester, find.text('Bookmarks'));
    expect(find.text('Genesis 1:1'), findsWidgets);
    expect(find.text(noteText), findsWidgets);
    await screenshot(tester, '07-bookmarks-and-notes');
    await tester.pageBack();
    await waitFor(tester, find.byIcon(Icons.expand_more));

    // About the texts: licenses and notices from the database.
    await openPicker(tester);
    await scrollTo(
      tester,
      find.text('About the texts'),
      find.byKey(bookPickerKey),
    );
    await tester.tap(find.text('About the texts'));
    await waitFor(tester, find.text('Bibles'));
    await screenshot(tester, '08-about-the-texts');
    await scrollTo(tester, find.text('Notices'), find.byKey(aboutListKey));
    await tester.pageBack();
    await waitFor(tester, find.byIcon(Icons.expand_more));

    // Second launch: a new app instance in the same process. Unmounting the
    // first runs SevenReadingsApp.dispose, which closes both databases; the
    // second reopens the copied content (the copy is skipped, the file
    // exists) and the user database, where the bookmark and note live.
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(milliseconds: 500));
    final second = await launch(tester);
    report('second_launch_ms', second);
    expect(find.text('WEB'), findsWidgets);
    await openReadings(tester);
    await waitFor(tester, find.byTooltip('Remove bookmark'));
    expect(find.text(noteText), findsWidgets);
    await screenshot(tester, '09-second-launch');
    await closeSheet(tester);
  });
}

/// Pumps a fresh app and waits for Genesis 1 with its verses on screen.
/// Returns the milliseconds from the first frame to that; on a first launch
/// it includes the content copy.
Future<int> launch(WidgetTester tester) async {
  // enterText goes through the test text input; the live binding may leave
  // the real keyboard in charge, so register it when it is not.
  if (!binding.testTextInput.isRegistered) binding.testTextInput.register();
  final clock = Stopwatch()..start();
  await tester.pumpWidget(
    RepaintBoundary(key: rootBoundaryKey, child: const SevenReadingsApp()),
  );
  await waitFor(
    tester,
    find.text('Genesis 1'),
    timeout: const Duration(minutes: 10),
  );
  await waitFor(tester, find.textContaining('In the beginning'));
  clock.stop();
  await tester.pump(const Duration(milliseconds: 500));
  return clock.elapsedMilliseconds;
}

/// Taps Genesis 1:1 (the first translation showing it) and waits for the
/// readings sheet to load.
Future<void> openReadings(WidgetTester tester) async {
  await tester.tap(find.textContaining('In the beginning').first);
  await waitFor(tester, find.byKey(readingsSheetKey));
  await tester.pump(const Duration(milliseconds: 500));
}

Future<void> closeSheet(WidgetTester tester) async {
  Navigator.of(tester.element(find.byKey(readingsSheetKey))).pop();
  await tester.pump(const Duration(milliseconds: 500));
  await waitFor(tester, find.byIcon(Icons.expand_more));
}

Future<void> openPicker(WidgetTester tester) async {
  await tester.pump(const Duration(milliseconds: 400));
  await tester.tap(find.byIcon(Icons.expand_more));
  await waitFor(tester, find.byKey(bookPickerKey));
  await tester.pump(const Duration(milliseconds: 500));
}

/// Scrolls the list [view] until [finder] is on stage, then aligns it.
/// Programmatic, not a drag: the first Linux run (2026-09-15) showed
/// synthetic drags not moving the readings sheet, and bringing an item
/// into view needs no gesture anyway.
Future<void> scrollTo(WidgetTester tester, Finder finder, Finder view) async {
  final scrollables = find.descendant(
    of: view,
    matching: find.byType(Scrollable),
  );
  final position = tester.state<ScrollableState>(scrollables.first).position;
  for (var i = 0; i < 100 && finder.evaluate().isEmpty; i++) {
    final max = position.maxScrollExtent;
    final next = position.pixels + 200;
    position.jumpTo(next > max ? max : next);
    await tester.pump();
  }
  await Scrollable.ensureVisible(tester.element(finder.first));
  await tester.pump(const Duration(milliseconds: 300));
}

/// Pumps real frames until [finder] matches; fails after [timeout].
Future<void> waitFor(
  WidgetTester tester,
  Finder finder, {
  Duration timeout = const Duration(seconds: 60),
}) async {
  final clock = Stopwatch()..start();
  while (finder.evaluate().isEmpty) {
    if (clock.elapsed > timeout) {
      fail('Timed out after ${timeout.inSeconds}s waiting for $finder');
    }
    await tester.pump(const Duration(milliseconds: 100));
  }
}

/// Whether the integration_test plugin captures screenshots here (Android,
/// iOS, web); elsewhere the test renders them itself.
bool get pluginScreenshots {
  if (kIsWeb) return true;
  final p = defaultTargetPlatform;
  return p == TargetPlatform.android || p == TargetPlatform.iOS;
}

/// Captures the screen under [name]. Android needs the surface converted
/// to an image once before the first capture.
Future<void> screenshot(WidgetTester tester, String name) async {
  await tester.pump(const Duration(milliseconds: 500));
  if (pluginScreenshots) {
    final android = !kIsWeb && defaultTargetPlatform == TargetPlatform.android;
    if (android && !surfaceConverted) {
      await binding.convertFlutterSurfaceToImage();
      surfaceConverted = true;
    }
    await binding.takeScreenshot(name);
    return;
  }
  final bytes = await renderRoot(tester);
  final report = binding.reportData ??= <String, dynamic>{};
  final shots = (report['screenshots'] ??= <dynamic>[]) as List<dynamic>;
  shots.add(<String, dynamic>{'screenshotName': name, 'bytes': bytes});
}

/// The app as PNG bytes, from the RepaintBoundary around it. Modal sheets,
/// dialogs and menus live in the app's own overlay, so they are included.
Future<List<int>> renderRoot(WidgetTester tester) async {
  final context = rootBoundaryKey.currentContext!;
  final boundary = context.findRenderObject()! as RenderRepaintBoundary;
  for (var i = 0; i < 5 && boundary.debugNeedsPaint; i++) {
    await tester.pump();
  }
  final ratio = tester.view.devicePixelRatio;
  final image = await boundary.toImage(pixelRatio: ratio);
  final data = await image.toByteData(format: ui.ImageByteFormat.png);
  image.dispose();
  return data!.buffer.asUint8List();
}

void report(String key, Object value) {
  binding.reportData ??= <String, dynamic>{};
  binding.reportData![key] = value;
  debugPrint('checklist: $key = $value');
}
