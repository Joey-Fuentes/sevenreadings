import 'package:flutter/material.dart';
import 'package:sr_core/sr_core.dart';
import 'package:sr_data/sr_data.dart';

/// Minimal reader: one chapter, all translations side by side (or stacked on
/// narrow screens), tap a verse for its readings. Replace freely; this exists
/// to prove the data path end to end.
class ReaderScreen extends StatefulWidget {
  const ReaderScreen({super.key, required this.db});

  final ContentDb db;

  @override
  State<ReaderScreen> createState() => _ReaderScreenState();
}

class _ReaderScreenState extends State<ReaderScreen> {
  VerseRef _chapter = const VerseRef(1, 1, 1);
  late Future<_ChapterData> _data = _load();

  Future<_ChapterData> _load() async {
    final translations = await widget.db.allTranslations().get();
    final verses = <String, List<ChapterVersesResult>>{};
    for (final t in translations) {
      verses[t.id] = await widget.db
          .chapterVerses(t.id, _chapter.chapterStart.id, _chapter.chapterEnd.id)
          .get();
    }
    return _ChapterData(translations, verses);
  }

  void _go(int bookDelta, int chapterDelta) {
    var book = _chapter.book;
    var chapter = _chapter.chapter + chapterDelta;
    if (bookDelta != 0) {
      book = (book + bookDelta).clamp(1, maxBookId);
      chapter = 1;
    } else if (chapter < 1) {
      book = (book - 1).clamp(1, maxBookId);
      chapter = bookById(book).chapters;
    } else if (chapter > bookById(book).chapters) {
      book = (book + 1).clamp(1, maxBookId);
      chapter = 1;
    }
    setState(() {
      _chapter = VerseRef(book, chapter, 1);
      _data = _load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('${_chapter.bookInfo.name} ${_chapter.chapter}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.chevron_left),
            onPressed: () => _go(0, -1),
          ),
          IconButton(
            icon: const Icon(Icons.chevron_right),
            onPressed: () => _go(0, 1),
          ),
        ],
      ),
      body: FutureBuilder<_ChapterData>(
        future: _data,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(child: Text('${snapshot.error}'));
          }
          final data = snapshot.data;
          if (data == null) {
            return const Center(child: CircularProgressIndicator());
          }
          return LayoutBuilder(
            builder: (context, constraints) {
              final columns = data.translations
                  .map(
                    (t) => Expanded(
                      child: _TranslationColumn(
                        translation: t,
                        verses: data.verses[t.id] ?? const [],
                        onTap: (verseId) => _showReadings(context, verseId),
                      ),
                    ),
                  )
                  .toList();
              if (constraints.maxWidth >= 720) {
                return Row(children: columns);
              }
              return Column(children: columns);
            },
          );
        },
      ),
    );
  }

  Future<void> _showReadings(BuildContext context, int verseId) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.6,
        builder: (_, controller) => _ReadingsSheet(
          db: widget.db,
          verse: VerseRef.fromId(verseId),
          controller: controller,
        ),
      ),
    );
  }
}

class _ChapterData {
  const _ChapterData(this.translations, this.verses);

  final List<Translation> translations;
  final Map<String, List<ChapterVersesResult>> verses;
}

class _TranslationColumn extends StatelessWidget {
  const _TranslationColumn({
    required this.translation,
    required this.verses,
    required this.onTap,
  });

  final Translation translation;
  final List<ChapterVersesResult> verses;
  final ValueChanged<int> onTap;

  /// Verse number, plus the translation's own number when it differs.
  static String _label(ChapterVersesResult v) {
    final n = VerseRef.fromId(v.verseId).verse;
    final native = v.nativeRef;
    return native == null ? '$n ' : '$n ($native) ';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(translation.abbreviation, style: theme.textTheme.labelLarge),
        const SizedBox(height: 8),
        for (final v in verses)
          InkWell(
            onTap: () => onTap(v.verseId),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Text.rich(
                TextSpan(
                  children: [
                    TextSpan(
                      text: _label(v),
                      style: theme.textTheme.labelSmall,
                    ),
                    TextSpan(text: v.body),
                  ],
                ),
                style: theme.textTheme.bodyLarge,
              ),
            ),
          ),
      ],
    );
  }
}

class _ReadingsSheet extends StatelessWidget {
  const _ReadingsSheet({
    required this.db,
    required this.verse,
    required this.controller,
  });

  final ContentDb db;
  final VerseRef verse;
  final ScrollController controller;

  Future<(List<Perspective>, List<ReadingsForVerseResult>)> _load() async {
    final perspectives = await db.allPerspectives().get();
    final readings = await db.readingsForVerse(verse.id).get();
    return (perspectives, readings);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return FutureBuilder(
      future: _load(),
      builder: (context, snapshot) {
        final data = snapshot.data;
        if (data == null) {
          return const Center(child: CircularProgressIndicator());
        }
        final (perspectives, readings) = data;
        return ListView(
          controller: controller,
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 32),
          children: [
            Text(verse.label, style: theme.textTheme.titleLarge),
            const SizedBox(height: 12),
            // "3 of 7 available" is the normal case: every perspective is
            // listed, and absent ones say so instead of disappearing.
            for (final p in perspectives) ...[
              Text(p.name, style: theme.textTheme.titleMedium),
              for (final r in readings.where((r) => r.perspectiveId == p.id))
                Padding(
                  padding: const EdgeInsets.only(top: 6, bottom: 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        [r.author, if (r.citation != null) r.citation!]
                            .join(' \u00b7 '),
                        style: theme.textTheme.labelMedium,
                      ),
                      if (r.heading != null)
                        Text(r.heading!, style: theme.textTheme.labelLarge),
                      Text(r.body),
                    ],
                  ),
                ),
              if (!readings.any((r) => r.perspectiveId == p.id))
                Padding(
                  padding: const EdgeInsets.only(top: 4, bottom: 12),
                  child: Text(
                    'No reading from this tradition here.',
                    style: theme.textTheme.bodySmall,
                  ),
                ),
            ],
          ],
        );
      },
    );
  }
}
