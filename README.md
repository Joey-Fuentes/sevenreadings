# sevenreadings

Offline, local-only Scripture study across seven readings: Bible text in
English, Hebrew and Greek read alongside Jewish literal, Jewish rationalist,
Catholic, Orthodox, Protestant, Islamic and secular-academic commentary.

Flutter/Dart. Targets Android, iOS, macOS, Windows, Linux, Web.
Live web build: https://sevenreadings.org/ (sevenreadings.com redirects there);
installable, and offline after the first visit. Screenshots from every
target's checklist run: https://sevenreadings.org/screenshots/.

**Working on this project? Start with [`AGENTS.md`](AGENTS.md)** (handoff for
AI sessions and new contributors), [`docs/workflow.md`](docs/workflow.md)
(the day-to-day commands) and [`docs/plan.md`](docs/plan.md) (stores,
per-target testing, donations, local chat, narrator — as spikes).

## What's in it today

Bibles: Berean Standard Bible, World English Bible, WEB Catholic Edition
(deuterocanon), Douay-Rheims (Challoner), SBL Greek New Testament, Byzantine
Majority Text (Robinson-Pierpont 2018), Westminster Leningrad Codex (Hebrew),
Swete's Septuagint. Commentary: Matthew Henry (Protestant), Haydock
(Catholic), Chrysostom (Orthodox), Rashi and Ibn Ezra (Jewish, English
versions with open licenses only), the International Critical Commentary
(Academic; Internet Archive OCR, unproofread), and the Qur'an in
Pickthall's translation at the Bible passages it parallels (Islamic). All
public domain or CC BY / CC BY-SA; see `docs/licensing.md`. Ibn Kathir
remains a documented stub (`pipeline/sevenreadings_pipeline/sources/stubs.py`).

Reader: verse-by-verse on phones, side-by-side columns on wide screens,
translation toggles, book/chapter picker in Protestant, Catholic or Tanakh
order, right-to-left Hebrew, original-numbering labels where a source numbers
differently, readings sheet with collapsible entries, full-text search over
verses and readings, bookmarks and notes per verse, an "About the texts"
screen with every source's license and notice, a narrator that reads a
chapter or a reading with the system voice (not on Linux yet), and,
outside the app stores, a "Support this project" screen (Stripe; card,
Apple Pay, Google Pay).

## Layout

```
.github/            CI (ci.yml), full matrix builds (build.yml), content releases
                    (content.yml), app releases (release.yml), the emulator
                    checklist (screenshots.yml), offline tools (tools.yml)
app/                Flutter app. UI only; no parsing, no schema.
packages/sr_core/   Pure Dart: canon, verse references. No Flutter.
packages/sr_data/   Drift schema + typed queries + per-platform DB opener.
pipeline/           Python (uv). Ingests upstream sources → sevenreadings.sqlite
docs/               ADRs, licensing matrix, schema notes, workflow.
tools/              Small scripts used by CI and developers (web assets, the
                    checklist run on a device, the icon generator).
packaging/          The icon as SVG and PNGs; the Flatpak manifest, desktop file
                    and AppStream metainfo.
```

## How content works

Content is a **build artifact, not source**. Any push to `main` that touches
`pipeline/` or the content schema runs the `Content release` workflow, which
builds the SQLite file from the pinned upstreams, publishes it as a GitHub
Release (`content-v<date>-<sha>`), commits the new pin to `app/content.lock`,
and re-runs CI so the app is built and deployed with it. App builds download
the pinned release, verify its SHA-256, and bundle it under
`app/assets/content/`. Nothing large is ever committed, and nothing is manual.

The schema lives in exactly one place, `packages/sr_data/lib/src/schema/content.drift`.
It is plain SQL: drift generates the Dart layer from it and the pipeline
executes it verbatim. FTS5 indexes are added by the pipeline after loading.

Every source is renumbered at ingest to one canonical verse-id scheme
(ADR 0003); the build reports each verse that fails to line up with the
reference translation, per book, so numbering tables are corrected from data.

User data (notes, bookmarks, positions) lives in a separate database
(`user.drift`) so content updates never touch it.

## Setting up with a Flutter toolchain

```
# Flutter (stable), uv (https://docs.astral.sh/uv/)
make bootstrap                         # deps and codegen
make content-sample                    # tiny fixture DB, no network
make web-assets                        # web only: sqlite3.wasm + drift worker
cd app && flutter run
```

Real content: `make content VERSION=dev` (network; unpinned upstreams print
their checksum and stop). The maintainer's own setup is Termux without
Flutter, which is why CI does all Flutter work; see `docs/workflow.md`.

## Not done yet (deliberately)

- A tafsir beside the Qur'an entries: Ibn Kathir has no English text with a
  shippable license. The ICC has one volume; more are one `sources.toml`
  entry each. The Qur'an pairings are a first selection.
- Reading positions and settings (schema exists in `UserDb`).
- Septuagint reorder tables for Exodus 36-40 and Proverbs 24-31.
- Every target builds in CI; Android and Web have been run by a person, and
  the first-launch checklist runs on an Android emulator in CI
  (`app/integration_test/`, `screenshots.yml`). Signing (Android release
  key, Apple Developer ID and notarization, iOS provisioning) and a first
  launch on the other platforms are open. Per-target state: `AGENTS.md`,
  "Targets".

## Decisions

See `docs/adr/`. In short: content as artifact; drift + sqlite3 on all six
targets; one canonical verse-id encoding with range-anchored commentary and
ingest-time renumbering; everything bundled in the binary.

## License

Application code: MIT (see `LICENSE`). Bundled texts carry their own licenses,
recorded per source in `pipeline/sources.toml` and `docs/licensing.md`.
