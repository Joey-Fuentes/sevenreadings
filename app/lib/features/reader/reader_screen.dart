import 'package:flutter/material.dart';
import 'package:sr_core/sr_core.dart';
import 'package:sr_data/sr_data.dart';

import '../about/about_screen.dart';
import '../narrator/narrator.dart';
import '../narrator/narrator_bar.dart';
import '../notes/notes_screen.dart';
import '../search/search_screen.dart';
import '../support/support_links.dart';
import '../support/support_screen.dart';
import 'markdown_text.dart';

/// The readings sheet's list and the book picker's list, for the integration
/// test to scroll (`integration_test/app_test.dart`).
const Key readingsSheetKey = Key('readings-sheet');
const Key bookPickerKey = Key('book-picker');

/// One chapter, every translation side by side (stacked on narrow screens),
/// tap a verse for its readings. Navigation follows the selected tradition's
/// book order from the `book_orders` table; search opens a chapter on the
/// verse that was hit.
class ReaderScreen extends StatefulWidget {
  const ReaderScreen({super.key, required this.db, required this.user});

  final ContentDb db;
  final UserDb user;

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

  /// Verse to mark and scroll to after a search, cleared by any navigation.
  int? _highlight;

  /// Translations the reader has switched off. Empty = show everything.
  final Set<String> _hidden = {};

  /// Reads the chapter (or a reading) aloud; the bar at the bottom shows
  /// it, and the verse being read is the highlighted one.
  late final Narrator _narrator = Narrator()..addListener(_narrated);
  static const _speedSetting = 'narrator.speed';
  String? _savedSpeed;
  int? _narratedVerse;

  Future<_ChapterData> _init() async {
    await _loadOrder();
    await _loadSpeed();
    return _load();
  }

  Future<void> _loadSpeed() async {
    try {
      final saved = await widget.user.setting(_speedSetting);
      final speed = double.tryParse(saved ?? '');
      if (speed != null && Narrator.speeds.contains(speed)) {
        _savedSpeed = saved;
        _narrator.speed = speed;
      }
    } catch (e) {
      debugPrint('narrator speed not loaded: $e');
    }
  }

  /// Follows the narrator: the verse it reads becomes the highlight, and
  /// a changed speed is remembered.
  void _narrated() {
    final verse = _narrator.active ? _narrator.current?.verseId : null;
    if (verse != _narratedVerse) {
      _narratedVerse = verse;
      if (verse != null && mounted) {
        setState(() {
          _highlight = verse;
        });
      }
    }
    final speed = '${_narrator.speed}';
    if (speed != _savedSpeed) {
      _savedSpeed = speed;
      widget.user.setSetting(_speedSetting, speed).ignore();
    }
  }

  @override
  void dispose() {
    _narrator.dispose();
    super.dispose();
  }

