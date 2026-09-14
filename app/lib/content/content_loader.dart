import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;
import 'package:sr_data/sr_data.dart';

const contentAssetKey = 'assets/content/sevenreadings.sqlite';
const manifestAssetKey = 'assets/content/manifest.json';

/// Written by the pipeline next to the SQLite file. Small enough to read
/// before deciding whether the on-device copy of the content is current.
class ContentManifest {
  const ContentManifest({required this.version, required this.builtAt});

  factory ContentManifest.fromJson(Map<String, dynamic> json) =>
      ContentManifest(
        version: json['version'] as String,
        builtAt: json['built_at'] as String? ?? '',
      );

  final String version;
  final String builtAt;
}

Future<ContentManifest> loadManifest() async {
  final raw = await rootBundle.loadString(manifestAssetKey);
  return ContentManifest.fromJson(jsonDecode(raw) as Map<String, dynamic>);
}

Future<ContentDb> loadContentDb() async {
  final manifest = await loadManifest();
  return openContentDb(
    assetKey: contentAssetKey,
    version: manifest.version,
  );
}
