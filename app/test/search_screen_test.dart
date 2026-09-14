import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sevenreadings/features/search/search_screen.dart';
import 'package:sr_core/sr_core.dart';

String _plain(List<InlineSpan> spans) =>
    spans.map((s) => (s as TextSpan).text ?? '').join();

void main() {
  test('snippet brackets become bold spans', () {
    final spans = snippetSpans('…the [word] was [God]…', null);
    expect(_plain(spans), '…the word was God…');
    final word = spans[1] as TextSpan;
    expect(word.text, 'word');
    expect(word.style?.fontWeight, FontWeight.w600);
    expect((spans[0] as TextSpan).style?.fontWeight, isNull);
  });

  test('snippets without markers pass through', () {
    expect(_plain(snippetSpans('plain text', null)), 'plain text');
    expect(_plain(snippetSpans('an [unclosed', null)), 'an [unclosed');
  });

  test('range labels', () {
    int id(int book, int chapter, int verse) =>
        VerseRef(book, chapter, verse).id;
    expect(rangeLabel(id(1, 1, 1), id(1, 1, 1)), 'Genesis 1:1');
    expect(rangeLabel(id(1, 1, 1), id(1, 1, 5)), 'Genesis 1:1-5');
    expect(rangeLabel(id(1, 1, 0), id(1, 1, 999)), 'Genesis 1');
    expect(rangeLabel(id(1, 1, 31), id(1, 2, 3)), 'Genesis 1:31-Genesis 2:3');
    expect(rangeLabel(id(19, 3, 0), id(19, 3, 0)), 'Psalms 3');
  });
}
