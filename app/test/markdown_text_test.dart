import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sevenreadings/features/reader/markdown_text.dart';

String _plain(List<InlineSpan> spans) =>
    spans.map((s) => (s as TextSpan).text ?? '').join();

void main() {
  test('asterisks become italic and bold spans, not text', () {
    final spans = markdownSpans(
      'the *heaven and the earth,* **all** good',
      null,
    );
    expect(_plain(spans), 'the heaven and the earth, all good');
    final italic = spans[1] as TextSpan;
    expect(italic.text, 'heaven and the earth,');
    expect(italic.style?.fontStyle, FontStyle.italic);
    final bold = spans[3] as TextSpan;
    expect(bold.text, 'all');
    expect(bold.style?.fontWeight, FontWeight.w600);
  });

  test('paragraphs are separated by a blank line', () {
    final spans = markdownSpans('one\n\ntwo', null);
    expect(_plain(spans), 'one\n\ntwo');
  });

  test('first paragraph preview', () {
    expect(firstParagraph('one\n\ntwo\n\nthree'), 'one');
    expect(firstParagraph('only'), 'only');
  });
}
