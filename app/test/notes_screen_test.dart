import 'package:flutter_test/flutter_test.dart';
import 'package:sevenreadings/features/notes/notes_screen.dart';

void main() {
  test('first line of a note', () {
    expect(firstLine('\n\n  Remember this.\nMore.'), 'Remember this.');
    expect(firstLine('single'), 'single');
    expect(firstLine('   '), '');
  });
}
