import 'package:flutter/material.dart';
import 'package:sr_core/sr_core.dart';
import 'package:sr_data/sr_data.dart';

/// One chapter, every translation side by side (stacked on narrow screens),
/// tap a verse for its readings. Navigation follows the selected tradition's
/// book order from the `book_orders` table.
class ReaderScreen extends StatefulWidget {
  const ReaderScreen({super.key, required this.db});

  final ContentDb db;

  @override
  State<ReaderScreen> createState() => _ReaderScreenState();
}

/// Book as the reader needs it, independent of which drift class carried it.
class _BookInfo {
  const _BookInfo(this.id, this.name, this.chapters);

  final int id;
  final String name;
  final int chapters;
}

class _ReaderScreenState extends State<ReaderScreen> {
  String _tradition = 'protestant';
  List<_BookInfo> _order = const [];
  VerseRef _chapter = const VerseRef(1, 1, 1);
  late Future<_ChapterData> _data = _init();

  Future<_ChapterData> _init() async {
    await _loadOrder();
    return _load();
  }

  Future<List<_BookInfo>> _loadOrder() async {
    final rows = await widget.db.bookOrder(_tradition).get();
    return _order = [
      for (final r in rows) _BookInfo(r.id, r.name, r.chapters),
    ];
  }

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

  void _open(int book, int chapter) {
    setState(() {
      _chapter = VerseRef(book, chapter, 1);
      _data = _load();
    });
  }

  /// Previous/next chapter, crossing book boundaries in tradition order.
  void _step(int delta) {
    var pos = _order.indexWhere((b) => b.id == _chapter.book);
    var chapter = _chapter.chapter + delta;
    if (pos < 0) {
      // Book outside this tradition's order: stay within the book.
      final max = _chapter.bookInfo.chapters;
      if (chapter < 1 || chapter > max) return;
      _open(_chapter.book, chapter);
      return;
    }
    if (chapter < 1) {
      if (pos == 0) return;
      pos -= 1;
      chapter = _order[pos].chapters;
    } else if (chapter > _order[pos].chapters) {
      if (pos == _order.length - 1) return;
      pos += 1;
      chapter = 1;
    }
    _open(_order[pos].id, chapter);
  }

  Future<void> _pickChapter(BuildContext context) async {
    final picked = await showModalBottomSheet<(int, int)>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => _BookPicker(
        order: _order,
        tradition: _tradition,
        current: _chapter,
        onTradition: (t) {
          _tradition = t;
          return _loadOrder();
        },
      ),
    );
    if (picked != null) _open(picked.$1, picked.$2);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: TextButton.icon(
          onPressed: () => _pickChapter(context),
          icon: const Icon(Icons.expand_more),
          label: Text('${_chapter.bookInfo.name} ${_chapter.chapter}'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.chevron_left),
            onPressed: () => _step(-1),
          ),
          IconButton(
            icon: const Icon(Icons.chevron_right),
            onPressed: () => _step(1),
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

/// Two-step picker: tradition + book list, then a chapter grid.
class _BookPicker extends StatefulWidget {
  const _BookPicker({
    required this.order,
    required this.tradition,
    required this.current,
    required this.onTradition,
  });

  final List<_BookInfo> order;
  final String tradition;
  final VerseRef current;
  final Future<List<_BookInfo>> Function(String tradition) onTradition;

  @override
  State<_BookPicker> createState() => _BookPickerState();
}

class _BookPickerState extends State<_BookPicker> {
  late String _tradition = widget.tradition;
  late List<_BookInfo> _order = widget.order;
  _BookInfo? _book;

  /// Books the content holds that this tradition's order leaves out, so the
  /// deuterocanon is still reachable from the Protestant list.
  List<_BookInfo> get _extras {
    final listed = {for (final b in _order) b.id};
    return [
      for (final b in canon)
        if (!listed.contains(b.id)) _BookInfo(b.id, b.name, b.chapters),
    ];
  }

  Future<void> _setTradition(String t) async {
    final order = await widget.onTradition(t);
    if (!mounted) return;
    setState(() {
      _tradition = t;
      _order = order;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final book = _book;
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.8,
      builder: (context, controller) {
        if (book != null) {
          return ListView(
            controller: controller,
            padding: const EdgeInsets.all(16),
            children: [
              Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back),
                    onPressed: () => setState(() => _book = null),
                  ),
                  Text(book.name, style: theme.textTheme.titleLarge),
                ],
              ),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (var c = 1; c <= book.chapters; c++)
                    ActionChip(
                      label: Text('$c'),
                      onPressed: () => Navigator.pop(context, (book.id, c)),
                    ),
                ],
              ),
            ],
          );
        }
        final extras = _extras;
        return ListView(
          controller: controller,
          padding: const EdgeInsets.all(16),
          children: [
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'protestant', label: Text('Protestant')),
                ButtonSegment(value: 'catholic', label: Text('Catholic')),
              ],
              selected: {_tradition},
              onSelectionChanged: (s) => _setTradition(s.first),
            ),
            const SizedBox(height: 12),
            for (final b in _order) _bookTile(b),
            if (extras.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text('Also in this content', style: theme.textTheme.labelLarge),
              for (final b in extras) _bookTile(b),
            ],
          ],
        );
      },
    );
  }

  Widget _bookTile(_BookInfo b) {
    return ListTile(
      title: Text(b.name),
      trailing: Text('${b.chapters}'),
      selected: b.id == widget.current.book,
      onTap: () => setState(() => _book = b),
    );
  }
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
        if (verses.isEmpty)
          Text('Not in this translation.', style: theme.textTheme.bodySmall),
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
