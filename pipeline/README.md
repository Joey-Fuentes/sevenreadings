# Content pipeline

```
uv sync
uv run srp sources                                   # list sources and license status
uv run srp lock <source>                             # print SHA-256 of each pinned upstream file
uv run srp build --version dev --only web,<source> --out dist/sevenreadings.sqlite
uv run srp build --sample --version 0.0.0-sample --out dist/sample.sqlite   # fixtures only, no network
uv run srp probe --db dist/sevenreadings.sqlite --translation lxx --books Exod,Ps
uv run pytest                                        # or: python tests/_run_without_pytest.py
```

Without uv (Termux): `pip install httpx` then `python -m sevenreadings_pipeline.cli …`.

## Structure

- `sources.toml` — one entry per source: `kind`, upstream (`url`, `urls`, or
  `repo`+`commit`), `sha256`, license and `license_status` (`clear` |
  `review` | `blocked`; blocked sources are skipped).
- `sevenreadings_pipeline/sources/` — one module per source kind:
  `usfm_bible` (eBible zips), `archive_bible` (GitHub archives: SBLGNT text,
  OSHB OSIS), `swete_lxx` (Swete token files), `ccel_mhc` (Matthew Henry),
  `jsonl_commentary` (generic normalised commentary), `stubs` (documented
  plans for the unwired commentaries).
- `refs.py` — canon (books 1-75), verse-id encoding, reference parsing, book
  orders per tradition. Mirrors `packages/sr_core`.
- `versification.py` — Masoretic and Septuagint renumbering to canonical ids,
  psalm-title offsets derived from data, and `check_alignment` which the build
  reports per book.
- `deuterocanon.py` — Greek Daniel/Esther and Letter of Jeremiah handling for
  Catholic-canon editions.
- `db.py` — creates the database from `packages/sr_data/lib/src/schema/content.drift`,
  loads rows, builds FTS (`sql/fts.sql`), writes `manifest.json`.
- `registry.py` — maps `kind` to a class; also defines the fixture sources used
  by `--sample` builds (CI smoke builds never touch the network).

## Adding a source

1. Confirm the upstream's format and license from the actual repository
   (ask for `gh api … contents` and a raw sample; don't guess).
2. Write a parser that yields `usfm.Verse` (Bibles) or `model.Entry`
   (commentary, inclusive verse-id range, Markdown body) records.
3. Add fixtures under `tests/fixtures/`, a test, and a fixture entry in
   `registry.SAMPLE_SOURCES`.
4. Add the `sources.toml` entry with `sha256 = "TODO"`; the maintainer runs
   `srp lock`, builds locally, reads the alignment report, then pushes. The
   content release, pin and deploy follow automatically.

## Reading the build output

- `N verses in M books` — sanity counts; English Bibles are ~31,200 verses,
  66 books (WEB Catholic 74 books, LXX 46).
- `skipped (not in canon)` — book codes the canon doesn't include.
- `X verses with no <ref> counterpart` / `Y <ref> OT verses with no <source>
  text`, per book — numbering left over or genuine textual differences.
  Consult `probe` before adding rules.
- `Psalm N: title verse inferred` — a psalm whose title is a separate verse
  in the source but whose verse count matched the English (Psalm 13).
- `stray chapter-boundary fragments reattached` — Swete digitisation glitch,
  repaired.
