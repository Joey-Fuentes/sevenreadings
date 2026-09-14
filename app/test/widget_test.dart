// Exists so `flutter create` never generates the default counter-app test,
// which references a MyApp that does not exist here.
import 'package:flutter_test/flutter_test.dart';
import 'package:sevenreadings/content/content_loader.dart';

void main() {
  test('manifest parses', () {
    final m = ContentManifest.fromJson({
      'version': '0.1.0',
      'built_at': '2026-09-14T00:00:00+00:00',
    });
    expect(m.version, '0.1.0');
    expect(m.builtAt, '2026-09-14T00:00:00+00:00');
  });

  test('manifest tolerates a missing built_at', () {
    expect(ContentManifest.fromJson({'version': 'x'}).builtAt, '');
  });
}