  /// Reads this chapter aloud in the first English translation shown, from
  /// the highlighted verse when there is one.
  Future<void> _listen() async {
    final data = await _data;
    final shown = data.translations.where(
      (t) => t.language == 'en' && !_hidden.contains(t.id),
    );
    for (final t in shown) {
      final verses = data.verses[t.id] ?? const [];
      if (verses.isEmpty) continue;
      final chunks = [
        for (final v in verses) NarratorChunk(v.body, verseId: v.verseId),
      ];
      var from = 0;
      final highlight = _highlight;
      if (highlight != null) {
        final i = verses.indexWhere((v) => v.verseId == highlight);
        if (i >= 0) from = i;
      }
      final title = '${_chapter.bookInfo.name} ${_chapter.chapter}';
      await _narrator.read(title, chunks, from: from);
      return;
    }
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('No English text to read here.')),
    );
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

  void _open(int book, int chapter, {int? highlight}) {
    _narrator.stop();
    setState(() {
      _chapter = VerseRef(book, chapter, 1);
      _highlight = highlight;
      _data = _load();
    });
  }

  Future<void> _search() async {
    final target = await Navigator.of(context).push<SearchTarget>(
      MaterialPageRoute(builder: (_) => SearchScreen(db: widget.db)),
    );
    _goTo(target);
  }

  Future<void> _notes() async {
    final target = await Navigator.of(context).push<SearchTarget>(
      MaterialPageRoute(builder: (_) => NotesScreen(user: widget.user)),
    );
    _goTo(target);
  }

  /// Open the chapter of a search, bookmark or note hit on its verse.
  void _goTo(SearchTarget? target) {
    if (target == null || !mounted) return;
    final ref = VerseRef.fromId(target.verseId);
    _open(ref.book, ref.chapter, highlight: target.verseId);
    if (target.showReadings) _showReadings(context, target.verseId);
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
        onAbout: _about,
        onNotes: _notes,
      ),
    );
    if (picked != null) _open(picked.$1, picked.$2);
  }

  void _about() {
    Navigator.of(context).push<void>(
      MaterialPageRoute(builder: (_) => AboutScreen(db: widget.db)),
    );
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
            icon: const Icon(Icons.headphones),
            tooltip: 'Listen',
            onPressed: _listen,
          ),
          IconButton(
            icon: const Icon(Icons.search),
            tooltip: 'Search',
            onPressed: _search,
          ),
          IconButton(
            icon: const Icon(Icons.chevron_left),
            onPressed: () => _step(-1),
          ),
          IconButton(
            icon: const Icon(Icons.chevron_right),
            onPressed: () => _step(1),
          ),
        ],
        bottom: showsSupportLinks ? const SupportBar() : null,
      ),
      bottomNavigationBar: NarratorBar(narrator: _narrator),
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
          // Translations with nothing in this chapter drop out on their own;
          // the chip stays, disabled, so the reader knows why.
          final present = data.translations
              .where((t) => (data.verses[t.id] ?? const []).isNotEmpty)
              .toList();
          final shown = present.where((t) => !_hidden.contains(t.id)).toList();
          return Column(
            children: [
              _TranslationChips(
                translations: data.translations,
                present: {for (final t in present) t.id},
                hidden: _hidden,
                onToggle: (id) => setState(() {
                  if (!_hidden.remove(id)) _hidden.add(id);
                }),
              ),
              Expanded(
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    if (constraints.maxWidth >= 720) {
                      return Row(
                        children: [
                          for (final t in shown)
                            Expanded(
                              child: _TranslationColumn(
                                translation: t,
                                verses: data.verses[t.id] ?? const [],
                                highlight: _highlight,
                                onTap: (id) => _showReadings(context, id),
                              ),
                            ),
                        ],
                      );
                    }
                    return _InterleavedView(
                      translations: shown,
                      verses: data.verses,
                      highlight: _highlight,
                      onTap: (id) => _showReadings(context, id),
                    );
                  },
                ),
              ),
            ],
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
          user: widget.user,
          narrator: _narrator,
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

/// Two-step picker: tradition + book list, then a chapter grid. Also the
/// way to the About screen, since the app bar has no room for another icon.
class _BookPicker extends StatefulWidget {
  const _BookPicker({
    required this.order,
    required this.tradition,
    required this.current,
    required this.onTradition,
    required this.onAbout,
    required this.onNotes,
  });

  final List<_BookInfo> order;
  final String tradition;
  final VerseRef current;
  final Future<List<_BookInfo>> Function(String tradition) onTradition;
  final VoidCallback onAbout;
  final VoidCallback onNotes;

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
          key: bookPickerKey,
          controller: controller,
          padding: const EdgeInsets.all(16),
          children: [
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'protestant', label: Text('Protestant')),
                ButtonSegment(value: 'catholic', label: Text('Catholic')),
                ButtonSegment(value: 'tanakh', label: Text('Tanakh')),
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
            const Divider(height: 24),
            ListTile(
              leading: const Icon(Icons.bookmarks_outlined),
              title: const Text('Bookmarks & notes'),
              onTap: () {
                Navigator.pop(context);
                widget.onNotes();
              },
            ),
            ListTile(
              leading: const Icon(Icons.info_outline),
              title: const Text('About the texts'),
              subtitle: const Text('Sources, licenses and notices'),
              onTap: () {
                Navigator.pop(context);
                widget.onAbout();
              },
            ),
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

class _TranslationChips extends StatelessWidget {
  const _TranslationChips({
    required this.translations,
    required this.present,
    required this.hidden,
    required this.onToggle,
  });

