import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sr_core/sr_core.dart';
import 'package:sr_data/sr_data.dart';

import '../support/support_screen.dart';

/// Where the reader should go after a result is tapped.
class SearchTarget {
  const SearchTarget(this.verseId, {required this.showReadings});

  final int verseId;

  /// True for commentary hits: open the readings sheet on arrival.
  final bool showReadings;
}

/// `Genesis 1:1`, `Genesis 1:1-5`, `Psalms 3` for a whole chapter, or
/// `Genesis 1:31-Genesis 2:3` across chapters.
String rangeLabel(int startId, int endId) {
  final start = VerseRef.fromId(startId);
  final end = VerseRef.fromId(endId);
  if (startId == endId || (start.verse == 0 && end.verse == 999)) {
    return start.label;
  }
  if (start.book == end.book && start.chapter == end.chapter) {
    return '${start.label}-${end.verse}';
  }
  return '${start.label}-${end.label}';
}

/// FTS5 snippets mark matches as `[term]`; render those bold.
List<InlineSpan> snippetSpans(String snippet, TextStyle? base) {
  final bold = (base ?? const TextStyle()).copyWith(
    fontWeight: FontWeight.w600,
  );
  final spans = <InlineSpan>[];
  var i = 0;
  while (i < snippet.length) {
    final open = snippet.indexOf('[', i);
    if (open < 0) break;
    final close = snippet.indexOf(']', open);
    if (close < 0) break;
    if (open > i) spans.add(TextSpan(text: snippet.substring(i, open)));
    spans.add(TextSpan(text: snippet.substring(open + 1, close), style: bold));
    i = close + 1;
  }
  if (i < snippet.length) spans.add(TextSpan(text: snippet.substring(i)));
  return spans;
}

enum _Scope { verses, readings }

class _Filters {
  const _Filters(this.translations, this.sources);

  final List<Translation> translations;
  final List<Source> sources;

  Translation? translation(String id) {
    for (final t in translations) {
      if (t.id == id) return t;
    }
    return null;
  }

  Source? source(String id) {
    for (final s in sources) {
      if (s.id == id) return s;
    }
    return null;
  }
}

class _Results {
  const _Results({required this.verses, required this.readings});

  final List<VerseSearchHit> verses;
  final List<CommentarySearchHit> readings;

  int get length => verses.length + readings.length;
}

