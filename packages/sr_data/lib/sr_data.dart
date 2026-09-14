/// Database layer for sevenreadings.
///
/// Two databases, deliberately separate:
///  * [ContentDb] - prebuilt, read-only, shipped as an asset, replaced
///    wholesale on content updates. Schema: `src/schema/content.drift`.
///  * [UserDb] - notes, bookmarks, positions. Created on device, migrated in
///    place. Schema: `src/schema/user.drift`.
library;

export 'src/content_db.dart';
export 'src/open/open.dart';
export 'src/user_db.dart';
