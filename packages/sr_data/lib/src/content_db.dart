import 'package:drift/drift.dart';

part 'content_db.g.dart';

/// The prebuilt, read-only content database.
///
/// Built by the pipeline; opened from a copied asset (see `open/`). Runtime
/// creation or migration is a bug, so both paths throw.
@DriftDatabase(
  include: {'schema/content.drift', 'schema/content_queries.drift'},
)
class ContentDb extends _$ContentDb {
  ContentDb(super.executor);

  /// Must equal the `PRAGMA user_version` the pipeline stamps into the file.
  static const int contentSchemaVersion = 4;

  @override
  int get schemaVersion => contentSchemaVersion;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onCreate: (_) async {
          throw StateError(
            'The content database is prebuilt by the pipeline; '
            'it must never be created at runtime.',
          );
        },
        onUpgrade: (_, from, to) async {
          throw StateError(
            'Content schema mismatch ($from -> $to). Rebuild content.',
          );
        },
      );

  /// Turns free text into an FTS5 MATCH expression that cannot fail to
  /// parse: each whitespace-separated term becomes a quoted phrase, so
  /// `AND`, `NOT`, quotes and operators are matched literally rather than
  /// interpreted, and the last term matches as a prefix so results appear
  /// while typing. Returns an empty string when there is nothing to search.
  static String ftsQuery(String raw) {
    final terms = raw
        .split(RegExp(r'\s+'))
        .map((t) => t.replaceAll('"', ''))
        .where((t) => t.isNotEmpty)
        .toList();
    if (terms.isEmpty) return '';
    final quoted = [for (final t in terms) '"$t"'];
    quoted[quoted.length - 1] = '${quoted.last}*';
    return quoted.join(' ');
  }

  /// Full-text search over commentary, optionally within one source. The
  /// FTS5 tables are built by the pipeline and are not part of the drift
  /// schema, hence a custom query. [query] must be FTS5 syntax; see
  /// [ftsQuery]. Matches in the snippet are wrapped in square brackets.
  Selectable<CommentarySearchHit> searchCommentary(
    String query, {
    String? sourceId,
    int limit = 50,
  }) {
    final filter = sourceId == null ? '' : 'AND ce.source_id = ? ';
    return customSelect(
      'SELECT ce.id, ce.source_id, ce.start_verse_id, ce.end_verse_id, '
      'ce.heading, snippet(commentary_fts, 1, \'[\', \']\', \'\u2026\', 14) '
      'AS snippet '
      'FROM commentary_fts '
      'JOIN commentary_entries ce ON ce.id = commentary_fts.rowid '
      'WHERE commentary_fts MATCH ? $filter'
      'ORDER BY rank LIMIT ?',
      variables: [
        Variable.withString(query),
        if (sourceId != null) Variable.withString(sourceId),
        Variable.withInt(limit),
      ],
      readsFrom: {commentaryEntries},
    ).map(
      (row) => CommentarySearchHit(
        entryId: row.read<int>('id'),
        sourceId: row.read<String>('source_id'),
        startVerseId: row.read<int>('start_verse_id'),
        endVerseId: row.read<int>('end_verse_id'),
        heading: row.readNullable<String>('heading'),
        snippet: row.read<String>('snippet'),
      ),
    );
  }

  /// Full-text search over verse text, optionally within one translation.
  /// [query] must be FTS5 syntax; see [ftsQuery].
  Selectable<VerseSearchHit> searchVerses(
    String query, {
    String? translationId,
    int limit = 50,
  }) {
    final filter = translationId == null ? '' : 'AND v.translation_id = ? ';
    return customSelect(
      'SELECT v.translation_id, v.verse_id, '
      'snippet(verses_fts, 0, \'[\', \']\', \'\u2026\', 14) AS snippet '
      'FROM verses_fts JOIN verses v ON v.id = verses_fts.rowid '
      'WHERE verses_fts MATCH ? $filter'
      'ORDER BY rank LIMIT ?',
      variables: [
        Variable.withString(query),
        if (translationId != null) Variable.withString(translationId),
        Variable.withInt(limit),
      ],
      readsFrom: {verses},
    ).map(
      (row) => VerseSearchHit(
        translationId: row.read<String>('translation_id'),
        verseId: row.read<int>('verse_id'),
        snippet: row.read<String>('snippet'),
      ),
    );
  }
}

class CommentarySearchHit {
  const CommentarySearchHit({
    required this.entryId,
    required this.sourceId,
    required this.startVerseId,
    required this.endVerseId,
    required this.heading,
    required this.snippet,
  });

  final int entryId;
  final String sourceId;
  final int startVerseId;
  final int endVerseId;
  final String? heading;
  final String snippet;
}

class VerseSearchHit {
  const VerseSearchHit({
    required this.translationId,
    required this.verseId,
    required this.snippet,
  });

  final String translationId;
  final int verseId;
  final String snippet;
}
