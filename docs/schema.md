# Content database

Defined once in `packages/sr_data/lib/src/schema/content.drift` (plain SQL).

| Table | Purpose |
|-------|---------|
| `meta` | `content_version`, `schema_version`, `built_at`, `sources` |
| `books` | 66-book canon, ids 1..66 |
| `translations` / `verses` | One row per verse per translation; `verse_id` is canonical (ADR 0003) |
| `perspectives` | The seven readings, in display order |
| `sources` | One row per commentary source with license + status |
| `commentary_entries` | Range-anchored commentary, Markdown body |
| `parallels` | Bible range -> external reference (e.g. Quran) |
| `versification_map` | Non-canonical numbering -> canonical id |
| `commentary_fts`, `verses_fts` | FTS5 external-content indexes (pipeline-only) |

`PRAGMA user_version` is stamped to the schema version so drift never tries to
create or migrate the prebuilt file.

Typed queries the app uses are in `content_queries.drift`; search goes through
`ContentDb.searchCommentary` / `searchVerses`.