/// Full-text search over Bible text and commentary. Pops with a
/// [SearchTarget] when a result is tapped.
class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key, required this.db});

  final ContentDb db;

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _controller = TextEditingController();
  late final Future<_Filters> _filters = _loadFilters();
  Timer? _debounce;
  _Scope _scope = _Scope.verses;
  String? _translation; // null = every translation
  String? _source; // null = every reading
  Future<_Results>? _results;

  Future<_Filters> _loadFilters() async {
    final translations = await widget.db.allTranslations().get();
    final sources = await widget.db.allSources().get();
    return _Filters(translations, sources);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _onChanged(String text) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 250), () => _run(text));
  }

  void _run(String text) {
    _debounce?.cancel();
    final query = ContentDb.ftsQuery(text);
    setState(() {
      _results = query.isEmpty ? null : _search(query);
    });
  }

  Future<_Results> _search(String query) async {
    if (_scope == _Scope.verses) {
      final hits = await widget.db
          .searchVerses(query, translationId: _translation, limit: 100)
          .get();
      return _Results(verses: hits, readings: const []);
    }
    final hits = await widget.db
        .searchCommentary(query, sourceId: _source, limit: 100)
        .get();
    return _Results(verses: const [], readings: hits);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _controller,
          autofocus: true,
          textInputAction: TextInputAction.search,
          decoration: const InputDecoration(
            hintText: 'Search verses and readings',
            border: InputBorder.none,
          ),
          onChanged: _onChanged,
          onSubmitted: _run,
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.clear),
            tooltip: 'Clear',
            onPressed: () {
              _controller.clear();
              _run('');
            },
          ),
        ],
        bottom: SupportBar.ifShown,
      ),
      body: FutureBuilder<_Filters>(
        future: _filters,
        builder: (context, snapshot) {
          final filters = snapshot.data;
          if (filters == null) {
            return const Center(child: CircularProgressIndicator());
          }
          return Column(
            children: [
              _scopeBar(filters),
              Expanded(child: _resultList(filters)),
            ],
          );
        },
      ),
    );
  }

  Widget _scopeBar(_Filters filters) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      child: Row(
        children: [
          SegmentedButton<_Scope>(
            segments: const [
              ButtonSegment(value: _Scope.verses, label: Text('Verses')),
              ButtonSegment(value: _Scope.readings, label: Text('Readings')),
            ],
            selected: {_scope},
            onSelectionChanged: (s) {
              _scope = s.first;
              _run(_controller.text);
            },
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _scope == _Scope.verses
                ? _filterMenu(
                    value: _translation,
                    all: 'All translations',
                    items: {
                      for (final t in filters.translations)
                        t.id: t.abbreviation,
                    },
                    onChanged: (v) {
                      _translation = v;
                      _run(_controller.text);
                    },
                  )
                : _filterMenu(
                    value: _source,
                    all: 'All readings',
                    items: {for (final s in filters.sources) s.id: s.author},
                    onChanged: (v) {
                      _source = v;
                      _run(_controller.text);
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _filterMenu({
    required String? value,
    required String all,
    required Map<String, String> items,
    required ValueChanged<String?> onChanged,
  }) {
    return DropdownButton<String?>(
      value: value,
      isExpanded: true,
      items: [
        DropdownMenuItem<String?>(value: null, child: Text(all)),
        for (final e in items.entries)
          DropdownMenuItem<String?>(value: e.key, child: Text(e.value)),
      ],
      onChanged: onChanged,
    );
  }

  Widget _resultList(_Filters filters) {
    final theme = Theme.of(context);
    final future = _results;
    if (future == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            'Type to search. Greek and Hebrew match with their accents '
            'and points.',
            style: theme.textTheme.bodySmall,
            textAlign: TextAlign.center,
          ),
        ),
      );
    }
    return FutureBuilder<_Results>(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return Center(child: Text('${snapshot.error}'));
        }
        final data = snapshot.data;
        if (data == null) {
          return const Center(child: CircularProgressIndicator());
        }
        if (data.length == 0) {
          return Center(
            child: Text('Nothing found.', style: theme.textTheme.bodySmall),
          );
        }
        return ListView.builder(
          itemCount: data.length,
          itemBuilder: (context, i) => i < data.verses.length
              ? _verseTile(data.verses[i], filters)
              : _readingTile(data.readings[i - data.verses.length], filters),
        );
      },
    );
  }

  Widget _verseTile(VerseSearchHit hit, _Filters filters) {
    final theme = Theme.of(context);
    final ref = VerseRef.fromId(hit.verseId);
    final t = filters.translation(hit.translationId);
    final rtl = t?.direction == 'rtl';
    final title = '${ref.label} \u00b7 ${t?.abbreviation ?? hit.translationId}';
    return ListTile(
      title: Text(title),
      subtitle: Directionality(
        textDirection: rtl ? TextDirection.rtl : TextDirection.ltr,
        child: Text.rich(
          TextSpan(
            children: snippetSpans(hit.snippet, theme.textTheme.bodyMedium),
          ),
        ),
      ),
      onTap: () => Navigator.pop(
        context,
        SearchTarget(hit.verseId, showReadings: false),
      ),
    );
  }

  Widget _readingTile(CommentarySearchHit hit, _Filters filters) {
    final theme = Theme.of(context);
    final s = filters.source(hit.sourceId);
    final where = rangeLabel(hit.startVerseId, hit.endVerseId);
    final start = VerseRef.fromId(hit.startVerseId);
    // A whole-chapter note has no row of its own: land on verse 1, whose
    // readings include it. A title note (verse 0 only) keeps verse 0.
    final target = start.verse == 0 && hit.endVerseId != hit.startVerseId
        ? VerseRef(start.book, start.chapter, 1).id
        : hit.startVerseId;
    final snippet = hit.snippet.replaceAll('*', '');
    return ListTile(
      title: Text('${s?.author ?? hit.sourceId} \u00b7 $where'),
      subtitle: Text.rich(
        TextSpan(
          children: snippetSpans(snippet, theme.textTheme.bodyMedium),
        ),
      ),
      onTap: () => Navigator.pop(
        context,
        SearchTarget(target, showReadings: true),
      ),
    );
  }
}
