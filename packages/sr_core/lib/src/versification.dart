/// Versification schemes the content database can map from.
///
/// Every verse id in the database is canonical (English/Protestant). Sources
/// that number verses differently (Rashi and Ibn Ezra follow the Masoretic
/// text; e.g. Psalm superscriptions count as verse 1, Joel has four chapters,
/// Malachi three) are normalised by the pipeline through the
/// `versification_map` table. This enum names those schemes.
enum VersificationScheme {
  /// Canonical: English/Protestant numbering used by BSB and WEB.
  canonical('canonical'),

  /// Masoretic text numbering (Tanakh).
  masoretic('mt'),

  /// Septuagint numbering.
  septuagint('lxx'),

  /// Vulgate numbering (Haydock quotes Douay-Rheims).
  vulgate('vul');

  const VersificationScheme(this.code);

  /// Code stored in `versification_map.scheme`.
  final String code;
}