  final List<Translation> translations;
  final Set<String> present;
  final Set<String> hidden;
  final ValueChanged<String> onToggle;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      child: Row(
        children: [
          for (final t in translations) ...[
            FilterChip(
              label: Text(t.abbreviation),
              selected: present.contains(t.id) && !hidden.contains(t.id),
              onSelected: present.contains(t.id) ? (_) => onToggle(t.id) : null,
            ),
            const SizedBox(width: 6),
          ],
        ],
      ),
    );
  }
}

/// Phone layout: one scroll, verse by verse, each translation's text under
/// the verse number. Hebrew rows switch direction individually. When a verse
/// is highlighted (after a search) the list scrolls to it once.
class _InterleavedView extends StatefulWidget {
  const _InterleavedView({
    required this.translations,
    required this.verses,
    required this.onTap,
    this.highlight,
  });

  final List<Translation> translations;
  final Map<String, List<ChapterVersesResult>> verses;
  final ValueChanged<int> onTap;
  final int? highlight;

  @override
  State<_InterleavedView> createState() => _InterleavedViewState();
}

class _InterleavedViewState extends State<_InterleavedView> {
  final _controller = ScrollController();
  final _target = GlobalKey();
  int? _scrolledTo;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  /// Rows are lazy and uneven: jump to the proportional offset so the row
  /// gets built, then let the framework line it up on the next frame.
  void _scrollTo(int index, int count) {
    if (_scrolledTo == widget.highlight) return;
    _scrolledTo = widget.highlight;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_controller.hasClients || count == 0) return;
      final max = _controller.position.maxScrollExtent;
      _controller.jumpTo((max * index / count).clamp(0.0, max).toDouble());
      WidgetsBinding.instance.addPostFrameCallback((_) {
        final ctx = _target.currentContext;
        if (ctx != null) Scrollable.ensureVisible(ctx, alignment: 0.1);
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final byVerse = <int, Map<String, ChapterVersesResult>>{};
    for (final t in widget.translations) {
      for (final v in widget.verses[t.id] ?? const <ChapterVersesResult>[]) {
        byVerse.putIfAbsent(v.verseId, () => {})[t.id] = v;
      }
    }
    final ids = byVerse.keys.toList()..sort();
    final highlight = widget.highlight;
    final index = highlight == null ? -1 : ids.indexOf(highlight);
    if (index >= 0) _scrollTo(index, ids.length);
    return ListView.builder(
      controller: _controller,
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
      itemCount: ids.length,
      itemBuilder: (context, i) {
        final id = ids[i];
        final ref = VerseRef.fromId(id);
        final rows = byVerse[id]!;
        final marked = id == highlight;
        return InkWell(
          key: marked ? _target : null,
          onTap: () => widget.onTap(id),
          child: Container(
            color: marked ? theme.colorScheme.secondaryContainer : null,
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  ref.verse == 0 ? 'Title' : '${ref.verse}',
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: theme.colorScheme.primary,
                  ),
                ),
                for (final t in widget.translations)
                  if (rows[t.id] != null)
                    _VerseText(translation: t, verse: rows[t.id]!),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _VerseText extends StatelessWidget {
  const _VerseText({required this.translation, required this.verse});

  final Translation translation;
  final ChapterVersesResult verse;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final rtl = translation.direction == 'rtl';
    final native = verse.nativeRef;
    final label = native == null
        ? translation.abbreviation
        : '${translation.abbreviation} $native';
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Directionality(
        textDirection: rtl ? TextDirection.rtl : TextDirection.ltr,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: theme.textTheme.labelSmall),
            Text(
              verse.body,
              style: rtl
                  ? theme.textTheme.titleMedium?.copyWith(height: 1.6)
                  : theme.textTheme.bodyLarge,
            ),
          ],
        ),
      ),
    );
  }
}

class _TranslationColumn extends StatelessWidget {
  const _TranslationColumn({
    required this.translation,
    required this.verses,
    required this.onTap,
    this.highlight,
  });

  final Translation translation;
  final List<ChapterVersesResult> verses;
  final ValueChanged<int> onTap;
  final int? highlight;

