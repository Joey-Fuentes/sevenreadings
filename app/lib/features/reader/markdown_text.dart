import 'package:flutter/material.dart';

/// The subset of Markdown the pipeline emits: `*italic*`, `**bold**`, and
/// paragraphs separated by blank lines. Deliberately no dependency; the
/// commentary bodies never use anything else.
List<InlineSpan> markdownSpans(String text, TextStyle? base) {
  final spans = <InlineSpan>[];
  final paragraphs = text.split(RegExp(r'\n\s*\n'));
  for (var p = 0; p < paragraphs.length; p++) {
    if (p > 0) spans.add(const TextSpan(text: '\n\n'));
    spans.addAll(_inline(paragraphs[p].trim(), base));
  }
  return spans;
}

List<InlineSpan> _inline(String text, TextStyle? base) {
  final out = <InlineSpan>[];
  final buffer = StringBuffer();
  var bold = false;
  var italic = false;

  void flush() {
    if (buffer.isEmpty) return;
    out.add(
      TextSpan(
        text: buffer.toString(),
        style: (base ?? const TextStyle()).copyWith(
          fontWeight: bold ? FontWeight.w600 : null,
          fontStyle: italic ? FontStyle.italic : null,
        ),
      ),
    );
    buffer.clear();
  }

  var i = 0;
  while (i < text.length) {
    if (text.startsWith('**', i)) {
      flush();
      bold = !bold;
      i += 2;
    } else if (text[i] == '*') {
      flush();
      italic = !italic;
      i += 1;
    } else {
      buffer.write(text[i]);
      i += 1;
    }
  }
  flush();
  return out;
}

/// First paragraph of a Markdown body, for collapsed previews.
String firstParagraph(String text) {
  final idx = text.indexOf(RegExp(r'\n\s*\n'));
  return idx < 0 ? text : text.substring(0, idx);
}
