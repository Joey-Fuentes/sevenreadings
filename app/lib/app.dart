import 'package:flutter/material.dart';
import 'package:sr_data/sr_data.dart';

import 'content/content_loader.dart';
import 'features/reader/reader_screen.dart';

class SevenReadingsApp extends StatefulWidget {
  const SevenReadingsApp({super.key});

  @override
  State<SevenReadingsApp> createState() => _SevenReadingsAppState();
}

class _SevenReadingsAppState extends State<SevenReadingsApp> {
  late final Future<ContentDb> _content = loadContentDb();
  late final UserDb _user = UserDb.open();

  @override
  void dispose() {
    // A second app instance in the same process (the integration test's
    // relaunch) must find both files closed.
    _content.then((db) => db.close()).ignore();
    _user.close().ignore();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'sevenreadings',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF5B4636),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorSchemeSeed: const Color(0xFF5B4636),
        brightness: Brightness.dark,
        useMaterial3: true,
      ),
      home: FutureBuilder<ContentDb>(
        future: _content,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Scaffold(
              body: Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text('Could not open content:\n${snapshot.error}'),
                ),
              ),
            );
          }
          if (!snapshot.hasData) {
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          }
          return ReaderScreen(db: snapshot.data!, user: _user);
        },
      ),
    );
  }
}
