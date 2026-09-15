# Content pipeline

```
uv sync
uv run srp sources                                   # list sources and license status
uv run srp lock --write <source>                     # record the SHA-256 of the upstream file in sources.toml
uv run srp build --version dev --only web,<source> --out dist/sevenreadings.sqlite
uv run srp build --sample --version 0.0.0-sample --out dist/sample.sqlite   # fixtures only, no network
uv run srp probe --db dist/sevenreadings.sqlite --translation lxx --books Exod,Ps
uv run pytest                                        # or: python tests/_run_without_pytest.py
```

Without uv (Termux): `pip install httpx` then `python -m sevenreadings_pipeline.cli …`.
Termux has no `/tmp`; write scratch output under `~/scratch`, never `/tmp`.

## Structure

- `sources.toml` — one entry per source: `kind`, upstream (`url`, `urls`, or
  `repo`+`commit`), `sha256`, license and `license_status` (`clear` |
  `review` | `blocked`; blocked sources are skipped).
- `sevenreadings_pipeline/sources/` — one module per source kind:
  `usfm_bible` (eBible zips), `archive_bible` (GitHub archives: SBLGNT text,
  OSHB OSIS, Byzantine Majority Text CSV), `swete_lxx` (Swete token files),
  `haydock` (Haydock's commentary and the Douay-Rheims text from the same
  pages), `ccel_mhc` (Matthew Henry), `ccel_thml` (Chrysostom from CCEL's
  ThML volumes), `sefaria` (Rashi, Ibn Ezra from Sefaria's export, chosen by
  recorded license), `jsonl_commentary` (generic normalised commentary),
  `stubs` (documented plans for the unwired commentaries).
- `refs.py` — canon (books 1-75), verse-id encoding, reference parsing, book
  orders per tradition. Mirrors `packages/sr_core`.
- `versification.py` — Masoretic, Septuagint and Vulgate renumbering to
  canonical ids, psalm-title offsets derived from data, and `check_alignment`
  which the build reports per book. `apply_vul` can record where every source
  verse landed (`trace`), which is how Haydock's notes follow the Douay text.
- `deuterocanon.py` — Greek Daniel/Esther and Letter of Jeremiah handling for
  Catholic-canon editions.
- `db.py` — creates the database from `packages/sr_data/lib/src/schema/content.drift`,
  loads rows, builds FTS (`sql/fts.sql`), stores the built sources' notices
  in `meta`, writes `manifest.json`.
- `registry.py` — maps `kind` to a class; also defines the fixture sources used
  by `--sample` builds (CI smoke builds never touch the network).

## Adding a source

1. Confirm the upstream's format and license from the actual repository
   (ask for `gh api … contents` and a raw sample; don't guess).
2. Write a parser that yields `usfm.Verse` (Bibles) or `model.Entry`
   (commentary, inclusive verse-id range, Markdown body) records.
3. Add fixtures under `tests/fixtures/`, a test, and a fixture entry in
   `registry.SAMPLE_SOURCES`.
4. Write `sources/<id>/NOTICE.md`: the underlying text's status, the
   digitisation's license quoted with its URL, what we changed, and the
   attribution the license requires. The build ships it (`meta.notices`).
5. Add the `sources.toml` entry with `sha256 = "TODO"`; the maintainer runs
   `srp lock --write`, builds locally, reads the alignment report, then
   pushes (the loop is written out in `docs/workflow.md`). The content
   release, pin and deploy follow automatically.

## Reading the build output

- `N verses in M books` — sanity counts; English Bibles are ~31,200 verses,
  66 books (WEB Catholic 74 books, LXX 46, Douay 73, Byzantine NT 27).
- `skipped (not in canon)` — book codes the canon doesn't include.
- `X verses with no <ref> counterpart` / `Y <ref> OT verses with no <source>
  text`, per book — numbering left over or genuine textual differences.
  Consult `probe` before adding rules.
- `Psalm N: title verse inferred` — a psalm whose title is a separate verse
  in the source but whose verse count matched the English (Psalm 13).
- `index lists N pages; M archived pages not in the index were skipped` /
  `page titles disagree with the index` — Haydock: the site index is
  trusted; both lines are informational unless the numbers move.
- `rashi:   Gen: <version> [<license>] <n>` — Sefaria: the version chosen
  per book and its recorded license; `no English version with an allowed
  license` lists the books that got nothing.
- `Masoretic numbering mapped through the WLC's ingest` — the intended
  case; `by the Hebrew rule table only` means wlc was not in the build.
- `chapter pages without Ver. markers` / `chapter pages without Bible text`
  / `notes on verses missing from the Douay text` — Haydock pages the
  parser could not read fully; paste one raw page (see `docs/workflow.md`,
  "Inspecting an upstream") so the markup variant can be added.
- `stray chapter-boundary fragments reattached` — Swete digitisation glitch,
  repaired.
