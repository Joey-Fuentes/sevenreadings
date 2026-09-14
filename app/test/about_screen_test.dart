import 'package:flutter_test/flutter_test.dart';
import 'package:sevenreadings/features/about/about_screen.dart';

void main() {
  test('notices split into headings and joined paragraphs', () {
    const notices = '# One (X)\n\nLine a\nline b.\n\nSee `sources.toml`.\n\n'
        '# Two\n\nPara.';
    final blocks = parseNotices(notices);
    expect(blocks.map((b) => b.isHeading).toList(), [
      true,
      false,
      false,
      true,
      false,
    ]);
    expect(blocks[0].text, 'One (X)');
    expect(blocks[1].text, 'Line a line b.');
    expect(blocks[2].text, 'See sources.toml.');
    expect(blocks[4].text, 'Para.');
  });

  test('empty notices give no blocks', () {
    expect(parseNotices(''), isEmpty);
    expect(parseNotices('\n\n  \n'), isEmpty);
  });
}