  /// Verse number (or "Title" for verse 0, as the phone layout says), plus
  /// the translation's own number when it differs.
  static String _label(ChapterVersesResult v) {
    final n = VerseRef.fromId(v.verseId).verse;
    final label = n == 0 ? 'Title' : '$n';
    final native = v.nativeRef;
    return native == null ? '$label ' : '$label ($native) ';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final rtl = translation.direction == 'rtl';
    // Hebrew with vowel points reads better a little larger.
    final body = rtl
        ? theme.textTheme.titleMedium?.copyWith(height: 1.6)
        : theme.textTheme.bodyLarge;
    return Directionality(
      textDirection: rtl ? TextDirection.rtl : TextDirection.ltr,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(translation.abbreviation, style: theme.textTheme.labelLarge),
          const SizedBox(height: 8),
          if (verses.isEmpty)
            Text('Not in this translation.', style: theme.textTheme.bodySmall),
          for (final v in verses)
            InkWell(
              onTap: () => onTap(v.verseId),
              child: Container(
                color: v.verseId == highlight
                    ? theme.colorScheme.secondaryContainer
                    : null,
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
                  style: body,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// One commentary entry: attribution, heading, and a body that opens
/// collapsed to its first paragraph. Henry's sections run to thousands of
/// words; showing all of them at once buries the other readings.
class _ReadingEntry extends StatefulWidget {
  const _ReadingEntry({required this.reading, required this.narrator});

  final ReadingsForVerseResult reading;
  final Narrator narrator;

  @override
  State<_ReadingEntry> createState() => _ReadingEntryState();
}

class _ReadingEntryState extends State<_ReadingEntry> {
  var _expanded = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final r = widget.reading;
    final preview = firstParagraph(r.body);
    final truncated = preview.length < r.body.length;
    final shown = _expanded || !truncated ? r.body : preview;
    final parts = [r.author, if (r.citation != null) r.citation!];
    final label = parts.join(' \u00b7 ');
    return Padding(
      padding: const EdgeInsets.only(top: 6, bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(label, style: theme.textTheme.labelMedium),
              ),
              _ListenButton(
                narrator: widget.narrator,
                title: label,
                body: r.body,
              ),
            ],
          ),
          if (r.heading != null)
            Text(r.heading!, style: theme.textTheme.labelLarge),
          Text.rich(
            TextSpan(
              children: markdownSpans(shown, theme.textTheme.bodyMedium),
            ),
          ),
          if (truncated)
            TextButton(
              onPressed: () => setState(() => _expanded = !_expanded),
              child: Text(_expanded ? 'Show less' : 'Show more'),
            ),
        ],
      ),
    );
  }
}

/// Reads one reading aloud, paragraph by paragraph; a stop button while
/// that reading is the one being read.
class _ListenButton extends StatelessWidget {
  const _ListenButton({
    required this.narrator,
    required this.title,
    required this.body,
  });

  final Narrator narrator;
  final String title;
  final String body;

  List<NarratorChunk> _chunks() {
    final plain = body.replaceAll('*', '');
    return [
      for (final p in plain.split(RegExp(r'\n\s*\n')))
        if (p.trim().isNotEmpty) NarratorChunk(p.trim()),
    ];
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: narrator,
      builder: (context, _) {
        final mine = narrator.active && narrator.title == title;
        return IconButton(
          icon: Icon(mine ? Icons.stop : Icons.headphones),
          tooltip: mine ? 'Stop' : 'Listen to this reading',
          visualDensity: VisualDensity.compact,
          onPressed: () {
            if (mine) {
              narrator.stop();
            } else {
              narrator.read(title, _chunks());
            }
          },
        );
      },
    );
  }
}

class _ReadingsSheet extends StatefulWidget {
  const _ReadingsSheet({
    required this.db,
    required this.user,
    required this.narrator,
    required this.verse,
    required this.controller,
  });

  final ContentDb db;
  final UserDb user;
  final Narrator narrator;
  final VerseRef verse;
  final ScrollController controller;

  @override
  State<_ReadingsSheet> createState() => _ReadingsSheetState();
}

class _SheetData {
  const _SheetData(
    this.perspectives,
    this.readings,
    this.notes,
    this.marked,
    this.userError,
  );

  final List<Perspective> perspectives;
  final List<ReadingsForVerseResult> readings;
  final List<Note> notes;
  final bool marked;

