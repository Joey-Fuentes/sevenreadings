import 'dart:io';

import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sr_core/sr_core.dart';
import 'package:sr_data/sr_data.dart';

/// Builds a content database in memory exactly the way the pipeline does
/// (execute content.drift verbatim, stamp user_version), then exercises the
/// generated queries. Guards against drift-only syntax creeping into the
/// shared schema file.
void main() {
  late ContentDb db;

  setUp(() async {
    final schema = File('lib/src/schema/content.drift').readAsStringSync();
    final executor = NativeDatabase.memory(
      setup: (raw) {
        raw.execute(schema);
        raw.execute('PRAGMA user_version = ${ContentDb.contentSchemaVersion}');
        raw.execute(
          "INSERT INTO translations VALUES ('web','World English Bible',"
          "'WEB','en','Public domain','https://ebible.org','test')",
        );
        raw.execute(
          "INSERT INTO perspectives VALUES ('protestant',5,"
          "'Protestant / Reformed','Christianity')",
        );
        raw.execute(
          "INSERT INTO sources VALUES ('sample','protestant','Test',"
          "'Test source','Public domain','clear','https://example','test')",
        );
        for (var v = 1; v <= 3; v++) {
          raw.execute(
            'INSERT INTO verses (translation_id, verse_id, body) '
            "VALUES ('web', ${VerseRef(1, 1, v).id}, 'Verse $v')",
          );
        }
        raw.execute(
          'INSERT INTO commentary_entries '
          '(source_id, start_verse_id, end_verse_id, body) VALUES '
          "('sample', ${const VerseRef(1, 1, 0).id}, "
          "${const VerseRef(1, 1, 999).id}, 'Whole chapter'), "
          "('sample', ${const VerseRef(1, 1, 2).id}, "
          "${const VerseRef(1, 1, 3).id}, 'Verses 2-3')",
        );
      },
    );
    db = ContentDb(executor);
  });

  tearDown(() => db.close());

  test('chapter verses come back in order', () async {
    const ref = VerseRef(1, 1, 1);
    final verses = await db
        .chapterVerses('web', ref.chapterStart.id, ref.chapterEnd.id)
        .get();
    expect(verses.map((v) => v.body), ['Verse 1', 'Verse 2', 'Verse 3']);
  });

  test('range-anchored readings resolve per verse', () async {
    final v1 = await db.readingsForVerse(const VerseRef(1, 1, 1).id).get();
    final v2 = await db.readingsForVerse(const VerseRef(1, 1, 2).id).get();
    expect(v1.map((r) => r.body), ['Whole chapter']);
    expect(v2.map((r) => r.body), ['Verses 2-3', 'Whole chapter']);
    expect(v2.first.perspectiveName, 'Protestant / Reformed');
  });

  test('nothing anchored in another chapter', () async {
    final none = await db.readingsForVerse(const VerseRef(1, 2, 1).id).get();
    expect(none, isEmpty);
  });
}
