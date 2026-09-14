# Content pipeline

```
uv sync
uv run srp sources                      # list sources and license status
uv run srp lock web                     # print SHA-256 of a pinned upstream
uv run srp build --version 0.1.0 --out dist/sevenreadings.sqlite
uv run srp build --sample --version 0.0.0-sample --out dist/sample.sqlite   # fixtures only, no network
uv run pytest
```

Every source is one module in `sevenreadings_pipeline/sources/` and one entry
in `sources.toml` (upstream, pin, checksum, license). Bibles parse USFM;
commentaries produce `Entry` records (source id, inclusive verse-id range,
heading, Markdown body, citation) and a shared loader writes them. Adding a
source means writing a parser that yields entries; nothing else changes.

Sources whose `license_status` is `blocked` are skipped. `review` is loaded
but flagged in the `sources` table so the app can surface it.

The schema is `packages/sr_data/lib/src/schema/content.drift`, executed
verbatim. FTS5 indexes come from `sevenreadings_pipeline/sql/fts.sql`.