  /// Why notes and bookmarks are unavailable, if they are. The readings
  /// never wait on the user database: it is optional here.
  final String? userError;
}

/// How long the readings sheet waits for the user database before showing
/// the readings without notes.
const _userDbTimeout = Duration(seconds: 4);

class _ReadingsSheetState extends State<_ReadingsSheet> {
  late Future<_SheetData> _data = _load();

  Future<_SheetData> _load() async {
    final id = widget.verse.id;
    final perspectives = await widget.db.allPerspectives().get();
    final readings = await widget.db.readingsForVerse(id).get();
    var notes = const <Note>[];
    var marked = false;
    String? userError;
    try {
      notes = await widget.user.notesForVerse(id).get().timeout(_userDbTimeout);
      final mark = await widget.user
          .bookmarkForVerse(id)
          .getSingleOrNull()
          .timeout(_userDbTimeout);
      marked = mark != null;
    } catch (e) {
      userError = '$e';
      debugPrint('user database unavailable: $e');
    }
    return _SheetData(perspectives, readings, notes, marked, userError);
  }

  // A block, not an arrow: an arrow would return the Future from _load(),
  // which setState rejects in debug builds (the integration test's first
  // run, 2026-09-15).
  void _refresh() {
    setState(() {
      _data = _load();
    });
  }

  Future<void> _guard(Future<void> Function() action) async {
    try {
      await action().timeout(_userDbTimeout);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not save: $e')),
      );
    }
    _refresh();
  }

  Future<void> _toggleBookmark() =>
      _guard(() => widget.user.toggleBookmark(widget.verse.id));

  Future<void> _addNote() async {
    final text = await noteDialog(context);
    if (text == null || text.isEmpty) return;
    await _guard(() => widget.user.addNote(widget.verse.id, text));
  }

  Future<void> _editNote(Note note) async {
    final text = await noteDialog(context, initial: note.body);
    if (text == null) return;
    if (text.isEmpty) {
      await _guard(() => widget.user.deleteNote(note.id));
    } else {
      await _guard(() => widget.user.updateNote(note.id, text));
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return FutureBuilder<_SheetData>(
      future: _data,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return ListView(
            controller: widget.controller,
            padding: const EdgeInsets.all(16),
            children: [
              Text(widget.verse.label, style: theme.textTheme.titleLarge),
              const SizedBox(height: 12),
              Text('Could not load readings: ${snapshot.error}'),
            ],
          );
        }
        final data = snapshot.data;
        if (data == null) {
          return const Center(child: CircularProgressIndicator());
        }
        final grouped = <String, List<ReadingsForVerseResult>>{};
        for (final r in data.readings) {
          grouped.putIfAbsent(r.perspectiveId, () => []).add(r);
        }
        return ListView(
          key: readingsSheetKey,
          controller: widget.controller,
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 32),
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    widget.verse.label,
                    style: theme.textTheme.titleLarge,
                  ),
                ),
                IconButton(
                  icon: Icon(
                    data.marked ? Icons.bookmark : Icons.bookmark_border,
                  ),
                  tooltip: data.marked ? 'Remove bookmark' : 'Bookmark',
                  onPressed: _toggleBookmark,
                ),
                IconButton(
                  icon: const Icon(Icons.note_add_outlined),
                  tooltip: 'Add a note',
                  onPressed: _addNote,
                ),
              ],
            ),
            if (data.userError != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(
                  'Notes and bookmarks unavailable: ${data.userError}',
                  style: theme.textTheme.bodySmall,
                ),
              ),
            if (data.notes.isNotEmpty) ...[
              Text('Your notes', style: theme.textTheme.titleMedium),
              for (final n in data.notes)
                InkWell(
                  onTap: () => _editNote(n),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    child: Text(n.body, style: theme.textTheme.bodyMedium),
                  ),
                ),
              const SizedBox(height: 8),
            ],
            const SizedBox(height: 4),
            // "3 of 7 available" is the normal case: every perspective is
            // listed, and absent ones say so instead of disappearing.
            for (final p in data.perspectives) ...[
              Text(p.name, style: theme.textTheme.titleMedium),
              for (final r in grouped[p.id] ?? const [])
                _ReadingEntry(reading: r, narrator: widget.narrator),
              if (grouped[p.id] == null)
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
