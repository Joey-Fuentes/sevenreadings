# ADR 0001: Content is a build artifact, not source

**Status:** accepted

## Context
The app bundles two Bibles and seven commentaries: 100-200 MB of text once
indexed. Upstream sources are heterogeneous (USFM, Sefaria JSON, HTML dumps,
OCR) and have their own release cadence and licensing. Committing parsed text
to git would bloat the repo permanently and tie content changes to app commits.

## Decision
A Python pipeline (`pipeline/`) turns pinned upstream sources into one SQLite
file. The `Content release` workflow publishes it as a GitHub Release
(`content-v<semver>`), with a manifest and checksums. `app/content.lock` pins
the version the app bundles; CI downloads and verifies it before building.
Upstream pins (URL + SHA-256, or repo + commit) live in `pipeline/sources.toml`.

## Consequences
- Repo stays small; content and app version independently.
- Every app build is reproducible against a specific content version.
- Content builds need network; app builds need only the release asset.
- CI smoke builds use a fixture-only `--sample` database so PRs never depend
  on upstream availability.
