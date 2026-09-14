# ADR 0004: Bundle all content in the binary

**Status:** accepted

## Context
Options were: bundle everything; bundle a core and offer downloadable packs
(still offline after download); vary by platform.

## Decision
Bundle everything. One artifact, one code path, no pack manager, no
partial-install states. The app is complete on first launch with no network,
which is the product's defining property.

## Consequences
- Binary size is 100-200 MB across the board.
- Android: Google Play caps the AAB download at 200 MB. If the content grows
  past that, move `sevenreadings.sqlite` into an install-time Play Asset
  Delivery pack (still bundled, still offline; only packaging changes).
- Web: first load fetches the whole database once, then persists it in OPFS.
  Acceptable for a study tool; document it on the landing page. Serve the
  asset with long cache headers and gzip/brotli.
- Desktop: no constraint.
- First launch on native copies the asset out of the bundle once per content
  version (a few seconds); the app shows a spinner.
