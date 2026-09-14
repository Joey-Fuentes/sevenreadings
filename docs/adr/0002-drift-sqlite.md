# ADR 0002: drift + sqlite3 on every platform

**Status:** accepted

## Context
Six targets, including web. The store must open a prebuilt file, do fast
range lookups, and offer full-text search, with no network.

## Decision
`drift` over `package:sqlite3` everywhere: native libraries come from
`package:sqlite3`'s own build hook (3.x), web via the sqlite3 WASM build with
OPFS/IndexedDB persistence. The schema is
a plain-SQL `.drift` file that drift compiles to typed Dart and the pipeline
executes verbatim, so there is exactly one schema definition. FTS5 provides
search; its virtual tables are created by the pipeline and accessed through
`customSelect`, keeping the drift schema portable.

Two databases: the read-only content DB (asset, copied once per content
version) and a user DB (notes, bookmarks, positions) created on device. A
content update never migrates user data.

## Alternatives rejected
- Isar / Hive: no equivalent to shipping a prebuilt file, weaker web story,
  no FTS.
- JSON assets in memory: 100+ MB heap on mobile, no indexing.
